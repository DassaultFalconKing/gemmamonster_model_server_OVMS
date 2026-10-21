# Qwenmonster generation policy design and outstanding gates

Status: **CANDIDATE, UNCOMPILED**. First version committed to `feature/qwenmonster-comparative-refit-20261021`.

## Policy implementation

Source: `src/llm/io_processing/qwen3coder/generation_config_builder.hpp`.
Factory: `src/llm/io_processing/generation_config_builder.hpp`, selector `qwen3coder`.
Bazel: `//src/llm:generation_config_builders`.
Contract tests: `//src:qwenmonster_generation_policy_test`.

### Decision matrix

| choice | constraints | guarantee / note |
| --- | --- | --- |
| none | no tools grammar | hard execution suppression belongs to API, not this builder alone |
| auto, guided OFF | unconstrained | reference candidate; model must voluntarily emit call |
| auto, guided ON | `TriggeredTags` `<tool_call>` | experimental lazy, no mandatory call |
| required | `TagsWithSeparator` `at_least_one=true` | non-lazy hard generation, verification pending |
| named | only named schema, `at_least_one=true` | nonexistent tool throws |
| parallel=false | `stop_after_first=true` | grammar-level constraint only when guided |
| parallel=true | `stop_after_first=false` | repeat calls possible, unique API IDs enforced by parser |

### Native grammar

The new builder creates `Tag(begin="<tool_call>\n<function=NAME>\n", content=QwenXMLParametersFormat(schema), end="</function>\n</tool_call>")`.

This uses native `qwen_xml_parameter` from GenAI/XGrammar, not Hermes JSON-wrapped grammar. It keeps multiple Qwen tools as alternatives and uses JSON Schema to describe parameters.

### Strict open gates

1. **Header/runtime compatibility:** the pinned OVMS GenAI headers must actually define `QwenXMLParametersFormat`. Upstream `6a35b97...` proves the API exists in current GenAI, not necessarily in our binary.
2. **Reasoning:** when a canonical Jinja ends with `<think>`, hard constraint at generation start may prevent valid reasoning or conflict with the already-open phase. Build render-suffix aware grammar or explicit fail-closed incompatibility, not silent fallback.
3. **XML serial form:** test exact schema-produced newline/closing-tag alignment with current tokenizer.
4. **Genuinely zero-parameter XML tools:** XGrammar #802 may loop on a whitespace-only XML parameter branch, even though `{}` is the *correct* semantic result for a tool declaring zero parameters. PRs #803 and #837 remain open/unmerged on 2026-10-21. This is unrelated to the historical Gemma `empty-args` anomaly when required properties were expected.
5. **End-marker drift:** XGrammar #650, PR #651 open/unmerged on 2026-10-21. Decoder mask must prevent malformed `</parameter1>` after the excluded close prefix, not just teach the parser to tolerate it. It is NOT fixed by Gemma's JSON whitespace bound.
6. **Required/named API:** validate compilation, GPU runtime and 100/100 valid simple schema attempts before claim.
7. **Unconstrained auto vs guided auto:** long (>10K token prompts, many tools) A/B against llama.cpp #26530 class. Tool-decision rate alone does not prove correctness.
8. **Hard error propagates:** malformed schema must not degrade hard tool choice into unguided.
9. **parallel=false with guided OFF:** request-level policy may still need a post-parser enforcement gate. Do not claim the builder enforces a constraint when no grammar is installed.

The draft remains intentionally isolated from the working C6.

## Three distinct historical bug classes plus one XML delimiter bug

See `WHITESPACE-DEFECT-TAXONOMY.md` for the status/evidence matrix. In particular:
- Gemma C5 JSON whitespace degeneration was **CONFIRMED FIXED** by bounded JSON grammar work. This must remain a control, not become a claimed XML grammar fix.
- Gemma C5 unexpected empty arguments for a tool **with required properties** were **NOT REPRODUCED** in 267 subsequent filled canonical calls. The verdict does not concern valid zero-argument tools.
- Qwen XML zero-parameter grammar self-loop (XGrammar #802, PR #803/#837) and `</parameter1>` drift (#650/#651) remain separate open upstream issues.

## GenAI ABI/API pinning warning

The upstream OpenVINO GenAI header at `openvinotoolkit/openvino.genai@6a35b97bbab88120930a87d81c2ecccd12fc0ba9` defines `JSONSchema(const std::string&)` (one parameter), while the Gemma C6 code calls `JSONSchema(toolSchemaWrapper.stringRepr, 2)`. This is a **local-patched interface** until the exact 2-argument GenAI header is independently pinned. The local commit `bf3255153ee73faeee9c7da277853ab6aa9298e2` was supplied as provenance but could not be resolved in public upstream GitHub. Do not replace C6's patched GenAI binary/headers with arbitrary upstream and call it compatible.

The current upstream `QwenXMLParametersFormat` accepts only a schema string and its serialized `qwen_xml_parameter` does not carry an explicit `max_whitespace_cnt` parameter. **Do not reinterpret Gemma's `JSONSchema(...,2)` as a Qwen XML grammar bound.** A future XGrammar fix or pinned downstream backport plus actual compilation/decoding tests are required.
