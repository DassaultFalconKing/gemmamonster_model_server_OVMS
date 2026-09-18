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

#include <string>
#include <vector>

namespace ovms {

// Configuration for a parser's phase-boundary detection and tokenizer decode mode.
//
// startTags are normal text phase openers. tokenIdStartTags are start-boundary
// strings expected to resolve to one special token and are detected proactively by
// OVMSTextStreamer. preambleStartTags are alternative entry points. Parsers that
// enable preambleStartTagsRequireBoundary ask OutputParser to accept those preambles
// only at a real response/phase/line boundary, so recovery syntax cannot be promoted
// from arbitrary prose merely because a streaming chunk happens to start there.
struct OutputParsingConfig {
    std::vector<std::string> startTags;
    std::vector<std::string> tokenIdStartTags;
    std::vector<std::string> preambleStartTags;
    std::string endTag;
    std::vector<std::string> stringsToErase;

    bool needsSpecialTokens = false;
    bool defaultDecodingWithSpecialTokens = false;
    bool preambleStartTagsRequireBoundary = false;

    // A reasoning parser may opt into treating a tool start marker as an
    // implicit reasoning end. This is format-specific and defaults to false.
    bool toolStartTerminatesReasoning = false;
};

}  // namespace ovms
