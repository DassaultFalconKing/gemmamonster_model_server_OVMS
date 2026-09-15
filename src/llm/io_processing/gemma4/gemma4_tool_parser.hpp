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

#include <optional>
#include <string>
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
    enum class State {
        Content,
        ToolCallStarted,
        ToolCallParameters,
        ToolCallEnded,
        AfterToolCall
    };

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
        BaseOutputParser(tokenizer,
            configOverride.has_value() ? std::move(*configOverride) : defaultParsingConfig()) {}

    void resetState() override {
        streamingContent.clear();
        streamingPosition = 0;
        currentState = State::Content;
        toolCall = {};
        toolCallIndex = -1;
        currentArgsOpen = '{';
        currentArgsClose = '}';
        currentCallValid = true;
    }

    std::optional<Delta> parseChunk(const std::string& chunk,
        const std::vector<int64_t>& tokens,
        ov::genai::GenerationFinishReason finishReason) override;

    // Compatibility helpers used by existing tests/callers. Executable calls use
    // parseNativeArgumentsBody(), which fails closed instead of stringifying malformed values.
    static std::string normalizeArgStr(const std::string& arg);
    static std::string parseArrayParameter(const std::string& argumentStr);
    static std::string parseObjectParameter(const std::string& argumentStr);

private:
    static std::optional<std::string> parseNativeArgumentsBody(const std::string& argumentsBody);
    static std::optional<size_t> findMatchingContainerEnd(
        const std::string& text,
        size_t openPos,
        char openChar,
        char closeChar,
        size_t& malformedEndTag);
    static std::string normalizeToolName(std::string rawName);

    bool parseNewContent();
    bool parseInContentState();
    bool parseInToolCallState();
    bool parseToolCallParametersState();
    bool parseInToolCallEndedState();

    std::optional<Delta> wrapDeltaContent(const std::string& content);
    ToolCallDelta wrapDeltaArgs(const std::string& argsStr, int toolCallIndex);

    std::string streamingContent;
    size_t streamingPosition{0};
    State currentState{State::Content};
    ToolCall toolCall;
    int toolCallIndex{-1};
    char currentArgsOpen{'{'};
    char currentArgsClose{'}'};
    bool currentCallValid{true};
};

}  // namespace ovms
