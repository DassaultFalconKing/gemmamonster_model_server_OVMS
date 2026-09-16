//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//*****************************************************************************

// RED-only adversarial coverage for Gemma4 streaming ToolCallDelta publication
// timing. These tests collect RAW deltas in publication order and must NOT use
// the sanitized ParsedOutput helper, which drops incomplete tool calls with
// empty arguments and would hide phantom header publication.

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

std::vector<std::string> splitInto(const std::string& input, size_t piece) {
    std::vector<std::string> chunks;
    for (size_t i = 0; i < input.size(); i += piece)
        chunks.push_back(input.substr(i, piece));
    return chunks;
}

// Feeds string chunks through the production OutputParser exactly as streaming
// would, then drains the state machine with STOP. Returns every published
// Delta in order, including ToolCallDelta{id, name, ""} headers that carry no
// arguments.
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
    for (int i = 0; i < 12 && quiet < 3; ++i) {
        if (push("", ov::genai::GenerationFinishReason::STOP))
            quiet = 0;
        else
            ++quiet;
    }
    return deltas;
}

size_t countHeaders(const std::vector<Delta>& deltas) {
    size_t count = 0;
    for (const auto& delta : deltas) {
        if (const auto* tool = std::get_if<ToolCallDelta>(&delta)) {
            if (tool->id.has_value() || tool->name.has_value())
                ++count;
        }
    }
    return count;
}

std::vector<int> executableIndices(const std::vector<Delta>& deltas) {
    std::vector<int> indices;
    for (const auto& delta : deltas) {
        if (const auto* tool = std::get_if<ToolCallDelta>(&delta)) {
            if (!tool->arguments.empty())
                indices.push_back(tool->index);
        }
    }
    return indices;
}

std::string contentText(const std::vector<Delta>& deltas) {
    std::string text;
    for (const auto& delta : deltas) {
        if (const auto* content = std::get_if<ContentDelta>(&delta))
            text += content->text;
    }
    return text;
}

class Gemma4PhantomToolCallTest : public testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        tokenizer = std::make_unique<ov::genai::Tokenizer>(defaultTokenizerPath());
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }

    std::vector<Delta> parseRaw(const std::string& input, size_t piece = 7) {
        OutputParser parser(*tokenizer, "gemma4", "gemma4", questionTools());
        return collectRawDeltas(parser, splitInto(input, piece));
    }
};

std::unique_ptr<ov::genai::Tokenizer> Gemma4PhantomToolCallTest::tokenizer;

}  // namespace

TEST_F(Gemma4PhantomToolCallTest, MalformedNumberPublishesNoExecutableHeader) {
    // `12foo` is not a valid JSON number lexeme, so no executable call exists.
    // Fail-closed publication must not emit id/name before arguments validate.
    auto deltas = parseRaw(R"(<|tool_call>call:question{x:12foo}<tool_call|>)");
    EXPECT_EQ(countHeaders(deltas), 0u);
    EXPECT_TRUE(executableIndices(deltas).empty());
}

TEST_F(Gemma4PhantomToolCallTest, MalformedNestedStructurePublishesNoExecutableHeader) {
    auto deltas = parseRaw(R"(<|tool_call>call:question{questions:[{x:1}<tool_call|>)");
    EXPECT_EQ(countHeaders(deltas), 0u);
    EXPECT_TRUE(executableIndices(deltas).empty());
}

TEST_F(Gemma4PhantomToolCallTest, UnknownRegisteredToolPublishesNoHeader) {
    auto deltas = parseRaw(R"(<|tool_call>call:not_in_request{x:1}<tool_call|>)");
    EXPECT_EQ(countHeaders(deltas), 0u);
    EXPECT_TRUE(executableIndices(deltas).empty());
}

TEST_F(Gemma4PhantomToolCallTest, MalformedThenValidKeepsIndexZero) {
    auto deltas = parseRaw(
        R"(<|tool_call>call:question{x:12foo}<tool_call|>)"
        R"(<|tool_call>call:question{x:1}<tool_call|>)");
    // The malformed call must not consume a tool-call index.
    EXPECT_EQ(countHeaders(deltas), 1u);
    ASSERT_EQ(executableIndices(deltas).size(), 1u);
    EXPECT_EQ(executableIndices(deltas)[0], 0);
}

TEST_F(Gemma4PhantomToolCallTest, StreamingSplitMalformedPublishesNothing) {
    // Header and body arrive in separate chunks: the publication-timing probe.
    OutputParser parser(*tokenizer, "gemma4", "gemma4", questionTools());
    auto deltas = collectRawDeltas(parser,
        {"<|tool_call>", "call:question", "{x:12foo}", "<tool_call|>"});
    EXPECT_EQ(countHeaders(deltas), 0u);
    EXPECT_TRUE(executableIndices(deltas).empty());
}

