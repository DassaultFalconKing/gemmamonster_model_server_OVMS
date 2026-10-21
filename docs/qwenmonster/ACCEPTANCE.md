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
3. Valid no-arg `{}` parser call, plus **required guided no-arg** run that must not loop forever (XGrammar #802).
4. XML `</parameter1>` and fragmented `</parameter` must never produce executable malformed argument; grammar-side root cause XGrammar #650/#651.
5. `required`/named 100/100 with simple nonempty JSON Schema on actual Qwen; no invalid fallback.
6. `auto` guided OFF and ON across short and long prompts; rate of `model chooses` vs `API extracted` separate.
7. Thinking OFF, ON; rendered prompt ends with open `<think>`; verify hard grammar doesn't force invalid second prefix.
8. One, two and repeated same-function tool calls in 1 chunk, arbitrary splits and SSE; correct id/index/content/finish.
9. Qwen3.6/Ornith distinct Jinja hashes, visible and token ID golden histories, tool-result replay.
10. Gemma4 + generic + Hermes3 unaffected.
11. STOP/LENGTH/CANCELLED backend semantics verified against streamer. `OVMSTextStreamer::end()` synthesizes STOP; direct parser LENGTH tests are insufficient.
12. 20 complete tool-result continuation loops, then 1/2/4 session agent harness workloads; GPU executor healthy.

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
