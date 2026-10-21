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
4. **Zero-args:** XGrammar #802 (open on 2026-10-21) may loop on whitespace-only XML parameters.
5. **End-marker drift:** XGrammar #650, PR #651 open/unmerged on 2026-10-21. Decoder mask must prevent malformed `</parameter1>`, not just teach parser to tolerate it.
6. **Required/named API:** validate compilation, GPU runtime and 100/100 valid simple schema attempts before claim.
7. **Unconstrained auto vs guided auto:** long (>10K token prompts, many tools) A/B against llama.cpp #26530 class. Tool-decision rate alone does not prove correctness.
8. **Hard error propagates:** malformed schema must not degrade hard tool choice into unguided.
9. **parallel=false with guided OFF:** request-level policy may still need a post-parser enforcement gate. Do not claim the builder enforces a constraint when no grammar is installed.

The draft remains intentionally isolated from the working C6.
