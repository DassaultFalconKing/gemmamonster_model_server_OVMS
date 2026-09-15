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

ToolsSchemas_t tools() {
    ToolsSchemas_t result;
    result.emplace("question", ToolSchemaWrapper{nullptr,
        R"({"type":"object","properties":{"questions":{"type":"array"}},"required":["questions"]})"});
    return result;
}
}  // namespace

TEST(Gemma4SpecialTokenHandoffTest, DetectsAdjacentToolMarkerWithDefaultDecodeMode) {
    ov::genai::Tokenizer tokenizer(tokenizerPath);
    OutputParser parser(tokenizer, "gemma4", "gemma4", tools());

    const std::string input =
        "<|channel>thought\nNeed a tool<channel|><|tool_call>call:question{questions:[]}<tool_call|>";
    auto tensor = tokenizer.encode(input).input_ids;
    std::vector<int64_t> tokens(tensor.data<int64_t>(), tensor.data<int64_t>() + tensor.get_size());

    // false mirrors the production default: visible special tokens are enabled only
    // while a parser phase requires them. The tool opener must survive the handoff
    // from reasoning even though the previous phase left special-token decoding on.
    ParsedOutput parsed = ovms::test::parseWithStreamer(tokenizer, parser, tokens, true, false);

    EXPECT_EQ(parsed.reasoning, "Need a tool");
    ASSERT_EQ(parsed.toolCalls.size(), 1u);
    EXPECT_EQ(parsed.toolCalls[0].name, "question");
    EXPECT_EQ(parsed.toolCalls[0].arguments, R"({"questions":[]})");
}
