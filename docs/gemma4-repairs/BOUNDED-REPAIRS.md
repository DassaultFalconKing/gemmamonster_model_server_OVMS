# Gemma4 bounded parser repairs

Date: 2026-10-21. Status: BUILD/UNIT PASS on repair HEAD `6378400a6`; ACCEPTED: NO.

## Scope and integration

Base/revert point: `e0772d161a81ed3420082af2bf68ab46d342e904`
(QWM-01, already includes the Qwenmonster parser work). Base tree:
`6126bf28479abea9119ea0e39764486bc57e02e0`.
Branch: `repair/gemma4-bounded-20261021`.
The user approved the bounded design: content visibility, contextual reasoning
routing, and raw-string semantic goldens. Preserve dependency source lock,
generation policy, Qwen parser/schema and active build checkout/cache. No upstream
merge, runtime promotion or fresh model inference is part of this repair.

Keep evidence/checkpoints here, rather than editing the concurrently maintained
`docs/qwenmonster/STATE.md`. Integrate atomic commits after the destination build
completes. Recheck destination HEAD and overlapping paths before integration;
a clean merge at preparation time cannot guarantee a future conflict-free merge.

## 1. No-tools content visibility

- **Cause:** Gemma paired parsers force special-token decoding in UNKNOWN/CONTENT
  even when tools are unavailable and the user requests skipping those tokens.
  The existing no-tools streamer test receives native tool and string markers.
- **Files:** `src/llm/io_processing/output_parser.{hpp,cpp}`,
  `src/llm/ovms_text_streamer.cpp`,
  `src/llm/io_processing/default_content_parser.cpp`, and their Gemma/default
  content parser tests.
- **Implementation:** keep internal decode mode unchanged. The streamer supplies
  the caller's visibility preference separately. Before content publication,
  hide native tool/string markers only when tools are unavailable and visibility
  is disabled; hold original buffered bytes if a marker is split. Keep
  reasoning-phase decoding and token-ID opener detection intact.
  Remember terminal status for content remainder draining without replaying finish
  notifications to tool/reasoning parsers. DefaultContentParser must not hold a
  terminal partial marker; retain its existing complete-over-incomplete policy.
- **Expected effect:** no-tools content follows the caller's token visibility;
  reasoning still routes privately, and no tool delta is executable. Explicit
  visibility and direct decoded-text parser calls keep their existing behavior.
- **Test:** existing no-tools RED, paired skip/keep streamer results, implicit and
  explicit reasoning without tools, every marker split, STOP/LENGTH fragments
  after a closed reasoning segment, reset, tool-enabled and generic/Qwen controls.
- **Provenance:** INDEPENDENT DESIGN using the existing content publication and
  buffered phase boundaries. No dependency changes. A narrower decode-mode-only
  experiment passed the original RED but failed explicit/implicit reasoning
  controls: a reasoning flush can already contain the next tool opener. It was
  replaced, not combined with a global decoding workaround.
  Review found a new partial-marker hold could retain terminal content forever
  when the finish notification had already been consumed by reasoning. Separately,
  DefaultContentParser's terminal overlap hold is inherited. Both receive named
  RED/GREEN controls so the new visibility layer does not lose final bytes.

## 2. Contextual reasoning preamble

- **Cause:** `lookupTag("thought\n")` treats a suffix `t` anywhere in content as
  an incomplete preamble. This holds ordinary content after a reasoning close.
  Separately, the duplicated-end fixture expects text after a closed channel to
  re-enter reasoning without an opener, which is not a streaming-safe contract.
- **Files:** `src/llm/io_processing/output_parser.{hpp,cpp}` and
  `src/test/llm/output_parsers/gemma4_output_parser_test.cpp`.
- **Implementation:** constrain the bare Gemma preamble to the initial channel
  header at the start of its buffer; a completed reasoning close disables bare
  preamble re-entry. Preserve complete explicit opener detection and the shared
  `stringsOverlap()` behavior. Reset restores initial header eligibility.
  Apply the existing partial-closer hold before the first reasoning-body flush,
  as well as when the router is already in REASONING.
