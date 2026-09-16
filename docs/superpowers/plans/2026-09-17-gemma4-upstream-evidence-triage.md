# Gemma4 Upstream Evidence Triage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `evidence/gemma4-upstream-pr-20260916` @ `167e3ba44f1bc0ef6d906a999954942c6a00d1df` into the smallest reviewable repair that makes the upstream test expectations agree with the accepted Gemma4 contracts without weakening fail-closed/atomic tool-call handling.

**Architecture:** Keep the accepted parser security model intact: one validated call per native envelope, no public tool-call delta before the envelope is complete, registry-aware fail-closed handling, bounded malformed recovery. Fix only the proven delimited-string escape regression in production code. Fix test infrastructure where it destroys lossless number lexemes, and reconcile legacy upstream tests that still assert pre-hardening behavior.

**Tech Stack:** C++17, GoogleTest, RapidJSON, OpenVINO GenAI tokenizer/streamer, Bazel on Windows.

**Spec:** `docs/gemmamonster/upstream-evidence-20260916/test-triage-handoff.md` on evidence commit `167e3ba44f1bc0ef6d906a999954942c6a00d1df`; accepted contract/provenance from the promotion docs around accepted RC `43bc254` and implementation commits including `909e21f07` and `bed7a1e54`.

## Global Constraints

- Base exactly `d582668e6405e5d4cffbf050e9ee7303f7b94ef0`.
- Do not merge the evidence branch into the PR branch.
- Do not mix `fix/gemma4-whitespace-regression-1609` or GenAI companion `e00eada6` into this work; whitespace is a separate grammar-level repair.
- Preserve one-call-per-envelope and atomic commit after validation.
- Preserve unknown hard-named-tool rejection.
- Preserve bounded malformed-input handling and registry-aware bare-call recovery.
- Do not claim GREEN until the Windows/Bazel gate is actually rerun on the resulting HEAD.
- The environmental `opt-125m` tokenizer failure is not a production-code target.

---

## Evidence classification

| Failure family | Count | Classification | Action |
|---|---:|---|---|
| `OutputParserInitializationDependsOnParserNames` | 1 | environmental | no code change; provide model fixture / exclude from product verdict |
| unknown named `tool_choice` | 1 | intended fail-closed | update stale HTTP test expectation to `INVALID_ARGUMENT` |
| lossless number lexeme | 1 | test-helper corruption | make `parseWithStreamer()` compact JSON losslessly; production parser already uses a number-preserving SAX writer |
| multiple `call:` entries in one `<|tool_call>...<tool_call|>` | 2 | intended rejection | update legacy tests to assert zero executable calls |
| streaming: valid single-call envelope expects early deltas | 6 | intended atomic hardening | keep semantics, move expected full call to envelope close |
| streaming: implicit multicall in one envelope | 2 | intended rejection | assert no executable calls for `HolisticStreaming` and `StreamingWithWhitespacesBetweenToolCalls` |
| streaming: missing canonical end tag | 1 | intended rejection | assert no executable call for `StreamingWithMissingEndTagBeforeStop` |
| malformed `broken{malformed_arg}` | 1 | intended rejection | update stale test to expect zero calls |
| escaped quotes inside `<|\"|>...<|\"|>` | 1 | real production regression | restore historical valid-JSON-escape decoding with fallback to literal bytes |

The handoff prose says “8” early-stream cases, but `ovmstest-failing-blocks.txt` contains **9**. The raw failing blocks are authoritative. Those nine are not homogeneous: six are valid single-call streams whose timing changed, two are now-forbidden implicit multicall envelopes, and one never closes its envelope and is intentionally dropped on STOP.

### Task 1: Make test JSON compaction number-lossless

**Files:**
- Modify: `src/test/llm/output_parsers/output_parser_test_utils.hpp`
- Existing RED: `Gemma4UpstreamRefitContractTest.PreservesValidNumberLexemesLosslessly`

