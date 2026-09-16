# Gemma4 upstream evidence triage — live handoff

Status: `TRIAGE_16_OF_16_CLASSIFIED / TEST_HELPER_FIX_COMMITTED / PARSER_FIX_COMMITTED / LEGACY_PARSER_TESTS_RECONCILED / SOURCE_DIFF_AUDITED / FRANKENSTEIN_MATRIX_DEFINED / HTTP_STALE_EXPECTATION_RECONCILED / HOST_GREEN_NOT_RUN`

## Immutable inputs

- PR code base: `d582668e6405e5d4cffbf050e9ee7303f7b94ef0`
- Evidence-only branch: `evidence/gemma4-upstream-pr-20260916`
- Evidence commit: `167e3ba44f1bc0ef6d906a999954942c6a00d1df`
- Working branch: `fix/gemma4-upstream-evidence-triage-20260917`
- Initial plan commit: `71dce5e19f86aa7d9553ab5701aa40b012f44057`
- Refined plan commit: `749c9769aeb06d07cc69822318342eb5087b9b82`
- Lossless test-helper fix: `d7e26e7d0ace229ee74066f9957e3f423cbcd238`
- Escaped-string production fix: `2dc4e54c4b07937effcb47e75c1de4058661ee2f`
- Parser legacy reconciliation: `dd3845f49aa9fcd11ed24da8eabc2459f9c916b4`
- Frankenstein test authority commit: `d01e951b8e55fa51d2cd9d3977795eb7b2b79df3`
- Clean split leaf to mirror only after GREEN: `62676e2e4`
- Separate whitespace repair: `fix/gemma4-whitespace-regression-1609` + GenAI `e00eada6`; do not collapse tracks before isolated gates.

Dependency heads captured for the matrix:

- OVMS upstream `main`: `204d3bf3ba6f8e2aeb489c5eeb7ab46c79fde482`.
- GenAI old base: `fe818c0467feb17b87c5adfb3f7e28dd70b76e99`.
- GenAI upstream `master`: `438e06189a07fe464fe39c544ac7997b73ca973d`.
- XGrammar bounded-whitespace pin: `9aa840b6d16abf094f3e8e2ac9c10465b77656c9`.
- XGrammar upstream `main`: `f6043f4daafd0d018f77c3ec07bcfcd70b7e0532`.

## Evidence triage result

Raw evidence: 229 filtered cases, 213 passed, 16 failed.

| Class | Count | Decision |
|---|---:|---|
| missing `opt-125m` tokenizer | 1 | environmental; no product fix |
| unknown hard-named tool expected OK by old test | 1 | stale expectation; keep `INVALID_ARGUMENT` |
| huge numeric lexeme changed to double | 1 | test helper bug; repaired in `d7e26e7d` |
| non-streaming implicit multicall in one envelope | 2 | stale expectation; accepted parser intentionally rejects it |
| streaming valid single-call envelopes expecting early deltas | 6 | stale timing expectation; expect one atomic call at close |
| streaming implicit multicall in one envelope | 2 | stale expectation; reject entire envelope |
| streaming missing canonical close before STOP | 1 | stale expectation; drop incomplete candidate |
| `broken{malformed_arg}` accepted by old test | 1 | stale expectation; malformed native argument must fail closed |
| `print(\"hello world\")` remains backslash-escaped | 1 | real parser regression; repaired in `2dc4e54c` |

Evidence prose says 8 streaming cases, raw `ovmstest-failing-blocks.txt` contains 9. Raw failing blocks win: 6 valid atomic streams + 2 invalid multicall envelopes + 1 incomplete envelope.

## Root causes and committed repairs

### 1. Lossless numbers — test harness, not product

Production `gemma4_tool_parser.cpp` already uses SAX `NumberPreservingWriter`. The failing test routed accumulated arguments through `output_parser_test_utils.hpp::parseWithStreamer()`, reparsed them into `rapidjson::Document`, then serialized through a normal writer, converting the long numeric lexeme through `double`.

