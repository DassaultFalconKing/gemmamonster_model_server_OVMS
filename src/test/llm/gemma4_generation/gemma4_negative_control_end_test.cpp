//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//*****************************************************************************

// Negative controls through one OVMSTextStreamer::end(). A Gemma tool example
// must stay non-executable when tools are unavailable, and when the active
// parsers are not the Gemma pair.

#include <gtest/gtest.h>

#include <cstdlib>
#include <memory>
#include <string>
#include <utility>
#include <variant>
#include <vector>

#include "src/llm/io_processing/output_parser.hpp"
#include "src/llm/ovms_text_streamer.hpp"

using namespace ovms;

namespace {

std::string defaultTokenizerPath() {
    if (const char* env = std::getenv("OVMS_TEST_TOKENIZER_PATH"))
        return env;
    return "C:/llm/models/runtime/gemma4-26-heretic-google-current";
}

ToolsSchemas_t questionTools() {
    ToolsSchemas_t tools;
    tools.emplace("question",
        ToolSchemaWrapper{nullptr, R"({"type":"object","properties":{"x":{}}})"});
    return tools;
}

struct Outcome {
    int toolDeltas = 0;
    std::string content;
    std::string reasoning;
    int lastSignals = 0;
};

Outcome runProductionEnd(ov::genai::Tokenizer& tokenizer,
    const std::string& toolParser,
    const std::string& reasoningParser,
    bool toolsAvailable,
    const std::vector<std::string>& chunks) {
    OutputParser parser(tokenizer, toolParser, reasoningParser, questionTools());
    Outcome out;
    auto absorb = [&](const Delta& delta) {
        if (std::holds_alternative<ToolCallDelta>(delta))
            ++out.toolDeltas;
        if (const auto* content = std::get_if<ContentDelta>(&delta))
            out.content += content->text;
        if (const auto* reasoning = std::get_if<ReasoningDelta>(&delta))
            out.reasoning += reasoning->text;
    };
    for (const auto& chunk : chunks) {
        auto delta = parser.parseChunk(chunk, {}, toolsAvailable, ov::genai::GenerationFinishReason::NONE);
        if (delta.has_value())
            absorb(*delta);
    }
    auto held = std::shared_ptr<OutputParser>(&parser, [](OutputParser*) {});
    OVMSTextStreamer streamer(tokenizer, held, toolsAvailable,
        [&](Delta delta, bool isLast) {
            absorb(delta);
            if (isLast)
                ++out.lastSignals;
            return ov::genai::StreamingStatus::RUNNING;
        },
        {});
    streamer.end();
    EXPECT_FALSE(streamer.hadParserError());
    EXPECT_EQ(out.lastSignals, 1);
    return out;
}

std::vector<std::string> cut(const std::string& text, size_t width) {
    std::vector<std::string> chunks;
    for (size_t i = 0; i < text.size(); i += width)
        chunks.push_back(text.substr(i, width));
    return chunks;
}

class Gemma4NegativeControlEndTest : public testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        tokenizer = std::make_unique<ov::genai::Tokenizer>(defaultTokenizerPath());
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }
};

std::unique_ptr<ov::genai::Tokenizer> Gemma4NegativeControlEndTest::tokenizer;

}  // namespace

TEST_F(Gemma4NegativeControlEndTest, ToolsUnavailableKeepsExampleText) {
    const std::string text = "<|channel>thought\nexample <|tool_call>call:question{x:1}";
    const std::string example = "example <|tool_call>call:question{x:1}";
    for (const auto& chunks : {std::vector<std::string>{text}, cut(text, 1)}) {
        const Outcome out = runProductionEnd(*tokenizer, "gemma4", "gemma4", false, chunks);
        EXPECT_EQ(out.toolDeltas, 0);
        EXPECT_EQ(out.reasoning, example);
        EXPECT_TRUE(out.content.empty());
    }
}

TEST_F(Gemma4NegativeControlEndTest, StreamerKeepsNonGemmaToolExamplesInReasoning) {
    const std::string example = "example <|tool_call>call:question{x:1}";
    const std::string text = "<think>" + example + "</think>AFTER";
    for (const auto& chunks : {std::vector<std::string>{text}, cut(text, 1), cut(text, 2), cut(text, 5)}) {
        const Outcome out = runProductionEnd(*tokenizer, "hermes3", "qwen3", true, chunks);
        EXPECT_EQ(out.toolDeltas, 0);
        EXPECT_EQ(out.reasoning, example);
        EXPECT_EQ(out.content, "AFTER");
    }
}
