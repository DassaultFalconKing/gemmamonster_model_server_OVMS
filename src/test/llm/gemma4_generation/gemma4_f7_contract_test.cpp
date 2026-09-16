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

#include <chrono>
#include <cstdlib>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "src/llm/apis/openai_completions.hpp"
#include "src/llm/apis/openai_responses.hpp"
#include "src/llm/io_processing/gemma4/gemma4_tool_parser.hpp"

using namespace ovms;

namespace {

std::string tokenizerPath() {
    if (const char* path = std::getenv("OVMS_TEST_TOKENIZER_PATH"))
        return path;
    return "C:/llm/models/runtime/gemma4-26-heretic-google-current";
}

ToolsSchemas_t arrayTool() {
    ToolsSchemas_t tools;
    tools.emplace("array_tool", ToolSchemaWrapper{
                                    nullptr,
                                    R"({"type":"object","properties":{"value":{}}})"});
    return tools;
}

std::vector<ToolCallDelta> parseNative(ov::genai::Tokenizer& tokenizer, const std::string& wire) {
    Gemma4ToolParser parser(tokenizer, arrayTool());
    std::vector<ToolCallDelta> calls;
    for (int i = 0; i < 8; ++i) {
        const auto delta = parser.parseChunk(i == 0 ? wire : "", {}, ov::genai::GenerationFinishReason::STOP);
        if (delta.has_value()) {
            if (const auto* call = std::get_if<ToolCallDelta>(&*delta))
                calls.push_back(*call);
        }
    }
    return calls;
}

template <typename Handler>
absl::Status parseRequest(ov::genai::Tokenizer& tokenizer, const std::string& json, Endpoint endpoint) {
    rapidjson::Document doc;
    doc.Parse(json.c_str());
    if (doc.HasParseError())
        return absl::InvalidArgumentError("invalid test JSON");
    Handler handler(doc, endpoint, std::chrono::system_clock::now(), tokenizer);
    return handler.parseRequest(std::nullopt, 0, std::nullopt);
}

class Gemma4F7ContractTest : public testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        tokenizer = std::make_unique<ov::genai::Tokenizer>(tokenizerPath());
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }
};

std::unique_ptr<ov::genai::Tokenizer> Gemma4F7ContractTest::tokenizer;

}  // namespace

TEST_F(Gemma4F7ContractTest, NativeArrayMatrixMatchesUpstreamSemantics) {
    const std::vector<std::pair<std::string, std::string>> cases{
        {"[]", "[]"},
        {"[1,true,null,-2.5]", "[1,true,null,-2.5]"},
        {R"([{name:<|"|>one<|"|>},{name:<|"|>two<|"|>}])", R"([{"name":"one"},{"name":"two"}])"},
        {R"([[1,2],[],[[3]]])", R"([[1,2],[],[[3]]])"},
        {R"([{nested:{items:[1,{label:<|"|>x<|"|>}]}}])", R"([{"nested":{"items":[1,{"label":"x"}]}}])"},
        {R"([<|"|>native, quote " text<|"|>,false,null])", R"(["native, quote \" text",false,null])"},
        {"[123456789012345678901234567890.12345678901234567890e-42]",
            "[123456789012345678901234567890.12345678901234567890e-42]"},
    };

    for (const auto& [nativeArray, expectedArray] : cases) {
        SCOPED_TRACE(nativeArray);
        const auto calls = parseNative(*tokenizer,
            "<|tool_call>call:array_tool{value:" + nativeArray + "}<tool_call|>");
        ASSERT_EQ(calls.size(), 1u);
        EXPECT_EQ(calls[0].index, 0);
        ASSERT_TRUE(calls[0].name.has_value());
        EXPECT_EQ(*calls[0].name, "array_tool");
        EXPECT_EQ(calls[0].arguments, R"({"value":)" + expectedArray + "}");
    }
}

TEST_F(Gemma4F7ContractTest, MalformedOrUnclosedArrayCommitsNoCall) {
    for (const std::string array : {"[1,2", "[1,,2]", "[{\"x\":1}]]", "[<|\"|>unterminated]"}) {
        SCOPED_TRACE(array);
        const auto calls = parseNative(*tokenizer,
            "<|tool_call>call:array_tool{value:" + array + "}<tool_call|>");
        EXPECT_TRUE(calls.empty());
    }
}