`d7e26e7d` repairs only the helper with RapidJSON Reader + `kParseNumbersAsStringsFlag` + RawNumber writer.

### 2. Escaped Gemma-native delimited strings — real product regression

Recursive parser commit `bed7a1e54` changed `<|\"|>...<|\"|>` handling to direct `writer.String(raw)`, changing established native escape semantics.

`2dc4e54c` changes only `NativeValueParser::parseDelimitedString()`: run the raw marker-delimited payload through existing `escapeAsJsonString()` and emit the resulting JSON string token with `RawValue`. No FSM, envelope, streamer, registry, generation, or recovery policy change.

### 3. Atomic/fail-closed cases — stale upstream expectations

`909e21f0770d3feff76b39cc3448ac5f6660cc5b` is authority:

- id/name/index stay private until name + args + canonical close validate;
- incomplete STOP/LENGTH candidates never become executable calls;
- one native envelope contains at most one `call:`;
- malformed/implicit multicall fails closed.

Therefore the parser test reconciliation in `dd3845f` moves valid-stream expectations to one complete atomic delta at `<tool_call|>`, expects implicit one-envelope multicall to yield no tool call, and expects missing-close/malformed-arg candidates to remain non-executable.

Canonical parallel calling through multiple independently closed native envelopes remains valid and must stay GREEN.

## Audit note

A first broad legacy-test edit `2489e342e1a8634bafa9cac2e955fb3e846f9efa` was rejected during diff audit because it touched too much of the file. `b9f65b96bb53e611a5bd4160a7739887584ccc90` restores that test file byte-for-byte to the pre-edit tree. The retained reconciliation `dd3845f` was then audited as one-file `42+ / 58-` focused delta.

Do not promote the `2489e342` / `b9f65b96` audit pair into the final clean PR series. Rebuild/squash the retained delta after host GREEN.

## Three-axis Frankenstein validation

Authority:

`docs/gemmamonster/upstream-fix-20260917/FRANKENSTEIN-TEST-MATRIX.md`

The matrix deliberately separates three moving axes:

1. OVMS Gemma4 parser/policy source;
2. OpenVINO GenAI structured-output / Continuous-Batching base;
3. XGrammar JSON-schema converter/runtime.

Candidate sequence:

- `C0 BASE-CONTROL`: `d582668` + GenAI `fe818c04` + XGrammar `v0.1.31`.
- `C1 PARSER-ONLY`: repaired OVMS + unchanged GenAI/XGrammar.
- `C2 WHITESPACE-OLDBASE`: baseline OVMS + whitespace call-site + GenAI `e00eada6` + XGrammar `9aa840b6`.
- `C3 FRANKENSTEIN-OLD`: parser repair + whitespace repair on old GenAI/XGrammar.
- `C4 FRANKENSTEIN-NEWGENAI`: same OVMS, GenAI whitespace series replayed on `438e061`, XGrammar still `9aa840b6`.
- `C5 FRANKENSTEIN-NEWXGRAMMAR`: same OVMS + same GenAI code, only XGrammar `9aa840b6 -> f6043f4`.
- `C6 SUPER-UPSTREAM`: freshly re-resolved OVMS + GenAI + XGrammar upstream heads, clean reviewer-ready histories.

Important attribution boundaries:

- C3 GREEN + C4 RED => GenAI upstream delta/interaction is primary suspect.
- C4 GREEN + C5 RED => XGrammar upstream delta/interaction is primary suspect.
- C5 GREEN => fresh XGrammar is eligible for `SUPER-UPSTREAM`.

At matrix creation XGrammar `main` is 7 commits ahead of `9aa840b6`. Current upstream still exposes `max_whitespace_cnt`; nevertheless source compatibility is not acceptance. The exact Gemma4 long-context streaming gate remains required.

## One remaining source edit before C1 host gate

