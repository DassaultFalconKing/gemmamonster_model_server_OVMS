//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//*****************************************************************************

#include <gtest/gtest.h>

#include <cstdlib>
#include <memory>
#include <string>
#include <vector>

#include "src/llm/io_processing/gemma4/gemma4_tool_parser.hpp"

using namespace ovms;

namespace {

std::string tokenizerPath() {
    if (const char* path = std::getenv("OVMS_TEST_TOKENIZER_PATH"))
        return path;
    return "C:/llm/models/runtime/gemma4-26-heretic-google-current";
}

ToolsSchemas_t guardedTool() {
    ToolsSchemas_t tools;
    tools.emplace("guarded", ToolSchemaWrapper{
                                 nullptr,
                                 R"({"type":"object","properties":{"value":{}}})"});
    return tools;
}

std::vector<ToolCallDelta> collectCalls(ov::genai::Tokenizer& tokenizer, const std::string& wire) {
    Gemma4ToolParser parser(tokenizer, guardedTool());
    std::vector<ToolCallDelta> calls;
    for (int i = 0; i < 12; ++i) {
        const auto delta = parser.parseChunk(i == 0 ? wire : "", {}, ov::genai::GenerationFinishReason::NONE);
        if (delta.has_value()) {
            if (const auto* call = std::get_if<ToolCallDelta>(&*delta))
                calls.push_back(*call);
        }
    }
    return calls;
}

void expectOnlyRecoveryCall(ov::genai::Tokenizer& tokenizer, const std::string& malformed) {
    const std::string recovery = "<|tool_call>call:guarded{value:7}<tool_call|>";
    const auto calls = collectCalls(tokenizer, malformed + recovery);
    ASSERT_EQ(calls.size(), 1u);
    EXPECT_EQ(calls[0].index, 0);
    ASSERT_TRUE(calls[0].name.has_value());
    EXPECT_EQ(*calls[0].name, "guarded");
    EXPECT_EQ(calls[0].arguments, R"({"value":7})");
}

class Gemma4F10GuardTest : public testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        tokenizer = std::make_unique<ov::genai::Tokenizer>(tokenizerPath());
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }
};

std::unique_ptr<ov::genai::Tokenizer> Gemma4F10GuardTest::tokenizer;

}  // namespace

TEST_F(Gemma4F10GuardTest, OversizedCandidateIsRejectedWithoutTruncateAndExecute) {
    const std::string oversized =
        "<|tool_call>call:guarded{value:<|\"|>" + std::string(70 * 1024, 'x') +
        "<|\"|>}<tool_call|>";
    expectOnlyRecoveryCall(*tokenizer, oversized);
}

TEST_F(Gemma4F10GuardTest, ExcessiveContainerDepthIsRejectedWithoutCommittedDelta) {
    const std::string deeplyNested =
        "<|tool_call>call:guarded{value:" + std::string(70, '[') + "0" +
        std::string(70, ']') + "}<tool_call|>";
    expectOnlyRecoveryCall(*tokenizer, deeplyNested);
}

TEST_F(Gemma4F10GuardTest, UnterminatedNativeStringRecoversAtEnvelopeBoundary) {
    expectOnlyRecoveryCall(
        *tokenizer, R"(<|tool_call>call:guarded{value:<|"|>unterminated}<tool_call|>)");
}

TEST_F(Gemma4F10GuardTest, UnterminatedJsonStringRecoversAtEnvelopeBoundary) {
    expectOnlyRecoveryCall(
        *tokenizer, R"(<|tool_call>call:guarded{value:"unterminated}<tool_call|>)");
}

TEST_F(Gemma4F10GuardTest, UnterminatedContainerRecoversAtEnvelopeBoundary) {
    expectOnlyRecoveryCall(
        *tokenizer, R"(<|tool_call>call:guarded{value:[1,2}<tool_call|>)");
}
