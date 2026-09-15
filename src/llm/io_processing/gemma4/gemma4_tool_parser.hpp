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
#pragma once

#include <deque>
#include <optional>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

#include "src/llm/io_processing/base_output_parser.hpp"

namespace ovms {

class Gemma4ToolParser : public BaseOutputParser {
public:
    static const std::string TOOL_CALL_START_TAG;
    static const std::string TOOL_CALL_END_TAG;
    static const std::string TOOL_CALL_NAME_PREFIX;
    static const std::string TOOL_ARGS_STRING_INDICATOR;
    static const std::string TURN_END_TAG;
    static const std::string TOOL_RESPONSE_START_TAG;

protected:
    enum class State { Content, ToolCallStarted, ToolCallParameters, ToolCallEnded, AfterToolCall };

public:
    Gemma4ToolParser() = delete;

    static OutputParsingConfig defaultParsingConfig() {
        OutputParsingConfig cfg;
        cfg.startTags = {TOOL_CALL_START_TAG};
        cfg.tokenIdStartTags = {TOOL_CALL_START_TAG};
        cfg.endTag = TOOL_CALL_END_TAG;
        cfg.needsSpecialTokens = true;
        return cfg;
    }

    explicit Gemma4ToolParser(ov::genai::Tokenizer& tokenizer,
        std::optional<OutputParsingConfig> configOverride = std::nullopt) :
        BaseOutputParser(tokenizer, configOverride.has_value() ? std::move(*configOverride) : defaultParsingConfig()) {}

    Gemma4ToolParser(ov::genai::Tokenizer& tokenizer,
        const ToolsSchemas_t& toolsSchemas,
        std::optional<OutputParsingConfig> configOverride = std::nullopt) :
        BaseOutputParser(tokenizer, configOverride.has_value() ? std::move(*configOverride) : defaultParsingConfig()) {
        for (const auto& [name, schema] : toolsSchemas) {
            (void)schema;
            allowedToolNames.insert(name);
        }
        enforceToolRegistry = !allowedToolNames.empty();
        if (enforceToolRegistry && !configOverride.has_value()) {
            parsingConfig.startTags.clear();
            parsingConfig.preambleStartTags.clear();
            parsingConfig.startTags.reserve(allowedToolNames.size() * 4);
            parsingConfig.preambleStartTags.reserve(allowedToolNames.size() * 2);
            for (const auto& name : allowedToolNames) {
                parsingConfig.startTags.push_back(TOOL_CALL_START_TAG + TOOL_CALL_NAME_PREFIX + name + "{");
                parsingConfig.startTags.push_back(TOOL_CALL_START_TAG + TOOL_CALL_NAME_PREFIX + name + "(");
                parsingConfig.startTags.push_back(TOOL_CALL_START_TAG + ":" + name + "{");
                parsingConfig.startTags.push_back(TOOL_CALL_START_TAG + ":" + name + "(");
                parsingConfig.preambleStartTags.push_back(TOOL_CALL_NAME_PREFIX + name + "{");
                parsingConfig.preambleStartTags.push_back(TOOL_CALL_NAME_PREFIX + name + "(");
            }
            parsingConfig.preambleStartTagsRequireBoundary = true;
        }
    }

    void resetState() override {
        streamingContent.clear();
        streamingPosition = 0;
        currentState = State::Content;
        clearCandidate();
        nextPublicIndex = 0;
        pendingEvents.clear();
        currentArgsOpen = '{';
        currentArgsClose = '}';
    }

    std::optional<Delta> parseChunk(const std::string& chunk,
        const std::vector<int64_t>& tokens,
        ov::genai::GenerationFinishReason finishReason) override;

    static std::string normalizeArgStr(const std::string& arg);
    static std::string parseArrayParameter(const std::string& argumentStr);
    static std::string parseObjectParameter(const std::string& argumentStr);

private:
    struct PrivateCandidate {
        std::string name;
        std::string arguments;
        bool nameValid{false};
        bool argsComplete{false};
        bool envelopeRejected{false};
    };

    static std::optional<std::string> parseNativeArgumentsBody(const std::string& argumentsBody);
    static std::optional<size_t> findMatchingContainerEnd(const std::string& text,
        size_t openPos, char openChar, char closeChar, size_t& malformedEndTag);
    static std::string normalizeToolName(std::string rawName);

    bool toolNameAllowed(const std::string& name) const {
        return !enforceToolRegistry || allowedToolNames.count(name) != 0;
    }

    void clearCandidate();
    void rejectCandidateEnvelope();
    void commitCandidateIfReady();
    bool parseNewContent();
    bool parseInContentState();
    bool parseInToolCallState();
    bool parseToolCallParametersState();
    bool parseInToolCallEndedState();
    std::optional<size_t> findBarePreamble(size_t from) const;
    std::optional<Delta> wrapDeltaContent(const std::string& content);
    std::optional<Delta> takePendingEvent();
    std::string eraseSpecialMarkers(std::string content) const;

    std::string streamingContent;
    size_t streamingPosition{0};
    State currentState{State::Content};
    PrivateCandidate candidate;
    int nextPublicIndex{0};
    char currentArgsOpen{'{'};
    char currentArgsClose{'}'};
    bool enforceToolRegistry{false};
    std::unordered_set<std::string> allowedToolNames;
    std::deque<Delta> pendingEvents;
};

}  // namespace ovms
