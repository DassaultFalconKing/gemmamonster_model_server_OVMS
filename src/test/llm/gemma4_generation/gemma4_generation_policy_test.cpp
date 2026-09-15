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

#include "src/llm/io_processing/generation_config_builder.hpp"

using namespace ovms;

namespace {
OpenAIRequest requiredWeatherRequest() {
    OpenAIRequest request;
    request.toolChoice = "required";
    request.toolNameSchemaMap.emplace(
        "weather",
        ToolSchemaWrapper{nullptr,
            R"({"type":"object","properties":{"city":{"type":"string"}},"required":["city"]})"});
    return request;
}
}  // namespace

TEST(Gemma4GenerationPolicyTest, RequiredToolChoiceInstallsNativeStructuredGrammar) {
    ov::genai::GenerationConfig baseConfig;
    GenerationConfigBuilder builder(baseConfig, "gemma4", true, DecodingMethod::STANDARD);

    builder.parseConfigFromRequest(requiredWeatherRequest());

    EXPECT_TRUE(builder.getConfig().structured_output_config.has_value());
}
