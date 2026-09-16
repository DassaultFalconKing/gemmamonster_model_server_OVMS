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

#include "gemma4_tool_parser.hpp"
#include "../utils.hpp"

#include <algorithm>
#include <cctype>
#include <deque>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include <rapidjson/reader.h>

#include "../../../logging.hpp"
#include "../../../stringutils.hpp"
#include "src/port/rapidjson_document.hpp"
#include "src/port/rapidjson_stringbuffer.hpp"
#include "src/port/rapidjson_writer.hpp"

namespace ovms {

const std::string Gemma4ToolParser::TOOL_CALL_START_TAG = "<|tool_call>";
const std::string Gemma4ToolParser::TOOL_CALL_END_TAG = "<tool_call|>";
const std::string Gemma4ToolParser::TOOL_CALL_NAME_PREFIX = "call:";
const std::string Gemma4ToolParser::TOOL_ARGS_STRING_INDICATOR = "<|\"|>";
const std::string Gemma4ToolParser::TURN_END_TAG = "<turn|>";
const std::string Gemma4ToolParser::TOOL_RESPONSE_START_TAG = "<|tool_response>";

namespace {
using JsonWriter = rapidjson::Writer<rapidjson::StringBuffer>;

// A generated tool call should be far smaller than the surrounding HTTP/model
// limits. These local caps prevent a malformed candidate from retaining
// unbounded streaming state while leaving ample room for legitimate arguments.
constexpr size_t MAX_NATIVE_TOOL_CANDIDATE_BYTES = 64 * 1024;
constexpr size_t MAX_NATIVE_TOOL_CONTAINER_DEPTH = 64;

class NumberPreservingWriter : public JsonWriter {
public:
    explicit NumberPreservingWriter(rapidjson::StringBuffer& buffer) : JsonWriter(buffer) {}
    bool RawNumber(const char* value, rapidjson::SizeType length, bool) {
        return RawValue(value, length, rapidjson::kNumberType);
    }
};

std::optional<std::string> normalizeJsonLosslessly(const std::string& input) {
    rapidjson::StringStream stream(input.c_str());
    rapidjson::Reader reader;
    rapidjson::StringBuffer buffer;
    NumberPreservingWriter writer(buffer);
    if (!reader.Parse<rapidjson::kParseNumbersAsStringsFlag>(stream, writer) || stream.Tell() != input.size())
        return std::nullopt;
    return std::string(buffer.GetString(), buffer.GetSize());
}

void trimLocal(std::string& value) {
    auto notSpace = [](unsigned char c) { return !std::isspace(c); };
    value.erase(value.begin(), std::find_if(value.begin(), value.end(), notSpace));
    value.erase(std::find_if(value.rbegin(), value.rend(), notSpace).base(), value.end());
}

bool saneToolName(const std::string& name) {
    return !name.empty() && std::all_of(name.begin(), name.end(), [](unsigned char c) {
        return std::isalnum(c) || c == '_' || c == '-' || c == '.';
    });
}

bool isLogicalBoundary(const std::string& text, size_t pos) {
    if (pos == 0)
        return true;  // The generic router only enters on a boundary-validated preamble.
    const size_t newline = text.rfind('\n', pos - 1);
    if (newline == std::string::npos)
        return false;
    for (size_t i = newline + 1; i < pos; ++i) {
        const char c = text[i];
        if (c != ' ' && c != '\t' && c != '\r')
            return false;
    }
    return true;
}

class NativeValueParser {
    const std::string& input;
    size_t pos{0};
    JsonWriter& writer;

