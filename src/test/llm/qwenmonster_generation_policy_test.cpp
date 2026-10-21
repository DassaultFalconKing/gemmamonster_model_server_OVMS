// Copyright 2026 Intel Corporation. Licensed under the Apache License, Version 2.0.
#include <gtest/gtest.h>
#include <memory>
#include <stdexcept>
#include <string>
#include <variant>

#include "src/llm/io_processing/generation_config_builder.hpp"

using namespace ovms;
namespace {
using Structured = ov::genai::StructuredOutputConfig;

OpenAIRequest makeRequest(const std::string& choice) {
    OpenAIRequest req;
    req.toolChoice = choice;
    req.toolNameSchemaMap.emplace(
        "weather", ToolSchemaWrapper{nullptr,
            R"({"type":"object","properties":{"city":{"type":"string"}},"required":["city"]})"});
    req.toolNameSchemaMap.emplace(
        "clock", ToolSchemaWrapper{nullptr,
            R"({"type":"object","properties":{"zone":{"type":"string"}},"required":["zone"]})"});
    return req;
}

const Structured::StructuralTag& requiredTag(const GenerationConfigBuilder& /*unused*/) = delete;

const Structured::StructuralTag* tag(ov::genai::GenerationConfig& cfg) {
    if (!cfg.structured_output_config ||
        !cfg.structured_output_config->structural_tags_config)
        return nullptr;
    return std::get_if<Structured::StructuralTag>(
        &*cfg.structured_output_config->structural_tags_config);
}
} // namespace

TEST(QwenmonsterGenerationPolicy, RequiredUsesNativeXMLSchemas) {
    GenerationConfigBuilder builder({}, "qwen3coder", false, DecodingMethod::STANDARD);
    builder.parseConfigFromRequest(makeRequest("required"));
    EXPECT_TRUE(builder.requiresValidStructuredOutput());
    const auto* g = tag(builder.getConfig());
    ASSERT_NE(g, nullptr);
    const auto* list = std::get_if<std::shared_ptr<Structured::TagsWithSeparator>>(g);
    ASSERT_NE(list, nullptr);
    ASSERT_TRUE(*list);
    EXPECT_TRUE((*list)->at_least_one);
    EXPECT_FALSE((*list)->stop_after_first);
    ASSERT_EQ((*list)->tags.size(), 2u);
    for (const auto& t : (*list)->tags) {
        EXPECT_NE(t.begin.find("<tool_call>"), std::string::npos);
        EXPECT_NE(t.begin.find("<function="), std::string::npos);
        EXPECT_EQ(t.end, "</function>\n</tool_call>");
        const auto* args = std::get_if<Structured::QwenXMLParametersFormat>(&t.content);
        ASSERT_NE(args, nullptr);
        EXPECT_NE(args->json_schema.find(R"("type":"object")"), std::string::npos);
    }
}

TEST(QwenmonsterGenerationPolicy, NamedRestrictsToOneTool) {
    auto req = makeRequest("clock");
    req.parallelToolCalls = false;
    GenerationConfigBuilder builder({}, "qwen3coder", false, DecodingMethod::STANDARD);
    builder.parseConfigFromRequest(req);
    auto* g = tag(builder.getConfig());
    ASSERT_NE(g, nullptr);
    const auto* list = std::get_if<std::shared_ptr<Structured::TagsWithSeparator>>(g);
    ASSERT_NE(list, nullptr);
    ASSERT_TRUE(*list);
    EXPECT_TRUE((*list)->stop_after_first);
    ASSERT_EQ((*list)->tags.size(), 1u);
    EXPECT_NE((*list)->tags[0].begin.find("<function=clock>"), std::string::npos);
    EXPECT_EQ((*list)->tags[0].begin.find("<function=weather>"), std::string::npos);
}

TEST(QwenmonsterGenerationPolicy, AutoUnconstrainedByDefault) {
    GenerationConfigBuilder builder({}, "qwen3coder", false, DecodingMethod::STANDARD);
    builder.parseConfigFromRequest(makeRequest("auto"));
    EXPECT_FALSE(builder.requiresValidStructuredOutput());
    EXPECT_FALSE(builder.getConfig().structured_output_config.has_value());
}

