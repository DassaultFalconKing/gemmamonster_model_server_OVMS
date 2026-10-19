//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//*****************************************************************************

// Registry-path number lexemes (R13) and bare-call boundaries (R14).
// One data pass plus a single empty STOP. This is not the historical helper
// that repeats STOP, and it is not Qwen proof.

#include <gtest/gtest.h>

#include <cstdlib>
#include <filesystem>
#include <memory>
#include <string>
#include <variant>
#include <vector>

#include "src/llm/io_processing/gemma4/gemma4_tool_parser.hpp"

using namespace ovms;

namespace {

std::string tokenizerPath() {
    if (const char* path = std::getenv("OVMS_TEST_TOKENIZER_PATH"))
        return path;
    const std::string cwd = std::filesystem::current_path().string();
    const size_t bazelOut = cwd.find("bazel-out");
    const std::string workspace = bazelOut == std::string::npos ? cwd : cwd.substr(0, bazelOut);
    return workspace + "/src/test/llm_testing/HuggingFaceTB/SmolLM2-360M-Instruct";
}

ToolsSchemas_t toolsFor(const std::string& name) {
    ToolsSchemas_t tools;
    tools.emplace(name, ToolSchemaWrapper{nullptr, R"({"type":"object","properties":{"n":{},"x":{}}})"});
    return tools;
}

std::vector<ToolCallDelta> toolDeltas(ov::genai::Tokenizer& tokenizer, const std::string& name, const std::vector<std::string>& chunks) {
    Gemma4ToolParser parser(tokenizer, toolsFor(name));
    std::vector<ToolCallDelta> calls;
    auto take = [&](const std::string& chunk, ov::genai::GenerationFinishReason reason) {
        auto delta = parser.parseChunk(chunk, {}, reason);
        if (!delta.has_value())
            return;
        if (const auto* call = std::get_if<ToolCallDelta>(&*delta))
            calls.push_back(*call);
    };
    for (size_t i = 0; i < chunks.size(); ++i) {
        const bool last = i + 1 == chunks.size();
        take(chunks[i], last ? ov::genai::GenerationFinishReason::STOP : ov::genai::GenerationFinishReason::NONE);
    }
    take("", ov::genai::GenerationFinishReason::STOP);
    return calls;
}

class GemmaArgumentBoundaryTest : public testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        tokenizer = std::make_unique<ov::genai::Tokenizer>(tokenizerPath());
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }
};

std::unique_ptr<ov::genai::Tokenizer> GemmaArgumentBoundaryTest::tokenizer;

}  // namespace

TEST_F(GemmaArgumentBoundaryTest, RegistryNumbersKeepTheirLexemes) {
    const std::vector<std::pair<std::string, std::string>> cases{
        {"0", R"({"n":0})"},
        {"-0", R"({"n":-0})"},
        {"1", R"({"n":1})"},
        {"-2", R"({"n":-2})"},
        {"1.0", R"({"n":1.0})"},
        {"1.5", R"({"n":1.5})"},
        {"1e-10", R"({"n":1e-10})"},
        {"1E+2", R"({"n":1E+2})"},
        {"9007199254740993", R"({"n":9007199254740993})"},
    };
    for (const auto& [lexeme, expected] : cases) {
        SCOPED_TRACE(lexeme);
        const std::string wire = "<|tool_call>call:num{n:" + lexeme + "}<tool_call|>";
        const auto calls = toolDeltas(*tokenizer, "num", {wire});
        ASSERT_EQ(calls.size(), 1u);
        EXPECT_EQ(calls[0].index, 0);
        ASSERT_TRUE(calls[0].name.has_value());
        EXPECT_EQ(*calls[0].name, "num");
        EXPECT_EQ(calls[0].arguments, expected);
    }
}

TEST_F(GemmaArgumentBoundaryTest, InvalidNumberLexemesPublishNoCall) {
    for (const std::string lexeme : {"01", "+1"}) {
        SCOPED_TRACE(lexeme);
        const std::string wire = "<|tool_call>call:num{n:" + lexeme + "}<tool_call|>";
        EXPECT_TRUE(toolDeltas(*tokenizer, "num", {wire}).empty());
    }
}

TEST_F(GemmaArgumentBoundaryTest, BareCallAtCursorPublishesAndMidLineDoesNot) {
    const auto atStart = toolDeltas(*tokenizer, "question", {R"(call:question{x:1}<tool_call|>)"});
    ASSERT_EQ(atStart.size(), 1u);
    ASSERT_TRUE(atStart[0].name.has_value());
    EXPECT_EQ(*atStart[0].name, "question");
    EXPECT_EQ(atStart[0].arguments, R"({"x":1})");

    const auto afterNewline = toolDeltas(*tokenizer, "question", {"answer\n", R"(call:question{x:1}<tool_call|>)"});
    ASSERT_EQ(afterNewline.size(), 1u);
    EXPECT_EQ(afterNewline[0].arguments, R"({"x":1})");

    const auto midLine = toolDeltas(*tokenizer, "question", {R"(hello call:question{x:1}<tool_call|>)"});
    EXPECT_TRUE(midLine.empty());

    const auto unknown = toolDeltas(*tokenizer, "question", {R"(call:not_registered{x:1}<tool_call|>)"});
    EXPECT_TRUE(unknown.empty());
}

TEST_F(GemmaArgumentBoundaryTest, IndentedBareCallOnLogicalBoundaryPublishesTheCall) {
    const auto calls = toolDeltas(*tokenizer, "question", {"answer\n", "  \tcall:question{x:1}<tool_call|>"});
    ASSERT_EQ(calls.size(), 1u);
    ASSERT_TRUE(calls[0].name.has_value());
    EXPECT_EQ(*calls[0].name, "question");
    EXPECT_EQ(calls[0].arguments, R"({"x":1})");
}
