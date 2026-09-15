//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//*****************************************************************************

#include <gtest/gtest.h>

#include <chrono>
#include <cstdlib>
#include <exception>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <variant>

#include <rapidjson/document.h>

#include "src/llm/apis/openai_completions.hpp"
#include "src/llm/io_processing/generation_config_builder.hpp"

using namespace ovms;

namespace {
OpenAIRequest weatherRequest(const std::string& toolChoice) {
    OpenAIRequest request;
    request.toolChoice = toolChoice;
    request.toolNameSchemaMap.emplace(
        "weather",
        ToolSchemaWrapper{nullptr,
            R"({"type":"object","properties":{"city":{"type":"string"}},"required":["city"]})"});
    return request;
}

const ov::genai::StructuredOutputConfig::StructuralTag* getStructuralTag(
    const ov::genai::GenerationConfig& config) {
    if (!config.structured_output_config || !config.structured_output_config->structural_tags_config)
        return nullptr;
    const auto& outer = *config.structured_output_config->structural_tags_config;
    return std::get_if<ov::genai::StructuredOutputConfig::StructuralTag>(&outer);
}

std::string structuralTagText(const ov::genai::StructuredOutputConfig::StructuralTag& grammar) {
    return std::visit([](const auto& element) {
        return ov::genai::StructuredOutputConfig::structural_tag_to_string(element);
    }, grammar);
}
}  // namespace

TEST(Gemma4GenerationPolicyTest, RequiredToolChoiceInstallsNativeStructuredGrammar) {
    ov::genai::GenerationConfig baseConfig;
    GenerationConfigBuilder builder(baseConfig, "gemma4", true, DecodingMethod::STANDARD);

    builder.parseConfigFromRequest(weatherRequest("required"));

    EXPECT_TRUE(builder.getConfig().structured_output_config.has_value());
}

TEST(Gemma4GenerationPolicyTest, AutoUsesLazyNativeToolTrigger) {
    using Structured = ov::genai::StructuredOutputConfig;
    ov::genai::GenerationConfig baseConfig;
    GenerationConfigBuilder builder(baseConfig, "gemma4", true, DecodingMethod::STANDARD);

    builder.parseConfigFromRequest(weatherRequest("auto"));

    const auto* grammar = getStructuralTag(builder.getConfig());
    ASSERT_NE(grammar, nullptr);
    const auto* triggered = std::get_if<std::shared_ptr<Structured::TriggeredTags>>(grammar);
    ASSERT_NE(triggered, nullptr);
    ASSERT_TRUE(*triggered);
    ASSERT_EQ((*triggered)->triggers.size(), 1u);
    EXPECT_EQ((*triggered)->triggers[0], "<|tool_call>");
    EXPECT_FALSE((*triggered)->at_least_one);
    ASSERT_EQ((*triggered)->tags.size(), 1u);
    EXPECT_EQ((*triggered)->tags[0].begin, "<|tool_call>call:weather");
    EXPECT_EQ((*triggered)->tags[0].end, "<tool_call|>");
}

TEST(Gemma4GenerationPolicyTest, NamedChoiceRestrictsGrammarToSelectedTool) {
    OpenAIRequest request = weatherRequest("weather");
    request.toolNameSchemaMap.emplace(
        "clock",
        ToolSchemaWrapper{nullptr,
            R"({"type":"object","properties":{"timezone":{"type":"string"}},"required":["timezone"]})"});

    ov::genai::GenerationConfig baseConfig;
    GenerationConfigBuilder builder(baseConfig, "gemma4", false, DecodingMethod::STANDARD);
    builder.parseConfigFromRequest(request);

    const auto* grammar = getStructuralTag(builder.getConfig());
    ASSERT_NE(grammar, nullptr);
    const std::string text = structuralTagText(*grammar);
    EXPECT_NE(text.find("<|tool_call>call:weather"), std::string::npos);
    EXPECT_EQ(text.find("<|tool_call>call:clock"), std::string::npos);
}

TEST(Gemma4GenerationPolicyTest, ActiveToolsRejectCompetingResponseFormat) {
    OpenAIRequest request = weatherRequest("required");
    request.responseFormat = R"({"type":"structural_tag","format":{"type":"json_object"}})";

    ov::genai::GenerationConfig baseConfig;
    GenerationConfigBuilder builder(baseConfig, "gemma4", true, DecodingMethod::STANDARD);

    EXPECT_THROW(builder.parseConfigFromRequest(request), std::invalid_argument);
}

TEST(Gemma4GenerationPolicyTest, ToolChoiceNoneLeavesResponseFormatAvailable) {
    OpenAIRequest request = weatherRequest("none");
    request.responseFormat = R"({"type":"structural_tag","format":{"type":"json_object"}})";

    ov::genai::GenerationConfig baseConfig;
    GenerationConfigBuilder builder(baseConfig, "gemma4", true, DecodingMethod::STANDARD);
    EXPECT_NO_THROW(builder.parseConfigFromRequest(request));
    EXPECT_TRUE(builder.getConfig().structured_output_config.has_value());
}

TEST(Gemma4GenerationPolicyTest, RequiredWithoutToolsIsRejected) {
    OpenAIRequest request;
    request.toolChoice = "required";

    ov::genai::GenerationConfig baseConfig;
    GenerationConfigBuilder builder(baseConfig, "gemma4", true, DecodingMethod::STANDARD);
    EXPECT_THROW(builder.parseConfigFromRequest(request), std::invalid_argument);
}

