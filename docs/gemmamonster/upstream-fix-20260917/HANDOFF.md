# Gemma4 upstream evidence triage — live handoff

Status: `PLAN_REFINED / TEST_HELPER_FIX_COMMITTED / PARSER_FIX_COMMITTED / LEGACY_TEST_RECONCILIATION_IN_PROGRESS / HOST_GREEN_NOT_RUN`

## Immutable inputs

- PR code base: `d582668e6405e5d4cffbf050e9ee7303f7b94ef0`
- Evidence-only branch: `evidence/gemma4-upstream-pr-20260916`
- Evidence commit: `167e3ba44f1bc0ef6d906a999954942c6a00d1df`
- Working branch: `fix/gemma4-upstream-evidence-triage-20260917`
- Initial plan commit: `71dce5e19f86aa7d9553ab5701aa40b012f44057`
- Refined plan commit: `749c9769aeb06d07cc69822318342eb5087b9b82`
- Lossless test-helper fix: `d7e26e7d0ace229ee74066f9957e3f423cbcd238`
- Escaped-string production fix: `2dc4e54c4b07937effcb47e75c1de4058661ee2f`
- Clean split leaf to mirror only after GREEN: `62676e2e4`
- Separate whitespace repair: `fix/gemma4-whitespace-regression-1609` + GenAI `e00eada6`; do not mix.

## Evidence triage result

Raw evidence: 229 filtered cases, 213 passed, 16 failed.

| Class | Count | Decision |
|---|---:|---|
| missing `opt-125m` tokenizer | 1 | environmental; no product fix |
| unknown hard-named tool expected OK by old test | 1 | stale expectation; keep INVALID_ARGUMENT |
| huge numeric lexeme changed to double | 1 | test helper bug; repaired in `d7e26e7d` |
| non-streaming implicit multicall in one envelope | 2 | stale expectation; accepted parser intentionally rejects it |
| streaming valid single-call envelopes expecting early deltas | 6 | stale timing expectation; expect one atomic call at close |
| streaming implicit multicall in one envelope | 2 | stale expectation; reject entire envelope |
| streaming missing canonical close before STOP | 1 | stale expectation; drop incomplete candidate |
| `broken{malformed_arg}` accepted by old test | 1 | stale expectation; malformed native argument must fail closed |
| `print(\"hello world\")` remains backslash-escaped | 1 | real parser regression; repaired in `2dc4e54c` |

Note: evidence prose says 8 streaming cases, raw `ovmstest-failing-blocks.txt` contains 9. Raw failing blocks win. Further source inspection splits those nine into 6 valid atomic streams + 2 invalid multicall envelopes + 1 incomplete envelope.

## Root-cause and committed repairs

### Lossless numbers

Production `gemma4_tool_parser.cpp` already uses a SAX `NumberPreservingWriter` for native numeric scalars. The failing test routed accumulated arguments through `src/test/llm/output_parsers/output_parser_test_utils.hpp::parseWithStreamer()`, which reparsed them into `rapidjson::Document` and serialized with a normal writer. That test-only roundtrip converted the long lexeme through `double`.

Committed repair `d7e26e7d`: test helper now compacts JSON with RapidJSON Reader + `kParseNumbersAsStringsFlag` + RawNumber writer, preserving numeric lexemes.

### Escaped delimited strings

Historical `escapeAsJsonString()` decodes valid JSON escape sequences once and falls back to literal bytes on parse failure. Recursive parser commit `bed7a1e54` changed `<|\"|>...<|\"|>` handling to direct `writer.String(raw)`, so `\"` became a literal backslash plus quote in the semantic string.

Committed repair `2dc4e54c`: `NativeValueParser::parseDelimitedString()` now runs the raw delimited payload through `escapeAsJsonString()` and emits the resulting valid JSON string token with `RawValue`. GitHub diff verification confirms exactly one hunk in exactly one production file; state machine, envelope logic, streamer and generation policy are untouched.

### Atomic/fail-closed cases

Commit `909e21f07` intentionally exposes a public tool call only after one complete validated envelope. It also rejects additional `call:` forms before the same `<tool_call|>` close. Therefore:

- `HolisticStreaming`: implicit sort+dummy multicall inside one envelope => reject entire envelope.
- `StreamingWithWhitespacesBetweenToolCalls`: implicit sort+dummy+solve multicall inside one envelope => reject entire envelope.
- `StreamingWithMissingEndTagBeforeStop`: no `<tool_call|>` => incomplete candidate is cleared on STOP.
- Six remaining streaming failures are valid one-call envelopes whose legacy tests expect name/arguments too early; tests must move the semantic call expectation to canonical close, not production code back to early emission.

Request-boundary commits (`355ae00c1`, `3755dc85b`, `cf6fc0412`) intentionally reject invalid hard tool choices. Do not weaken these paths to satisfy legacy upstream tests.

## Verification state

- Evidence RED on base: `229 ran / 213 passed / 16 failed`.
- Source inspection/root-cause classification: complete for all 16 failures.
- Test-helper commit source-reviewed: yes.
- Production parser commit diff-verified: yes, exactly one hunk/one file.
- Windows/Bazel GREEN on current HEAD: **not run in this environment**.
- Do not report any repaired test as PASS until host gate executes.

## Next exact actions

1. Reconcile stale HTTP named-choice expectation.
2. Reconcile parser legacy expectations: non-stream multicall, malformed arg, six valid atomic streams, two streaming multicall rejects, one incomplete-envelope reject.
3. Run focused 229-case host gate with evidence environment.
4. Run fresh six-target / 64-case semantic gate.
5. Only after GREEN, mirror/regenerate onto split leaf `62676e2e4`.

Implementation plan: `docs/superpowers/plans/2026-09-17-gemma4-upstream-evidence-triage.md`.
