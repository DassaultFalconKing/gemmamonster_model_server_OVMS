# Qwenmonster independent coding track (no GenAI/XGrammar fork dependency)

Branch: `feature/qwenmonster-parser-invariants-20261021` (isolated from original C6 and from main comparative refit).  
Status: **FOCUSED BUILD/UNIT EXECUTED; NOT RUNTIME-VERIFIED**.

Current measured checkpoint: STATE.md. Qwen69/69, policy9/9, generic29/29;
Gemma67/70, same initial failures. The lifecycle reproducer is now active and
green; no Qwen disabled tests remain. Partition corpus has 14 cases / 2340 runs.
The source-only plan below is retained as historical context and is superseded
where it describes unexecuted unit tests or the disabled lifecycle regression.

## Historical source-only entry plan

- `src/test/llm/output_parsers/qwen3coder_output_parser_test.cpp`: exhaustive two-chunk byte split reconstruction for two completed calls; index/ID correctness, delta ordering and call-local arguments; reset after LENGTH.
- A `DISABLED_QwenmonsterRejectedPrefixMustNotStealNextCall` is a **known RED reproducer**, disabled intentionally because the current implementation may emit a speculative name delta before validating the call, then reuse the old index after rejection. This must not be counted as a green test.
- `scripts/qwenmonster/compare_parser_captures.py`: dependency-free semantic comparison of JSONL captures, validates every fixture including failures, call ID uniqueness, call-local order and typed JSON.
- `docs/qwenmonster/fixtures/qwen-xml-tool-semantics.jsonl`: static native XML, tool schema and expected complete calls; 10 fixtures. These are authored test expectations, not captures from an actual engine.

## Execution

```bash
bazel test //src:qwenmonster_output_parser_test --test_output=errors
python3 scripts/qwenmonster/compare_parser_captures.py \
  --fixtures docs/qwenmonster/fixtures/qwen-xml-tool-semantics.jsonl \
  --capture path/to/normalized-ovms.jsonl \
  --engine OVMS
```

Capture input: one JSON object per line, with `id` matching fixture `id`; include completed `tool_calls` in normalized form or OpenAI `choices[0].message.tool_calls`. Every function has `name` and `arguments` (JSON object or JSON-encoded object string). Optional call `id` and `index` are checked. **The runner compares supplied captures; it does not execute or simulate vLLM, llama.cpp, a model, or OVMS.** Use a real, pinned adapter for each engine.

## Historical task ranking (current next action is in STATE.md)

1. **P0 / RED contract:** decide speculative SSE name semantics, then repair rejected-prefix identity in `queueFirstDeltaIfNeeded` / `queueFullDeltas`; make the disabled test active. Two options: (a) defer name until completed/validated XML, trading incremental name latency for fail-closed integrity; or (b) permit speculative headers, add per-envelope lifecycle and explicit cancellation semantics, which OpenAI SSE does not natively provide. In absence of an API cancellation mechanism, (a) is safest but affects legacy streaming tests, so treat as deliberate compatibility change, not a casual refactor.
2. **P0:** run and promote arbitrary-split tests; enumerate multi-chunk partitions around each `<function` / `<parameter` / `</parameter>` boundary.
3. **P1:** renderer/tool response round-trip golden tests with native pinned template, separate thinking-on and -off.
4. **P1:** complete-phase reasoning→tool streamer tests and capture traces; no unguided model claims.
5. **P1:** report accepted vs emitted vs rejected calls and tool-delegation rate, outside parser protocol.
6. **WAIT** on real GenAI/XGrammar fork pins for grammar compilation/backports #651 / #803 / #837. Do not add fake XML whitespace workarounds to C++ parser.

## Evidence labels

`SOURCE`: GitHub commit and official repo code.  
`RED-EXPECTED`: disabled reproducer, not executed.  
`STATIC`: new C++ tests and Python comparator committed.  
`BUILD/UNIT/LIVE`: **none** as of creation.  

## Public source publication unblocks a source-level gate

Canonical public cohort now available: `docs/qwenmonster/public-source-lock.json`, `PUBLIC-COHORT-INTEGRATION.md`. Verify `2decb9ec` GenAI + `c77d5e0d` XGrammar + `b5bfb148` OpenVINO + `83eb074e` Minja before targeted compile. GenAI `JSONSchema(schema,2)` and XGrammar empty `ExcludeToken()` semantics have public source references; neither proves XML #650/#802 resolved.
