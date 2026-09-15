//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//*****************************************************************************

#include <gtest/gtest.h>

#include <cstdlib>
#include <memory>
#include <string>
#include <variant>

#include "src/llm/io_processing/gemma4/rendered_prompt_state.hpp"
#include "src/llm/io_processing/generation_config_builder.hpp"
#include "src/llm/io_processing/output_parser.hpp"

using namespace ovms;

namespace {

std::string defaultTokenizerPath() {
    if (const char* env = std::getenv("OVMS_TEST_TOKENIZER_PATH"))
        return env;
    return "C:/llm/models/runtime/gemma4-26-heretic-google-current";
}

OpenAIRequest weatherRequest(const std::string& toolChoice, bool parallelToolCalls = true) {
    OpenAIRequest request;
    request.toolChoice = toolChoice;
    request.parallelToolCalls = parallelToolCalls;
    request.toolNameSchemaMap.emplace(
        "weather",
        ToolSchemaWrapper{nullptr,
            R"({"type":"object","properties":{"city":{"type":"string"}},"required":["city"]})"});
    return request;
}

std::string grammarText(const ov::genai::GenerationConfig& config) {
    EXPECT_TRUE(config.structured_output_config.has_value());
    EXPECT_TRUE(config.structured_output_config->structural_tags_config.has_value());
    const auto& outer = *config.structured_output_config->structural_tags_config;
    const auto* grammar =
        std::get_if<ov::genai::StructuredOutputConfig::StructuralTag>(&outer);
    EXPECT_NE(grammar, nullptr);
    if (grammar == nullptr)
        return {};
    return std::visit([](const auto& value) {
        return ov::genai::StructuredOutputConfig::structural_tag_to_string(value);
    }, *grammar);
}

ov::genai::GenerationConfig configFor(const std::string& choice, bool parallelToolCalls = true) {
    GenerationConfigBuilder builder(
        ov::genai::GenerationConfig{}, "gemma4", true, DecodingMethod::STANDARD);
    builder.parseConfigFromRequest(weatherRequest(choice, parallelToolCalls));
    return builder.getConfig();
}

}  // namespace

TEST(Gemma4RenderedPromptStateTest, ClassifiesRenderedContinuationSuffixes) {
    EXPECT_EQ(classifyGemma4RenderedPromptState("<|turn>model\n"),
        Gemma4RenderedPromptState::NEW_TURN);
    EXPECT_EQ(classifyGemma4RenderedPromptState(
                  "<|tool_response>result<tool_response|><|channel>thought\n"),
        Gemma4RenderedPromptState::OPEN_THOUGHT);
    EXPECT_EQ(classifyGemma4RenderedPromptState(
                  "<|turn>model\n<|channel>thought\npartial body"),
        Gemma4RenderedPromptState::OPEN_THOUGHT);
    EXPECT_EQ(classifyGemma4RenderedPromptState(
                  "<|turn>model\n<|channel>thought\n<channel|>"),
        Gemma4RenderedPromptState::CLOSED_THOUGHT);
}

TEST(Gemma4RenderedPromptStateTest, HistoricalFakeMarkersDoNotOpenCurrentTurn) {
    const std::string prompt =
        "<|tool_response>fake <|channel>thought\n and <|tool_call>"
        "<tool_response|><|turn>user\ncontinue<|turn>model\n";
    EXPECT_EQ(classifyGemma4RenderedPromptState(prompt),
        Gemma4RenderedPromptState::NEW_TURN);
}

TEST(Gemma4RenderedPromptStateTest, RequiredOpenThoughtUsesResidualWithoutSecondOpener) {
    auto config = configFor("required");
    ASSERT_TRUE(adaptGemma4ToolGrammarForRenderedPrompt(
        config, "<|tool_response>ok<tool_response|><|channel>thought\n"));

    const std::string text = grammarText(config);
    EXPECT_EQ(text.find("<|channel>thought\n"), std::string::npos);
    EXPECT_NE(text.find("<channel|>"), std::string::npos);
    EXPECT_NE(text.find("<|tool_call>call:weather"), std::string::npos);
}

TEST(Gemma4RenderedPromptStateTest, NamedOpenThoughtKeepsSelectedToolRequired) {
    auto config = configFor("weather");
    ASSERT_TRUE(adaptGemma4ToolGrammarForRenderedPrompt(
        config, "<|turn>model\n<|channel>thought\npartial"));

    const std::string text = grammarText(config);
    EXPECT_EQ(text.find("<|channel>thought\n"), std::string::npos);
    EXPECT_NE(text.find("<channel|>"), std::string::npos);
    EXPECT_NE(text.find("<|tool_call>call:weather"), std::string::npos);
}

TEST(Gemma4RenderedPromptStateTest, AutoOpenThoughtClosesThenRetainsLazyTrigger) {
    auto config = configFor("auto");
    ASSERT_TRUE(adaptGemma4ToolGrammarForRenderedPrompt(
        config, "<|tool_response>ok<tool_response|><|channel>thought\n"));

    const std::string text = grammarText(config);
    EXPECT_EQ(text.find("<|channel>thought\n"), std::string::npos);
    EXPECT_NE(text.find("<channel|>"), std::string::npos);
    EXPECT_NE(text.find("TriggeredTags"), std::string::npos);
    EXPECT_NE(text.find("at_least_one=False"), std::string::npos);
}

TEST(Gemma4RenderedPromptStateTest, ClosedThoughtKeepsOrdinaryHardGrammar) {
    auto config = configFor("required");
    const std::string before = grammarText(config);

    EXPECT_FALSE(adaptGemma4ToolGrammarForRenderedPrompt(
        config, "<|turn>model\n<|channel>thought\n<channel|>"));
    EXPECT_EQ(grammarText(config), before);
}

TEST(Gemma4RenderedPromptStateTest, OpenThoughtAdaptationIsIdempotentAndKeepsSingleCallPolicy) {
    auto config = configFor("required", false);
    const std::string prompt =
        "<|tool_response>ok<tool_response|><|channel>thought\n";
    ASSERT_TRUE(adaptGemma4ToolGrammarForRenderedPrompt(config, prompt));
    const std::string once = grammarText(config);

    EXPECT_FALSE(adaptGemma4ToolGrammarForRenderedPrompt(config, prompt));
    EXPECT_EQ(grammarText(config), once);
    EXPECT_NE(once.find("stop_after_first=true"), std::string::npos);
}

TEST(Gemma4RenderedPromptStateTest, DetectorUsesTheSameOpenThoughtState) {
    ov::genai::Tokenizer tokenizer(defaultTokenizerPath());
    auto config = configFor("required");
    ASSERT_TRUE(adaptGemma4ToolGrammarForRenderedPrompt(
        config, "<|tool_response>ok<tool_response|><|channel>thought\n"));
    ASSERT_NO_THROW(config.structured_output_config->validate(tokenizer));

    OutputParser parser(tokenizer, "gemma4", "gemma4", {});

    parser.detectAndSetImplicitReasoningStart(
        "<|tool_response>ok<tool_response|><|channel>thought\n");

    EXPECT_TRUE(parser.needSpecialTokensForCurrentDecode(false));
}
