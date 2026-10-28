// Copyright 2026 Intel Corporation. SPDX-License-Identifier: Apache-2.0
#include <gtest/gtest.h>
#include <stdexcept>
#include <string>
#include <variant>
#include <fstream>
#include <sstream>
#include "src/llm/io_processing/generation_config_builder.hpp"
#include "src/test/platform_utils.hpp"

namespace {
using Structured = ov::genai::StructuredOutputConfig;
ovms::OpenAIRequest lfmRequest(const std::string& choice) {
    ovms::OpenAIRequest request;
    request.toolChoice = choice;
    request.toolNameSchemaMap.emplace("cwd", ovms::ToolSchemaWrapper{nullptr,
        R"({"type":"object","properties":{},"additionalProperties":false})"});
    request.toolNameSchemaMap.emplace("write", ovms::ToolSchemaWrapper{nullptr,
        R"({"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"},"append":{"type":"boolean"}},"required":["path","content"],"additionalProperties":false})"});
    return request;
}
std::string grammar(ov::genai::GenerationConfig& config) {
    if (!config.structured_output_config || !config.structured_output_config->structural_tags_config)
        return {};
    auto* held = std::get_if<Structured::StructuralTag>(&*config.structured_output_config->structural_tags_config);
    if (!held) return {};
    auto* ebnf = std::get_if<Structured::EBNF>(held);
    return ebnf ? ebnf->value : std::string{};
}
}

