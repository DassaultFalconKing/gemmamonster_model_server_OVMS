// Copyright 2026 Intel Corporation. SPDX-License-Identifier: Apache-2.0
#pragma once
#include <cstddef>
#include <string_view>

namespace ovms::lfm2 {
inline constexpr std::size_t kDemotionLeadingProseLimit = 200;
namespace thought_detail {
inline bool space(char c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v';
}
inline std::string_view trim(std::string_view v) {
    while (!v.empty() && space(v.front())) v.remove_prefix(1);
    while (!v.empty() && space(v.back())) v.remove_suffix(1);
    return v;
}
inline bool key(std::string_view v) {
    return v == "explanation" || v == "plan" || v == "commands" || v == "command" || v == "steps";
}
// Inspect top-level key positions, never values or nested objects. Deliberately
// tolerate malformed *values* so broken pseudo-plans can still be recognized.
inline bool topLevelPlanKey(std::string_view object) {
    int braces = 0, brackets = 0;
    bool quoted = false, escaped = false, keyExpected = false;
    char quote = 0;
    std::size_t keyStart = 0;
    for (std::size_t i = 0; i < object.size(); ++i) {
        const char c = object[i];
        if (quoted) {
            if (escaped) escaped = false;
            else if (c == '\\') escaped = true;
            else if (c == quote) {
                quoted = false;
                if (keyExpected && braces == 1 && brackets == 0) {
                    auto j = i + 1;
                    while (j < object.size() && space(object[j])) ++j;
                    if (j < object.size() && object[j] == ':' && key(object.substr(keyStart, i - keyStart)))
                        return true;
                }
                keyExpected = false;
            }
            continue;
        }
        if ((c == '"' || c == '\'') && braces > 0) {
            quoted = true;
            quote = c;
            keyStart = i + 1;
            continue;
        }
        if (c == '{') {
            ++braces;
            if (braces == 1) keyExpected = true;
        } else if (c == '}') {
            if (braces == 0) return false;
            --braces;
            keyExpected = false;
        } else if (c == '[') {
            ++brackets;
            keyExpected = false;
        } else if (c == ']') {
            if (brackets > 0) --brackets;
        } else if (c == ',' && braces == 1 && brackets == 0) {
            keyExpected = true;
        } else if (!space(c) && braces == 1 && brackets == 0 && keyExpected) {
            keyExpected = false;
        }
    }
    return false;
}
inline bool pseudoToolLines(std::string_view input) {
    bool found = false;
    while (!input.empty()) {
        const auto pos = input.find('\n');
        const auto line = trim(input.substr(0, pos));
        if (!line.empty()) {
            if (line.size() < 8 || line.substr(0, 6) != "[tool:") return false;
            const auto close = line.find(']', 6);
            if (close == std::string_view::npos || close == 6) return false;
            found = true;
        }
        if (pos == std::string_view::npos) break;
        input.remove_prefix(pos + 1);
    }
    return found;
}
}  // namespace thought_detail

// Experimental content classifier only: MUST NOT authorize any executable
// tool. Caller owns streaming phase boundaries and finish-time flush.
inline bool shouldDemoteSegment(std::string_view segment) {
    segment = thought_detail::trim(segment);
    if (segment.empty()) return false;
    if (thought_detail::pseudoToolLines(segment)) return true;
    const auto brace = segment.find('{');
    if (brace == std::string_view::npos || brace > kDemotionLeadingProseLimit || segment.back() != '}')
        return false;
    return thought_detail::topLevelPlanKey(segment.substr(brace));
}
}  // namespace ovms::lfm2
