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

#include <openvino/genai/tokenizer.hpp>
#include <string>
#include <vector>

#include "../../../logging.hpp"
#include "gemma4_reasoning_parser.hpp"

namespace ovms {
void Gemma4ReasoningParser::skipToken(const std::vector<int64_t>& generatedTokens, size_t& pos, int64_t tokenId) {
    if (pos < generatedTokens.size() && generatedTokens[pos] == tokenId) {
        pos++;
    }
}

// Use Qwen3ReasoningParser::parseChunk: strip phase entry/end tags and emit body.
// The previous Gemma override dropped any chunk containing a marker, which made
// coalesced `<|channel>thought\nsecret<channel|>answer` lose both secret and answer.
}  // namespace ovms
