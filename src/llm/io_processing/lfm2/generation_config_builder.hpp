// Copyright 2026 Intel Corporation. SPDX-License-Identifier: Apache-2.0
#pragma once
#include <stdexcept>
#include "../base_generation_config_builder.hpp"
#include "tool_grammar.hpp"

namespace ovms {
class Lfm2GenerationConfigBuilder : public BaseGenerationConfigBuilder {
    bool hardToolPolicy = false;
public:
    explicit Lfm2GenerationConfigBuilder(const ov::genai::GenerationConfig& base,
        bool guided, DecodingMethod method) : BaseGenerationConfigBuilder(base, guided, method) {}
    bool requiresValidStructuredOutput() const override { return hardToolPolicy; }
    void parseConfigFromRequest(const OpenAIRequest& request) override {
        if (hardToolPolicy)
            config.structured_output_config.reset();
        hardToolPolicy = false;
        BaseGenerationConfigBuilder::parseConfigFromRequest(request);
        const bool named = !request.toolChoice.empty() && request.toolChoice != "none" &&
                           request.toolChoice != "auto" && request.toolChoice != "required";
        const bool hard = request.toolChoice == "required" || named;
        if (!hard) {
            if (request.toolChoice != "none") {
                for (const auto& [name, schema] : request.toolNameSchemaMap) {
                    if (!isSupportedQwenXmlToolSchema(schema.stringRepr))
                        throw std::invalid_argument("LFM schema is outside the executable retainer profile: " + name);
                }
            }
            if (request.toolChoice != "none" && enableToolGuidedGeneration &&
                !request.toolNameSchemaMap.empty() && !request.responseFormat.has_value()) {
                using Structured = ov::genai::StructuredOutputConfig;
                auto lazy = std::make_shared<Structured::TriggeredTags>();
                lazy->triggers = {"<think>", "<|tool_call_start|>"};
                // While in the thought tag, tool-like drafts are plain text.
                // Native call constraints activate only outside that span.
                lazy->tags.emplace_back("<think>", Structured::AnyText{}, "</think>");
                lazy->tags.emplace_back("<|tool_call_start|>",
                    Structured::EBNF(lfm2::toolGrammar(request.toolNameSchemaMap, request.parallelToolCalls, false)),
                    "<|tool_call_end|>");
                setStructuralTagsConfig(lazy);
                hardToolPolicy = true;  // Own/reset the installed grammar; fail closed if compilation fails.
            }
            return;
        }
        if (request.responseFormat.has_value())
            throw std::invalid_argument("LFM hard tool_choice conflicts with response_format");
        if (request.toolNameSchemaMap.empty())
            throw std::invalid_argument("LFM hard tool_choice requires registered tools");
        ToolsSchemas_t selected;
        if (named) {
            const auto found = request.toolNameSchemaMap.find(request.toolChoice);
            if (found == request.toolNameSchemaMap.end())
                throw std::invalid_argument("LFM named tool_choice is unavailable: " + request.toolChoice);
            selected.emplace(*found);
        } else selected = request.toolNameSchemaMap;
        const auto grammar = lfm2::toolGrammar(selected, request.parallelToolCalls);
        setStructuralTagsConfig(ov::genai::StructuredOutputConfig::EBNF(grammar));
        hardToolPolicy = true;
    }
};
}  // namespace ovms