TEST(Gemma4GenerationPolicyTest, HardChoiceRequiresSuccessfulGrammarValidation) {
    ov::genai::GenerationConfig baseConfig;
    GenerationConfigBuilder requiredBuilder(baseConfig, "gemma4", true, DecodingMethod::STANDARD);
    requiredBuilder.parseConfigFromRequest(weatherRequest("required"));
    EXPECT_TRUE(requiredBuilder.requiresValidStructuredOutput());

    GenerationConfigBuilder autoBuilder(baseConfig, "gemma4", true, DecodingMethod::STANDARD);
    autoBuilder.parseConfigFromRequest(weatherRequest("auto"));
    EXPECT_FALSE(autoBuilder.requiresValidStructuredOutput());
}

namespace {
class Gemma4ApiValidationTest : public testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        const char* localTokenizer = std::getenv("OVMS_TEST_TOKENIZER_PATH");
        std::string path;
        if (localTokenizer != nullptr) {
            path = localTokenizer;
        } else {
            const std::string cwd = std::filesystem::current_path().string();
            const size_t bazelOut = cwd.find("bazel-out");
            const std::string workspace = bazelOut == std::string::npos ? cwd : cwd.substr(0, bazelOut);
            path = workspace + "/src/test/llm_testing/HuggingFaceTB/SmolLM2-360M-Instruct";
        }
        tokenizer = std::make_unique<ov::genai::Tokenizer>(path);
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }
};

std::unique_ptr<ov::genai::Tokenizer> Gemma4ApiValidationTest::tokenizer;

constexpr const char* INVALID_REQUIRED_TOOL_REQUEST = R"({"model":"m","messages":[{"role":"user","content":"Call weather"}],"tool_choice":"required","tools":[{"type":"function","function":{"name":"weather","parameters":{"type":"invalid_schema_type"}}}]})";
constexpr const char* INVALID_AUTO_TOOL_REQUEST = R"({"model":"m","messages":[{"role":"user","content":"Call weather"}],"tool_choice":"auto","tools":[{"type":"function","function":{"name":"weather","parameters":{"type":"invalid_schema_type"}}}]})";
constexpr const char* MISSING_NAMED_TOOL_REQUEST = R"({"model":"m","messages":[{"role":"user","content":"Call weather"}],"tool_choice":{"type":"function","function":{"name":"missing"}},"tools":[{"type":"function","function":{"name":"weather","parameters":{"type":"object"}}}]})";
}  // namespace

TEST_F(Gemma4ApiValidationTest, InvalidRequiredGrammarReturnsInvalidArgumentWithoutFallback) {
    rapidjson::Document doc;
    doc.Parse(INVALID_REQUIRED_TOOL_REQUEST);
    ASSERT_FALSE(doc.HasParseError());
    OpenAIChatCompletionsHandler handler(doc, Endpoint::CHAT_COMPLETIONS, std::chrono::system_clock::now(), *tokenizer);
    ASSERT_TRUE(handler.parseRequest(std::nullopt, 0, std::nullopt).ok());

    GenerationConfigBuilder builder(ov::genai::GenerationConfig{}, "gemma4", true, DecodingMethod::STANDARD);
    builder.parseConfigFromRequest(handler.getRequest());
    std::string validationError;
    try {
        builder.validateStructuredOutputConfig(*tokenizer);
    } catch (const std::exception& e) {
        validationError = e.what();
    }
    ASSERT_FALSE(validationError.empty());
    SCOPED_TRACE(validationError);

    auto result = handler.extractInputRequest(builder);
    EXPECT_EQ(result.status().code(), absl::StatusCode::kInvalidArgument);
}

TEST_F(Gemma4ApiValidationTest, InvalidAutoGrammarKeepsOptionalFallback) {
    rapidjson::Document doc;
    doc.Parse(INVALID_AUTO_TOOL_REQUEST);
    ASSERT_FALSE(doc.HasParseError());
    OpenAIChatCompletionsHandler handler(doc, Endpoint::CHAT_COMPLETIONS, std::chrono::system_clock::now(), *tokenizer);
    ASSERT_TRUE(handler.parseRequest(std::nullopt, 0, std::nullopt).ok());

    GenerationConfigBuilder builder(ov::genai::GenerationConfig{}, "gemma4", true, DecodingMethod::STANDARD);
    builder.parseConfigFromRequest(handler.getRequest());
    ASSERT_THROW(builder.validateStructuredOutputConfig(*tokenizer), std::exception);

    auto result = handler.extractInputRequest(builder);
    ASSERT_TRUE(result.ok()) << result.status();
    EXPECT_FALSE(result->generationConfig.structured_output_config.has_value());
}

TEST_F(Gemma4ApiValidationTest, InvalidNamedPolicyReturnsStatusInsteadOfThrowing) {
    rapidjson::Document doc;
    doc.Parse(MISSING_NAMED_TOOL_REQUEST);
    ASSERT_FALSE(doc.HasParseError());
    OpenAIChatCompletionsHandler handler(doc, Endpoint::CHAT_COMPLETIONS, std::chrono::system_clock::now(), *tokenizer);
    ASSERT_TRUE(handler.parseRequest(std::nullopt, 0, std::nullopt).ok());

    GenerationConfigBuilder builder(ov::genai::GenerationConfig{}, "gemma4", true, DecodingMethod::STANDARD);
    EXPECT_NO_THROW({
        auto result = handler.extractInputRequest(builder);
        EXPECT_EQ(result.status().code(), absl::StatusCode::kInvalidArgument);
    });
}
