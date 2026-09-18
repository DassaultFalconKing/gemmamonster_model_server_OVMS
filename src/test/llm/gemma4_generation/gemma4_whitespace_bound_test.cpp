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

#include <memory>
#include <variant>

#include "src/llm/io_processing/generation_config_builder.hpp"

using namespace ovms;

namespace {
OpenAIRequest namedWeatherRequest() {
    OpenAIRequest request;
    request.toolChoice = "weather";
    request.toolNameSchemaMap.emplace(
        "weather",
        ToolSchemaWrapper{nullptr,
            R"({"type":"object","properties":{"city":{"type":"string"}},"required":["city"]})"});
    return request;
}

const std::string* namedToolGrammar(
    const ov::genai::GenerationConfig& config) {
    using Structured = ov::genai::StructuredOutputConfig;
    if (!config.structured_output_config || !config.structured_output_config->structural_tags_config)
        return nullptr;

    const auto* grammar = std::get_if<Structured::StructuralTag>(
        &*config.structured_output_config->structural_tags_config);
    if (grammar == nullptr)
        return nullptr;

    return std::get_if<std::string>(grammar);
}
}  // namespace

TEST(Gemma4WhitespaceBoundTest, NamedToolSchemaBoundsInterElementWhitespace) {
    ov::genai::GenerationConfig baseConfig;
    GenerationConfigBuilder builder(baseConfig, "gemma4", true, DecodingMethod::STANDARD);

    builder.parseConfigFromRequest(namedWeatherRequest());

    const auto* grammar = namedToolGrammar(builder.getConfig());
    ASSERT_NE(grammar, nullptr);
    EXPECT_NE(grammar->find("\"max_whitespace_cnt\": 2"), std::string::npos);
    EXPECT_NE(grammar->find("\"required\":[\"city\"]"), std::string::npos);
    EXPECT_NE(grammar->find("\"begin\":{\"type\":\"token\",\"token\":\"<|tool_call>\"}"), std::string::npos);
    EXPECT_NE(grammar->find("\"end\":{\"type\":\"token\",\"token\":\"<tool_call|>\"}"), std::string::npos);
}
