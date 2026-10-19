//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//*****************************************************************************

// Separate Gemma4 tool envelopes through one OVMSTextStreamer::end().
// end() sends one STOP parseChunk and then drainPendingDelta until nullopt.
// A loop that calls parseChunk(..., STOP) again is not this path.

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

std::string envelope(int n) {
    return "<|tool_call>call:question{x:" + std::to_string(n) + "}<tool_call|>";
}

struct Call {
    int index = -1;
    std::string name;
    std::string arguments;
};

struct Outcome {
    std::vector<Call> calls;
    std::string content;
    std::string reasoning;
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
    if (const auto* reasoning = std::get_if<ReasoningDelta>(&delta))
        out.reasoning += reasoning->text;
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

void expectCalls(const Outcome& out, const std::vector<std::string>& arguments) {
    ASSERT_EQ(out.calls.size(), arguments.size());
    for (size_t i = 0; i < arguments.size(); ++i) {
        EXPECT_EQ(out.calls[i].index, static_cast<int>(i));
        EXPECT_EQ(out.calls[i].name, "question");
        EXPECT_EQ(out.calls[i].arguments, arguments[i]);
    }
}

void expectNoToolMarkup(const std::string& text) {
    EXPECT_EQ(text.find("<|tool_call>"), std::string::npos);
    EXPECT_EQ(text.find("<tool_call|>"), std::string::npos);
    EXPECT_EQ(text.find("call:question"), std::string::npos);
}

std::vector<std::string> argsFor(int count) {
    std::vector<std::string> arguments;
    for (int n = 1; n <= count; ++n)
        arguments.push_back("{\"x\":" + std::to_string(n) + "}");
    return arguments;
}

std::string joinedEnvelopes(int count) {
    std::string text;
    for (int n = 1; n <= count; ++n)
        text += envelope(n);
    return text;
}

class Gemma4SeparateEnvelopeEndTest : public testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        tokenizer = std::make_unique<ov::genai::Tokenizer>(defaultTokenizerPath());
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }
};

std::unique_ptr<ov::genai::Tokenizer> Gemma4SeparateEnvelopeEndTest::tokenizer;

}  // namespace

TEST_F(Gemma4SeparateEnvelopeEndTest, ProductionEndRecoversTwoSeparateEnvelopes) {
    const std::string text = joinedEnvelopes(2);
    const auto expected = argsFor(2);
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
        expectCalls(out, expected);
        EXPECT_TRUE(out.content.empty());
        EXPECT_TRUE(out.reasoning.empty());
    }
}

TEST_F(Gemma4SeparateEnvelopeEndTest, ProductionEndRecoversThreeSeparateEnvelopes) {
    const std::string text = joinedEnvelopes(3);
    const auto expected = argsFor(3);
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
        expectCalls(out, expected);
        EXPECT_TRUE(out.content.empty());
    }
}

TEST_F(Gemma4SeparateEnvelopeEndTest, ProductionEndRecoversManySeparateEnvelopes) {
    const std::string text = joinedEnvelopes(4);
    const auto expected = argsFor(4);
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
        expectCalls(out, expected);
        EXPECT_TRUE(out.content.empty());
    }
}

TEST_F(Gemma4SeparateEnvelopeEndTest, ProductionEndKeepsContentAfterAClosedEnvelope) {
    const std::string text = envelope(1) + "AFTER";
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
        expectCalls(out, argsFor(1));
        EXPECT_EQ(out.content, "AFTER");
        expectNoToolMarkup(out.content);
    }
}

TEST_F(Gemma4SeparateEnvelopeEndTest, ProductionEndKeepsContentBetweenAndAfterSeparateEnvelopes) {
    const std::string text = "BEFORE" + envelope(1) + "MID" + envelope(2) + "LATE" + envelope(3) + "AFTER";
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
        expectCalls(out, argsFor(3));
        EXPECT_EQ(out.content, "BEFOREMIDLATEAFTER");
        expectNoToolMarkup(out.content);
    }
}

TEST_F(Gemma4SeparateEnvelopeEndTest, RepeatedProductionEndDoesNotDuplicateSeparateEnvelopes) {
    const std::string text = joinedEnvelopes(2);
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        OutputParser parser(*tokenizer, "gemma4", "gemma4", questionTools());
        Outcome out;
        for (const auto& chunk : partition.chunks) {
            auto delta = parser.parseChunk(chunk, {}, true, ov::genai::GenerationFinishReason::NONE);
            if (delta.has_value())
                absorb(out, *delta);
        }
        auto held = std::shared_ptr<OutputParser>(&parser, [](OutputParser*) {});
        OVMSTextStreamer streamer(*tokenizer, held, true,
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
        const std::vector<Call> afterFirst = out.calls;
        streamer.end();
        EXPECT_FALSE(streamer.hadParserError());
        ASSERT_EQ(out.calls.size(), afterFirst.size());
        ASSERT_EQ(afterFirst.size(), 2u);
        for (size_t i = 0; i < afterFirst.size(); ++i) {
            EXPECT_EQ(out.calls[i].index, afterFirst[i].index);
            EXPECT_EQ(out.calls[i].name, afterFirst[i].name);
            EXPECT_EQ(out.calls[i].arguments, afterFirst[i].arguments);
        }
        expectCalls(out, argsFor(2));
    }
}
