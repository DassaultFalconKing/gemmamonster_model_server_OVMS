# Qwenmonster M1/refit + M2 candidate acceptance

Status: **NOT RUN**. Never infer results from this checklist.

## Build/protocol gates

On matching OVMS build host with pinned 2026 GenAI headers and valid Qwen tokenizer:
```bash
bazel test //src:qwenmonster_output_parser_test \
  //src:qwenmonster_generation_policy_test \
  //src:gemma4_output_parser_test \
  //src:output_parser_core_test \
  --test_output=errors
```

After build, inspect `GenerationConfig::structured_output_config` and validate its grammar with **the exact running tokenizer and actual GenAI/XGrammar**. A constructor-only test does not prove the grammar is accepted by XGrammar.

## Blockers to reproduce explicitly

1. Unknown `<function=...>` never executable.
2. Typed-invalid scalar/array/object and missing schema required key never published as completed tool.
3. **Valid zero-parameter tool**: parser returns semantic `{}` for a schema with `properties={}` and `required=[]`; independently run **required guided generation** and prove it emits a complete XML close without indefinite whitespace (XGrammar #802; open PR #803/#837).
4. **XML string end-marker drift**: `</parameter1>` and split `</parameter` must be rejected as malformed and, separately, prevented by a verified decoder mask (XGrammar #650/#651). Parser-only RED/GREEN does not establish grammar repair.
5. **Required arguments that must not be empty**: `required=["city"]`, nonempty schema, 100/100 generated calls with an actual `city` value; do not report the separate C5 unexpected-empty-args incident as reproduced. Run `required`/named on actual Qwen with no invalid fallback.
6. `auto` guided OFF and ON across short and long prompts; rate of `model chooses` vs `API extracted` separate.
7. Thinking OFF, ON; rendered prompt ends with open `<think>`; verify hard grammar doesn't force invalid second prefix.
8. One, two and repeated same-function tool calls in 1 chunk, arbitrary splits and SSE; correct id/index/content/finish.
9. Qwen3.6/Ornith distinct Jinja hashes, visible and token ID golden histories, tool-result replay.
10. Gemma4 + generic + Hermes3 unaffected.
11. STOP/LENGTH/CANCELLED backend semantics verified against streamer. `OVMSTextStreamer::end()` synthesizes STOP; direct parser LENGTH tests are insufficient.
12. 20 complete tool-result continuation loops, then 1/2/4 session agent harness workloads; GPU executor healthy.

## Whitespace provenance and positive/negative controls

- **Gemma bounded JSON whitespace:** run/retain the existing Gemma baseline gates against its pinned local patched GenAI/XGrammar, including `JSONSchema(..., 2)`. **Do not** extrapolate these results to `qwen_xml_parameter`.
- **Gemma historical empty-args:** retain `24847c968`'s `NOT REPRODUCED` status and 267-filled evidence. These are tools requiring arguments; not equivalent to a no-parameter tool.
- **Qwen genuine zero-argument tool:** schema `{"type":"object","properties":{},"required":[]}` should generate a completed XML call with zero parameter elements, finite whitespace and normalized API JSON `{}`. Save raw token/mask trace as well as API output.
- **Qwen required-argument tool:** schema requiring `city`; no empty object or malformed argument should pass as executable.
- **Qwen XML drift:** distinguish model's raw invalid close token from grammar accidentally permitting an invalid close, and collect incremental masks around every prefix of `</parameter>`.
- **Pin check:** record actual loaded OpenVINO GenAI header/library and XGrammar fork revision. Confirm whether `JSONSchema(schema, 2)` exists and whether XGrammar #651/#803/#837 are actually present. If absent, mark grammar risks OPEN even when parser tests pass.

## Required evidence artifacts

`BUILD.txt`, `UNIT-QWEN.txt`, `UNIT-GEMMA.txt`, `GENAI-XGRAMMAR-PIN.txt`, `GRAMMAR-COMPILE.json`, `CANONICAL-TEMPLATE-HASHES.json`, `LIVE-UNARY.json`, `LIVE-SSE.jsonl`, `FINISH-REASONS.jsonl`, `AGENT-LOOPS.jsonl`, `FAILURE-TRIAGE.md`.

Until these are measured, promotion status remains NOT ACCEPTED.

## Focused code locations

- `src/llm/io_processing/qwen3coder/qwen3coder_tool_parser.cpp`
- `src/llm/io_processing/qwen3coder/generation_config_builder.hpp`
- `src/test/llm/output_parsers/qwen3coder_output_parser_test.cpp`
- `src/test/llm/qwenmonster_generation_policy_test.cpp`
- `src/llm/io_processing/output_parser.cpp`
- `src/llm/ovms_text_streamer.cpp`
