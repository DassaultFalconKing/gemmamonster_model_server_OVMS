//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//*****************************************************************************

// Argument seams through one OVMSTextStreamer::end(): quoted tags stay inside
// strings, Windows paths stay literal JSON values, and invalid guided JSON
// does not become an executable call. Characters between <|\"|> are literal.

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
        ToolSchemaWrapper{nullptr, R"({"type":"object","properties":{}}})"});
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

std::string wrapCall(const std::string& body) {
    return "<|tool_call>call:question{" + body + "}<tool_call|>";
}

void expectOne(const Outcome& out, const std::string& arguments) {
    ASSERT_EQ(out.calls.size(), 1u);
    EXPECT_EQ(out.calls[0].index, 0);
    EXPECT_EQ(out.calls[0].name, "question");
    EXPECT_EQ(out.calls[0].arguments, arguments);
    EXPECT_TRUE(out.content.empty());
}

class Gemma4ArgumentSeamEndTest : public testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        tokenizer = std::make_unique<ov::genai::Tokenizer>(defaultTokenizerPath());
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }
};

std::unique_ptr<ov::genai::Tokenizer> Gemma4ArgumentSeamEndTest::tokenizer;

}  // namespace

TEST_F(Gemma4ArgumentSeamEndTest, QuotedEndTagInsideNativeStringDoesNotStealRemainder) {
    const std::string note = "see <tool_call|> and <|tool_call> inside";
    const std::string text = "BEFORE" + wrapCall("note:<|\"|>" + note + "<|\"|>") +
                             "AFTER" + wrapCall("x:2") + "TAIL";
    const std::string noteJson = std::string("{\"note\":\"") + note + "\"}";
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
        ASSERT_EQ(out.calls.size(), 2u);
        EXPECT_EQ(out.calls[0].index, 0);
        EXPECT_EQ(out.calls[0].name, "question");
        EXPECT_EQ(out.calls[0].arguments, noteJson);
        EXPECT_EQ(out.calls[1].index, 1);
        EXPECT_EQ(out.calls[1].name, "question");
        EXPECT_EQ(out.calls[1].arguments, R"({"x":2})");
        EXPECT_EQ(out.content, "BEFOREAFTERTAIL");
        EXPECT_EQ(out.content.find("<tool_call|>"), std::string::npos);
        EXPECT_EQ(out.content.find("<|tool_call>"), std::string::npos);
    }
}

TEST_F(Gemma4ArgumentSeamEndTest, QuotedEndTagInsideJsonStringDoesNotStealRemainder) {
    const std::string text =
        "BEFORE<|tool_call>call:question{note:\"see <tool_call|> inside\"}"
        "call:question{x:2}<tool_call|>TAIL";
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
        ASSERT_EQ(out.calls.size(), 2u);
        EXPECT_EQ(out.calls[0].index, 0);
        EXPECT_EQ(out.calls[0].name, "question");
        EXPECT_EQ(out.calls[0].arguments, R"({"note":"see <tool_call|> inside"})");
        EXPECT_EQ(out.calls[1].index, 1);
        EXPECT_EQ(out.calls[1].name, "question");
        EXPECT_EQ(out.calls[1].arguments, R"({"x":2})");
        EXPECT_EQ(out.content, "BEFORETAIL");
        EXPECT_EQ(out.content.find("<tool_call|>"), std::string::npos);
    }
}

TEST_F(Gemma4ArgumentSeamEndTest, WindowsPathsRemainJsonArrayNotStringifiedJson) {
    const std::string text = wrapCall(
        "paths:[<|\"|>C:\\Users\\a<|\"|>,<|\"|>D:\\data\\b.txt<|\"|>]");
    const std::string expected = R"({"paths":["C:\\Users\\a","D:\\data\\b.txt"]})";
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
        expectOne(out, expected);
        EXPECT_EQ(out.calls[0].arguments.find("\"paths\":\"["), std::string::npos);
        EXPECT_NE(out.calls[0].arguments.find("["), std::string::npos);
    }
}

TEST_F(Gemma4ArgumentSeamEndTest, FinishInsideUnclosedQuotedWindowsPath) {
    const std::string text = "<|tool_call>call:question{path:<|\"|>C:\\Users\\unclosed";
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
        EXPECT_TRUE(out.calls.empty());
    }
}

TEST_F(Gemma4ArgumentSeamEndTest, EscapeMatrixEveryBytePreservesLiteralStringsAndTypes) {
    struct Payload {
        const char* name;
        std::string wire;
        std::string arguments;
    };
    const std::string twoSlashes(2, '\\');
    const std::string fourSlashes(4, '\\');
    const std::vector<Payload> payloads = {
        {"plain", wrapCall("s:<|\"|>plain<|\"|>"), R"({"s":"plain"})"},
        {"embedded-quote", wrapCall("s:<|\"|>say \"hi\"<|\"|>"), R"({"s":"say \"hi\""})"},
        {"users-path", wrapCall("s:<|\"|>C:\\Users\\a<|\"|>"), R"({"s":"C:\\Users\\a"})"},
        {"temp-path-backslash-t-n", wrapCall("s:<|\"|>C:\\temp\\notes.txt<|\"|>"), R"({"s":"C:\\temp\\notes.txt"})"},
        {"nested-object", wrapCall("obj:{n:<|\"|>x<|\"|>,k:2}"), R"({"obj":{"n":"x","k":2}})"},
        {"nested-array", wrapCall("rows:[[1,2],[3,4]]"), R"({"rows":[[1,2],[3,4]]})"},
        {"scalars", wrapCall("flag:true,off:false,empty:null,n:-2"), R"({"flag":true,"off":false,"empty":null,"n":-2})"},
        {"empty-string", wrapCall("s:<|\"|><|\"|>"), R"({"s":""})"},
        {"two-backslashes", wrapCall("s:<|\"|>" + twoSlashes + "<|\"|>"), std::string("{\"s\":\"") + fourSlashes + "\"}"},
        {"unicode", wrapCall("s:<|\"|>zażółć<|\"|>"), R"({"s":"zażółć"})"},
        {"comma-inside-string", wrapCall("s:<|\"|>a,b<|\"|>"), R"({"s":"a,b"})"},
    };
    ASSERT_EQ(payloads.size(), 11u);
    for (const auto& payload : payloads) {
        for (const auto& partition : partitionsOf(payload.wire)) {
            SCOPED_TRACE(payload.name);
            SCOPED_TRACE(partition.name);
            const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
            expectOne(out, payload.arguments);
        }
    }
}

TEST_F(Gemma4ArgumentSeamEndTest, InvalidGuidedJsonCannotFallBackToNativeCoercion) {
    const std::string text = R"(<|tool_call>call:question{x:{"a":}}call:question{x:7}<tool_call|>)";
    for (const auto& partition : partitionsOf(text)) {
        SCOPED_TRACE(partition.name);
        const Outcome out = runProductionEnd(*tokenizer, partition.chunks);
        ASSERT_EQ(out.calls.size(), 1u);
        EXPECT_EQ(out.calls[0].index, 0);
        EXPECT_EQ(out.calls[0].name, "question");
        EXPECT_EQ(out.calls[0].arguments, R"({"x":7})");
        EXPECT_EQ(out.calls[0].arguments.find("\"a\""), std::string::npos);
    }
}
