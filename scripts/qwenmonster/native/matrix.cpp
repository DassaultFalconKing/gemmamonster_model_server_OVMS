#include <iostream>
#include <iomanip>
#include <stdexcept>
#include <string>
#include <vector>
#include <xgrammar/xgrammar.h>
#include "json_schema_converter.h"

struct Row {
  const char* id;
  const char* schema;
  bool xml;
  const char* text;
  bool expected;
  bool compile_error;
  bool known_open;
  const char* expected_schema_diagnostic=nullptr;
};

int main() {
  std::vector<std::string> vocab;
  for (int i=0; i<128; ++i) vocab.emplace_back(1, static_cast<char>(i));
  xgrammar::GrammarCompiler compiler(xgrammar::TokenizerInfo(vocab),1,false);
  const std::vector<Row> rows{
    {"empty_min0_epsilon", R"({"type":"object","properties":{},"required":[],"minProperties":0,"additionalProperties":false})",true,"",true,false,false},
    {"empty_min0_space", R"({"type":"object","properties":{},"required":[],"minProperties":0,"additionalProperties":false})",true," ",false,false,false},
    {"empty_min0_tab", R"({"type":"object","properties":{},"required":[],"minProperties":0,"additionalProperties":false})",true,"\t",false,false,false},
    {"empty_min0_lf", R"({"type":"object","properties":{},"required":[],"minProperties":0,"additionalProperties":false})",true,"\n",false,false,false},
    {"closed_min1_unsatisfiable", R"({"type":"object","properties":{},"required":[],"minProperties":1,"additionalProperties":false})",true,"",false,true,false,"minProperties is greater than the number of properties, but additional properties aren't allowed: 1 > 0"},
    {"open_min1_parameter", R"({"type":"object","properties":{},"required":[],"minProperties":1,"additionalProperties":true})",true,"<parameter=city>Paris</parameter>",true,false,false},
    {"open_min1_empty", R"({"type":"object","properties":{},"required":[],"minProperties":1,"additionalProperties":true})",true,"",false,false,false},
    {"open_min1_space", R"({"type":"object","properties":{},"required":[],"minProperties":1,"additionalProperties":true})",true," ",false,false,false},
    {"declared_min1_parameter", R"({"type":"object","properties":{"city":{"type":"string"}},"required":[],"minProperties":1,"additionalProperties":false})",true,"<parameter=city>Paris</parameter>",true,false,false},
    {"declared_min1_empty", R"({"type":"object","properties":{"city":{"type":"string"}},"required":[],"minProperties":1,"additionalProperties":false})",true,"",false,false,false},
    {"required_declared_unset_max_parameter", R"({"type":"object","properties":{"city":{"type":"string"}},"required":["city"],"minProperties":0,"additionalProperties":false})",true,"<parameter=city>Paris</parameter>",true,false,false},
    {"required_declared_unset_max_empty", R"({"type":"object","properties":{"city":{"type":"string"}},"required":["city"],"minProperties":0,"additionalProperties":false})",true,"",false,false,false},
    {"explicit_max0_epsilon", R"({"type":"object","properties":{"city":{"type":"string"}},"required":[],"maxProperties":0})",true,"",true,false,false},
    {"explicit_max0_parameter", R"({"type":"object","properties":{"city":{"type":"string"}},"required":[],"maxProperties":0})",true,"<parameter=city>Paris</parameter>",false,false,false},
    {"explicit_max0_space", R"({"type":"object","properties":{"city":{"type":"string"}},"required":[],"maxProperties":0})",true," ",false,false,false},
    {"required_max0_unsatisfiable", R"({"type":"object","properties":{"city":{"type":"string"}},"required":["city"],"maxProperties":0})",true,"",false,true,false,"maxProperties is less than the number of required properties: 0 < 1"},
    {"required_empty_props_empty_OPEN", R"({"type":"object","properties":{},"required":["a"],"additionalProperties":false})",true,"",false,false,true},
    {"required_empty_props_spaces_OPEN", R"({"type":"object","properties":{},"required":["a"],"additionalProperties":false})",true,"                                                                ",false,false,true},
    {"required_undeclared_open_empty_OPEN", R"({"type":"object","required":["a"],"additionalProperties":true})",true,"",false,false,true},
    {"required_undeclared_open_parameter", R"({"type":"object","required":["a"],"additionalProperties":true})",true,"<parameter=a>x</parameter>",true,false,false},
    {"nested_empty_braces", R"({"type":"object","properties":{"config":{"type":"object","properties":{},"additionalProperties":false}},"required":["config"]})",true,"<parameter=config>{}</parameter>",true,false,false},
    {"json_empty_braces", R"({"type":"object","properties":{},"required":[],"minProperties":0,"additionalProperties":false})",false,"{}",true,false,false},
    {"json_empty_spaced_braces", R"({"type":"object","properties":{},"required":[],"minProperties":0,"additionalProperties":false})",false,"{ \n\t}",true,false,false},
    {"json_no_bare_epsilon", R"({"type":"object","properties":{},"required":[],"minProperties":0,"additionalProperties":false})",false,"",false,false,false},
    {"json_closed_min1_unsatisfiable", R"({"type":"object","properties":{},"minProperties":1,"additionalProperties":false})",false,"{}",false,true,false,"minProperties is greater than the number of properties, but additional properties aren't allowed: 1 > 0"},
    {"json_declared_min1_empty", R"({"type":"object","properties":{"city":{"type":"string"}},"minProperties":1,"additionalProperties":false})",false,"{}",false,false,false},
    {"json_declared_min1_value", R"({"type":"object","properties":{"city":{"type":"string"}},"minProperties":1,"additionalProperties":false})",false,R"({"city":"Paris"})",true,false,false},
    {"json_required_empty_props_OPEN", R"({"type":"object","properties":{},"required":["a"],"additionalProperties":false})",false,"{}",false,false,true}
  };
  int failures=0, open=0, passed=0;
  for (const auto& row:rows) {
    bool threw=false, accepted=false;
    std::string phase="schema_conversion", exception_text;
    try {
      const auto ebnf=xgrammar::JSONSchemaToEBNF(
        std::string(row.schema),true,std::nullopt,std::nullopt,true,std::nullopt,
        row.xml?xgrammar::JSONFormat::kQwenXML:xgrammar::JSONFormat::kJSON);
      phase="grammar_construction";
      const auto grammar=xgrammar::Grammar::FromEBNF(ebnf);
      phase="matcher_compilation";
      const auto compiled=compiler.CompileGrammar(grammar);
      phase="matching";
      xgrammar::GrammarMatcher matcher(compiled,std::nullopt,true);
      accepted=matcher.AcceptString(row.text) && matcher.IsCompleted();
    } catch (const std::exception& error) {
      threw=true; exception_text=error.what();
      std::cout<<"DIAGNOSTIC "<<row.id<<" phase="<<phase
        <<" exception_text="<<std::quoted(exception_text)<<'\n';
    }
    const bool expected_schema_error=threw && phase=="schema_conversion" &&
      row.expected_schema_diagnostic &&
      exception_text.find(row.expected_schema_diagnostic)!=std::string::npos;
    const bool good=row.compile_error ? expected_schema_error : (!threw && accepted==row.expected);
    const char* status=good ? (row.known_open?"UNEXPECTED_PASS_REVIEW":"PASS")
      : (row.known_open && !threw ? "EXPECTED_FAIL_OPEN" : "FAIL");
    if(row.known_open) ++open;
    if(good && !row.known_open) ++passed;
    if((!good && !row.known_open) || (row.known_open && (good || threw))) ++failures;
    std::cout<<"ROW "<<row.id<<" status="<<status<<" compile_error="<<threw
      <<" accepted="<<accepted<<" desired="<<row.expected
      <<" phase="<<phase<<" schema_specific_error="<<expected_schema_error<<'\n';
  }
  std::cout<<"SUMMARY rows="<<rows.size()<<" passed="<<passed<<" open="<<open
    <<" unexpected="<<failures<<" ACCEPTED=NO\n";
  // Exit 2 explicitly preserves open semantics even if every regression matched.
  return failures?1:(open?2:0);
}
