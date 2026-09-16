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

#include <memory>
#include <openvino/genai/tokenizer.hpp>
#include <string>
#include <vector>

#include "base_output_parser.hpp"
#include "src/llm/apis/tool_schema_wrapper.hpp"

namespace ovms {

class OutputParser {
public:
    enum TagLookupStatus {
        NOT_FOUND,
        FOUND_COMPLETE,
        FOUND_INCOMPLETE
    };

    class StreamOutputCache {
        std::string buffer;

    public:
        TagLookupStatus lookupTag(const std::string& tag) const;
        TagLookupStatus lookupTags(const std::vector<std::string>& tags) const;
        TagLookupStatus lookupTagsAtBoundary(const std::vector<std::string>& tags, bool bufferStartIsBoundary) const;
        void add(const std::string& chunk);
        void clear();
        const std::string& getBuffer() const;
    };

    enum ProcessingPhase {
        UNKNOWN,
        CONTENT,
        REASONING,
        TOOL_CALLS_PROCESSING_TOOL,
        TOOL_CALLS_WAITING_FOR_TOOL
    };

private:
    ov::genai::Tokenizer tokenizer;
    std::unique_ptr<BaseOutputParser> toolParser = nullptr;
    std::unique_ptr<BaseOutputParser> reasoningParser = nullptr;
    std::unique_ptr<BaseOutputParser> contentParser = nullptr;

    ProcessingPhase processingPhase = UNKNOWN;
    StreamOutputCache streamOutputCache;
    bool implicitReasoningStart = false;
    bool defaultDecodingWithSpecialTokens = false;
    // Boundary state immediately before streamOutputCache[0]. It survives cache
    // clears, so a chunk boundary cannot manufacture a recovery boundary.
    bool preambleBoundaryAtBufferStart = true;

    std::optional<Delta> parseContentChunk(ProcessingPhase newPhase = CONTENT);
    std::optional<Delta> parseToolCallChunk(const std::vector<int64_t>& tokens,
        ov::genai::GenerationFinishReason finishReason,
        ProcessingPhase newPhase = TOOL_CALLS_PROCESSING_TOOL);
    std::optional<Delta> parseReasoningChunk(const std::vector<int64_t>& tokens,
        ov::genai::GenerationFinishReason finishReason,
        ProcessingPhase newPhase = REASONING);

    TagLookupStatus lookupPreambleTags(const BaseOutputParser& parser) const;
    void setImplicitReasoningStart(bool value);

public:
    OutputParser() = delete;
    explicit OutputParser(ov::genai::Tokenizer& tokenizer,
        const std::string toolParserName,
        const std::string reasoningParserName,
        const ToolsSchemas_t& toolNameSchemaMap);

    bool isToolParserAvailable() const;
    bool isReasoningParserAvailable() const;
    std::string getToolParserStartTag() const;

    void resetStreamingState();
    void detectAndSetImplicitReasoningStart(const std::string& renderedPrompt);

    std::optional<Delta> parseChunk(const std::string& chunkResponse,
        const std::vector<int64_t>& tokens,
        const bool toolsAvailable,
        ov::genai::GenerationFinishReason finishReason);

    bool needSpecialTokensForCurrentDecode(bool userWantsSpecialTokens = false) const;
    std::string getPhaseStartTagForToken(int64_t tokenId, bool toolsAvailable = true) const;
};

}  // namespace ovms