TEST_F(Gemma4F7ContractTest, HttpAcceptsOnlyUnambiguouslyObjectRootSchemas) {
    const std::vector<std::string> validSchemas{
        R"({"type":"object"})",
        R"({"$ref":"#/$defs/Args","$defs":{"Args":{"type":"object"}}})",
        R"({"oneOf":[{"type":"object"},{"$ref":"#/$defs/Args"}],"$defs":{"Args":{"type":"object"}}})",
        R"({"anyOf":[{"type":"object"},{"type":"object","properties":{"x":{"type":"string"}}}]})",
    };
    const std::vector<std::string> invalidSchemas{
        R"({"type":"string"})",
        R"({"type":"array"})",
        R"({"type":["object","null"]})",
        R"({"oneOf":[{"type":"object"},{"type":"string"}]})",
        R"({"anyOf":[{"type":"object"},{"type":"array"}]})",
    };

    for (const std::string& schema : validSchemas) {
        SCOPED_TRACE(schema);
        const std::string chat =
            R"({"model":"m","messages":[{"role":"user","content":"x"}],"tools":[{"type":"function","function":{"name":"f","parameters":)" +
            schema + "}}]}";
        const std::string responses =
            R"({"model":"m","input":"x","tools":[{"type":"function","name":"f","parameters":)" + schema + "}]}";
        EXPECT_TRUE((parseRequest<OpenAIChatCompletionsHandler>(
                         *tokenizer, chat, Endpoint::CHAT_COMPLETIONS))
                        .ok());
        EXPECT_TRUE((parseRequest<OpenAIResponsesHandler>(
                         *tokenizer, responses, Endpoint::RESPONSES))
                        .ok());
    }

    for (const std::string& schema : invalidSchemas) {
        SCOPED_TRACE(schema);
        const std::string chat =
            R"({"model":"m","messages":[{"role":"user","content":"x"}],"tools":[{"type":"function","function":{"name":"f","parameters":)" +
            schema + "}}]}";
        const std::string responses =
            R"({"model":"m","input":"x","tools":[{"type":"function","name":"f","parameters":)" + schema + "}]}";
        EXPECT_EQ((parseRequest<OpenAIChatCompletionsHandler>(
                       *tokenizer, chat, Endpoint::CHAT_COMPLETIONS))
                      .code(),
            absl::StatusCode::kInvalidArgument);
        EXPECT_EQ((parseRequest<OpenAIResponsesHandler>(
                       *tokenizer, responses, Endpoint::RESPONSES))
                      .code(),
            absl::StatusCode::kInvalidArgument);
    }
}

TEST_F(Gemma4F7ContractTest, ToolWithoutParametersGetsCanonicalEmptyObjectSchema) {
    rapidjson::Document doc;
    doc.Parse(R"({"model":"m","messages":[{"role":"user","content":"x"}],"tools":[{"type":"function","function":{"name":"f"}}]})");
    ASSERT_FALSE(doc.HasParseError());
    OpenAIChatCompletionsHandler handler(
        doc, Endpoint::CHAT_COMPLETIONS, std::chrono::system_clock::now(), *tokenizer);

    ASSERT_TRUE(handler.parseRequest(std::nullopt, 0, std::nullopt).ok());
    const auto& schemas = handler.getRequest().toolNameSchemaMap;
    ASSERT_EQ(schemas.size(), 1u);
    EXPECT_EQ(schemas.at("f").stringRepr, R"({"type":"object","properties":{}})");
}

TEST_F(Gemma4F7ContractTest, DuplicateToolNamesWithDifferentSchemasAreRejected) {
    const std::string chat =
        R"({"model":"m","messages":[{"role":"user","content":"x"}],"tools":[)"
        R"({"type":"function","function":{"name":"f","parameters":{"type":"object","properties":{"x":{"type":"string"}}}}},)"
        R"({"type":"function","function":{"name":"f","parameters":{"type":"object","properties":{"x":{"type":"number"}}}}}]})";
    const std::string responses =
        R"({"model":"m","input":"x","tools":[)"
        R"({"type":"function","name":"f","parameters":{"type":"object","properties":{"x":{"type":"string"}}}},)"
        R"({"type":"function","name":"f","parameters":{"type":"object","properties":{"x":{"type":"number"}}}}]})";

    EXPECT_EQ((parseRequest<OpenAIChatCompletionsHandler>(
                   *tokenizer, chat, Endpoint::CHAT_COMPLETIONS))
                  .code(),
        absl::StatusCode::kInvalidArgument);
    EXPECT_EQ((parseRequest<OpenAIResponsesHandler>(
                   *tokenizer, responses, Endpoint::RESPONSES))
                  .code(),
        absl::StatusCode::kInvalidArgument);
}