TEST(QwenmonsterGenerationPolicy, AutoGuidedIsLazyNotForced) {
    auto req = makeRequest("auto");
    req.parallelToolCalls = false;
    GenerationConfigBuilder builder({}, "qwen3coder", true, DecodingMethod::STANDARD);
    builder.parseConfigFromRequest(req);
    const auto* g = tag(builder.getConfig());
    ASSERT_NE(g, nullptr);
    const auto* trig = std::get_if<std::shared_ptr<Structured::TriggeredTags>>(g);
    ASSERT_NE(trig, nullptr);
    ASSERT_TRUE(*trig);
    ASSERT_EQ((*trig)->triggers.size(), 1u);
    EXPECT_EQ((*trig)->triggers[0], "<tool_call>");
    EXPECT_FALSE((*trig)->at_least_one);
    EXPECT_TRUE((*trig)->stop_after_first);
}

TEST(QwenmonsterGenerationPolicy, NoneDoesNotInstallGrammar) {
    GenerationConfigBuilder builder({}, "qwen3coder", true, DecodingMethod::STANDARD);
    builder.parseConfigFromRequest(makeRequest("none"));
    EXPECT_FALSE(builder.getConfig().structured_output_config.has_value());
}

TEST(QwenmonsterGenerationPolicy, UnknownNamedAndEmptyRequiredFailClosed) {
    auto req = makeRequest("missing");
    GenerationConfigBuilder named({}, "qwen3coder", false, DecodingMethod::STANDARD);
    EXPECT_THROW(named.parseConfigFromRequest(req), std::invalid_argument);
    OpenAIRequest empty;
    empty.toolChoice = "required";
    GenerationConfigBuilder required({}, "qwen3coder", true, DecodingMethod::STANDARD);
    EXPECT_THROW(required.parseConfigFromRequest(empty), std::invalid_argument);
}

TEST(QwenmonsterGenerationPolicy, SchemaAndNameValidation) {
    auto req = makeRequest("required");
    req.toolNameSchemaMap.emplace(
        "bad<name", ToolSchemaWrapper{nullptr, R"({"type":"object","properties":{}})"});
    GenerationConfigBuilder badName({}, "qwen3coder", false, DecodingMethod::STANDARD);
    EXPECT_THROW(badName.parseConfigFromRequest(req), std::invalid_argument);
    req = makeRequest("required");
    req.toolNameSchemaMap["weather"] = ToolSchemaWrapper{nullptr, ""};
    GenerationConfigBuilder badSchema({}, "qwen3coder", false, DecodingMethod::STANDARD);
    EXPECT_THROW(badSchema.parseConfigFromRequest(req), std::invalid_argument);
}

TEST(QwenmonsterGenerationPolicy, RejectsResponseFormatConflict) {
    auto req = makeRequest("required");
    req.responseFormat = R"({"type":"structural_tag","format":{"type":"json_object"}})";
    GenerationConfigBuilder builder({}, "qwen3coder", true, DecodingMethod::STANDARD);
    EXPECT_THROW(builder.parseConfigFromRequest(req), std::invalid_argument);
}

TEST(QwenmonsterGenerationPolicy, ParserFamilyIsolation) {
    auto req = makeRequest("required");
    GenerationConfigBuilder generic({}, "", false, DecodingMethod::STANDARD);
    EXPECT_NO_THROW(generic.parseConfigFromRequest(req));
    EXPECT_FALSE(generic.requiresValidStructuredOutput());
    GenerationConfigBuilder hermes({}, "hermes3", false, DecodingMethod::STANDARD);
    EXPECT_NO_THROW(hermes.parseConfigFromRequest(req));
    GenerationConfigBuilder gemma({}, "gemma4", false, DecodingMethod::STANDARD);
    EXPECT_NO_THROW(gemma.parseConfigFromRequest(req));
    EXPECT_TRUE(gemma.requiresValidStructuredOutput());
}
