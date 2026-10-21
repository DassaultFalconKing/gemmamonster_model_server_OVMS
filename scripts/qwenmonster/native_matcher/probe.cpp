#include <fstream>
#include <iostream>
#include <memory>
#include <variant>
#include <vector>
#include <openvino/genai/generation_config.hpp>
#include <xgrammar/xgrammar.h>
#ifdef _WIN32
#include <windows.h>
#endif

using S = ov::genai::StructuredOutputConfig;

int main() {
#ifdef _WIN32
    for (const auto* name : {"openvino_genai.dll", "openvino.dll", "openvino_tokenizers.dll"}) {
        char path[32768];
        const auto module = GetModuleHandleA(name);
        if (module && GetModuleFileNameA(module, path, sizeof(path)))
            std::cout << "LOADED_MODULE " << name << " " << path << '\n';
        else
            std::cout << "NOT_LOADED " << name << '\n';
    }
#endif
    std::vector<std::string> vocab;
    for (int c = 0; c < 128; ++c) vocab.emplace_back(1, static_cast<char>(c));
    xgrammar::GrammarCompiler compiler(xgrammar::TokenizerInfo(vocab), 1, false);
    const std::string required = R"({"type":"object","properties":{"city":{"type":"string"}},"required":["city"]})";
    const std::string empty = R"({"type":"object","properties":{},"required":[]})";
    for (const bool zero : {false, true}) {
        S::Tag tag("<tool_call>\n<function=weather>\n", S::QwenXMLParametersFormat(zero ? empty : required), "</function>\n</tool_call>");
        for (const bool lazy : {false, true}) {
            std::string format = lazy ? S::TriggeredTags({"<tool_call>"}, {tag}, false, true).to_json()
                                      : S::TagsWithSeparator({tag}, "\n", true, true).to_json();
            std::cout << "MODE zero=" << zero << " lazy=" << lazy << '\n' << format << '\n';
            const auto parsed = xgrammar::Grammar::FromStructuralTag("{\"type\":\"structural_tag\",\"format\":" + format + "}");
            if (!std::holds_alternative<xgrammar::Grammar>(parsed)) {
                std::visit([](const auto& e) { std::cout << "COMPILE_ERROR " << e.what() << '\n'; }, std::get<xgrammar::StructuralTagError>(parsed));
                continue;
            }
            const auto& grammar = std::get<xgrammar::Grammar>(parsed);
            std::cout << grammar.ToString() << '\n';
            const auto compiled = compiler.CompileGrammar(grammar);
            for (const bool drift : {false, true}) {
                if (zero && drift) continue;
                xgrammar::GrammarMatcher matcher(compiled, std::nullopt, true);
                const std::string body = zero ? "" : std::string("<parameter=city>Paris</parameter") + (drift ? "1" : "") + ">\n";
                const std::string wire = (lazy ? "Let me check.\n" : "") + tag.begin + body + tag.end;
                bool accepted = true;
                std::vector<int32_t> mask(xgrammar::GetBitmaskSize(128));
                int64_t shape = static_cast<int64_t>(mask.size());
                DLTensor tensor{};
                tensor.data = mask.data();
                tensor.device = {kDLCPU, 0};
                tensor.ndim = 1;
                tensor.dtype = xgrammar::GetBitmaskDLType();
                tensor.shape = &shape;
                for (size_t i = 0; i < wire.size(); ++i) {
                    matcher.FillNextTokenBitmask(&tensor);
                    const auto ch = static_cast<unsigned char>(wire[i]);
                    const bool allowed = (static_cast<uint32_t>(mask[ch / 32]) >> (ch % 32)) & 1;
                    std::cout << "MASK offset=" << i << " char=" << int(ch) << " allowed=" << allowed << '\n';
                    if (!matcher.AcceptToken(ch)) { accepted = false; break; }
                }
                std::cout << "RESULT drift=" << drift << " accepted=" << accepted << " completed=" << matcher.IsCompleted() << '\n';
            }
            if (zero) {
                xgrammar::GrammarMatcher matcher(compiled, std::nullopt, true);
                bool accepted = matcher.AcceptString(tag.begin);
                int spaces = 0;
                while (accepted && spaces < 1024 && matcher.AcceptString(" ")) ++spaces;
                std::cout << "ZERO_SPACES " << spaces << " CLOSABLE " << matcher.AcceptString(tag.end) << '\n';
            }
        }
    }
}
