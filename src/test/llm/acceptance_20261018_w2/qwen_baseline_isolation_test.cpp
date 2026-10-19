//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//*****************************************************************************

// Deterministic isolation for the Qwen3.6-35B-A3B baseline parser name.
// Factory source maps "qwen3coder" to BaseGenerationConfigBuilder and
// "qwen3" / "hermes3" to Hermes3GenerationConfigBuilder. These tests do not
// load the A3B model and are not Gemma policy proof.

#include <gtest/gtest.h>

#include <string>
#include <utility>
#include <vector>

#include "src/llm/io_processing/generation_config_builder.hpp"
#include "src/llm/io_processing/qwen3coder/qwen3coder_tool_parser.hpp"

using namespace ovms;

namespace {

OpenAIRequest weatherRequest(const std::string& toolChoice, bool parallelToolCalls) {
    OpenAIRequest request;
    request.toolChoice = toolChoice;
    request.parallelToolCalls = parallelToolCalls;
    request.toolNameSchemaMap.emplace(
        "weather",
        ToolSchemaWrapper{nullptr,
            R"({"type":"object","properties":{"city":{"type":"string"}},"required":["city"]})"});
    request.toolNameSchemaMap.emplace(
        "clock",
        ToolSchemaWrapper{nullptr,
            R"({"type":"object","properties":{"timezone":{"type":"string"}}})"});
    return request;
}

bool hasStructuredOutput(GenerationConfigBuilder& builder) {
    return builder.getConfig().structured_output_config.has_value();
}

}  // namespace

TEST(QwenBaselineIsolationTest, CoderParserInstallsNoGemmaGrammarForAnyModeOrParallelFlag) {
    const std::vector<std::string> choices{"none", "auto", "required", "weather"};
    for (const std::string& choice : choices) {
        for (const bool parallel : {false, true}) {
            SCOPED_TRACE(choice + (parallel ? " parallel" : " unary"));
            GenerationConfigBuilder builder(
                ov::genai::GenerationConfig{}, "qwen3coder", true, DecodingMethod::STANDARD);
            EXPECT_NO_THROW(builder.parseConfigFromRequest(weatherRequest(choice, parallel)));
            EXPECT_FALSE(builder.requiresValidStructuredOutput());
            EXPECT_FALSE(hasStructuredOutput(builder));
        }
    }
}

TEST(QwenBaselineIsolationTest, ZeroArgCoderToolStillInstallsNoGrammarWhenParallelIsFalse) {
    OpenAIRequest request;
    request.toolChoice = "required";
    request.parallelToolCalls = false;
    request.toolNameSchemaMap.emplace(
        "ping",
        ToolSchemaWrapper{nullptr, R"({"type":"object","properties":{}})"});

    GenerationConfigBuilder builder(
        ov::genai::GenerationConfig{}, "qwen3coder", true, DecodingMethod::STANDARD);
    EXPECT_NO_THROW(builder.parseConfigFromRequest(request));
    EXPECT_FALSE(builder.requiresValidStructuredOutput());
    EXPECT_FALSE(hasStructuredOutput(builder));
}

TEST(QwenBaselineIsolationTest, Qwen3NameIsHermesAliasNotTheCoderBaseline) {
    GenerationConfigBuilder hermes(
        ov::genai::GenerationConfig{}, "qwen3", true, DecodingMethod::STANDARD);
    EXPECT_NO_THROW(hermes.parseConfigFromRequest(weatherRequest("required", false)));
    EXPECT_FALSE(hermes.requiresValidStructuredOutput());
    EXPECT_TRUE(hasStructuredOutput(hermes));

    GenerationConfigBuilder coder(
        ov::genai::GenerationConfig{}, "qwen3coder", true, DecodingMethod::STANDARD);
    EXPECT_NO_THROW(coder.parseConfigFromRequest(weatherRequest("required", false)));
    EXPECT_FALSE(hasStructuredOutput(coder));
}

TEST(QwenBaselineIsolationTest, GemmaNoneWithParallelFalseDoesNotInstallToolGrammar) {
    GenerationConfigBuilder builder(
        ov::genai::GenerationConfig{}, "gemma4", true, DecodingMethod::STANDARD);
    EXPECT_NO_THROW(builder.parseConfigFromRequest(weatherRequest("none", false)));
    EXPECT_FALSE(builder.requiresValidStructuredOutput());
    EXPECT_FALSE(hasStructuredOutput(builder));
}

TEST(QwenCoderParserIsolationTest, ForeignEnvelopesAreNotCoderToolCalls) {
    const ToolsParameterTypeMap_t types{
        {"weather", {{"city", ParameterType::STRING}}},
        {"ping", {}},
    };
    const std::vector<std::string> foreign{
        R"(<|tool_call>call:weather{city:"Paris"}<tool_call|>)",
        "<tool_call>\n{\"name\": \"weather\", \"arguments\": {\"city\": \"Paris\"}}\n</tool_call>",
        "<|channel>thought\nsecret<channel|>",
    };
    for (const std::string& text : foreign) {
        SCOPED_TRACE(text);
        Qwen3CoderToolParserImpl parser(types);
        EXPECT_FALSE(parser.parseChunk(text).has_value());
        EXPECT_FALSE(parser.finalizeOnGenerationEnd().has_value());
    }
}

TEST(QwenCoderParserIsolationTest, CoderXmlZeroArgAndSecondCallStayOnTheParser) {
    const ToolsParameterTypeMap_t types{{"ping", {}}};
    Qwen3CoderToolParserImpl parser(types);
    const std::string input =
        "<tool_call>\n<function=ping>\n</function>\n</tool_call>\n"
        "<tool_call>\n<function=ping>\n</function>\n</tool_call>";
    const auto calls = parser.parseChunk(input);
    ASSERT_TRUE(calls.has_value());
    ASSERT_EQ(calls->size(), 2u);
    EXPECT_EQ((*calls)[0].name, "ping");
    EXPECT_EQ((*calls)[0].arguments, "{}");
    EXPECT_EQ((*calls)[1].name, "ping");
    EXPECT_EQ((*calls)[1].arguments, "{}");
}
