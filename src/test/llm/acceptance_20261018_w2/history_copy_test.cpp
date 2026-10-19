//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//*****************************************************************************

// HTTP schema-reference bounds and template-history normalization that the
// retained Gemma suites do not already assert. Execution is not part of W2.

#include <gtest/gtest.h>

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <memory>
#include <string>
#include <variant>

#include <rapidjson/document.h>

#include "src/llm/apis/openai_completions.hpp"
#include "src/llm/apis/openai_responses.hpp"
#include "src/llm/io_processing/generation_config_builder.hpp"

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

std::string objectSchemaAtRefDepth(size_t hops) {
    std::string defs;
    for (size_t i = 1; i < hops; ++i) {
        if (i > 1)
            defs += ",";
        defs += "\"d" + std::to_string(i) + "\":{\"$ref\":\"#/$defs/d" + std::to_string(i + 1) + "\"}";
    }
    if (hops > 1)
        defs += ",";
    defs += "\"d" + std::to_string(hops) + "\":{\"type\":\"object\"}";
    return "{\"$ref\":\"#/$defs/d1\",\"$defs\":{" + defs + "}}";
}

std::string chatTools(const std::string& parametersJson) {
    return R"({"model":"m","messages":[{"role":"user","content":"x"}],"tools":[{"type":"function","function":{"name":"f","parameters":)" +
           parametersJson + "}}]}";
}

std::string responsesTools(const std::string& parametersJson) {
    return R"({"model":"m","input":"x","tools":[{"type":"function","name":"f","parameters":)" +
           parametersJson + "}]}";
}

template <typename Handler>
absl::Status parseEndpoint(ov::genai::Tokenizer& tokenizer, const std::string& json, Endpoint endpoint) {
    rapidjson::Document doc;
    doc.Parse(json.c_str());
    if (doc.HasParseError())
        return absl::InvalidArgumentError("invalid test JSON");
    Handler handler(doc, endpoint, std::chrono::system_clock::now(), tokenizer);
    return handler.parseRequest(std::nullopt, 0, std::nullopt);
}

class PolicyHistorySchemaTest : public testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        tokenizer = std::make_unique<ov::genai::Tokenizer>(tokenizerPath());
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }
};

std::unique_ptr<ov::genai::Tokenizer> PolicyHistorySchemaTest::tokenizer;

}  // namespace

TEST_F(PolicyHistorySchemaTest, QwenBaselineHistoryKeepsStringArgumentsAndSkipsGemmaGrammar) {
    rapidjson::Document doc;
    doc.Parse(R"({
        "model":"m",
        "messages":[
            {"role":"assistant","content":null,"tool_calls":[
                {"id":"call_1","type":"function","function":{"name":"ping"}}
            ]},
            {"role":"tool","tool_call_id":"call_1","content":"ok"}
        ],
        "tools":[{"type":"function","function":{"name":"ping","parameters":{"type":"object","properties":{}}}}],
        "tool_choice":"required",
        "parallel_tool_calls":false
    })");
    ASSERT_FALSE(doc.HasParseError());
    OpenAIChatCompletionsHandler handler(
        doc, Endpoint::CHAT_COMPLETIONS, std::chrono::system_clock::now(), *tokenizer, "qwen3coder", "qwen3");
    ASSERT_TRUE(handler.parseRequest(std::nullopt, 0, std::nullopt).ok());
    EXPECT_EQ(handler.getRequest().toolChoice, "required");
    EXPECT_FALSE(handler.getRequest().parallelToolCalls);
    EXPECT_EQ(handler.getChatHistory()[0]["tool_calls"][0]["function"]["arguments"].get_string(), "{}");

    GenerationConfigBuilder builder(ov::genai::GenerationConfig{}, "qwen3coder", true, DecodingMethod::STANDARD);
    auto result = handler.extractInputRequest(builder);
    ASSERT_TRUE(result.ok()) << result.status();
    EXPECT_FALSE(builder.getConfig().structured_output_config.has_value());
    const auto& copy = std::get<ov::genai::ChatHistory>(result->input);
    const auto arguments = copy.get_messages()[0]["tool_calls"][0]["function"]["arguments"];
    EXPECT_TRUE(arguments.is_string());
    EXPECT_FALSE(arguments.is_object());
    EXPECT_EQ(arguments.get_string(), "{}");
}

TEST_F(PolicyHistorySchemaTest, QwenBaselineKeepsNonObjectHistoryArgumentsAsStrings) {
    rapidjson::Document doc;
    doc.Parse(R"({
        "model":"m",
        "messages":[
            {"role":"assistant","content":null,"tool_calls":[
                {"id":"call_1","type":"function","function":{"name":"ping","arguments":"[]"}}
            ]},
            {"role":"tool","tool_call_id":"call_1","content":"ok"}
        ]
    })");
    ASSERT_FALSE(doc.HasParseError());
    OpenAIChatCompletionsHandler handler(
        doc, Endpoint::CHAT_COMPLETIONS, std::chrono::system_clock::now(), *tokenizer, "qwen3coder", "qwen3");
    ASSERT_TRUE(handler.parseRequest(std::nullopt, 0, std::nullopt).ok());
    GenerationConfigBuilder builder(ov::genai::GenerationConfig{}, "qwen3coder", false, DecodingMethod::STANDARD);
    auto result = handler.extractInputRequest(builder);
    ASSERT_TRUE(result.ok()) << result.status();
    const auto& copy = std::get<ov::genai::ChatHistory>(result->input);
    const auto arguments = copy.get_messages()[0]["tool_calls"][0]["function"]["arguments"];
    EXPECT_TRUE(arguments.is_string());
    EXPECT_EQ(arguments.get_string(), "[]");
}

TEST_F(PolicyHistorySchemaTest, GemmaHistoryTurnsOmittedArgumentsIntoAnObjectOnTheCopyOnly) {
    rapidjson::Document doc;
    doc.Parse(R"({
        "model":"m",
        "messages":[
            {"role":"assistant","content":null,"tool_calls":[
                {"id":"call_1","type":"function","function":{"name":"ping"}}
            ]},
            {"role":"tool","tool_call_id":"call_1","content":"ok"}
        ],
        "tools":[{"type":"function","function":{"name":"ping","parameters":{"type":"object","properties":{}}}}],
        "tool_choice":"auto"
    })");
    ASSERT_FALSE(doc.HasParseError());
    OpenAIChatCompletionsHandler handler(
        doc, Endpoint::CHAT_COMPLETIONS, std::chrono::system_clock::now(), *tokenizer, "gemma4", "gemma4");
    ASSERT_TRUE(handler.parseRequest(std::nullopt, 0, std::nullopt).ok());
    EXPECT_EQ(handler.getChatHistory()[0]["tool_calls"][0]["function"]["arguments"].get_string(), "{}");

    GenerationConfigBuilder builder(ov::genai::GenerationConfig{}, "gemma4", false, DecodingMethod::STANDARD);
    auto result = handler.extractInputRequest(builder);
    ASSERT_TRUE(result.ok()) << result.status();
    const auto& copy = std::get<ov::genai::ChatHistory>(result->input);
    const auto arguments = copy.get_messages()[0]["tool_calls"][0]["function"]["arguments"];
    EXPECT_TRUE(arguments.is_object());
    EXPECT_FALSE(arguments.is_string());
    EXPECT_EQ(handler.getRequest().chatHistory.get_messages()[0]["tool_calls"][0]["function"]["arguments"].get_string(), "{}");
}
