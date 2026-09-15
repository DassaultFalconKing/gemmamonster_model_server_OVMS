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

#include <memory>
#include <string>
#include <variant>

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
