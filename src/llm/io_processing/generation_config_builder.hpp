//*****************************************************************************
// Copyright 2025 Intel Corporation
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

#pragma once
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <openvino/genai/generation_config.hpp>
#include <openvino/genai/tokenizer.hpp>

#include "base_generation_config_builder.hpp"
#include "phi4/generation_config_builder.hpp"
#include "llama3/generation_config_builder.hpp"
#include "hermes3/generation_config_builder.hpp"
#include "devstral/generation_config_builder.hpp"
#include "../apis/openai_request.hpp"
#include "../../logging.hpp"

namespace ovms {

class Gemma4GenerationConfigBuilder : public BaseGenerationConfigBuilder {
    static ov::genai::StructuredOutputConfig::Tag buildToolTag(
        const std::string& toolName,
        const ToolSchemaWrapper& toolSchemaWrapper) {
        if (toolSchemaWrapper.stringRepr.empty()) {
            throw std::invalid_argument("Gemma4 guided tool schema for '" + toolName + "' is empty");
        }

        ov::genai::StructuredOutputConfig::Tag tag;
        tag.begin = "<|tool_call>call:" + toolName;
        tag.content = ov::genai::StructuredOutputConfig::JSONSchema(toolSchemaWrapper.stringRepr);
        tag.end = "<tool_call|>";
        return tag;
    }

    static std::vector<ov::genai::StructuredOutputConfig::Tag> buildToolTags(
        const OpenAIRequest& request) {
        std::vector<ov::genai::StructuredOutputConfig::Tag> toolTags;
        toolTags.reserve(request.toolNameSchemaMap.size());
        for (const auto& [toolName, toolSchemaWrapper] : request.toolNameSchemaMap) {
            toolTags.push_back(buildToolTag(toolName, toolSchemaWrapper));
        }
        return toolTags;
    }

    static ov::genai::StructuredOutputConfig::StructuralTag buildRequiredToolGrammar(
        std::vector<ov::genai::StructuredOutputConfig::Tag> toolTags) {
        using Structured = ov::genai::StructuredOutputConfig;

        auto requiredTags = std::make_shared<Structured::TagsWithSeparator>();
        requiredTags->tags = std::move(toolTags);
        requiredTags->separator = "";
        requiredTags->at_least_one = true;

        auto thought = std::make_shared<Structured::Tag>();
        thought->begin = "<|channel>thought\n";
        thought->content = Structured::AnyText();
        thought->end = "<channel|>";

        auto thoughtThenTools = std::make_shared<Structured::Concat>();
        thoughtThenTools->elements = {thought, requiredTags};

        auto alternatives = std::make_shared<Structured::Union>();
        alternatives->elements = {requiredTags, thoughtThenTools};
        return alternatives;
    }

    static ov::genai::StructuredOutputConfig::StructuralTag buildAutoToolGrammar(
        std::vector<ov::genai::StructuredOutputConfig::Tag> toolTags) {
        using Structured = ov::genai::StructuredOutputConfig;
        auto triggeredTags = std::make_shared<Structured::TriggeredTags>();
        triggeredTags->triggers = {"<|tool_call>"};
        triggeredTags->tags = std::move(toolTags);
        triggeredTags->at_least_one = false;
        return triggeredTags;
    }

public:
    Gemma4GenerationConfigBuilder() = delete;
    explicit Gemma4GenerationConfigBuilder(
        const ov::genai::GenerationConfig& baseConfig,
        bool enableToolGuidedGeneration,
        DecodingMethod decodingMethod) :
        BaseGenerationConfigBuilder(baseConfig, enableToolGuidedGeneration, decodingMethod) {}

    void parseConfigFromRequest(const OpenAIRequest& request) override {
        BaseGenerationConfigBuilder::parseConfigFromRequest(request);

        if (request.toolNameSchemaMap.empty() || request.toolChoice == "none") {
            return;
        }

        auto toolTags = buildToolTags(request);
        if (request.toolChoice == "required") {
            setStructuralTagsConfig(buildRequiredToolGrammar(std::move(toolTags)));
            return;
        }

        if ((request.toolChoice.empty() || request.toolChoice == "auto") && enableToolGuidedGeneration) {
            setStructuralTagsConfig(buildAutoToolGrammar(std::move(toolTags)));
        }
    }
};

class GenerationConfigBuilder {
    std::unique_ptr<BaseGenerationConfigBuilder> builder_impl;

public:
    GenerationConfigBuilder() = delete;
    // Using tool parser name to select appropriate builder implementation to avoid introducing additional parameters. Might be insufficient in the future.
    explicit GenerationConfigBuilder(const ov::genai::GenerationConfig& baseConfig, std::string toolParserName, bool enableToolGuidedGeneration, DecodingMethod decodingMethod) {
        if (toolParserName == "llama3") {
            builder_impl = std::make_unique<Llama3GenerationConfigBuilder>(baseConfig, enableToolGuidedGeneration, decodingMethod);
        } else if (toolParserName == "qwen3") {
            // Qwen3 and Hermes3 share the same mechanism for generating tool calls, so we can use Hermes3GenerationConfigBuilder
            builder_impl = std::make_unique<Hermes3GenerationConfigBuilder>(baseConfig, enableToolGuidedGeneration, decodingMethod);
        } else if (toolParserName == "hermes3") {
            builder_impl = std::make_unique<Hermes3GenerationConfigBuilder>(baseConfig, enableToolGuidedGeneration, decodingMethod);
        } else if (toolParserName == "gemma4") {
            builder_impl = std::make_unique<Gemma4GenerationConfigBuilder>(baseConfig, enableToolGuidedGeneration, decodingMethod);
        } else if (toolParserName == "phi4") {
            builder_impl = std::make_unique<Phi4GenerationConfigBuilder>(baseConfig, enableToolGuidedGeneration, decodingMethod);
        } else if (toolParserName == "devstral") {
            builder_impl = std::make_unique<DevstralGenerationConfigBuilder>(baseConfig, enableToolGuidedGeneration, decodingMethod);
        } else {
            if (enableToolGuidedGeneration) {
                SPDLOG_LOGGER_DEBUG(llm_calculator_logger, "Option enable_tool_guided_generation is set, but will not be effective since no valid tool parser has been provided.");
            }
            builder_impl = std::make_unique<BaseGenerationConfigBuilder>(baseConfig, enableToolGuidedGeneration, decodingMethod);
        }
    }

    ov::genai::GenerationConfig& getConfig() {
        return builder_impl->getConfig();
    }

    void adjustConfigForDecodingMethod() {
        builder_impl->adjustConfigForDecodingMethod();
    }

    void validateStructuredOutputConfig(ov::genai::Tokenizer& tokenizer) {
        builder_impl->validateStructuredOutputConfig(tokenizer);
    }

    void unsetStructuredOutputConfig() {
        builder_impl->unsetStructuredOutputConfig();
    }

    void parseConfigFromRequest(const OpenAIRequest& request) {
        builder_impl->parseConfigFromRequest(request);
    }

    void addStopString(const std::string& decodedStopString) {
        builder_impl->addStopString(decodedStopString);
    }
};
}  // namespace ovms
