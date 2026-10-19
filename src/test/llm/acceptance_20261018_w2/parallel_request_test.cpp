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

#include <chrono>
#include <cstdlib>
#include <exception>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <variant>

#include <rapidjson/document.h>

#include "src/llm/apis/openai_completions.hpp"
#include "src/llm/apis/openai_responses.hpp"
#include "src/llm/io_processing/generation_config_builder.hpp"

using namespace ovms;

namespace {
class Gemma4ApiValidationTest : public testing::Test {
protected:
    static std::unique_ptr<ov::genai::Tokenizer> tokenizer;

    static void SetUpTestSuite() {
        const char* localTokenizer = std::getenv("OVMS_TEST_TOKENIZER_PATH");
        std::string path;
        if (localTokenizer != nullptr) {
            path = localTokenizer;
        } else {
            const std::string cwd = std::filesystem::current_path().string();
            const size_t bazelOut = cwd.find("bazel-out");
            const std::string workspace = bazelOut == std::string::npos ? cwd : cwd.substr(0, bazelOut);
            path = workspace + "/src/test/llm_testing/HuggingFaceTB/SmolLM2-360M-Instruct";
        }
        tokenizer = std::make_unique<ov::genai::Tokenizer>(path);
    }

    static void TearDownTestSuite() {
        tokenizer.reset();
    }

    static std::string weatherJson(const std::string& extraFields) {
        return std::string(R"({"model":"m","messages":[{"role":"user","content":"Call weather"}],"tools":[{"type":"function","function":{"name":"weather","parameters":{"type":"object","properties":{}}}}])") + extraFields + "}";
    }
};

std::unique_ptr<ov::genai::Tokenizer> Gemma4ApiValidationTest::tokenizer;

}
TEST_F(Gemma4ApiValidationTest, ParallelPolicyRejectsNonBooleanHttpValue) {
    rapidjson::Document doc;
    const std::string json = weatherJson(R"(,"parallel_tool_calls":"false")");
    doc.Parse(json.c_str());
    ASSERT_FALSE(doc.HasParseError());
    OpenAIChatCompletionsHandler handler(doc, Endpoint::CHAT_COMPLETIONS, std::chrono::system_clock::now(), *tokenizer);
    EXPECT_EQ(handler.parseRequest(std::nullopt, 0, std::nullopt).code(), absl::StatusCode::kInvalidArgument);
}
TEST_F(Gemma4ApiValidationTest, ResponsesEchoesExplicitParallelFalse) {
    rapidjson::Document doc;
    doc.Parse(R"({"model":"m","input":"Call weather","parallel_tool_calls":false,"tools":[{"type":"function","name":"weather","parameters":{"type":"object","properties":{}}}]})");
    ASSERT_FALSE(doc.HasParseError());
    OpenAIResponsesHandler handler(doc, Endpoint::RESPONSES, std::chrono::system_clock::now(), *tokenizer);
    ASSERT_TRUE(handler.parseRequest(std::nullopt, 0, std::nullopt).ok());
    EXPECT_FALSE(handler.getRequest().parallelToolCalls);

    const std::vector<Delta> deltas;
    const std::string response = handler.serializeUnaryResponse(deltas, ov::genai::GenerationFinishReason::STOP);
    rapidjson::Document responseDoc;
    responseDoc.Parse(response.c_str());
    ASSERT_FALSE(responseDoc.HasParseError()) << response;
    ASSERT_TRUE(responseDoc.HasMember("parallel_tool_calls"));
    ASSERT_TRUE(responseDoc["parallel_tool_calls"].IsBool());
    EXPECT_FALSE(responseDoc["parallel_tool_calls"].GetBool());
}
