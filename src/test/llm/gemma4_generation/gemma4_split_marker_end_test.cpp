//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//*****************************************************************************

// Split Gemma4 tool opener and closer. Incomplete markers stay held across
// NONE chunks. One OVMSTextStreamer::end() then publishes the call and the
// surrounding text, and neither tag leaks into content.

#include <gtest/gtest.h>

#include <cstdlib>
#include <memory>
#include <string>
#include <utility>
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

struct Call {
    int index = -1;
    std::string name;
    std::string arguments;
};

struct Outcome {
    std::vector<Call> calls;
    std::string content;
    int lastSignals = 0;
};

void absorb(Outcome& out, const Delta& delta) {
    if (const auto* tool = std::get_if<ToolCallDelta>(&delta)) {
        Call call;
        call.index = tool->index;
        if (tool->name.has_value())
            call.name = *tool->name;
        call.arguments = tool->arguments;
        out.calls.push_back(std::move(call));
        return;
    }
    if (const auto* content = std::get_if<ContentDelta>(&delta))
        out.content += content->text;
}

Outcome runProductionEnd(ov::genai::Tokenizer& tokenizer, const std::vector<std::string>& chunks) {
    OutputParser parser(tokenizer, "gemma4", "gemma4", questionTools());
    Outcome out;
    for (const auto& chunk : chunks) {
        auto delta = parser.parseChunk(chunk, {}, true, ov::genai::GenerationFinishReason::NONE);
        if (delta.has_value())
            absorb(out, *delta);
    }
    auto held = std::shared_ptr<OutputParser>(&parser, [](OutputParser*) {});
    OVMSTextStreamer streamer(tokenizer, held, true,
        [&](Delta delta, bool isLast) {
            absorb(out, delta);
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

void expectOneQuestion(const Outcome& out) {
    ASSERT_EQ(out.calls.size(), 1u);
    EXPECT_EQ(out.calls[0].index, 0);
    EXPECT_EQ(out.calls[0].name, "question");
    EXPECT_EQ(out.calls[0].arguments, R"({"x":1})");
    EXPECT_EQ(out.content, "LEADTAIL");
    EXPECT_EQ(out.content.find("<|tool_call>"), std::string::npos);
    EXPECT_EQ(out.content.find("<tool_call|>"), std::string::npos);
    EXPECT_EQ(out.content.find("<|tool_"), std::string::npos);
    EXPECT_EQ(out.content.find("<tool_cal"), std::string::npos);
}

class Gemma4SplitMarkerEndTest : public testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        tokenizer = std::make_unique<ov::genai::Tokenizer>(defaultTokenizerPath());
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }
};

std::unique_ptr<ov::genai::Tokenizer> Gemma4SplitMarkerEndTest::tokenizer;

const char kFull[] = "LEAD<|tool_call>call:question{x:1}<tool_call|>TAIL";

}  // namespace

TEST_F(Gemma4SplitMarkerEndTest, SplitToolCallStartTagDoesNotLeakIntoContent) {
    const Outcome split = runProductionEnd(*tokenizer,
        {"LEAD<|too", "l_call>call:question{x:1}<tool_call|>TAIL"});
    expectOneQuestion(split);

    const Outcome bytes = runProductionEnd(*tokenizer, cut(kFull, 1));
    expectOneQuestion(bytes);
    const Outcome two = runProductionEnd(*tokenizer, cut(kFull, 2));
    expectOneQuestion(two);
    const Outcome five = runProductionEnd(*tokenizer, cut(kFull, 5));
    expectOneQuestion(five);
}

TEST_F(Gemma4SplitMarkerEndTest, SplitToolCallEndTagDoesNotLeakIntoContent) {
    const Outcome split = runProductionEnd(*tokenizer,
        {"LEAD<|tool_call>call:question{x:1}<tool_cal", "l|>TAIL"});
    expectOneQuestion(split);

    const Outcome bytes = runProductionEnd(*tokenizer, cut(kFull, 1));
    expectOneQuestion(bytes);
    const Outcome two = runProductionEnd(*tokenizer, cut(kFull, 2));
    expectOneQuestion(two);
    const Outcome five = runProductionEnd(*tokenizer, cut(kFull, 5));
    expectOneQuestion(five);
}