`HttpOpenAIHandlerParsingTest.ParseRequestWithTools_Provided3_ChoiceNotInProvidedList` is stale. `3755dc85b` intentionally requires hard named tool choice to resolve to a usable declared tool; `cf6fc0412` reinforces fail-hard validation.

Required edit in `src/test/http_openai_handler_test.cpp`:

```cpp
TEST_F(HttpOpenAIHandlerParsingTest, ParseRequestWithTools_Provided3_ChoiceNotInProvidedList) {
    std::vector<std::string> providedTools{"get_weather1", "get_weather2", "get_weather3"};
    std::string toolsChoice = R"({"type": "function", "function": {"name": "get_weather4"}})";
    assertRequestWithTools(providedTools, toolsChoice, absl::StatusCode::kInvalidArgument);
}
```

Do not weaken production request validation to satisfy the old `OK` expectation.

Stage record 2026-09-17: edit applied as `d554273a5` (`test(gemma4): stale hard-named
tool expectation now requires INVALID_ARGUMENT`, `src/test/http_openai_handler_test.cpp`
2+/2-, comment updated). Note: branch snippet with `vector<string> providedTools` does
not match the `assertRequestWithTools(string, string, StatusCode)` helper signature;
applied the minimal compilable form (same raw-JSON tools, `kInvalidArgument` status).
C1 host gate (focused 229 + semantic 64) still NOT_RUN on this HEAD.

## Verification state

- Evidence RED on base: `229 ran / 213 passed / 16 failed`.
- Root-cause classification: complete 16/16.
- Test-helper source repair: committed/reviewed.
- Production parser repair: committed; one-hunk/one-file diff verified.
- Parser legacy reconciliation: committed; focused source diff audited.
- Three-axis Frankenstein matrix: committed.
- HTTP stale test: pending.
- Windows/Bazel GREEN on current repaired HEAD: **not run**.

No repaired test or Frankenstein candidate is to be reported as PASS until its host gate executes.

## C1 host gate

Use the evidence environment:

```text
MSVC C:\BuildTools 14.44.35207
MSYS bash first in PATH
BAZEL_SH=C:/opt/msys64/usr/bin/bash.exe
Python 3.12.10
--output_user_root=C:/o
```

Required fixtures:

```text
src\test\llm_testing\OpenVINO\gemma-4-E4B-it-int4-ov
  -> C:\llm\models\OpenVINO\gemma-4-E4B-it-int4-ov
src\test\llm_testing\facebook\opt-125m
  -> valid local opt-125m tokenizer/model fixture
```

Focused gate:

```text
bazel test --config=win_mp_on_py_on --nocache_test_results --test_output=all \
  --test_env=PYTHONPATH=<workspace>\bazel-out\x64_windows-opt\bin\src\python\binding;C:/opt/openvino/python \
  --test_filter=Gemma4OutputParserTest.*:Gemma4UpstreamRefitContractTest.*:Gemma4SpecialTokenHandoffTest.*:HttpOpenAIHandlerParsingTest.* \
  //src:ovms_test
```

Then rerun all six existing Gemma4 semantic targets on the same HEAD/dependency set.

The old `64/64` is baseline evidence only, not proof for this repaired HEAD.

## Resume point

1. apply the single pending HTTP stale-expectation edit;
2. audit final C1 source diff vs `d582668`;
3. run C1 focused 229-case host gate with both fixtures;
4. run fresh C1 64-case semantic gate;
5. finish/record C2 currently-running old-base whitespace build and live gate;
6. construct C3 only after C1 and C2 satisfy their own required gates;
7. promote sequentially through C4 (fresh GenAI), C5 (fresh XGrammar), then C6 `SUPER-UPSTREAM`;
8. only after C6 GREEN regenerate reviewer-facing split/upstream PR history.

Implementation plan: `docs/superpowers/plans/2026-09-17-gemma4-upstream-evidence-triage.md`.
Test authority: `docs/gemmamonster/upstream-fix-20260917/FRANKENSTEIN-TEST-MATRIX.md`.