    bool startsWith(const std::string& marker) const {
        return pos + marker.size() <= input.size() && input.compare(pos, marker.size(), marker) == 0;
    }
    void skipWs() {
        while (pos < input.size() && std::isspace(static_cast<unsigned char>(input[pos])))
            ++pos;
    }
    bool writeJsonScalar(const std::string& token) {
        auto normalized = normalizeJsonLosslessly(token);
        if (!normalized || normalized->empty())
            return false;
        const char first = normalized->front();
        rapidjson::Type type = rapidjson::kNumberType;
        if (first == '"') type = rapidjson::kStringType;
        else if (first == 't') type = rapidjson::kTrueType;
        else if (first == 'f') type = rapidjson::kFalseType;
        else if (first == 'n') type = rapidjson::kNullType;
        else if (!(first == '-' || std::isdigit(static_cast<unsigned char>(first)))) return false;
        return writer.RawValue(normalized->data(), static_cast<rapidjson::SizeType>(normalized->size()), type);
    }
    bool parseDelimitedString() {
        if (!startsWith(Gemma4ToolParser::TOOL_ARGS_STRING_INDICATOR)) return false;
        pos += Gemma4ToolParser::TOOL_ARGS_STRING_INDICATOR.size();
        const size_t end = input.find(Gemma4ToolParser::TOOL_ARGS_STRING_INDICATOR, pos);
        if (end == std::string::npos) return false;
        writer.String(input.data() + pos, static_cast<rapidjson::SizeType>(end - pos));
        pos = end + Gemma4ToolParser::TOOL_ARGS_STRING_INDICATOR.size();
        return true;
    }
    bool parseJsonString() {
        if (pos >= input.size() || input[pos] != '"') return false;
        const size_t start = pos++;
        bool escaped = false;
        while (pos < input.size()) {
            const char c = input[pos++];
            if (escaped) { escaped = false; continue; }
            if (c == '\\') { escaped = true; continue; }
            if (c == '"') return writeJsonScalar(input.substr(start, pos - start));
        }
        return false;
    }
    bool parseKey(std::string& key) {
        skipWs();
        if (startsWith(Gemma4ToolParser::TOOL_ARGS_STRING_INDICATOR)) {
            pos += Gemma4ToolParser::TOOL_ARGS_STRING_INDICATOR.size();
            const size_t end = input.find(Gemma4ToolParser::TOOL_ARGS_STRING_INDICATOR, pos);
            if (end == std::string::npos) return false;
            key = input.substr(pos, end - pos);
            pos = end + Gemma4ToolParser::TOOL_ARGS_STRING_INDICATOR.size();
            return true;
        }
        if (pos < input.size() && input[pos] == '"') {
            const size_t start = pos++;
            bool escaped = false;
            while (pos < input.size()) {
                const char c = input[pos++];
                if (escaped) { escaped = false; continue; }
                if (c == '\\') { escaped = true; continue; }
                if (c == '"') {
                    const std::string token = input.substr(start, pos - start);
                    rapidjson::Document doc;
                    doc.Parse(token.c_str());
                    if (doc.HasParseError() || !doc.IsString()) return false;
                    key.assign(doc.GetString(), doc.GetStringLength());
                    return true;
                }
            }
            return false;
        }
        const size_t start = pos;
        while (pos < input.size() && input[pos] != ':') ++pos;
        if (pos == input.size()) return false;
        key = input.substr(start, pos - start);
        trimLocal(key);
        return !key.empty();
    }
    bool parseObject() {
        if (pos >= input.size() || input[pos] != '{') return false;
        ++pos; writer.StartObject(); skipWs();
        if (pos < input.size() && input[pos] == '}') { ++pos; writer.EndObject(); return true; }
        while (pos < input.size()) {
            std::string key;
            if (!parseKey(key)) return false;
            skipWs(); if (pos >= input.size() || input[pos] != ':') return false;
            ++pos; writer.Key(key.c_str(), static_cast<rapidjson::SizeType>(key.size()));
            if (!parseValue()) return false;
            skipWs();
            if (pos < input.size() && input[pos] == ',') { ++pos; skipWs(); continue; }
            if (pos < input.size() && input[pos] == '}') { ++pos; writer.EndObject(); return true; }
            return false;
        }
        return false;
    }
    bool parseArray() {
        if (pos >= input.size() || input[pos] != '[') return false;
        ++pos; writer.StartArray(); skipWs();
        if (pos < input.size() && input[pos] == ']') { ++pos; writer.EndArray(); return true; }
        while (pos < input.size()) {
            if (!parseValue()) return false;
            skipWs();
            if (pos < input.size() && input[pos] == ',') { ++pos; skipWs(); continue; }
            if (pos < input.size() && input[pos] == ']') { ++pos; writer.EndArray(); return true; }
            return false;
        }
        return false;
    }
    bool parseBareScalar() {
        const size_t start = pos;
        while (pos < input.size()) {
            const char c = input[pos];
            if (c == ',' || c == '}' || c == ']' || c == ')') break;
            ++pos;
        }
        std::string token = input.substr(start, pos - start);
        trimLocal(token);
        return !token.empty() && writeJsonScalar(token);
    }

public:
    NativeValueParser(const std::string& input, JsonWriter& writer) : input(input), writer(writer) {}
    bool parseValue() {
        skipWs(); if (pos >= input.size()) return false;
        if (startsWith(Gemma4ToolParser::TOOL_ARGS_STRING_INDICATOR)) return parseDelimitedString();
        if (input[pos] == '"') return parseJsonString();
        if (input[pos] == '{') return parseObject();
        if (input[pos] == '[') return parseArray();
        return parseBareScalar();
    }
    bool parseArgumentsBody() {
        writer.StartObject(); skipWs();
        if (pos == input.size()) { writer.EndObject(); return true; }
        while (pos < input.size()) {
            std::string key;
            if (!parseKey(key)) return false;
            skipWs(); if (pos >= input.size() || input[pos] != ':') return false;
            ++pos; writer.Key(key.c_str(), static_cast<rapidjson::SizeType>(key.size()));
            if (!parseValue()) return false;
            skipWs();
            if (pos == input.size()) { writer.EndObject(); return true; }
            if (input[pos] != ',') return false;
            ++pos; skipWs(); if (pos == input.size()) return false;
        }
        return false;
    }
    bool parseSingleValueFully() {
        if (!parseValue()) return false;
        skipWs(); return pos == input.size();
    }
};

std::optional<std::string> normalizeSingleNativeValue(const std::string& arg) {
    std::string value = arg; trimLocal(value);
    if (value.empty()) return std::nullopt;
    rapidjson::StringBuffer buffer; JsonWriter writer(buffer);
    NativeValueParser parser(value, writer);
    if (!parser.parseSingleValueFully()) return std::nullopt;
    return std::string(buffer.GetString(), buffer.GetSize());
}
}  // namespace

std::optional<std::string> Gemma4ToolParser::parseNativeArgumentsBody(const std::string& body) {
    rapidjson::StringBuffer buffer; JsonWriter writer(buffer); NativeValueParser parser(body, writer);
    if (!parser.parseArgumentsBody()) return std::nullopt;
    return std::string(buffer.GetString(), buffer.GetSize());
}

std::optional<size_t> Gemma4ToolParser::findMatchingContainerEnd(const std::string& text,
    size_t openPos, char openChar, char closeChar, size_t& malformedEndTag,
    bool& candidateLimitExceeded) {
    malformedEndTag = std::string::npos;
    candidateLimitExceeded = false;
    if (openPos >= text.size() || text[openPos] != openChar) return std::nullopt;
    std::vector<char> closers{closeChar};
    bool malformed = false;
    size_t i = openPos + 1;
    while (i < text.size()) {
        if (i - openPos > MAX_NATIVE_TOOL_CANDIDATE_BYTES) {
            candidateLimitExceeded = true;
            malformedEndTag = text.find(TOOL_CALL_END_TAG, i);
            return std::nullopt;
        }
        if (text.compare(i, TOOL_ARGS_STRING_INDICATOR.size(), TOOL_ARGS_STRING_INDICATOR) == 0) {
            const size_t end = text.find(TOOL_ARGS_STRING_INDICATOR, i + TOOL_ARGS_STRING_INDICATOR.size());
            const size_t envelopeEnd = text.find(TOOL_CALL_END_TAG, i + TOOL_ARGS_STRING_INDICATOR.size());
            if (envelopeEnd != std::string::npos && (end == std::string::npos || envelopeEnd < end)) {
                malformedEndTag = envelopeEnd;
                return std::nullopt;
            }
            if (end == std::string::npos)
                return std::nullopt;
            if (end - openPos > MAX_NATIVE_TOOL_CANDIDATE_BYTES) {
                candidateLimitExceeded = true;
                malformedEndTag = text.find(TOOL_CALL_END_TAG, end);
                return std::nullopt;
            }
            i = end + TOOL_ARGS_STRING_INDICATOR.size(); continue;
        }
        if (text[i] == '"') {
            ++i; bool escaped = false;
            bool closed = false;
            while (i < text.size()) {
                if (i - openPos > MAX_NATIVE_TOOL_CANDIDATE_BYTES) {
                    candidateLimitExceeded = true;
                    malformedEndTag = text.find(TOOL_CALL_END_TAG, i);
                    return std::nullopt;
                }
                if (text.compare(i, TOOL_CALL_END_TAG.size(), TOOL_CALL_END_TAG) == 0) {
                    malformedEndTag = i;
                    return std::nullopt;
                }
                const char c = text[i++];
                if (escaped) { escaped = false; continue; }
                if (c == '\\') { escaped = true; continue; }
                if (c == '"') {
                    closed = true;
                    break;
                }
            }
            if (!closed)
                return std::nullopt;
            continue;
        }
        if (text.compare(i, TOOL_CALL_END_TAG.size(), TOOL_CALL_END_TAG) == 0) {
            malformedEndTag = i; return std::nullopt;
        }
        switch (text[i]) {
        case '{':
        case '[':
        case '(':
            if (closers.size() >= MAX_NATIVE_TOOL_CONTAINER_DEPTH) {
                candidateLimitExceeded = true;
                malformedEndTag = text.find(TOOL_CALL_END_TAG, i);
                return std::nullopt;
            }
            if (text[i] == '{')
                closers.push_back('}');
            else if (text[i] == '[')
                closers.push_back(']');
            else
                closers.push_back(')');
            break;
        case '}': case ']': case ')':
            if (closers.empty() || closers.back() != text[i]) { malformed = true; break; }
            closers.pop_back();
            if (closers.empty() && !malformed) return i;
            break;
        default: break;
        }
        ++i;
    }
    return std::nullopt;
}

std::string Gemma4ToolParser::normalizeToolName(std::string name) {
    trim(name);
    if (name.rfind(TOOL_CALL_NAME_PREFIX, 0) == 0) name.erase(0, TOOL_CALL_NAME_PREFIX.size());
    trim(name);
    if (!name.empty() && name.front() == ':') name.erase(name.begin());
    trim(name);
    return name;
}

std::string Gemma4ToolParser::normalizeArgStr(const std::string& arg) {
    auto normalized = normalizeSingleNativeValue(arg);
    return normalized.value_or(arg);
}
std::string Gemma4ToolParser::parseArrayParameter(const std::string& arg) { return normalizeArgStr(arg); }
std::string Gemma4ToolParser::parseObjectParameter(const std::string& arg) { return normalizeArgStr(arg); }

std::optional<size_t> Gemma4ToolParser::findBarePreamble(size_t from) const {
    std::optional<size_t> best;
    for (const auto& tag : parsingConfig.preambleStartTags) {
        size_t pos = streamingContent.find(tag, from);
        while (pos != std::string::npos) {
            if (isLogicalBoundary(streamingContent, pos)) {
                if (!best.has_value() || pos < *best) best = pos;
                break;
            }
            pos = streamingContent.find(tag, pos + 1);
        }
    }
    return best;
}

void Gemma4ToolParser::clearCandidate() {
    candidate = {};
}

void Gemma4ToolParser::rejectCandidateEnvelope() {
    clearCandidate();
    candidate.envelopeRejected = true;
}

bool Gemma4ToolParser::discardRejectedCandidate() {
    const size_t end = streamingContent.find(TOOL_CALL_END_TAG, streamingPosition);
    if (end != std::string::npos) {
        streamingPosition = end + TOOL_CALL_END_TAG.size();
        clearCandidate();
        currentState = State::AfterToolCall;
        return true;
    }

    // Preserve only enough suffix to recognize an end tag split across chunks.
    const size_t keep = TOOL_CALL_END_TAG.size() - 1;
    if (streamingContent.size() > keep) {
        streamingContent.erase(0, streamingContent.size() - keep);
        streamingPosition = 0;
    }
    return false;
}

void Gemma4ToolParser::commitCandidateIfReady() {
    // Public index/id/name exist only after a fully validated closed envelope.
    if (!candidate.envelopeRejected && candidate.nameValid && candidate.argsComplete && !candidate.arguments.empty()) {
        pendingEvents.push_back(ToolCallDelta{
            nextPublicIndex++,
            generateRandomId(),
            candidate.name,
            candidate.arguments});
    }
    clearCandidate();
}

bool Gemma4ToolParser::parseInContentState() {
    const size_t canonical = streamingContent.find(TOOL_CALL_START_TAG, streamingPosition);
    const auto bare = findBarePreamble(streamingPosition);
    size_t next = canonical;
    bool isBare = false;
    if (bare.has_value() && (next == std::string::npos || *bare < next)) {
        next = *bare;
        isBare = true;
    }
    if (next == std::string::npos)
        return false;
    if (next > streamingPosition) {
        std::string content = streamingContent.substr(streamingPosition, next - streamingPosition);
        streamingPosition = next;
        content = eraseSpecialMarkers(std::move(content));
        if (!content.empty())
            pendingEvents.push_back(ContentDelta{std::move(content)});
        return true;
    }
    if (!isBare)
        streamingPosition = next + TOOL_CALL_START_TAG.size();
    clearCandidate();
    currentState = State::ToolCallStarted;
    return true;
}

bool Gemma4ToolParser::parseInToolCallState() {
    const size_t endTag = streamingContent.find(TOOL_CALL_END_TAG, streamingPosition);
    const size_t brace = streamingContent.find('{', streamingPosition);
    const size_t paren = streamingContent.find('(', streamingPosition);
    size_t args = brace;
    if (paren != std::string::npos && (args == std::string::npos || paren < args))
        args = paren;
    if (endTag != std::string::npos && (args == std::string::npos || endTag < args)) {
        streamingPosition = endTag + TOOL_CALL_END_TAG.size();
        currentState = State::AfterToolCall;
        clearCandidate();
        return true;
    }
    if (args == std::string::npos)
        return false;
    const std::string name = normalizeToolName(streamingContent.substr(streamingPosition, args - streamingPosition));
    candidate.name = name;
    candidate.nameValid = saneToolName(name) && toolNameAllowed(name);
    candidate.argsComplete = false;
    candidate.arguments.clear();
    if (!candidate.nameValid) {
        SPDLOG_LOGGER_WARN(llm_calculator_logger,
            "Gemma4 parser refusing malformed or unavailable tool name: '{}'", name);
    }
    currentArgsOpen = streamingContent[args];
    currentArgsClose = currentArgsOpen == '(' ? ')' : '}';
    streamingPosition = args + 1;
    currentState = State::ToolCallParameters;
    return true;
}

bool Gemma4ToolParser::parseToolCallParametersState() {
    if (candidate.envelopeRejected)
        return discardRejectedCandidate();
    if (streamingPosition == 0)
        return false;
    const size_t openPos = streamingPosition - 1;
    size_t malformedEnd = std::string::npos;
    bool candidateLimitExceeded = false;
    auto close = findMatchingContainerEnd(
        streamingContent, openPos, currentArgsOpen, currentArgsClose, malformedEnd, candidateLimitExceeded);
    if (!close.has_value()) {
        if (malformedEnd != std::string::npos) {
            streamingPosition = malformedEnd + TOOL_CALL_END_TAG.size();
            currentState = State::AfterToolCall;
            clearCandidate();
            return true;
        }
        if (candidateLimitExceeded) {
            SPDLOG_LOGGER_WARN(llm_calculator_logger,
                "Gemma4 parser refusing tool-call candidate beyond byte/depth limits.");
            rejectCandidateEnvelope();
            return discardRejectedCandidate();
        }
        return false;
    }
    const std::string body = streamingContent.substr(streamingPosition, *close - streamingPosition);
    if (candidate.nameValid) {
        auto parsed = parseNativeArgumentsBody(body);
        if (parsed) {
            candidate.arguments = std::move(*parsed);
            candidate.argsComplete = true;
        } else {
            candidate.nameValid = false;
            candidate.arguments.clear();
            candidate.argsComplete = false;
            SPDLOG_LOGGER_WARN(llm_calculator_logger,
                "Gemma4 native argument parse failed; refusing executable tool call '{}'.", candidate.name);
        }
    }
    streamingPosition = *close + 1;
    currentState = State::ToolCallEnded;
    return true;
}

bool Gemma4ToolParser::parseInToolCallEndedState() {
    const size_t end = streamingContent.find(TOOL_CALL_END_TAG, streamingPosition);
    const size_t next = streamingContent.find(TOOL_CALL_NAME_PREFIX, streamingPosition);
    if (next != std::string::npos && (end == std::string::npos || next < end)) {
        // One native envelope may contain only one call. Extra `call:` before
        // `<tool_call|>` is garbage / implicit multicall and fail-closes the envelope.
        streamingPosition = next;
        rejectCandidateEnvelope();
        // Consume through the closing tag if present so a later canonical envelope can recover.
        if (end != std::string::npos) {
            streamingPosition = end + TOOL_CALL_END_TAG.size();
            clearCandidate();
            currentState = State::AfterToolCall;
            return true;
        }
        // Skip the unexpected preamble and keep scanning for the envelope close.
        streamingPosition = next + TOOL_CALL_NAME_PREFIX.size();
        return true;
    }
    if (end != std::string::npos) {
        streamingPosition = end + TOOL_CALL_END_TAG.size();
        commitCandidateIfReady();
        currentState = State::AfterToolCall;
        return true;
    }
    return false;
}

bool Gemma4ToolParser::parseNewContent() {
    switch (currentState) {
    case State::Content:
        return parseInContentState();
    case State::ToolCallStarted:
        return parseInToolCallState();
    case State::ToolCallParameters:
        return parseToolCallParametersState();
    case State::ToolCallEnded:
        return parseInToolCallEndedState();
    case State::AfterToolCall:
        currentState = State::Content;
        return true;
    }
    return false;
}

std::string Gemma4ToolParser::eraseSpecialMarkers(std::string content) const {
    for (const std::string& erase : {TURN_END_TAG, TOOL_RESPONSE_START_TAG}) {
        size_t pos = content.find(erase);
        while (pos != std::string::npos) {
            content.erase(pos, erase.size());
            pos = content.find(erase, pos);
        }
    }
    return content;
}

std::optional<Delta> Gemma4ToolParser::wrapDeltaContent(const std::string& content) {
    return content.empty() ? std::nullopt : std::optional<Delta>{ContentDelta{content}};
}

std::optional<Delta> Gemma4ToolParser::takePendingEvent() {
    if (pendingEvents.empty())
        return std::nullopt;
    Delta delta = std::move(pendingEvents.front());
    pendingEvents.pop_front();
    return delta;
}

std::optional<Delta> Gemma4ToolParser::parseChunk(const std::string& chunk,
    const std::vector<int64_t>& /*tokens*/, ov::genai::GenerationFinishReason finishReason) {
    if (streamingPosition >= 4096) {
        const size_t keep = currentState == State::ToolCallParameters ? 1 : 0;
        streamingContent.erase(0, streamingPosition - keep);
        streamingPosition = keep;
    }

    // Drain events produced by a prior parseChunk before accepting more bytes.
    if (auto pending = takePendingEvent())
        return pending;

    if (!chunk.empty()) {
        // OutputParser passes the current unparsed buffer (not a delta) and may
        // re-feed a remainder we already retained past streamingPosition.
        const std::string unparsed = streamingContent.substr(streamingPosition);
        if (chunk != unparsed)
            streamingContent += chunk;
    }

    // Progress until one event is ready or more bytes are required. Stop after a
    // single envelope reaches AfterToolCall so OutputParser remainder ownership
    // can re-enter for the next canonical envelope without double-parsing.
    for (int steps = 0; steps < 64; ++steps) {
        const size_t posBefore = streamingPosition;
        const State stateBefore = currentState;
        const size_t pendingBefore = pendingEvents.size();
        if (!parseNewContent())
            break;
        if (!pendingEvents.empty())
            return takePendingEvent();
        if (stateBefore != State::AfterToolCall && currentState == State::AfterToolCall)
            break;
        if (streamingPosition == posBefore && currentState == stateBefore && pendingEvents.size() == pendingBefore)
            break;
    }

    if (finishReason != ov::genai::GenerationFinishReason::NONE) {
        if (auto pending = takePendingEvent())
            return pending;
        if (currentState != State::Content && currentState != State::AfterToolCall) {
            clearCandidate();
            currentState = State::Content;
        }
        if (currentState == State::AfterToolCall)
            currentState = State::Content;
        if (currentState == State::Content && streamingPosition < streamingContent.size()) {
            // Do not flush bytes that belong to a subsequent canonical envelope;
            // OutputParser owns that remainder after the first end tag.
            const size_t nextStart = streamingContent.find(TOOL_CALL_START_TAG, streamingPosition);
            const size_t end = nextStart == std::string::npos ? streamingContent.size() : nextStart;
            if (end > streamingPosition) {
                auto content = eraseSpecialMarkers(streamingContent.substr(streamingPosition, end - streamingPosition));
                streamingPosition = end;
                return wrapDeltaContent(content);
            }
        }
    }
    return std::nullopt;
}

}  // namespace ovms
