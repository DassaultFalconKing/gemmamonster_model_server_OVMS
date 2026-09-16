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

const ov::genai::StructuredOutputConfig::JSONSchema* namedToolSchema(
    const ov::genai::GenerationConfig& config) {
    using Structured = ov::genai::StructuredOutputConfig;
    if (!config.structured_output_config || !config.structured_output_config->structural_tags_config)
        return nullptr;

    const auto* grammar = std::get_if<Structured::StructuralTag>(
        &*config.structured_output_config->structural_tags_config);
    if (grammar == nullptr)
        return nullptr;

    const auto* alternatives = std::get_if<std::shared_ptr<Structured::Union>>(grammar);
    if (alternatives == nullptr || !*alternatives || (*alternatives)->elements.empty())
        return nullptr;

    const auto* requiredTags = std::get_if<std::shared_ptr<Structured::TagsWithSeparator>>(
        &(*alternatives)->elements.front());
    if (requiredTags == nullptr || !*requiredTags || (*requiredTags)->tags.size() != 1u)
        return nullptr;

    return std::get_if<Structured::JSONSchema>(&(*requiredTags)->tags.front().content);
}
}  // namespace

TEST(Gemma4WhitespaceBoundTest, NamedToolSchemaBoundsInterElementWhitespace) {
    ov::genai::GenerationConfig baseConfig;
    GenerationConfigBuilder builder(baseConfig, "gemma4", true, DecodingMethod::STANDARD);

    builder.parseConfigFromRequest(namedWeatherRequest());

    const auto* schema = namedToolSchema(builder.getConfig());
    ASSERT_NE(schema, nullptr);
    ASSERT_TRUE(schema->max_whitespace_cnt.has_value());
    EXPECT_EQ(*schema->max_whitespace_cnt, 2);
    EXPECT_NE(schema->to_json().find("\"max_whitespace_cnt\": 2"), std::string::npos);
}