**Interfaces:**
- Consumes: `ToolCall.arguments` as an already-valid JSON string.
- Produces: compact JSON with the original numeric token spelling preserved byte-for-byte.

- [x] **Step 1: Preserve the observed RED**

Evidence on `d582668e6`:

```text
actual:   {"x":1.2345678901234566e-13}
expected: {"x":123456789012345678901234567890.12345678901234567890e-42}
```

The production parser's `NumberPreservingWriter` is upstream of the failing helper; the helper currently reparses into `rapidjson::Document` and serializes through a normal writer, causing the conversion.

- [x] **Step 2: Replace DOM compaction with lossless SAX compaction**

Implemented in `d7e26e7d0ace229ee74066f9957e3f423cbcd238` with a test-only number-preserving RapidJSON SAX writer.

- [ ] **Step 3: Run focused RED→GREEN**

```powershell
bazel test //src:ovms_test --config=win_mp_on_py_on --nocache_test_results --test_output=all `
  --test_filter=Gemma4UpstreamRefitContractTest.PreservesValidNumberLexemesLosslessly
```

Expected: PASS with exact lexeme preserved.

- [x] **Step 4: Commit**

```text
d7e26e7d test(gemma4): preserve number lexemes in streamer helper
```

### Task 2: Restore escaped-string semantics in the recursive native parser

**Files:**
- Modify: `src/llm/io_processing/gemma4/gemma4_tool_parser.cpp`
- Existing RED: `Gemma4OutputParserTest.ParseToolCallWithStringArgumentsContainingEscapedQuotes`

**Interfaces:**
- Consumes: contents of Gemma native delimited strings `<|\"|>...<|\"|>`.
- Produces: JSON string values with valid JSON escapes interpreted once; invalid JSON escape sequences remain literal, matching the pre-refit helper semantics.

- [x] **Step 1: Preserve the observed RED**

```text
input semantic payload: print(\"hello world\")
actual JSON value:      print(\\\"hello world\\\")
expected JSON value:    print(\"hello world\")
```

- [x] **Step 2: Implement the minimal compatibility repair**

Committed as `2dc4e54c4b07937effcb47e75c1de4058661ee2f`. In `NativeValueParser::parseDelimitedString()`, direct `writer.String(raw...)` was replaced by the existing `escapeAsJsonString()` compatibility contract and `writer.RawValue(..., kStringType)`. Verified commit diff is exactly one hunk in one production file.

- [ ] **Step 3: Run focused GREEN plus backslash neighbors**

```powershell
bazel test //src:ovms_test --config=win_mp_on_py_on --nocache_test_results --test_output=all `
  --test_filter=Gemma4OutputParserTest.ParseToolCallWithStringArgumentsContainingEscapedQuotes:Gemma4OutputParserTest.ParseToolCallWithStringArgumentsContainingBackslashes:Gemma4OutputParserTest.ParseToolCallWithStringArgumentsContainingSpecialCharacters
