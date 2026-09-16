# Gemma4 upstream evidence triage — live handoff

Status: `TRIAGE_16_OF_16_CLASSIFIED / TEST_HELPER_FIX_COMMITTED / PARSER_FIX_COMMITTED / LEGACY_PARSER_TESTS_RECONCILED / SOURCE_DIFF_AUDITED / HTTP_STALE_EXPECTATION_PENDING / HOST_GREEN_NOT_RUN`

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
- Clean split leaf to mirror only after GREEN: `62676e2e4`
- Separate whitespace repair: `fix/gemma4-whitespace-regression-1609` + GenAI `e00eada6`; do not mix.

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

## One remaining source edit before host gate

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

## Verification state

- Evidence RED on base: `229 ran / 213 passed / 16 failed`.
- Root-cause classification: complete 16/16.
- Test-helper source repair: committed/reviewed.
- Production parser repair: committed; one-hunk/one-file diff verified.
- Parser legacy reconciliation: committed; focused source diff audited.
- HTTP stale test: pending.
- Windows/Bazel GREEN on current HEAD: **not run**.

No repaired test is to be reported as PASS until host gate executes.

## Host gate

Use the evidence environment:

```text
MSVC C:\BuildTools 14.44.35207
MSYS bash first in PATH
BAZEL_SH=C:/opt/msys64/usr/bin/bash.exe
Python 3.12.10
--output_user_root=C:/o
```

Tokenizer fixture:

```text
src\test\llm_testing\OpenVINO\gemma-4-E4B-it-int4-ov
  -> C:\llm\models\OpenVINO\gemma-4-E4B-it-int4-ov
```

Focused gate (`py_on` is required because the upstream `servable.hpp:239` py_off issue is outside this repair):

```text
bazel test --config=win_mp_on_py_on --nocache_test_results --test_output=all \
  --test_env=PYTHONPATH=<workspace>\bazel-out\x64_windows-opt\bin\src\python\binding;C:/opt/openvino/python \
  --test_filter=Gemma4OutputParserTest.*:Gemma4UpstreamRefitContractTest.*:Gemma4SpecialTokenHandoffTest.*:HttpOpenAIHandlerParsingTest.* \
  //src:ovms_test
```

Then rerun all six existing Gemma4 semantic targets on the same HEAD/dependency set:

```text
gemma4_generation_policy_test
gemma4_phantom_tool_call_test
gemma4_chunk_invariance_test
gemma4_rendered_prompt_state_test
gemma4_f7_contract_test
gemma4_f10_guard_test
```

The old `64/64` is baseline evidence only, not proof for this repaired HEAD.

## Resume point

1. apply the single pending HTTP stale-expectation edit;
2. audit final source diff vs `12f14d4` and baseline `d582668`;
3. run focused host gate;
4. run fresh six-target semantic gate;
5. if GREEN, rebuild a clean promotion series without `2489e342` / `b9f65b96`;
6. only then regenerate/mirror `upstream/gemma4-tool-calling-split` (`62676e2e4`).

Implementation plan: `docs/superpowers/plans/2026-09-17-gemma4-upstream-evidence-triage.md`.
