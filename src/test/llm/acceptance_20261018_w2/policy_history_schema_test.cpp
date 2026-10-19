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
    Handler handler(doc, endpoint, std::chrono::system_clock::now(), tokenizer, "gemma4");
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

TEST_F(PolicyHistorySchemaTest, SchemaReferenceDepth64IsAcceptedAnd65IsRejected) {
    const std::string accepted = objectSchemaAtRefDepth(64);
    const std::string rejected = objectSchemaAtRefDepth(65);
    EXPECT_TRUE((parseEndpoint<OpenAIChatCompletionsHandler>(
                     *tokenizer, chatTools(accepted), Endpoint::CHAT_COMPLETIONS))
                    .ok());
    EXPECT_TRUE((parseEndpoint<OpenAIResponsesHandler>(
                     *tokenizer, responsesTools(accepted), Endpoint::RESPONSES))
                    .ok());

    const auto chat = parseEndpoint<OpenAIChatCompletionsHandler>(
        *tokenizer, chatTools(rejected), Endpoint::CHAT_COMPLETIONS);
    const auto responses = parseEndpoint<OpenAIResponsesHandler>(
        *tokenizer, responsesTools(rejected), Endpoint::RESPONSES);
    EXPECT_EQ(chat.code(), absl::StatusCode::kInvalidArgument);
    EXPECT_NE(std::string(chat.message()).find("unambiguous object root"), std::string::npos);
    EXPECT_EQ(responses.code(), absl::StatusCode::kInvalidArgument);
    EXPECT_NE(std::string(responses.message()).find("unambiguous object root"), std::string::npos);
}

TEST_F(PolicyHistorySchemaTest, CyclicAndNonLocalSchemaReferencesAreRejected) {
    const std::vector<std::string> schemas{
        R"({"$ref":"#"})",
        R"({"$ref":"#/$defs/A","$defs":{"A":{"$ref":"#/$defs/A"}}})",
        R"({"$ref":"https://example.invalid/schema"})",
    };
    for (const std::string& schema : schemas) {
        SCOPED_TRACE(schema);
        const auto chat = parseEndpoint<OpenAIChatCompletionsHandler>(
            *tokenizer, chatTools(schema), Endpoint::CHAT_COMPLETIONS);
        const auto responses = parseEndpoint<OpenAIResponsesHandler>(
            *tokenizer, responsesTools(schema), Endpoint::RESPONSES);
        EXPECT_EQ(chat.code(), absl::StatusCode::kInvalidArgument);
        EXPECT_EQ(responses.code(), absl::StatusCode::kInvalidArgument);
    }
}

TEST_F(PolicyHistorySchemaTest, IdenticalDuplicateToolSchemasAreKeptOnce) {
    const std::string parameters = R"({"type":"object","properties":{}})";
    const std::string chat =
        R"({"model":"m","messages":[{"role":"user","content":"x"}],"tools":[)"
        R"({"type":"function","function":{"name":"f","parameters":)" +
        parameters + "}}," +
        R"({"type":"function","function":{"name":"f","parameters":)" +
        parameters + "}}]}";
    const std::string responses =
        R"({"model":"m","input":"x","tools":[)"
        R"({"type":"function","name":"f","parameters":)" +
        parameters + "}," +
        R"({"type":"function","name":"f","parameters":)" +
        parameters + "}]}";

    rapidjson::Document chatDoc;
    chatDoc.Parse(chat.c_str());
    ASSERT_FALSE(chatDoc.HasParseError());
    OpenAIChatCompletionsHandler chatHandler(
        chatDoc, Endpoint::CHAT_COMPLETIONS, std::chrono::system_clock::now(), *tokenizer, "gemma4");
    ASSERT_TRUE(chatHandler.parseRequest(std::nullopt, 0, std::nullopt).ok());
    ASSERT_EQ(chatHandler.getRequest().toolNameSchemaMap.size(), 1u);
    EXPECT_EQ(chatHandler.getRequest().toolNameSchemaMap.at("f").stringRepr, parameters);

    rapidjson::Document responsesDoc;
    responsesDoc.Parse(responses.c_str());
    ASSERT_FALSE(responsesDoc.HasParseError());
    OpenAIResponsesHandler responsesHandler(
        responsesDoc, Endpoint::RESPONSES, std::chrono::system_clock::now(), *tokenizer, "gemma4");
    ASSERT_TRUE(responsesHandler.parseRequest(std::nullopt, 0, std::nullopt).ok());
    ASSERT_EQ(responsesHandler.getRequest().toolNameSchemaMap.size(), 1u);
    EXPECT_EQ(responsesHandler.getRequest().toolNameSchemaMap.at("f").stringRepr, parameters);
}
