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
#include <openvino/genai/tokenizer.hpp>

#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "../../../llm/io_processing/output_parser.hpp"
#include "output_parser_test_utils.hpp"
#include "../../platform_utils.hpp"

using namespace ovms;

namespace {
#ifdef _WIN32
const std::string tokenizerPath = getWindowsRepoRootPath() + "\\src\\test\\llm_testing\\OpenVINO\\gemma-4-E4B-it-int4-ov";
#else
const std::string tokenizerPath = "/ovms/src/test/llm_testing/OpenVINO/gemma-4-E4B-it-int4-ov";
#endif

const std::string questionSchema =
    R"({"type":"object","properties":{"questions":{"type":"array"},"x":{}},"additionalProperties":true})";

ToolsSchemas_t questionTools() {
    ToolsSchemas_t tools;
    tools.emplace("question", ToolSchemaWrapper{nullptr, questionSchema});
    return tools;
}

void appendDelta(ParsedOutput& output, std::vector<ToolCall>& calls, const std::optional<Delta>& delta) {
    if (!delta.has_value())
        return;
    std::visit(overloaded{
                   [&](const ContentDelta& d) { output.content += d.text; },
                   [&](const ReasoningDelta& d) { output.reasoning += d.text; },
                   [&](const ToolCallDelta& d) {
                       if (d.index < 0)
                           return;
                       const auto idx = static_cast<size_t>(d.index);
                       if (idx >= calls.size())
                           calls.resize(idx + 1);
                       auto& call = calls[idx];
                       if (d.id)
                           call.id = *d.id;
                       if (d.name)
                           call.name = *d.name;
                       call.arguments += d.arguments;
                   },
                   [](const FinishDelta&) {},
                   [](const AudioDelta&) {},
               },
        *delta);
}

class Gemma4UpstreamRefitContractTest : public ::testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        tokenizer = std::make_unique<ov::genai::Tokenizer>(tokenizerPath);
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }

    ParsedOutput parse(const std::string& input, const ToolsSchemas_t& tools = questionTools()) {
        OutputParser parser(*tokenizer, "gemma4", "gemma4", tools);
        auto tensor = tokenizer->encode(input).input_ids;
        std::vector<int64_t> tokens(tensor.data<int64_t>(), tensor.data<int64_t>() + tensor.get_size());
        return ovms::test::parseWithStreamer(*tokenizer, parser, tokens, true, true);
    }
};

std::unique_ptr<ov::genai::Tokenizer> Gemma4UpstreamRefitContractTest::tokenizer;

}  // namespace

TEST_F(Gemma4UpstreamRefitContractTest, ParsesNestedNativeArgumentsRecursively) {
    const std::string input =
        R"(<|tool_call>call:question{questions:[{question:<|"|>Pick?<|"|>,options:[{label:<|"|>A<|"|>,meta:{score:22.8,flags:[true,false,null,3]}}]}]}<tool_call|>)";
    auto parsed = parse(input);
    ASSERT_EQ(parsed.toolCalls.size(), 1u);
    EXPECT_EQ(parsed.toolCalls[0].name, "question");
    EXPECT_EQ(parsed.toolCalls[0].arguments,
        R"({"questions":[{"question":"Pick?","options":[{"label":"A","meta":{"score":22.8,"flags":[true,false,null,3]}}]}]})");
}

TEST_F(Gemma4UpstreamRefitContractTest, AcceptsParenthesizedNativeArguments) {
    auto parsed = parse(R"(<|tool_call>call:question(questions:[])<tool_call|>)");
    ASSERT_EQ(parsed.toolCalls.size(), 1u);
    EXPECT_EQ(parsed.toolCalls[0].name, "question");
    EXPECT_EQ(parsed.toolCalls[0].arguments, R"({"questions":[]})");
}

TEST_F(Gemma4UpstreamRefitContractTest, RejectsUnknownRegisteredTool) {
    auto parsed = parse(R"(<|tool_call>call:not_in_request{x:1}<tool_call|>)");
    EXPECT_TRUE(parsed.toolCalls.empty());
}