TEST(LfmGenerationPolicy, RequiredInstallsNativeEnvelopeFromFirstToken) {
    ovms::GenerationConfigBuilder builder({}, "lfm2", false, ovms::STANDARD);
    builder.parseConfigFromRequest(lfmRequest("required"));
    EXPECT_TRUE(builder.requiresValidStructuredOutput());
    const auto text = grammar(builder.getConfig());
    EXPECT_NE(text.find("<|tool_call_start|>"), std::string::npos);
    EXPECT_NE(text.find("<|tool_call_end|>"), std::string::npos);
    EXPECT_NE(text.find("cwd"), std::string::npos);
    EXPECT_NE(text.find("write"), std::string::npos);
    EXPECT_EQ(text.find("<think>"), std::string::npos);
}
TEST(LfmGenerationPolicy, GuidedAutoProtectsThinkingAndConstrainsNativeCallsOnly) {
    ovms::GenerationConfigBuilder builder({}, "lfm2", true, ovms::STANDARD);
    auto request = lfmRequest("auto");
    request.toolNameSchemaMap["glob"].stringRepr = R"({"type":"object","properties":{"i":{"type":"string"},"path":{"type":"string"}},"required":["i"],"additionalProperties":false})";
    builder.parseConfigFromRequest(request);
    ASSERT_TRUE(builder.getConfig().structured_output_config.has_value());
    auto& cfg = *builder.getConfig().structured_output_config;
    ASSERT_TRUE(cfg.structural_tags_config.has_value());
    auto* held = std::get_if<Structured::StructuralTag>(&*cfg.structural_tags_config);
    ASSERT_NE(held, nullptr);
    auto* triggered = std::get_if<std::shared_ptr<Structured::TriggeredTags>>(held);
    ASSERT_NE(triggered, nullptr);
    EXPECT_FALSE((*triggered)->at_least_one);
    ASSERT_EQ((*triggered)->tags.size(), 2);
    EXPECT_EQ((*triggered)->tags[0].begin, "<think>");
    EXPECT_EQ((*triggered)->tags[0].end, "</think>");
    EXPECT_EQ((*triggered)->tags[1].begin, "<|tool_call_start|>");
    EXPECT_EQ((*triggered)->tags[1].end, "<|tool_call_end|>");
    auto* body = std::get_if<Structured::EBNF>(&(*triggered)->tags[1].content);
    ASSERT_NE(body, nullptr);
    EXPECT_NE(body->value.find("glob"), std::string::npos);
    EXPECT_EQ(body->value.find("execute"), std::string::npos);
    EXPECT_EQ(body->value.find("<|tool_call_start|>"), std::string::npos);
}
TEST(LfmGenerationPolicy, GuidedAutoCompilesRealOmpSchemasForBothTokenizers) {
#ifdef _WIN32
    const auto root = getWindowsRepoRootPath();
#else
    const std::string root = "/ovms";
#endif
    std::ifstream input(root + "/src/test/llm/output_parsers/fixtures/omp-lfm-tools.json");
    ASSERT_TRUE(input.good());
    std::stringstream buffer;
    buffer << input.rdbuf();
    rapidjson::Document schemas;
    ASSERT_FALSE(schemas.Parse(buffer.str().c_str()).HasParseError());
    for (const auto& family : {"LFM2-2.6B", "LFM2.5-8B-A1B"}) {
        auto request = lfmRequest("auto");
        request.toolNameSchemaMap.clear();
        for (auto it = schemas.MemberBegin(); it != schemas.MemberEnd(); ++it) {
            rapidjson::StringBuffer text;
            rapidjson::Writer<rapidjson::StringBuffer> writer(text);
            it->value.Accept(writer);
            request.toolNameSchemaMap.emplace(it->name.GetString(), ovms::ToolSchemaWrapper{nullptr, text.GetString()});
        }
        ov::genai::Tokenizer tokenizer(root + "/src/test/llm_testing/LiquidAI/" + family);
        ovms::GenerationConfigBuilder builder({}, "lfm2", true, ovms::STANDARD);
        ASSERT_NO_THROW(builder.parseConfigFromRequest(request));
        EXPECT_NO_THROW(builder.validateStructuredOutputConfig(tokenizer)) << family;
        builder.parseConfigFromRequest(lfmRequest("none"));
        EXPECT_FALSE(builder.getConfig().structured_output_config.has_value());
    }
}
TEST(LfmGenerationPolicy, NamedRestrictsGrammarAndParallelFalse) {
    auto request = lfmRequest("write");
    request.parallelToolCalls = false;
    ovms::GenerationConfigBuilder builder({}, "lfm2", true, ovms::STANDARD);
    builder.parseConfigFromRequest(request);
    EXPECT_TRUE(builder.requiresValidStructuredOutput());
    const auto text = grammar(builder.getConfig());
    EXPECT_NE(text.find("write"), std::string::npos);
    EXPECT_EQ(text.find("cwd"), std::string::npos);
    EXPECT_EQ(text.find("lfmcall (lfmws"), std::string::npos);
}
TEST(LfmGenerationPolicy, AutoRemainsUnconstrainedWithGuidanceDisabled) {
    for (const auto enabled : {false}) {
        ovms::GenerationConfigBuilder builder({}, "lfm2", enabled, ovms::STANDARD);
        builder.parseConfigFromRequest(lfmRequest("auto"));
        EXPECT_FALSE(builder.requiresValidStructuredOutput());
        EXPECT_FALSE(builder.getConfig().structured_output_config.has_value());
    }
}
TEST(LfmGenerationPolicy, NonePreservesResponseFormat) {
    auto request = lfmRequest("none");
    request.responseFormat = R"({"type":"json_object"})";
    ovms::GenerationConfigBuilder builder({}, "lfm2", true, ovms::STANDARD);
    builder.parseConfigFromRequest(request);
    EXPECT_FALSE(builder.requiresValidStructuredOutput());
    ASSERT_TRUE(builder.getConfig().structured_output_config.has_value());
    ASSERT_TRUE(builder.getConfig().structured_output_config->structural_tags_config.has_value());
    const auto& held = std::get<Structured::StructuralTag>(*builder.getConfig().structured_output_config->structural_tags_config);
    EXPECT_EQ(std::get<std::string>(held), *request.responseFormat);
}
TEST(LfmGenerationPolicy, InvalidHardChoicesAndConflictsFailClosed) {
    ovms::GenerationConfigBuilder builder({}, "lfm2", true, ovms::STANDARD);
    EXPECT_THROW(builder.parseConfigFromRequest(lfmRequest("missing")), std::invalid_argument);
    ovms::OpenAIRequest empty;
    empty.toolChoice = "required";
    EXPECT_THROW(builder.parseConfigFromRequest(empty), std::invalid_argument);
    auto request = lfmRequest("required");
    request.responseFormat = R"({"type":"json_object"})";
    EXPECT_THROW(builder.parseConfigFromRequest(request), std::invalid_argument);
}
TEST(LfmGenerationPolicy, UnsupportedSchemaConstraintFailsInsteadOfIgnoringIt) {
    auto request = lfmRequest("required");
    request.toolNameSchemaMap["write"].stringRepr = R"({"type":"object","properties":{"n":{"type":"integer","minimum":7}}})";
    ovms::GenerationConfigBuilder builder({}, "lfm2", true, ovms::STANDARD);
    EXPECT_THROW(builder.parseConfigFromRequest(request), std::invalid_argument);
}
TEST(LfmGenerationPolicy, NestedTypedOptionalAndZeroArgumentSchemas) {
    auto request = lfmRequest("required");
    request.toolNameSchemaMap["write"].stringRepr = R"({"type":"object","properties":{"payload":{"type":"object","properties":{"items":{"type":"array","items":{"type":"number"}},"enabled":{"type":"boolean"}},"required":["items"]},"note":{"type":["string","null"]}},"required":["payload"]})";
    ovms::GenerationConfigBuilder builder({}, "lfm2", true, ovms::STANDARD);
    EXPECT_NO_THROW(builder.parseConfigFromRequest(request));
    EXPECT_TRUE(builder.requiresValidStructuredOutput());
    EXPECT_FALSE(grammar(builder.getConfig()).empty());
}
TEST(LfmGenerationPolicy, HardGrammarCompilesWithBothRealTokenizers) {
#ifdef _WIN32
    const auto root = getWindowsRepoRootPath();
#else
    const std::string root = "/ovms";
#endif
    for (const auto& family : {"LFM2-2.6B", "LFM2.5-8B-A1B"}) {
        ov::genai::Tokenizer tokenizer(root + "/src/test/llm_testing/LiquidAI/" + family);
        ovms::GenerationConfigBuilder builder({}, "lfm2", true, ovms::STANDARD);
        builder.parseConfigFromRequest(lfmRequest("required"));
        EXPECT_NO_THROW(builder.validateStructuredOutputConfig(tokenizer)) << family;
    }
}
TEST(LfmGenerationPolicy, ReusingBuilderReplacesHardWithLazyAndDropsGrammarForNone) {
    ovms::GenerationConfigBuilder builder({}, "lfm2", true, ovms::STANDARD);
    builder.parseConfigFromRequest(lfmRequest("required"));
    ASSERT_TRUE(builder.requiresValidStructuredOutput());
    builder.parseConfigFromRequest(lfmRequest("auto"));
    EXPECT_TRUE(builder.requiresValidStructuredOutput());
    EXPECT_TRUE(builder.getConfig().structured_output_config.has_value());
    builder.parseConfigFromRequest(lfmRequest("required"));
    builder.parseConfigFromRequest(lfmRequest("none"));
    EXPECT_FALSE(builder.getConfig().structured_output_config.has_value());
}
TEST(LfmGenerationPolicy, HardSchemaProfileMatchesRetainer) {
    auto request = lfmRequest("required");
    request.toolNameSchemaMap["write"].stringRepr = R"({"type":"object","properties":{"content":{"type":"string","const":"hello"}},"required":["content"]})";
    ovms::GenerationConfigBuilder builder({}, "lfm2", true, ovms::STANDARD);
    EXPECT_THROW(builder.parseConfigFromRequest(request), std::invalid_argument);
}
TEST(LfmGenerationPolicy, HardToolNamesMatchNativeRetainerIdentifiers) {
    for (const auto& name : {"read-file", "functions.cwd", "1bad"}) {
        auto request = lfmRequest("required");
        request.toolNameSchemaMap.emplace(name, ovms::ToolSchemaWrapper{nullptr,
            R"({"type":"object","properties":{}})"});
        ovms::GenerationConfigBuilder builder({}, "lfm2", true, ovms::STANDARD);
        EXPECT_THROW(builder.parseConfigFromRequest(request), std::invalid_argument) << name;
    }
}
TEST(LfmGenerationPolicy, AutoRejectsUnsupportedPublicationProfile) {
    auto request = lfmRequest("auto");
    request.toolNameSchemaMap["write"].stringRepr = R"({"type":"object","properties":{"content":{"const":"hello"}}})";
    ovms::GenerationConfigBuilder builder({}, "lfm2", true, ovms::STANDARD);
    EXPECT_THROW(builder.parseConfigFromRequest(request), std::invalid_argument);
    request.toolChoice = "none";
    request.responseFormat = R"({"type":"json_object"})";
    EXPECT_NO_THROW(builder.parseConfigFromRequest(request));
    EXPECT_FALSE(builder.requiresValidStructuredOutput());
    ASSERT_TRUE(builder.getConfig().structured_output_config.has_value());
}
