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

#include <algorithm>
#include <cctype>
#include <unordered_set>

#include "src/logging.hpp"
#include "src/stringutils.hpp"
#include "output_parser.hpp"
#include "parser_config_validation.hpp"
#include "llama3/tool_parser.hpp"
#include "hermes3/tool_parser.hpp"
#include "phi4/tool_parser.hpp"
#include "mistral/tool_parser.hpp"
#include "gptoss/tool_parser.hpp"
#include "qwen3/reasoning_parser.hpp"
#include "qwen3coder/qwen3coder_tool_parser.hpp"
#include "devstral/tool_parser.hpp"
#include "gemma4/gemma4_reasoning_parser.hpp"
#include "gptoss/reasoning_parser.hpp"
#include "lfm2/lfm2_tool_parser.hpp"
#include "lfm2/lfm25_reasoning_parser.hpp"
#include "gemma4/gemma4_tool_parser.hpp"
#include "onyx/onyx_tool_parser.hpp"
#include "onyx/onyx_reasoning_parser.hpp"
#include "onyx/onyx_content_parser.hpp"
#include "default_content_parser.hpp"
#include "minicpm5/minicpm5_tool_parser.hpp"
#include "minicpm5/minicpm5_reasoning_parser.hpp"

namespace ovms {
namespace {

bool updateBoundaryState(bool boundary, const std::string& consumed) {
    for (const char c : consumed) {
        if (c == '\n') {
            boundary = true;
        } else if (boundary && (c == ' ' || c == '\t' || c == '\r')) {
            continue;
        } else {
            boundary = false;
        }
    }
    return boundary;
}

}  // namespace

OutputParser::TagLookupStatus OutputParser::StreamOutputCache::lookupTag(const std::string& tag) const {
    if (tag.empty())
        return TagLookupStatus::NOT_FOUND;
    if (tag.size() > buffer.size())
        return stringsOverlap(buffer, tag) ? TagLookupStatus::FOUND_INCOMPLETE : TagLookupStatus::NOT_FOUND;
    if (tag.size() < buffer.size()) {
        if (buffer.find(tag) != std::string::npos)
            return TagLookupStatus::FOUND_COMPLETE;
        return stringsOverlap(buffer, tag) ? TagLookupStatus::FOUND_INCOMPLETE : TagLookupStatus::NOT_FOUND;
    }
    if (buffer == tag)
        return TagLookupStatus::FOUND_COMPLETE;
    return stringsOverlap(buffer, tag) ? TagLookupStatus::FOUND_INCOMPLETE : TagLookupStatus::NOT_FOUND;
}

OutputParser::TagLookupStatus OutputParser::StreamOutputCache::lookupTags(const std::vector<std::string>& tags) const {
    TagLookupStatus result = TagLookupStatus::NOT_FOUND;
    for (const auto& tag : tags) {
        const auto status = lookupTag(tag);
        if (status == TagLookupStatus::FOUND_COMPLETE)
            return status;
        if (status == TagLookupStatus::FOUND_INCOMPLETE)
            result = status;
    }
    return result;
}

OutputParser::TagLookupStatus OutputParser::StreamOutputCache::lookupTagsAtBoundary(
    const std::vector<std::string>& tags,
    bool bufferStartIsBoundary) const {
    TagLookupStatus result = TagLookupStatus::NOT_FOUND;
    auto isBoundary = [&](size_t pos) {
        size_t begin = 0;
        bool boundary = bufferStartIsBoundary;
        if (pos > 0) {
            const size_t newline = buffer.rfind('\n', pos - 1);
            if (newline != std::string::npos) {
                begin = newline + 1;
                boundary = true;
            }
        }
        if (!boundary)
            return false;
        for (size_t i = begin; i < pos; ++i) {
            const char c = buffer[i];
            if (c != ' ' && c != '\t' && c != '\r')
                return false;
        }
        return true;
    };

    for (const auto& tag : tags) {
        if (tag.empty())
            continue;
        for (size_t pos = 0; pos < buffer.size(); ++pos) {
            if (!isBoundary(pos))
                continue;
            const size_t available = buffer.size() - pos;
            const size_t matched = std::min(available, tag.size());
            if (buffer.compare(pos, matched, tag, 0, matched) != 0)
                continue;
            if (available >= tag.size())
                return TagLookupStatus::FOUND_COMPLETE;
            result = TagLookupStatus::FOUND_INCOMPLETE;
        }
    }
    return result;
}

void OutputParser::StreamOutputCache::add(const std::string& chunk) {
    buffer += chunk;
}

void OutputParser::StreamOutputCache::clear() {
    buffer.clear();
}

const std::string& OutputParser::StreamOutputCache::getBuffer() const {
    return buffer;
}

OutputParser::TagLookupStatus OutputParser::lookupPreambleTags(const BaseOutputParser& parser) const {
    const auto& config = parser.getParsingConfig();
    if (config.preambleStartTagsRequireBoundary)
        return streamOutputCache.lookupTagsAtBoundary(config.preambleStartTags, preambleBoundaryAtBufferStart);
    return streamOutputCache.lookupTags(config.preambleStartTags);
}

std::optional<Delta> OutputParser::parseContentChunk(ProcessingPhase newPhase) {
    const std::string consumed = streamOutputCache.getBuffer();
    auto result = contentParser->parseChunk(consumed, {}, ov::genai::GenerationFinishReason::NONE);
    if (!result.has_value())
        return std::nullopt;
    preambleBoundaryAtBufferStart = updateBoundaryState(preambleBoundaryAtBufferStart, consumed);
    streamOutputCache.clear();
    processingPhase = newPhase;
    if (const auto* cd = std::get_if<ContentDelta>(&*result)) {
        if (cd->text.empty())
            return std::nullopt;
    }
    return result;
}

std::optional<Delta> OutputParser::parseToolCallChunk(const std::vector<int64_t>& tokens,
    ov::genai::GenerationFinishReason finishReason,
    ProcessingPhase newPhase) {
    if (!toolParser)
        throw std::runtime_error("Tool parser is not available, cannot parse tool call chunk");
    std::string remainder;
    const std::string& endTag = toolParser->getParsingConfig().endTag;
    if (!endTag.empty()) {
        const auto& buf = streamOutputCache.getBuffer();
        const size_t pos = buf.find(endTag);
        if (pos != std::string::npos)
            remainder = buf.substr(pos + endTag.size());
    }
    std::optional<Delta> result;
    try {
        result = toolParser->parseChunk(streamOutputCache.getBuffer(), tokens, finishReason);
    } catch (...) {
        streamOutputCache.clear();
        throw;
    }
    streamOutputCache.clear();
    processingPhase = newPhase;
    if (!remainder.empty())
        streamOutputCache.add(remainder);
    return result;
}

std::optional<Delta> OutputParser::parseReasoningChunk(const std::vector<int64_t>& tokens,
    ov::genai::GenerationFinishReason finishReason,
    ProcessingPhase newPhase) {
    if (!reasoningParser)
        throw std::runtime_error("Reasoning parser is not available, cannot parse reasoning chunk");
    std::string remainder;
    const std::string& endTag = reasoningParser->getParsingConfig().endTag;
    if (!endTag.empty()) {
        const auto& buf = streamOutputCache.getBuffer();
        const size_t pos = buf.find(endTag);
        if (pos != std::string::npos)
            remainder = buf.substr(pos + endTag.size());
    }
    std::optional<Delta> result;
    try {
        result = reasoningParser->parseChunk(streamOutputCache.getBuffer(), tokens, finishReason);
    } catch (...) {
        streamOutputCache.clear();
        throw;
    }
    streamOutputCache.clear();
    processingPhase = newPhase;
    if (newPhase == UNKNOWN)
        preambleBoundaryAtBufferStart = true;
    if (!remainder.empty())
        streamOutputCache.add(remainder);
    return result;
}

OutputParser::OutputParser(ov::genai::Tokenizer& tokenizer,
    const std::string toolParserName,
    const std::string reasoningParserName,
    const ToolsSchemas_t& toolNameSchemaMap) :
    tokenizer(tokenizer) {
    if (toolParserName == "llama3")
        toolParser = std::make_unique<Llama3ToolParser>(tokenizer);
    else if (toolParserName == "hermes3")
        toolParser = std::make_unique<Hermes3ToolParser>(tokenizer);
    else if (toolParserName == "phi4")
        toolParser = std::make_unique<Phi4ToolParser>(tokenizer);
    else if (toolParserName == "mistral")
        toolParser = std::make_unique<MistralToolParser>(tokenizer);
    else if (toolParserName == "gptoss")
        toolParser = std::make_unique<GptOssToolParser>(tokenizer);
    else if (toolParserName == "qwen3coder")
        toolParser = std::make_unique<Qwen3CoderToolParser>(tokenizer, toolNameSchemaMap);
    else if (toolParserName == "devstral")
        toolParser = std::make_unique<DevstralToolParser>(tokenizer, toolNameSchemaMap);
    else if (toolParserName == "lfm2")
        toolParser = std::make_unique<Lfm2ToolParser>(tokenizer);
    else if (toolParserName == "gemma4")
        toolParser = std::make_unique<Gemma4ToolParser>(tokenizer, toolNameSchemaMap);
    else if (toolParserName == "onyx")
        toolParser = std::make_unique<OnyxToolParser>(tokenizer, toolNameSchemaMap);
    else if (toolParserName == "minicpm5")
        toolParser = std::make_unique<Minicpm5ToolParser>(tokenizer, toolNameSchemaMap);
    else if (!toolParserName.empty())
        throw std::runtime_error("Unsupported tool parser: \"" + toolParserName +
                                 "\". Supported tool parsers are: " + getSupportedToolParserNamesAsString());

    if (reasoningParserName == "qwen3")
        reasoningParser = std::make_unique<Qwen3ReasoningParser>(tokenizer);
    else if (reasoningParserName == "gemma4")
        reasoningParser = std::make_unique<Gemma4ReasoningParser>(tokenizer);
    else if (reasoningParserName == "gptoss")
        reasoningParser = std::make_unique<GptOssReasoningParser>(tokenizer);
    else if (reasoningParserName == "minicpm5")
        reasoningParser = std::make_unique<Minicpm5ReasoningParser>(tokenizer);
    else if (reasoningParserName == "lfm2")
        reasoningParser = std::make_unique<Lfm25ReasoningParser>(tokenizer);
    else if (reasoningParserName == "onyx")
        reasoningParser = std::make_unique<OnyxReasoningParser>(tokenizer);
    else if (!reasoningParserName.empty())
        throw std::runtime_error("Unsupported reasoning parser: \"" + reasoningParserName +
                                 "\". Supported reasoning parsers are: " + getSupportedReasoningParserNamesAsString());

    if (toolParserName == "onyx" || reasoningParserName == "onyx")
        contentParser = std::make_unique<OnyxContentParser>(tokenizer);
    else if (toolParserName == "gptoss" || reasoningParserName == "gptoss")
        contentParser = std::make_unique<DefaultContentParser>(tokenizer, std::vector<std::string>{
                                                                              "<|start|>assistant<|channel|>final<|message|>",
                                                                              "<|channel|>final<|message|>",
                                                                              "<|channel|>commentary<|message|>",
                                                                              "<|end|>",
                                                                              "<|return|>"});
    else if (toolParserName == "gemma4")
        contentParser = std::make_unique<DefaultContentParser>(tokenizer, std::vector<std::string>{"<turn|>", "<|tool_response>", "<|channel>thought\n", "<channel|>"});
    else if (toolParserName == "lfm2")
        contentParser = std::make_unique<DefaultContentParser>(tokenizer, std::vector<std::string>{"<|im_end|>"});
    else if (toolParserName == "minicpm5")
        contentParser = std::make_unique<DefaultContentParser>(tokenizer, std::vector<std::string>{"<s>", "<|im_end|>"});
    else
        contentParser = std::make_unique<DefaultContentParser>(tokenizer);

    defaultDecodingWithSpecialTokens =
        (toolParser && toolParser->getParsingConfig().defaultDecodingWithSpecialTokens) ||
        (reasoningParser && reasoningParser->getParsingConfig().defaultDecodingWithSpecialTokens);

    if (llm_calculator_logger->should_log(spdlog::level::debug)) {
        const std::string toolConfig = toolParser ? toolParser->buildParsingConfigStringRepresentation() : "N/A";
        const std::string reasoningConfig = reasoningParser ? reasoningParser->buildParsingConfigStringRepresentation() : "N/A";
        SPDLOG_LOGGER_DEBUG(llm_calculator_logger,
            "OutputParser initialized with tool parser: \"{}\" (parsing config: {}), reasoning parser: \"{}\" (parsing config: {}), defaultDecodingWithSpecialTokens={}",
            toolParserName, toolConfig, reasoningParserName, reasoningConfig, defaultDecodingWithSpecialTokens);
    }
}

bool OutputParser::isToolParserAvailable() const { return toolParser != nullptr; }
bool OutputParser::isReasoningParserAvailable() const { return reasoningParser != nullptr; }

std::string OutputParser::getToolParserStartTag() const {
    if (!toolParser)
        throw std::runtime_error("Tool parser is not available, cannot get start tag");
    return toolParser->getParsingConfig().startTags[0];
}

void OutputParser::resetStreamingState() {
    processingPhase = UNKNOWN;
    streamOutputCache.clear();
    preambleBoundaryAtBufferStart = true;
    if (toolParser)
        toolParser->resetState();
    if (reasoningParser)
        reasoningParser->resetState();
    if (contentParser)
        contentParser->resetState();
    if (implicitReasoningStart)
        setImplicitReasoningStart(true);
}

bool OutputParser::needSpecialTokensForCurrentDecode(bool userWantsSpecialTokens) const {
    if (processingPhase == CONTENT || processingPhase == UNKNOWN)
        return defaultDecodingWithSpecialTokens || userWantsSpecialTokens;
    if (processingPhase == REASONING)
        return reasoningParser && reasoningParser->getParsingConfig().needsSpecialTokens;
    if (processingPhase == TOOL_CALLS_PROCESSING_TOOL || processingPhase == TOOL_CALLS_WAITING_FOR_TOOL)
        return toolParser && toolParser->getParsingConfig().needsSpecialTokens;
    return false;
}

std::string OutputParser::getPhaseStartTagForToken(int64_t tokenId, bool toolsAvailable) const {
    if (toolParser && toolsAvailable) {
        const auto& tokenMap = toolParser->getResolvedStartTokenToTag();
        const auto it = tokenMap.find(tokenId);
        if (it != tokenMap.end() && processingPhase != TOOL_CALLS_PROCESSING_TOOL && processingPhase != TOOL_CALLS_WAITING_FOR_TOOL)
            return it->second;
    }
    if (reasoningParser) {
        const auto& tokenMap = reasoningParser->getResolvedStartTokenToTag();
        const auto it = tokenMap.find(tokenId);
        if (it != tokenMap.end() && processingPhase != REASONING)
            return it->second;
    }
    return {};
}

void OutputParser::setImplicitReasoningStart(bool value) {
    implicitReasoningStart = value;
    if (!reasoningParser)
        return;
    reasoningParser->setImplicitStart(value);
    if (processingPhase == UNKNOWN || processingPhase == REASONING)
        processingPhase = value ? REASONING : UNKNOWN;
}

void OutputParser::detectAndSetImplicitReasoningStart(const std::string& renderedPrompt) {
    if (!reasoningParser)
        return;
    std::string trimmed = renderedPrompt;
    rtrim(trimmed);
    const auto& startTags = reasoningParser->getParsingConfig().startTags;
    const bool detected = std::any_of(startTags.begin(), startTags.end(),
        [&](const std::string& tag) { return !tag.empty() && endsWith(trimmed, tag); });
    setImplicitReasoningStart(detected);
}

std::optional<Delta> OutputParser::parseChunk(const std::string& chunkResponse,
    const std::vector<int64_t>& tokens,
    const bool toolsAvailable,
    ov::genai::GenerationFinishReason finishReason) {
    const bool reasoningStreaming = reasoningParser && !reasoningParser->getParsingConfig().startTags.empty() && !reasoningParser->getParsingConfig().endTag.empty();
    const bool toolStreaming = toolParser && !toolParser->getParsingConfig().startTags.empty();
    const bool applyToolParser = toolStreaming && toolsAvailable;

    streamOutputCache.add(chunkResponse);

    if (processingPhase == UNKNOWN) {
        TagLookupStatus anyStart = TagLookupStatus::NOT_FOUND;
        if (reasoningStreaming) {
            auto status = streamOutputCache.lookupTags(reasoningParser->getParsingConfig().startTags);
            if (status == TagLookupStatus::NOT_FOUND)
                status = lookupPreambleTags(*reasoningParser);
            if (status == TagLookupStatus::FOUND_COMPLETE)
                return parseReasoningChunk(tokens, finishReason);
            anyStart = status;
        }
        if (applyToolParser) {
            auto status = streamOutputCache.lookupTags(toolParser->getParsingConfig().startTags);
            if (status == TagLookupStatus::NOT_FOUND)
                status = lookupPreambleTags(*toolParser);
            if (status == TagLookupStatus::FOUND_COMPLETE)
                return parseToolCallChunk(tokens, finishReason);
            if (status == TagLookupStatus::FOUND_INCOMPLETE)
                anyStart = status;
        }
        if ((!reasoningStreaming && !applyToolParser) ||
            finishReason != ov::genai::GenerationFinishReason::NONE ||
            anyStart == TagLookupStatus::NOT_FOUND)
            return parseContentChunk();
        return std::nullopt;
    }

    if (processingPhase == REASONING) {
        const auto status = streamOutputCache.lookupTag(reasoningParser->getParsingConfig().endTag);
        if (status == TagLookupStatus::FOUND_COMPLETE)
            return parseReasoningChunk(tokens, finishReason, UNKNOWN);
        if (status == TagLookupStatus::FOUND_INCOMPLETE && finishReason == ov::genai::GenerationFinishReason::NONE)
            return std::nullopt;
        return parseReasoningChunk(tokens, finishReason);
    }

    if (processingPhase == CONTENT) {
        if (applyToolParser) {
            auto status = streamOutputCache.lookupTags(toolParser->getParsingConfig().startTags);
            if (status == TagLookupStatus::NOT_FOUND && toolParser->getParsingConfig().preambleStartTagsRequireBoundary)
                status = lookupPreambleTags(*toolParser);
            if (status == TagLookupStatus::FOUND_COMPLETE)
                return parseToolCallChunk(tokens, finishReason);
            if (status == TagLookupStatus::FOUND_INCOMPLETE && finishReason == ov::genai::GenerationFinishReason::NONE)
                return std::nullopt;
        }
        return parseContentChunk();
    }

    if (processingPhase == TOOL_CALLS_PROCESSING_TOOL) {
        const auto status = streamOutputCache.lookupTag(toolParser->getParsingConfig().endTag);
        if (status == TagLookupStatus::FOUND_INCOMPLETE && finishReason == ov::genai::GenerationFinishReason::NONE)
            return std::nullopt;
        if (status == TagLookupStatus::FOUND_COMPLETE)
            return parseToolCallChunk(tokens, finishReason, TOOL_CALLS_WAITING_FOR_TOOL);
        return parseToolCallChunk(tokens, finishReason);
    }

    if (processingPhase == TOOL_CALLS_WAITING_FOR_TOOL) {
        const auto toolStatus = streamOutputCache.lookupTags(toolParser->getParsingConfig().startTags);
        if (toolStatus == TagLookupStatus::FOUND_COMPLETE)
            return parseToolCallChunk(tokens, finishReason, TOOL_CALLS_PROCESSING_TOOL);
        const auto& contentStartTags = contentParser->getParsingConfig().startTags;
        if (!contentStartTags.empty()) {
            const auto contentStatus = streamOutputCache.lookupTags(contentStartTags);
            if (contentStatus == TagLookupStatus::FOUND_COMPLETE || finishReason != ov::genai::GenerationFinishReason::NONE)
                return parseContentChunk();
            return std::nullopt;
        }
        if (toolStatus == TagLookupStatus::FOUND_INCOMPLETE && finishReason == ov::genai::GenerationFinishReason::NONE)
            return std::nullopt;
        return parseToolCallChunk(tokens, finishReason, TOOL_CALLS_WAITING_FOR_TOOL);
    }

    SPDLOG_LOGGER_ERROR(llm_calculator_logger, "Unexpected processing phase: {}", static_cast<int>(processingPhase));
    throw std::runtime_error("Unexpected error during stream output parsing");
}

}  // namespace ovms
