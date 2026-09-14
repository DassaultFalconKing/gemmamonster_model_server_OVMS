#include <openvino/genai/generation_config.hpp>
#include <xgrammar/xgrammar.h>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <variant>

using Structured = ov::genai::StructuredOutputConfig;

template <typename T>
auto setBound(T& schema, int) -> decltype(schema.max_whitespace_cnt = 2, void()) {
    schema.max_whitespace_cnt = 2;
}
template <typename T>
void setBound(T&, long) {} // Compile the baseline and observe grammar acceptance RED.

void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}

int main(int argc, char** argv) {
    try {
        std::vector<std::string> vocab;
        for (int i = 0; i < 128; ++i) vocab.emplace_back(1, static_cast<char>(i));
        xgrammar::GrammarCompiler compiler(xgrammar::TokenizerInfo(vocab), 1);
        for (const std::string choice : {"auto", "required", "echo"}) {
            for (bool parallel : {false, true}) {
                std::string format;
                if (argc == 2) {
                    std::ifstream input(std::string(argv[1]) + "/" + choice + (parallel ? "-parallel.json" : "-single.json"));
                    require(input.good(), "Missing real-builder grammar fixture");
                    format.assign(std::istreambuf_iterator<char>(input), {});
                } else {
                    Structured::JSONSchema schema(R"({"type":"object","properties":{"text":{"type":"string"}},"required":["text"],"additionalProperties":false})");
                    setBound(schema, 0);
                    Structured::Tag tag{"<|tool_call>call:echo", schema, "<tool_call|>"};
                    if (choice == "auto") {
                        auto tags = std::make_shared<Structured::TriggeredTags>();
                        tags->triggers = {"<|tool_call>"}; tags->tags = {tag};
                        tags->stop_after_first = !parallel;
                        format = tags->to_json();
                    } else {
                        auto tags = std::make_shared<Structured::TagsWithSeparator>();
                        tags->tags = {tag}; tags->separator = "";
                        tags->at_least_one = true; tags->stop_after_first = !parallel;
                        format = tags->to_json();
                    }
                }
                auto parsed = xgrammar::Grammar::FromStructuralTag("{\"type\":\"structural_tag\",\"format\":" + format + "}");
                require(std::holds_alternative<xgrammar::Grammar>(parsed), "Structural grammar rejected");
                const auto compiled = compiler.CompileGrammar(std::get<xgrammar::Grammar>(parsed));
                const auto accepts = [&](const std::string& text) {
                    xgrammar::GrammarMatcher matcher(compiled, std::nullopt, true);
                    return matcher.AcceptString(text);
                };
                const std::string begin = "<|tool_call>call:echo{";
                const std::string end = "}<tool_call|>";
                const std::string canonical = begin + "\"text\":\"A\"" + end;
                require(accepts(canonical), choice + ": canonical call rejected");
                require(accepts(begin + "\n\t\"text\"  :\r\n\"A    B\"\t " + end), choice + ": legal whitespace rejected");
                for (const std::string gap : {"   ", "\n\n\n", "\t\n\t"}) {
                    require(!accepts(begin + gap + "\"text\":\"A\"" + end), choice + ": runaway whitespace ACCEPTED");
                    require(!accepts(begin + "\"text\"" + gap + ":\"A\"" + end), choice + ": whitespace before colon ACCEPTED");
                    require(!accepts(begin + "\"text\":" + gap + "\"A\"" + end), choice + ": whitespace after colon ACCEPTED");
                    require(!accepts(begin + "\"text\":\"A\"" + gap + end), choice + ": whitespace before close ACCEPTED");
                }
                require(accepts(canonical + canonical) == parallel, choice + ": parallel multiplicity changed");
                std::cout << "PASS " << choice << (parallel ? " parallel" : " single") << '\n';
            }
        }
        Structured::JSONSchema unbounded(R"({"type":"object"})");
        require(unbounded.to_json().find("max_whitespace_cnt") == std::string::npos, "Default GenAI JSONSchema changed");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}