TEST_F(Gemma4UpstreamRefitContractTest, RecoversBareKnownCallAtReasoningPhaseBoundary) {
    auto parsed = parse(R"(<|channel>thought
Need user input<channel|>call:question{questions:[]}<tool_call|>)");
    EXPECT_EQ(parsed.reasoning, "Need user input");
    ASSERT_EQ(parsed.toolCalls.size(), 1u);
    EXPECT_EQ(parsed.toolCalls[0].name, "question");
    EXPECT_EQ(parsed.toolCalls[0].arguments, R"({"questions":[]})");
}

TEST_F(Gemma4UpstreamRefitContractTest, RecoversBareKnownCallAtCrossChunkLineBoundary) {
    OutputParser parser(*tokenizer, "gemma4", "gemma4", questionTools());
    ParsedOutput output;
    std::vector<ToolCall> calls;

    appendDelta(output, calls, parser.parseChunk("Need a choice.\n", {}, true, ov::genai::GenerationFinishReason::NONE));
    appendDelta(output, calls, parser.parseChunk("call:question{questions:[]}<tool_call|>", {}, true, ov::genai::GenerationFinishReason::NONE));
    appendDelta(output, calls, parser.parseChunk("", {}, true, ov::genai::GenerationFinishReason::STOP));

    EXPECT_EQ(output.content, "Need a choice.\n");
    ASSERT_EQ(calls.size(), 1u);
    EXPECT_EQ(calls[0].name, "question");
    EXPECT_EQ(calls[0].arguments, R"({"questions":[]})");
}

TEST_F(Gemma4UpstreamRefitContractTest, DoesNotPromoteCrossChunkBareCallMidSentence) {
    OutputParser parser(*tokenizer, "gemma4", "gemma4", questionTools());
    ParsedOutput output;
    std::vector<ToolCall> calls;

    appendDelta(output, calls, parser.parseChunk("Documentation example: ", {}, true, ov::genai::GenerationFinishReason::NONE));
    appendDelta(output, calls, parser.parseChunk("call:question{questions:[]}", {}, true, ov::genai::GenerationFinishReason::STOP));

    EXPECT_TRUE(calls.empty());
    EXPECT_EQ(output.content, "Documentation example: call:question{questions:[]}");
}

TEST_F(Gemma4UpstreamRefitContractTest, PreservesValidNumberLexemesLosslessly) {
    const std::string input =
        R"(<|tool_call>call:question{x:123456789012345678901234567890.12345678901234567890e-42}<tool_call|>)";
    auto parsed = parse(input);
    ASSERT_EQ(parsed.toolCalls.size(), 1u);
    EXPECT_EQ(parsed.toolCalls[0].arguments,
        R"({"x":123456789012345678901234567890.12345678901234567890e-42})");
}

TEST_F(Gemma4UpstreamRefitContractTest, RejectsInvalidNumberLikeBareScalars) {
    for (const std::string invalid : {"12foo", "-x", "01", "1.", "1e"}) {
        SCOPED_TRACE(invalid);
        auto parsed = parse("<|tool_call>call:question{x:" + invalid + "}<tool_call|>");
        EXPECT_TRUE(parsed.toolCalls.empty());
    }
}

TEST_F(Gemma4UpstreamRefitContractTest, MalformedCallIsBoundedAndLaterValidCallSurvives) {
    const std::string input =
        R"(<|tool_call>call:question{questions:[{question:<|"|>broken<|"|>}<tool_call|><|tool_call>call:question{questions:[]}<tool_call|>)";
    auto parsed = parse(input);
    ASSERT_EQ(parsed.toolCalls.size(), 1u);
    EXPECT_EQ(parsed.toolCalls[0].name, "question");
    EXPECT_EQ(parsed.toolCalls[0].arguments, R"({"questions":[]})");
}