```

Expected: all three PASS.

- [x] **Step 4: Commit**

```text
2dc4e54c fix(gemma4): restore escaped delimited string semantics
```

### Task 3: Reconcile stale fail-closed expectations

**Files:**
- Modify: `src/test/http_openai_handler_test.cpp`
- Modify: `src/test/llm/output_parsers/gemma4_output_parser_test.cpp`

**Interfaces:**
- Consumes: accepted contracts already implemented in request validation and `Gemma4ToolParser`.
- Produces: upstream tests that assert those contracts instead of pre-hardening permissive behavior.

- [ ] **Step 1: Unknown named tool stays rejected**

Change `HttpOpenAIHandlerParsingTest.ParseRequestWithTools_Provided3_ChoiceNotInProvidedList` to expect `absl::StatusCode::kInvalidArgument`. Do not weaken request validation.

- [ ] **Step 2: Multiple calls inside one native envelope stay rejected**

For `ParseTwoToolCallsAtOnce` and `ParseToolCallOutputWithThreeToolCalls`, assert `parsedOutput.toolCalls.empty()`. Rename to `RejectsTwoToolCallsInsideSingleEnvelope` / `RejectsThreeToolCallsInsideSingleEnvelope` if practical. Separate canonical envelopes remain the supported representation for parallel calls.

- [ ] **Step 3: Malformed argument without `:` stays rejected**

For `ParseToolCallWithArgumentMissingEquals` (`broken{malformed_arg}`), assert zero tool calls. The recursive parser must not promote malformed syntax to executable output.

- [ ] **Step 4: Reconcile six valid single-call streaming timing tests**

For these cases, no public `ToolCallDelta` should appear before `<tool_call|>`; move/aggregate the existing expected name+arguments into the full atomic delta emitted when the envelope closes. Keep content deltas exact.

```text
ParseToolCallWithArrayOfObjectsArgumentsStreaming
ParseToolCallWithMultipleUtfCharsStreaming
ParseToolCallArgumentValueWithUnclosedQuoteAndBraceMidStream
StreamingWithBiggerChunks
StreamingWithToolCallWithEmptyParams
StreamingWithToolResponseTokenAtTheEndOfGeneration
```

- [ ] **Step 5: Convert invalid streaming envelopes into rejection tests**

`HolisticStreaming` and `StreamingWithWhitespacesBetweenToolCalls` each contain multiple `call:` forms before one canonical `<tool_call|>` close. Under `909e21f07` that entire envelope is rejected. Preserve surrounding content checks, but assert no executable tool calls.

`StreamingWithMissingEndTagBeforeStop` never emits `<tool_call|>`. On STOP the current accepted parser clears the incomplete candidate. Assert no executable tool call.

- [ ] **Step 6: Run filtered 229-case gate**

Use the exact environment from the evidence handoff (`py_on`, explicit `PYTHONPATH`, E4B tokenizer junction) and rerun:

```text
Gemma4OutputParserTest.*
Gemma4UpstreamRefitContractTest.*
Gemma4SpecialTokenHandoffTest.*
HttpOpenAIHandlerParsingTest.*
```

Expected product-code/test result: all non-environmental cases GREEN. `OutputParserInitializationDependsOnParserNames` requires its `opt-125m` fixture and must not be papered over.

- [ ] **Step 7: Commit**

```text
test(gemma4): align legacy expectations with atomic fail-closed parsing
```

### Task 4: Re-run accepted semantic gates

**Files:** none unless a genuine regression is found.

- [ ] **Step 1: Run the six-target semantic suite**

```text
//src/test/llm/gemma4_generation:gemma4_generation_policy_test
//src/test/llm/gemma4_generation:gemma4_phantom_tool_call_test
//src/test/llm/gemma4_generation:gemma4_chunk_invariance_test
//src/test/llm/gemma4_generation:gemma4_rendered_prompt_state_test
//src/test/llm/gemma4_generation:gemma4_f7_contract_test
//src/test/llm/gemma4_generation:gemma4_f10_guard_test
```

Baseline evidence is 6/6 targets, 64 cases on `d582668e6`. The repaired HEAD must produce fresh evidence; do not reuse the old 64/64 receipt.

- [ ] **Step 2: Verify diff scope**

Expected product delta is one parser behavior change plus test/harness reconciliation and docs. No generation-policy, whitespace grammar, streamer, or CB scheduling changes.

### Task 5: Mirror the accepted repair into the clean PR series

**Files:** same logical changes as Tasks 1-3.

- [ ] **Step 1:** After the repaired main PR branch is GREEN, apply the exact repair commits to a branch based on `upstream/gemma4-tool-calling-split` @ `62676e2e4` (or regenerate the clean split from the repaired PR branch if that is the repository's established promotion method).

- [ ] **Step 2:** Re-run the same focused parser gate and six-target semantic gate on the split leaf.

- [ ] **Step 3:** Record both final SHAs and evidence paths in `docs/gemmamonster/upstream-fix-20260917/HANDOFF.md`.
