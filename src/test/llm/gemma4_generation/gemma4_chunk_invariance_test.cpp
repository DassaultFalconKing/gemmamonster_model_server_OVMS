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

#include <cstdlib>
#include <memory>
#include <string>
#include <vector>

#include "src/llm/io_processing/output_parser.hpp"

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

std::vector<Delta> collectRawDeltas(OutputParser& parser, const std::vector<std::string>& chunks) {
    std::vector<Delta> deltas;
    auto push = [&](const std::string& chunk, ov::genai::GenerationFinishReason reason) {
        auto delta = parser.parseChunk(chunk, {}, true, reason);
        if (delta.has_value()) {
            deltas.push_back(std::move(*delta));
            return true;
        }
        return false;
    };
    for (const auto& chunk : chunks)
        push(chunk, ov::genai::GenerationFinishReason::NONE);
    int quiet = 0;
    for (int i = 0; i < 16 && quiet < 3; ++i) {
        if (push("", ov::genai::GenerationFinishReason::STOP))
            quiet = 0;
        else
            ++quiet;
    }
    return deltas;
}

struct ToolSemantic {
    std::vector<std::pair<int, std::string>> calls;  // index, arguments
};

ToolSemantic toolSemantics(const std::vector<Delta>& deltas) {
    ToolSemantic out;
    for (const auto& delta : deltas) {
        if (const auto* tool = std::get_if<ToolCallDelta>(&delta)) {
            if (!tool->arguments.empty())
                out.calls.emplace_back(tool->index, tool->arguments);
        }
    }
    return out;
}

bool sameToolSemantics(const ToolSemantic& a, const ToolSemantic& b) {
    return a.calls == b.calls;
}

struct ReasoningSemantic {
    std::string reasoning;
    std::string content;
};

ReasoningSemantic reasoningSemantics(const std::vector<Delta>& deltas) {
    ReasoningSemantic out;
    for (const auto& delta : deltas) {
        if (const auto* reasoning = std::get_if<ReasoningDelta>(&delta))
            out.reasoning += reasoning->text;
        if (const auto* content = std::get_if<ContentDelta>(&delta))
            out.content += content->text;
    }
    return out;
}

class Gemma4ChunkInvarianceTest : public testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        tokenizer = std::make_unique<ov::genai::Tokenizer>(defaultTokenizerPath());
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }

    ToolSemantic parseTools(const std::vector<std::string>& chunks) {
        OutputParser parser(*tokenizer, "gemma4", "gemma4", questionTools());
        return toolSemantics(collectRawDeltas(parser, chunks));
    }

    ReasoningSemantic parseReasoning(const std::vector<std::string>& chunks) {
        OutputParser parser(*tokenizer, "gemma4", "gemma4", questionTools());
        return reasoningSemantics(collectRawDeltas(parser, chunks));
    }
};

std::unique_ptr<ov::genai::Tokenizer> Gemma4ChunkInvarianceTest::tokenizer;

}  // namespace

TEST_F(Gemma4ChunkInvarianceTest, SingleCanonicalCallIndependentOfPartition) {
    const std::string text = R"(<|tool_call>call:question{x:1}<tool_call|>)";
    std::vector<std::string> byteChunks;
    for (char c : text)
        byteChunks.emplace_back(1, c);

    const auto whole = parseTools({text});
    const auto bytes = parseTools(byteChunks);
    const auto beforeBrace = parseTools({"<|tool_call>call:question", "{x:1}<tool_call|>"});
    const auto beforeClose = parseTools({"<|tool_call>call:question{x:1}", "<tool_call|>"});
    const auto tokenish = parseTools({"<|tool_call>", "call:question", "{x:1}", "<tool_call|>"});

    ASSERT_EQ(whole.calls.size(), 1u);
    EXPECT_EQ(whole.calls[0].first, 0);
    EXPECT_TRUE(sameToolSemantics(whole, bytes));
    EXPECT_TRUE(sameToolSemantics(whole, beforeBrace));
    EXPECT_TRUE(sameToolSemantics(whole, beforeClose));
    EXPECT_TRUE(sameToolSemantics(whole, tokenish));
}

TEST_F(Gemma4ChunkInvarianceTest, TwoCanonicalCallsIndependentOfPartition) {
    const std::string a = R"(<|tool_call>call:question{x:1}<tool_call|>)";
    const std::string b = R"(<|tool_call>call:question{x:2}<tool_call|>)";
    const std::string text = a + b;

    const auto oneChunk = parseTools({text});
    const auto twoChunks = parseTools({a, b});
    std::vector<std::string> many;
    for (size_t i = 0; i < text.size(); i += 5)
        many.push_back(text.substr(i, 5));
    const auto manyChunks = parseTools(many);

    ASSERT_EQ(oneChunk.calls.size(), 2u);
    EXPECT_EQ(oneChunk.calls[0].first, 0);
    EXPECT_EQ(oneChunk.calls[1].first, 1);
    EXPECT_TRUE(sameToolSemantics(oneChunk, twoChunks));
    EXPECT_TRUE(sameToolSemantics(oneChunk, manyChunks));
}

TEST_F(Gemma4ChunkInvarianceTest, MalformedThenValidKeepsValidAtIndexZero) {
    const std::string text =
        R"(<|tool_call>call:question{x:12foo}<tool_call|>)"
        R"(<|tool_call>call:question{x:1}<tool_call|>)";
    const auto oneChunk = parseTools({text});
    std::vector<std::string> bytes;
    for (char c : text)
        bytes.emplace_back(1, c);
    const auto byteChunks = parseTools(bytes);

    ASSERT_EQ(oneChunk.calls.size(), 1u);
    EXPECT_EQ(oneChunk.calls[0].first, 0);
    EXPECT_TRUE(sameToolSemantics(oneChunk, byteChunks));
}

TEST_F(Gemma4ChunkInvarianceTest, ReasoningContentIndependentOfPartition) {
    const std::string text = "<|channel>thought\nsecret<channel|>answer";
    std::vector<std::string> bytes;
    for (char c : text)
        bytes.emplace_back(1, c);

    const auto whole = parseReasoning({text});
    const auto split = parseReasoning(bytes);
    const auto phased = parseReasoning({"<|channel>thought\n", "secret", "<channel|>", "answer"});

    EXPECT_EQ(whole.reasoning, "secret");
    EXPECT_EQ(whole.content, "answer");
    EXPECT_EQ(whole.reasoning, split.reasoning);
    EXPECT_EQ(whole.content, split.content);
    EXPECT_EQ(whole.reasoning, phased.reasoning);
    EXPECT_EQ(whole.content, phased.content);
}
