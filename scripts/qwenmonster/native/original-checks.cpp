#include <algorithm>
#include <cctype>
#include <iostream>
#include <string>
#include <variant>
#include <vector>
#include <windows.h>
#include <openvino/genai/tokenizer.hpp>
#include <openvino/genai/generation_config.hpp>
#include <xgrammar/xgrammar.h>
#include "json_schema_converter.h"

int failures = 0;
void check(const std::string& label, bool result) {
    std::cout << "CHECK " << label << " " << (result ? "PASS" : "FAIL") << '\n';
    if (!result) ++failures;
}
bool accepts(const xgrammar::CompiledGrammar& compiled, const std::string& value) {
    xgrammar::GrammarMatcher matcher(compiled, std::nullopt, true);
    return matcher.AcceptString(value) && matcher.IsCompleted();
}
std::vector<int32_t> mask(xgrammar::GrammarMatcher& matcher, int vocabSize) {
    std::vector<int32_t> data(xgrammar::GetBitmaskSize(vocabSize));
    int64_t shape = data.size();
    DLTensor tensor{};
    tensor.data=data.data(); tensor.device={kDLCPU,0}; tensor.ndim=1;
    tensor.dtype=xgrammar::GetBitmaskDLType(); tensor.shape=&shape;
    matcher.FillNextTokenBitmask(&tensor);
    return data;
}
bool allows(const std::vector<int32_t>& data, int token) {
    return (static_cast<uint32_t>(data[token/32]) >> (token%32)) & 1U;
}
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    using S = ov::genai::StructuredOutputConfig;
    std::vector<std::string> ascii;
    for (int i=0;i<128;++i) ascii.emplace_back(1,static_cast<char>(i));
    xgrammar::GrammarCompiler compiler(xgrammar::TokenizerInfo(ascii),1,false);
    const std::vector<std::string> emptySchemas{
        R"({"type":"object","properties":{},"required":[]})",
        R"({"type":"object","properties":{},"required":[],"additionalProperties":false})",
        R"({"type":"object","properties":{"city":{"type":"string"}},"maxProperties":0})"};
    auto compile = [&](const std::string& schema, bool xml) {
        return compiler.CompileGrammar(xgrammar::Grammar::FromEBNF(xgrammar::JSONSchemaToEBNF(schema,true,std::nullopt,std::nullopt,true,std::nullopt,xml?xgrammar::JSONFormat::kQwenXML:xgrammar::JSONFormat::kJSON)));
    };
    for(size_t i=0;i<emptySchemas.size();++i) {
        const auto compiled=compile(emptySchemas[i],true);
        check("empty_"+std::to_string(i)+"_epsilon",accepts(compiled,""));
        for(const auto& text:std::vector<std::string>{" ","\t","\n",std::string(16,'\t')})
            check("empty_"+std::to_string(i)+"_reject_whitespace_len"+std::to_string(text.size()),!accepts(compiled,text));
    }
    for(const auto& schema:std::vector<std::string>{R"({"type":"object"})",R"({"type":"object","properties":{},"additionalProperties":true})"})
        check("open_object_keeps_parameter",accepts(compile(schema,true),"<parameter=city>Paris</parameter>"));
    check("nested_empty_keeps_braces",accepts(compile(R"({"type":"object","properties":{"config":{"type":"object","properties":{},"additionalProperties":false}},"required":["config"]})",true),"<parameter=config>{}</parameter>"));
    auto json=compile(emptySchemas[0],false);
    check("plain_json_empty",accepts(json,"{}"));
    check("plain_json_spaced_empty",accepts(json,"{ \n\t}"));
    check("plain_json_reject_epsilon",!accepts(json,""));
    const auto required = compile(R"({"type":"object","properties":{"city":{"type":"string"}},"required":["city"],"additionalProperties":false})",true);
    check("required_declared_parameter",accepts(required,"<parameter=city>Paris</parameter>"));
    check("required_declared_reject_empty",!accepts(required,""));
    // R1: required non-empty must not take the #802 epsilon shortcut. The
    // generic object path may still accept "" for undeclared required keys —
    // that inherited gap is recorded, not claimed fixed. Parser validation
    // remains fail-closed for missing required arguments.
    try {
        const auto requiredEmptyProps = compile(R"({"type":"object","properties":{},"required":["a"],"additionalProperties":false})",true);
        check("required_empty_props_compiles", true);
        std::cout << "OBSERVATION required_empty_props_accepts_empty=" << accepts(requiredEmptyProps, "")
                  << " accepts_1024_spaces=" << accepts(requiredEmptyProps, std::string(1024, ' ')) << '\n';
    } catch (const std::exception& e) {
        std::cout << "OBSERVATION required_empty_props_exception=" << e.what() << '\n';
        check("required_empty_props_compiles", false);
    }
    try {
        const auto undeclaredRequired = compile(R"({"type":"object","required":["a"]})",true);
        check("undeclared_required_compiles", true);
        std::cout << "OBSERVATION undeclared_required_accepts_empty=" << accepts(undeclaredRequired, "") << '\n';
    } catch (const std::exception& e) {
        std::cout << "OBSERVATION undeclared_required_exception=" << e.what() << '\n';
        check("undeclared_required_compiles", false);
    }

    ov::genai::Tokenizer tokenizer{std::filesystem::path(argv[1])};
    const auto& vocab=tokenizer.get_vocab_vector();
    const auto eos=static_cast<int32_t>(tokenizer.get_eos_token_id());
    std::cout << "TOKENIZER vocab=" << vocab.size() << " eos=" << eos << '\n';
    // Match the production GenAI XGrammar bridge's RAW vocabulary and metadata.
    xgrammar::TokenizerInfo info(vocab,xgrammar::VocabType::RAW,static_cast<int>(vocab.size()),std::vector<int32_t>{eos},true);
    xgrammar::GrammarCompiler actualCompiler(info,1,false);
    for(const bool lazy:{false,true}) {
        const S::Tag tag("<tool_call>\n<function=ping>\n",S::QwenXMLParametersFormat(emptySchemas[0]),"</function>\n</tool_call>");
        const auto format=lazy?S::TriggeredTags({"<tool_call>"},{tag},false,true).to_json():S::TagsWithSeparator({tag},"\n",true,true).to_json();
        const auto parsed=xgrammar::Grammar::FromStructuralTag("{\"type\":\"structural_tag\",\"format\":"+format+"}",info);
        if(!std::holds_alternative<xgrammar::Grammar>(parsed)) {check("structural_compile",false);continue;}
        const auto compiled=actualCompiler.CompileGrammar(std::get<xgrammar::Grammar>(parsed));
        xgrammar::GrammarMatcher matcher(compiled,std::nullopt,true);
        check("actual_prefix",matcher.AcceptString((lazy?"Checking.\n":"")+tag.begin));
        const auto data=mask(matcher,static_cast<int>(vocab.size()));
        int whiteCount=0, allowedWhite=0;
        for(size_t i=0;i<vocab.size();++i) {
            if(vocab[i].empty() || !std::all_of(vocab[i].begin(),vocab[i].end(),[](unsigned char c){return std::isspace(c)!=0;})) continue;
            ++whiteCount;
            if(allows(data,static_cast<int>(i))) {++allowedWhite;std::cout<<"ALLOWED_WHITE lazy="<<lazy<<" id="<<i<<" bytes="<<vocab[i].size()<<'\n';}
        }
        std::cout<<"ACTUAL_MASK lazy="<<lazy<<" whitespace_tokens="<<whiteCount<<" allowed="<<allowedWhite<<'\n';
        check("actual_no_whitespace_tokens",whiteCount>0 && allowedWhite==0);
        check("actual_immediate_close",matcher.AcceptString(tag.end) && matcher.IsCompleted());
    }
    for(const auto* name:{"openvino_genai.dll","openvino.dll","openvino_tokenizers.dll"}) {
        char path[32768]; const auto module=GetModuleHandleA(name);
        if(module && GetModuleFileNameA(module,path,sizeof(path))) std::cout<<"LOADED_MODULE "<<name<<" "<<path<<'\n';
        else std::cout<<"NOT_LOADED "<<name<<'\n';
    }
    std::cout<<"SUMMARY failures="<<failures<<'\n';
    return failures?1:0;
}