TEST_F(Gemma4PhantomToolCallTest, CanonicalTwoEnvelopesYieldTwoCalls) {
    auto deltas = parseRaw(
        R"(<|tool_call>call:question{x:1}<tool_call|>)"
        R"(<|tool_call>call:question{x:2}<tool_call|>)");
    EXPECT_EQ(countHeaders(deltas), 2u);
    EXPECT_EQ(executableIndices(deltas), (std::vector<int>{0, 1}));
}

TEST_F(Gemma4PhantomToolCallTest, OneEnvelopeGarbageMulticallPublishesNothing) {
    // Extra `call:` before `<tool_call|>` fails closed for the whole envelope.
    auto deltas = parseRaw(
        R"(<|tool_call>call:question{x:1} garbage call:question{x:2}<tool_call|>)");
    EXPECT_EQ(countHeaders(deltas), 0u);
    EXPECT_TRUE(executableIndices(deltas).empty());
}

TEST_F(Gemma4PhantomToolCallTest, OneEnvelopeAdjacentMulticallPublishesNothing) {
    auto deltas = parseRaw(
        R"(<|tool_call>call:question{x:1}call:question{x:2}<tool_call|>)");
    EXPECT_EQ(countHeaders(deltas), 0u);
    EXPECT_TRUE(executableIndices(deltas).empty());
}

TEST_F(Gemma4PhantomToolCallTest, StopBeforeEnvelopeClosePublishesNothing) {
    OutputParser parser(*tokenizer, "gemma4", "gemma4", questionTools());
    auto deltas = collectRawDeltas(parser, {"<|tool_call>call:question{x:1}"});
    EXPECT_EQ(countHeaders(deltas), 0u);
    EXPECT_TRUE(executableIndices(deltas).empty());
}

TEST_F(Gemma4PhantomToolCallTest, LengthBeforeEnvelopeClosePublishesNothing) {
    OutputParser parser(*tokenizer, "gemma4", "gemma4", questionTools());
    std::vector<Delta> deltas;
    auto push = [&](const std::string& chunk, ov::genai::GenerationFinishReason reason) {
        auto delta = parser.parseChunk(chunk, {}, true, reason);
        if (delta.has_value())
            deltas.push_back(std::move(*delta));
    };
    push("<|tool_call>call:question{x:1}", ov::genai::GenerationFinishReason::NONE);
    for (int i = 0; i < 8; ++i)
        push("", ov::genai::GenerationFinishReason::LENGTH);
    EXPECT_EQ(countHeaders(deltas), 0u);
    EXPECT_TRUE(executableIndices(deltas).empty());
}

TEST_F(Gemma4PhantomToolCallTest, RepeatedFinalizationDoesNotDuplicateCommittedCall) {
    OutputParser parser(*tokenizer, "gemma4", "gemma4", questionTools());
    std::vector<Delta> deltas;
    auto push = [&](const std::string& chunk, ov::genai::GenerationFinishReason reason) {
        auto delta = parser.parseChunk(chunk, {}, true, reason);
        if (delta.has_value())
            deltas.push_back(std::move(*delta));
    };
    push(R"(<|tool_call>call:question{x:1}<tool_call|>)", ov::genai::GenerationFinishReason::NONE);
    for (int i = 0; i < 8; ++i)
        push("", ov::genai::GenerationFinishReason::STOP);
    EXPECT_EQ(countHeaders(deltas), 1u);
    EXPECT_EQ(executableIndices(deltas), (std::vector<int>{0}));
}

TEST_F(Gemma4PhantomToolCallTest, CanonicalValidCallPublishesOneAtomicDelta) {
    auto deltas = parseRaw(R"(<|tool_call>call:question{x:1}<tool_call|>)");
    EXPECT_EQ(countHeaders(deltas), 1u);
    ASSERT_EQ(executableIndices(deltas).size(), 1u);
    EXPECT_EQ(executableIndices(deltas)[0], 0);
    size_t toolDeltas = 0;
    for (const auto& delta : deltas) {
        if (const auto* tool = std::get_if<ToolCallDelta>(&delta)) {
            ++toolDeltas;
            EXPECT_TRUE(tool->id.has_value());
            EXPECT_TRUE(tool->name.has_value());
            EXPECT_FALSE(tool->arguments.empty());
        }
    }
    EXPECT_EQ(toolDeltas, 1u);
}
