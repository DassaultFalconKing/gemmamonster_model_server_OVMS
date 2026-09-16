# Gemma4 upstream evidence triage — live handoff

Status: `PLAN_COMMITTED / IMPLEMENTATION_NOT_YET_COMMITTED / HOST_GREEN_NOT_RUN`

## Immutable inputs

- PR code base: `d582668e6405e5d4cffbf050e9ee7303f7b94ef0`
- Evidence-only branch: `evidence/gemma4-upstream-pr-20260916`
- Evidence commit: `167e3ba44f1bc0ef6d906a999954942c6a00d1df`
- Working branch: `fix/gemma4-upstream-evidence-triage-20260917`
- Plan commit: `71dce5e19f86aa7d9553ab5701aa40b012f44057`
- Clean split leaf to mirror only after GREEN: `62676e2e4`
- Separate whitespace repair: `fix/gemma4-whitespace-regression-1609` + GenAI `e00eada6`; do not mix.

## Evidence triage result

Raw evidence: 229 filtered cases, 213 passed, 16 failed.

| Class | Count | Decision |
|---|---:|---|
| missing `opt-125m` tokenizer | 1 | environmental; no product fix |
| unknown hard-named tool expected OK by old test | 1 | stale expectation; keep INVALID_ARGUMENT |
| huge numeric lexeme changed to double | 1 | test helper bug: `parseWithStreamer()` reparses through DOM and normal writer |
| 2/3 calls in one native envelope | 2 | stale expectation; accepted parser intentionally rejects implicit multicall envelope |
| partial streaming early tool-call deltas | 9 | stale timing expectation; accepted contract commits only a complete validated envelope |
| `broken{malformed_arg}` accepted by old test | 1 | stale expectation; malformed native argument must fail closed |
| `print(\"hello world\")` remains backslash-escaped | 1 | real parser regression in recursive refit; production fix required |

Note: evidence prose says 8 streaming cases, raw `ovmstest-failing-blocks.txt` contains 9. Raw failing blocks win.

## Root-cause notes

### Lossless numbers

Production `gemma4_tool_parser.cpp` already uses a SAX `NumberPreservingWriter` for native numeric scalars. The failing test then routes accumulated arguments through `src/test/llm/output_parsers/output_parser_test_utils.hpp::parseWithStreamer()`, which parses into `rapidjson::Document` and serializes with a normal writer. That test-only roundtrip converts the long lexeme through `double`.

Repair target: test helper only; compact via RapidJSON Reader + `kParseNumbersAsStringsFlag` + RawNumber writer.

### Escaped delimited strings

Historical `escapeAsJsonString()` tries to parse valid JSON escapes and falls back to literal bytes on parse error. Recursive parser commit `bed7a1e54` changed `<|\"|>...<|\"|>` handling to direct `writer.String(raw)`, so an input `\"` becomes a literal backslash plus quote in the semantic string. Restore the historical decode-on-valid/fallback-on-invalid behavior inside `parseDelimitedString()` without changing recursive containers.

### Atomic/fail-closed cases

Commit `909e21f07` intentionally made a public tool-call delta appear only after one complete validated envelope, and intentionally rejects multiple `call:` entries inside one envelope. Request-boundary commits (`355ae00c1`, `3755dc85b`, `cf6fc0412`) intentionally reject invalid hard tool choices. Do not weaken these paths to satisfy legacy upstream tests.

## Next exact actions

1. Commit lossless JSON compaction in test helper.
2. Commit escaped-delimited-string parser repair.
3. Reconcile stale HTTP/parser test expectations, including nine streaming timing cases.
4. Run focused 229-case host gate with the evidence environment.
5. Run fresh six-target / 64-case semantic gate.
6. Only after GREEN, mirror/regenerate onto split leaf `62676e2e4`.

Implementation plan: `docs/superpowers/plans/2026-09-17-gemma4-upstream-evidence-triage.md`.
