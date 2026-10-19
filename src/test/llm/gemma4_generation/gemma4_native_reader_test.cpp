#include "src/llm/io_processing/gemma4/gemma4_tool_parser.hpp"
#include <gtest/gtest.h>
#include <cassert>
#include <iostream>

// Explicit-instantiation access for a pure private production function; no
// parser/tokenizer construction, substitute implementation, or runtime DLL.
template <class Tag, typename Tag::type Function>
struct FunctionAccess { friend typename Tag::type get(Tag) { return Function; } };
struct BodyTag {
    using type = std::optional<std::string> (*)(const std::string&);
    friend type get(BodyTag);
};
template struct FunctionAccess<BodyTag, &ovms::Gemma4ToolParser::parseNativeArgumentsBody>;
struct ContainerTag {
    using type = std::optional<size_t> (*)(const std::string&, size_t, char, char, size_t&, bool&);
    friend type get(ContainerTag);
};
template struct FunctionAccess<ContainerTag, &ovms::Gemma4ToolParser::findMatchingContainerEnd>;

TEST(Gemma4NativeReader, ExactAndBoundedArguments) {
    const auto parse = get(BodyTag{});
    const std::vector<std::pair<std::string, std::string>> valid{
        {"", "{}"}, {"x:1", "{\"x\":1}"},
        {"x:9007199254740993", "{\"x\":9007199254740993}"},
        {"x:1e-100", "{\"x\":1e-100}"},
        {"x:null", "{\"x\":null}"}, {"x:true", "{\"x\":true}"},
        {"x:[]", "{\"x\":[]}"}, {"x:{}", "{\"x\":{}}"},
        {"x:[1,{a:false},null]", "{\"x\":[1,{\"a\":false},null]}"},
        {"x:<|\"|><|\"|>", "{\"x\":\"\"}"},
        {"x:<|\"|>a}b<|\"|>", "{\"x\":\"a}b\"}"},
    };
    int assertions = 0;
    for (const auto& [input, expected] : valid) {
        const auto result = parse(input);
        ASSERT_TRUE(result && *result == expected);
        ++assertions;
    }
    for (const auto& input : {"x:12foo", "x:[1,,2]", "x:[1,2", "x:", "x:1,", "x:{a:1", "x:<|\"|>unterminated"}) {
        ASSERT_TRUE(!parse(input));
        ++assertions;
    }
    const auto scan = get(ContainerTag{});
    for (const auto& text : {std::string("{x:[1,{a:2}]}"), std::string("{x:<|\"|>a}b<|\"|>}"), std::string("{}")}) {
        size_t malformed; bool limit;
        const auto end = scan(text, 0, '{', '}', malformed, limit);
        ASSERT_TRUE(end && *end == text.size() - 1 && !limit);
        ++assertions;
    }
    for (const auto& text : {std::string("{x:[1,2}<tool_call|>"), std::string("{x:<|\"|>unterminated}<tool_call|><|tool_call>call:next{}")}) {
        size_t malformed; bool limit;
        ASSERT_TRUE(!scan(text, 0, '{', '}', malformed, limit) && malformed != std::string::npos);
        ++assertions;
    }
    for (const auto& text : {"{x:" + std::string(70, '[') + "0" + std::string(70, ']') + "}",
             "{x:" + std::string(70 * 1024, '1') + "}",
             "{x:<|\"|>" + std::string(70 * 1024, 'a'),
             "{x:<|\"|>" + std::string(70 * 1024, 'a') + "}<tool_call|>"}) {
        size_t malformed; bool limit;
        ASSERT_TRUE(!scan(text, 0, '{', '}', malformed, limit) && limit);
        ++assertions;
    }
    std::cout << "PASS " << assertions << " native parser assertions; pure functions only\n";
}
