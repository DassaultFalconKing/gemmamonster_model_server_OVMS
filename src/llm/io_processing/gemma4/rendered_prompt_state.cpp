//*****************************************************************************
// Copyright 2026 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//*****************************************************************************

#include "rendered_prompt_state.hpp"

#include <algorithm>
#include <memory>
#include <utility>
#include <variant>

namespace ovms {
namespace {

constexpr const char* GEMMA4_THOUGHT_START = "<|channel>thought\n";
constexpr const char* GEMMA4_THOUGHT_END = "<channel|>";

size_t latestGenerationBoundary(const std::string& prompt) {
    // These anchors begin the only suffix that can describe the next decode.
    // Markers in earlier user/tool content therefore cannot open current reasoning.
    static const std::vector<std::string> anchors{
        "<|turn>model\n",
        "<|im_start|>assistant\n",
        "<tool_response|>",
    };
    size_t boundary = 0;
    for (const auto& anchor : anchors) {
        const size_t pos = prompt.rfind(anchor);
        if (pos != std::string::npos)
            boundary = std::max(boundary, pos + anchor.size());
    }
    return boundary;
}

size_t latestTag(
    const std::string& prompt,
    const std::vector<std::string>& tags,
    size_t from) {
    size_t latest = std::string::npos;
    for (const auto& tag : tags) {
        if (tag.empty())
            continue;
        const size_t pos = prompt.rfind(tag);
        if (pos != std::string::npos && pos >= from &&
            (latest == std::string::npos || pos > latest))
            latest = pos;
    }
    return latest;
}

bool isResidualThoughtGrammar(
    const ov::genai::StructuredOutputConfig::StructuralTag& grammar) {
    using Structured = ov::genai::StructuredOutputConfig;
    const auto* concat = std::get_if<std::shared_ptr<Structured::Concat>>(&grammar);
    if (concat == nullptr || !*concat || (*concat)->elements.empty())
        return false;
    const auto* thought =
        std::get_if<std::shared_ptr<Structured::Tag>>(&(*concat)->elements.front());
    return thought != nullptr && *thought &&
           (*thought)->begin.empty() && (*thought)->end == GEMMA4_THOUGHT_END;
}

std::shared_ptr<ov::genai::StructuredOutputConfig::Tag> residualThought() {
    using Structured = ov::genai::StructuredOutputConfig;
    auto thought = std::make_shared<Structured::Tag>();
    thought->begin = "";
    thought->content = Structured::AnyText();
    thought->end = GEMMA4_THOUGHT_END;
    return thought;
}

}  // namespace

Gemma4RenderedPromptState classifyRenderedPromptState(
    const std::string& renderedPrompt,
    const std::vector<std::string>& thoughtStartTags,
    const std::string& thoughtEndTag) {
    const size_t boundary = latestGenerationBoundary(renderedPrompt);
    const size_t start = latestTag(renderedPrompt, thoughtStartTags, boundary);
    const size_t end = thoughtEndTag.empty() ? std::string::npos :
                                               renderedPrompt.rfind(thoughtEndTag);
    const bool endInCurrentSuffix = end != std::string::npos && end >= boundary;

    if (start != std::string::npos && (!endInCurrentSuffix || start > end))
        return Gemma4RenderedPromptState::OPEN_THOUGHT;
    if (endInCurrentSuffix && (start == std::string::npos || end > start))
        return Gemma4RenderedPromptState::CLOSED_THOUGHT;
    return Gemma4RenderedPromptState::NEW_TURN;
}

Gemma4RenderedPromptState classifyGemma4RenderedPromptState(
    const std::string& renderedPrompt) {
    return classifyRenderedPromptState(
        renderedPrompt, {GEMMA4_THOUGHT_START}, GEMMA4_THOUGHT_END);
}

bool adaptGemma4ToolGrammarForRenderedPrompt(
    ov::genai::GenerationConfig& config,
    const std::string& renderedPrompt) {
    using Structured = ov::genai::StructuredOutputConfig;
    if (classifyGemma4RenderedPromptState(renderedPrompt) !=
        Gemma4RenderedPromptState::OPEN_THOUGHT)
        return false;
    if (!config.structured_output_config ||
        !config.structured_output_config->structural_tags_config)
        return false;

    auto& outer = *config.structured_output_config->structural_tags_config;
    auto* grammar = std::get_if<Structured::StructuralTag>(&outer);
    if (grammar == nullptr || isResidualThoughtGrammar(*grammar))
        return false;

    Structured::StructuralTag continuation;
    if (const auto* alternatives =
            std::get_if<std::shared_ptr<Structured::Union>>(grammar);
        alternatives != nullptr && *alternatives &&
        !(*alternatives)->elements.empty()) {
        const auto* required =
            std::get_if<std::shared_ptr<Structured::TagsWithSeparator>>(
                &(*alternatives)->elements.front());
        if (required == nullptr || !*required || !(*required)->at_least_one)
            return false;
        continuation = *required;
    } else if (const auto* triggered =
                   std::get_if<std::shared_ptr<Structured::TriggeredTags>>(grammar);
               triggered != nullptr && *triggered) {
        continuation = *triggered;
    } else {
        return false;
    }

    auto residual = std::make_shared<Structured::Concat>();
    residual->elements = {residualThought(), std::move(continuation)};
    *grammar = std::move(residual);
    return true;
}

}  // namespace ovms
