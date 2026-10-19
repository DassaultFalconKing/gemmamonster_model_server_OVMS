//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//*****************************************************************************

// Reasoning, content, and tool publication order through one
// OVMSTextStreamer::end(). Implicit handoff is a tool opener inside an
// unclosed thought. Explicit handoff closes <channel|> before the tool.

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

enum class Kind { Reasoning, Content, Tool };

struct Call {
    int index = -1;
    std::string name;
    std::string arguments;
};

struct Event {
    Kind kind;
    std::string text;
};

struct Outcome {
    std::vector<Call> calls;
    std::string content;
    std::string reasoning;
    std::vector<Event> events;
    int lastSignals = 0;
};

void absorb(Outcome& out, const Delta& delta) {
    if (const auto* tool = std::get_if<ToolCallDelta>(&delta)) {
        Call call;
        call.index = tool->index;
        if (tool->name.has_value())
            call.name = *tool->name;
        call.arguments = tool->arguments;
        out.events.push_back(Event{Kind::Tool, call.arguments});
        out.calls.push_back(std::move(call));
        return;
    }
    if (const auto* content = std::get_if<ContentDelta>(&delta)) {
        out.content += content->text;
        out.events.push_back(Event{Kind::Content, content->text});
        return;
    }
    if (const auto* reasoning = std::get_if<ReasoningDelta>(&delta)) {
        out.reasoning += reasoning->text;
        out.events.push_back(Event{Kind::Reasoning, reasoning->text});
    }
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

struct Partition {
    const char* name;
    std::vector<std::string> chunks;
};

std::vector<Partition> partitionsOf(const std::string& text) {
    return {
        {"coalesced", {text}},
        {"two-byte", cut(text, 2)},
        {"five-byte", cut(text, 5)},
        {"every-byte", cut(text, 1)},
    };
}

size_t firstOf(const Outcome& out, Kind kind) {
    for (size_t i = 0; i < out.events.size(); ++i) {
        if (out.events[i].kind == kind)
            return i;
    }
    return out.events.size();
}

std::string contentAround(const Outcome& out, size_t toolAt, bool before) {
    std::string text;
    for (size_t i = 0; i < out.events.size(); ++i) {
        if (out.events[i].kind != Kind::Content)
            continue;
        if (before == (i < toolAt))
            text += out.events[i].text;
    }
    return text;
}

class Gemma4ReasoningOrderEndTest : public testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        tokenizer = std::make_unique<ov::genai::Tokenizer>(defaultTokenizerPath());
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }
};

std::unique_ptr<ov::genai::Tokenizer> Gemma4ReasoningOrderEndTest::tokenizer;

}  // namespace

TEST_F(Gemma4ReasoningOrderEndTest, ProductionEndKeepsReasoningBeforeAnswer) {
    const std::string text = "<|channel>thought\nsecret<channel|>answer";
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
        EXPECT_EQ(out.reasoning, "secret");
        EXPECT_EQ(out.content, "answer");
        EXPECT_TRUE(out.calls.empty());
        EXPECT_LT(firstOf(out, Kind::Reasoning), firstOf(out, Kind::Content));
        EXPECT_EQ(out.reasoning.find("<|channel>"), std::string::npos);
        EXPECT_EQ(out.reasoning.find("<channel|>"), std::string::npos);
        EXPECT_EQ(out.content.find("<channel|>"), std::string::npos);
    }
}

TEST_F(Gemma4ReasoningOrderEndTest, ImplicitReasoningToolHandoffPublishesReasoningBeforeCall) {
    const std::string text = "<|channel>thought\nsecret<|tool_call>call:question{x:1}<tool_call|>";
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
        EXPECT_EQ(out.reasoning, "secret");
        EXPECT_TRUE(out.content.empty());
        ASSERT_EQ(out.calls.size(), 1u);
        EXPECT_EQ(out.calls[0].index, 0);
        EXPECT_EQ(out.calls[0].name, "question");
        EXPECT_EQ(out.calls[0].arguments, R"({"x":1})");
        EXPECT_LT(firstOf(out, Kind::Reasoning), firstOf(out, Kind::Tool));
        EXPECT_EQ(out.reasoning.find("<|tool_call>"), std::string::npos);
    }
}

TEST_F(Gemma4ReasoningOrderEndTest, ExplicitReasoningToolHandoffKeepsContentAroundCall) {
    const std::string text =
        "<|channel>thought\nsecret<channel|>GO"
        "<|tool_call>call:question{x:1}<tool_call|>"
        "TAIL";
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
        EXPECT_EQ(out.reasoning, "secret");
        EXPECT_EQ(out.content, "GOTAIL");
        ASSERT_EQ(out.calls.size(), 1u);
        EXPECT_EQ(out.calls[0].index, 0);
        EXPECT_EQ(out.calls[0].name, "question");
        EXPECT_EQ(out.calls[0].arguments, R"({"x":1})");
        const size_t reasonAt = firstOf(out, Kind::Reasoning);
        const size_t toolAt = firstOf(out, Kind::Tool);
        const size_t contentAt = firstOf(out, Kind::Content);
        EXPECT_LT(reasonAt, contentAt);
        EXPECT_LT(contentAt, toolAt);
        EXPECT_EQ(contentAround(out, toolAt, true), "GO");
        EXPECT_EQ(contentAround(out, toolAt, false), "TAIL");
        EXPECT_EQ(out.content.find("<|tool_call>"), std::string::npos);
        EXPECT_EQ(out.content.find("<tool_call|>"), std::string::npos);
        EXPECT_EQ(out.content.find("<channel|>"), std::string::npos);
    }
}