- **Expected effect:** `content` emits promptly as content, while a true initial
  `t` + `hought\n` remains valid reasoning. First closer ends reasoning; repeated
  closers are structural noise and do not retroactively reclassify content.
  In the malformed example, `OopsFinal content` is content exactly once.
- **Test:** exact delta timing for ordinary `content`, full/split `thought\n`,
  post-reasoning preamble-like text, duplicated closer partitions and reset.
  Correct the duplicated-end fixture explicitly, retaining its input and adding
  a streaming-safe channel expectation; do not silently hide a failed test.
- **Provenance:** INDEPENDENT DESIGN. Google documents an opener/header followed
  by a closer; behavior for a duplicated closer is our explicit recovery policy,
  not a claimed upstream Gemma requirement.

## 3. Native string semantics

- **Cause:** one fixture expects `\"` in native-delimited input to lose its
  backslash; the passing source-code fixture expects those same bytes preserved.
  Both production conversion paths currently preserve native bytes and JSON
  escape them once. These expectations cannot both describe one raw contract.
- **Files:** `src/test/llm/output_parsers/gemma4_output_parser_test.cpp`, this note;
  production `escapeAsJsonString()` and native parsing remain unchanged.
- **Implementation:** semantic goldens parse emitted JSON and compare its string
  value to hand-authored literal payloads. Cover native literal quotes,
  backslash-quote, backslashes, literal `\n` versus a newline, nested containers,
  and ordinary JSON-string escaping. Native delimiter itself remains reserved;
  do not invent an escape for embedding it. After the new semantic goldens passed
  on the prior parser, retain the conflicting fixture's exact input and correct
  its expected JSON and decoded value to preserve the native backslash. This is
  a fixture-contract correction, not a production string-parser repair.
- **Expected effect:** no executable code or path corruption from a global
  unescape. Distinguish JSON representation from the decoded argument value.
- **Test:** native raw and JSON-escaped inputs, legacy/registry paths where
  applicable, tokenizer/streamer output and chunk partitions. A passing
  characterization is not evidence of a production parser repair.
- **Provenance:** [Google Gemma4 prompt format](https://ai.google.dev/gemma/docs/core/prompt-formatting-gemma4)
  describes native-delimited characters as literal text;
  [official function extraction example](https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4)
  does not unescape native backslashes. Preserving backslashes is an interpretation
  consistent with these examples and the existing passing code/path fixtures.

## Evidence and next gates

Historical source diagnosis: three failures in 70 cases, not an established new
Qwen regression. C6 binary comparison has not been run.

Fresh existing-binary replay: 4 selected cases, 3 failures, 1 pass (the source-code
special-character control). Binary SHA256:
`b008b97aaa13a6133e39be8fde41e3a64480faa3e4701618d11b4957b9fca568`.
This is a replay of the prior parser executable, not a build of this worktree.
The initial replay completed and wrote XML, then its shell failed during hash
reporting; the subsequent read verified fresh XML and binary hash separately.

Measured BUILD/UNIT on this worktree (isolated output root `C:/gb/g4b`, jobs=2):

| Suite | Result |
|---|---|
| `gemma4_output_parser_test` | **79/79 PASS** |
| `output_parser_core_test` | **29/29 PASS** |
| `qwenmonster_output_parser_test` | **69/69 PASS** |
| `qwenmonster_generation_policy_test` | **9/9 PASS** |

Three legacy Gemma failure names are now PASS after explicit expectation/contract
fixes (duplicated-end channel, no-tools visibility, native-string fixture):

- `ParseReasoningWithDuplicatedEndTagDoesNotEmitInterveningTextTwice`
- `ParseToolCallOutputWithNoToolsInTheRequest`
- `ParseToolCallWithStringArgumentsContainingEscapedQuotes`

Executable SHA256 (`gemma4_output_parser_test.exe`):
`80625f3047fae6746aa7eb338438f665fcbeddf48479a771ce3c846655b63691`.
Staged runtime/tokenizer hashes match the C6 cohort used for HTTP gates
(`openvino`/`genai`/`tokenizers` as in private hub
`C:/gm/qwenmonster/gemma4-bounded-20261021/results/unit-controls.json`).
Fresh per-suite GTest XML retained in that hub. API/LIVE/AGENTIC and C6 binary
comparison: still NOT RUN.
