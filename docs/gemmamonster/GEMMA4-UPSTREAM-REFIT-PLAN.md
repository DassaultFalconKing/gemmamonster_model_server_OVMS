# Gemma4 Upstream Contribution Refit Plan

**Status:** ACTIVE / implementation in progress  
**Updated:** 2026-09-15 (local-agent session: parallel_tool_calls GREEN, tool-name validation GREEN, phantom-publication RED committed)  
**Working branch:** `staging/gemma4-upstream-refit-clean-20260915`  
**Current checkpoint before this document commit:** `fe894aad9` (local-agent session HEAD; full SHAs in §13)  
**Upstream base:** `openvinotoolkit/model_server@a5136cb285482aaef5410a053b5ecd04ff9324ec`  
**Authority dossier:** `docs/gemmamonster/COMPARATIVE-GEMMA4-PARSER-VERDICT.md`

This file is the recovery point for the post-#4103 Gemma4 upstream contribution refit. If the implementation session is interrupted, do not infer the next step from old 2026.4/2026.5 branches. Re-resolve the branch and continue from the first unchecked item below.

## 1. Non-negotiable design decisions

- Refit onto current upstream `main` after PR #4103. Do not resurrect old `PyJinjaTemplateProcessor` wiring.
- Preserve OVMS-native architecture. Borrow semantics, not foreign parser frameworks.
- Google/current Gemma model metadata is protocol/template authority.
- vLLM is primary parser FSM / streaming-boundary evidence, not the hard-generation authority.
- llama.cpp is primary native Gemma hard/lazy generation-policy evidence.
- SGLang is useful for two-phase reasoning/tool evidence and as a warning against generic JSON fallback.
- OpenVINO GenAI `StructuredOutputConfig` / structural tags are the execution mechanism.
- Every behavioral commit must carry `Provenance / Driven by / Fixes / Decision` in its commit body.
- Hard `required` and named tool choice must fail closed. `auto` may degrade only where explicitly allowed.
- Do not mix unrelated context-length, MTP, performance, session-store or deployment work into this contribution line.

## 2. Completed semantic work

### Parser / special-token refit

- [x] `8488307d` — post-#4103 parser protocol contracts.
- [x] `bed7a1e5` — recursive/lossless native argument parsing.
- [x] `e001de93` — request-registry validation and logical-boundary bare-call recovery.
- [x] `251f4b58` — RED contract for reasoning-close -> tool-open special-token handoff.
- [x] `f3410cfa` — refreshed comparative parser/generation/template dossier.
- [x] `a887757a` — production special-token phase-handoff ordering fix.
- [x] `58fe7b7` — hygiene: restored `../utils.hpp` declaration include lost from the connector-written parser rewrite; targeted parser build PASS.

Important invariant: no hard-coded Gemma token IDs. Token boundaries remain tokenizer-resolved and generic streamer logic remains model-agnostic.

### Generation policy refit

- [x] `8495f0ce` — RED: `tool_choice=required` must install native structured grammar.
- [x] `9c0b698e` — GREEN: native Gemma required grammar with at-least-one semantics and direct-tool / thought-then-tool alternatives.
- [x] `45891c27` — RED: `auto` needs lazy native activation.
- [x] `5d8327cf` — GREEN: `auto` uses `<|tool_call>` `TriggeredTags`, `at_least_one=false`.
- [x] `41efa8de` — RED: named choice must restrict generation to selected tool.
- [x] `5af1c047` — GREEN: named tool choice is hard-enforced at generation boundary and unavailable names are rejected.
- [x] `a08d7dae` — RED: active tools and `response_format` cannot silently compete for one grammar slot.
- [x] `76c792ca` — GREEN: explicit reject of `response_format + active Gemma4 tools`; `tool_choice=none` leaves response format available.
- [x] `92a30faf` — RED: hard tool policy must require successful structured-output validation and `required` without tools must fail.
- [x] `27b66eda` — partial GREEN: base/builder contract now exposes `requiresValidStructuredOutput()`, hard Gemma policy is tracked explicitly, and hard choice without available schemas is rejected before the inactive-tools early return.
- [x] `7d2ef35` — API-boundary RED: required malformed schema returned OK after GenAI validation failure; unavailable named choice escaped as `std::invalid_argument`; optional auto fallback remained OK.
- [x] `cf6fc04` — API-boundary GREEN: parsing errors return `InvalidArgument`; mandatory grammar validation cannot fall back to unguided generation.

## 3. Current exact implementation state

The hard-validation API boundary is implemented and locally verified. `parseConfigFromRequest()` input errors become `InvalidArgument` status. When GenAI validation throws, `requiresValidStructuredOutput()` makes required/named requests fail at `extractInputRequest()`; optional `auto` still logs and removes its grammar. The RED validation cause was xgrammar `json_schema_converter.cc:898: Unsupported type "invalid_schema_type"` using a real tokenizer. After GREEN, both the three-case API filter and the complete `//src/test/llm/gemma4_generation:gemma4_generation_policy_test` target passed with `OVMS_TEST_TOKENIZER_PATH=C:/llm/models/runtime/gemma4-26-heretic-google-current`.

Current `upstream/main` is `e338fb74b53dc8ac1c48707903b85e3901adcbdc`, one commit after the pinned `a5136cb...` base. No rebase was performed. The next semantic task is `parallel_tool_calls`; source-wide API/input-processing regression and live Arc/Gemma4 acceptance remain separate gates.

### Hard-validation boundary checkpoint

- [x] Add default `virtual bool requiresValidStructuredOutput() const { return false; }` on `BaseGenerationConfigBuilder`.
- [x] Track hard Gemma4 policy after request parsing: `required` or named choice => mandatory validation; `auto` => optional.
- [x] Expose the accessor through `GenerationConfigBuilder`.
- [x] Reject hard tool choice if no tool schemas are available.
- [x] Add an API-boundary RED test around structured-output validation behavior without distorting production code.
- [x] Change `OpenAIApiHandler::extractInputRequest()` validation catch:
  - `configBuilder.requiresValidStructuredOutput() == true` => return `absl::InvalidArgumentError(...)` including validation cause;
  - optional policy => log and `unsetStructuredOutputConfig()` exactly as today.
- [x] Verify status propagation: `GenAiServable::parseRequest()` returns the `StatusOr` failure, and `HttpLLMCalculator` returns that status before input preparation or execution.
- [x] Run the focused API-boundary cases and full generation-policy target: both PASS after GREEN.
- [ ] Run the existing broader API/input-processing targets after target discovery and fixture setup.
- [x] Commit the API-boundary GREEN separately with full provenance body.

Do not merely leave an invalid hard grammar installed and hope a later GenAI call fails. Fail at the request boundary where the contract violation can be explained.

## 4. Local-agent fetch and integrity gate

The local agent must verify the connector-written branch before continuing implementation.

- [x] `git fetch --all --prune` resolved `origin/staging/gemma4-upstream-refit-clean-20260915` at `d90a7e6769fa903d414d13a5617814efe07379b8`.
- [x] Confirm fetched ancestry contains `92a30faf` and later `27b66eda` before local commits.
- [x] Confirm fetched remote branch HEAD is `d90a7e6769fa903d414d13a5617814efe07379b8`, with docs checkpoints above the behavioral GREEN.
- [x] Confirm fetched tree excludes `docs/gemmamonster/.noop`.
- [x] Confirm fetched tree excludes `src/llm/io_processing/gemma4/generation_policy.hpp`.
- [x] Worktree was clean immediately after checkout/reset to remote.
- [x] Inspect exact `a5136cb...HEAD` diff; `git diff --check` passed before changes.
- [ ] Complete style/buildifier review of connector-written files. No truncation or conflict markers were found; compiler exposed the missing parser include, repaired as `58fe7b7`.
- [ ] In particular inspect:
  - `src/llm/io_processing/base_generation_config_builder.hpp`
  - `src/llm/io_processing/generation_config_builder.hpp`
  - `src/llm/apis/openai_api_handler.cpp`
  - `src/test/llm/gemma4_generation/gemma4_generation_policy_test.cpp`
  - Gemma4 parser/reasoning files changed earlier in this branch.
- [x] Connector include damage was repaired in dedicated hygiene commit `58fe7b7`, with no semantic changes.

## 5. Generation TODO after hard-validation GREEN

### `parallel_tool_calls`

Current observation: `OpenAIRequest` / builder work existed in the old line, but current `parseTools()` does not yet propagate the HTTP `parallel_tool_calls` field into generation policy.

- [x] Add HTTP/API RED contract: explicit `parallel_tool_calls=false` reaches the internal request as false; true/default semantics remain documented. (RED `18de2c26c`)
- [x] Decide and document default using current OpenAI-compatible OVMS behavior rather than guessing from the old branch. (absent/null => `true`)
- [x] Add internal request field only if not already present on the post-#4103 base. (`OpenAIRequest::parallelToolCalls{true}`)
- [x] Required/named grammar: `parallel_tool_calls=false` => max one native call. (`stop_after_first=true` on `TagsWithSeparator`)
- [x] `parallel_tool_calls=true` => native repeated calls allowed. (`stop_after_first=false`)
- [x] Auto grammar must apply the same repetition policy after trigger. (`stop_after_first` on `TriggeredTags`)
- [x] Add direct builder tests and an HTTP parsing test so laboratory-only field assignment cannot masquerade as API support. (GREEN `7be4b7aa4`; non-bool rejected with `InvalidArgument`; Responses echoes explicit value)

Source: llama.cpp native Gemma policy plus OpenAI parallel-tool semantics. Do not copy SGLang generic JSON fallback.

### Tool-name validation (adversarial follow-up, completed this session)

- [x] RED `447718b8d`: invalid tool names accepted into `<|tool_call>call:<name>` tags for required/named/auto.
- [x] GREEN `547df8030`: `buildToolTag` rejects names outside `[A-Za-z0-9_.-]` with `std::invalid_argument` (fail-closed for all policies; auto cannot degrade to unguided sampling). Predicate duplicated with TODO referencing parser `saneToolName`; no shared-helper refactor.

### Generation validation matrix

- [ ] no tools + `auto` => no tool grammar.
- [ ] no tools + `required` => request error.
- [ ] `tool_choice=none` + tools => no tool grammar; response format remains usable.
- [ ] named tool absent from registry => request error.
- [ ] empty / malformed tool schema in hard mode => request error, never unguided fallback.
- [ ] empty / malformed schema in auto => determine whether request reject or guided fallback from actual GenAI validation behavior; document observation before choosing.
- [ ] direct `required` and thought-then-tool forms remain valid.

## 6. Post-#4103 template adaptation TODO

Target architecture: #4103 prepares runtime Jinja separately from tokenizer/Minja, but both render paths converge on final `req.promptText`. Reconciliation must happen after that convergence.

- [ ] Re-read current `ChatTemplateProcessor` before patching; do not transplant old constructor/wiring.
- [ ] Add RED contract for rendered prompt ending inside open Gemma thought channel after a tool response.
- [ ] Add RED contract for template-emitted closed empty thought block when thinking is disabled.
- [ ] Refit `adaptGemma4HardToolGrammarForRenderedPrompt()` as a post-render semantic operation.
- [ ] Apply equally to prepared runtime-Jinja and tokenizer/Minja output.
- [ ] Open-thought prompt + hard choice: allow thought continuation, but require eventual transition to an allowed native tool tag.
- [ ] Closed/no-thought prompt: retain normal hard grammar.
- [ ] Do not detect model state from model name alone when rendered prompt state is sufficient.

Authority: current Google Gemma4 template and Transformers prefix-aware response parsing.

## 7. Template capability TODO

- [ ] Preserve existing `requiresObjectArguments` replay adaptation for prior assistant tool calls.
- [ ] Preserve removal/handling of unsupported tool-definition fields through existing capability analysis.
- [ ] Do **not** unconditionally convert role:`tool` JSON strings to objects.
- [ ] If any tool-response object conversion remains necessary for non-Google templates, add a capability probe that excludes templates which iterate content parts via `part.get(...)`.
- [ ] Verify current Google template under both runtime Jinja and tokenizer/Minja paths.
- [ ] Keep full declarative `response_template` metadata support as follow-up scope, not this upstream PR.

## 8. Parser regression TODO

Core parser semantic work is implemented, but before promotion:

- [ ] Import/translate current upstream Gemma array regression from merged #4532 into our clean test matrix where not already covered.
- [ ] Verify cross-chunk false-positive case: prose suffix + next chunk `call:known_tool{...}` remains content.
- [ ] Verify actual logical newline + bare known call is recoverable.
- [ ] Verify unknown tool never becomes executable.
- [ ] Verify malformed numeric lexemes (`12foo`, `01`, `1.`, `1e`, `-x`) fail instead of becoming numbers/strings in executable calls.
- [ ] Verify large integer lexeme remains byte-preserved.
- [ ] Verify malformed call followed by valid call does not poison parser state.
- [ ] Verify structural markers never leak to client content.

Note (2026-09-15 session): contract tests for the above exist
(`gemma4_upstream_refit_contract_test.cpp`) but were NOT executed here:
they are linked only into the full `//src:ovms_test` binary, which was
never built in this environment. The only parser-level tests executed
this session are the new raw-Delta RED tests (`fe894aad9`,
`//src/test/llm/gemma4_generation:gemma4_phantom_tool_call_test`):
phantom `ToolCallDelta{id, name, ""}` publication on malformed input
REPRODUCED (4 failing), unknown-tool header guard PASS, multi-call
characterization PASS (bare second `call:` is executable, indices 0,1,
no content leak). The transactional publication fix is deferred to
Codex (see §13).

## 9. Build / source hygiene TODO

The connector environment cannot run the Windows/Bazel build. Local verification is authoritative for compilation claims.

Before local handoff is considered accepted:

- [ ] Inspect `src/llm/BUILD` for new headers/sources. If Gemma generation builder remains header-only, ensure upstream style permits it; otherwise split into `gemma4/generation_config_builder.hpp/.cpp` and wire target cleanly.
- [ ] Ensure `src/test/llm/gemma4_generation/BUILD` resolves all direct includes/deps.
- [ ] Run buildifier/style/license-oriented source audit using repository-standard commands.
- [ ] Run the narrowest relevant Bazel test targets first, then broader affected suites.
- [ ] Compare clean staging against `a5136cb...` and remove accidental archaeology/runtime/docs unrelated to contribution.
- [ ] Check current upstream `main` again before final promotion for drift after `a5136cb`.

Local-machine acceptance after implementation:

- [ ] Bazel/Windows build.
- [ ] parser contract tests.
- [ ] special-token handoff test.
- [ ] generation-policy target.
- [ ] relevant API/OpenAI parsing tests.
- [ ] runtime-Jinja and Minja template tests.
- [ ] live Gemma4 unary required/named/auto.
- [ ] live streaming required/named/auto.
- [ ] multi-turn tool response -> follow-up call.
- [ ] parallel false/true probes.
- [ ] NovaClaw/OpenCode style agent loop acceptance.

## 10. Final history / promotion TODO

Do not promote staging until all semantic layers are represented and source-audited.

- [ ] Reconstruct/reword early clean commits that predate the explicit provenance-message requirement if necessary.
- [ ] Keep test RED and production GREEN commits logically paired where useful to reviewer comprehension.
- [ ] Verify every behavioral commit answers:
  1. where the solution came from;
  2. what observation demanded it;
  3. what exact failure it fixes;
  4. what alternative was deliberately rejected.
- [ ] Force-move / recreate `integration/gemma4-upstream-contribution-refit-20260915` to the final clean history only after review of staging diff.
- [ ] Do not move `main`, release branches or unrelated refs.
- [ ] After local acceptance, decide whether to replace/update PR #4525 or open a clean successor PR.

## 11. Recovery procedure after session loss

1. Resolve `staging/gemma4-upstream-refit-clean-20260915` from GitHub.
2. Read this file and `COMPARATIVE-GEMMA4-PARSER-VERDICT.md`.
3. Read the latest behavioral commit body; if it is a `test(...)` RED commit, finish that RED->GREEN pair before starting another concern.
4. The hard-validation builder half is GREEN at `27b66eda`; the active unfinished concern is the API validation catch in `OpenAIApiHandler::extractInputRequest()`.
5. Do not skip directly to `parallel_tool_calls` until that API-boundary behavior has a test/evidence and GREEN implementation.
6. After every new semantic pair, update this plan's completed/pending sections and exact HEAD checkpoint.
7. Never infer success from old `integration/gemma4-protocol-hardening-2026.5`; it is evidence/reference only.

## 12. Questions that should be escalated to the user

Escalate semantic forks as **observable experiments**, not library trivia. Useful questions include:

- Given this exact rendered prompt suffix, which first raw tokens does the model emit?
- Under `required`, does live Gemma finish existing thought before `<|tool_call>`, or attempt prose/content instead?
- With `parallel_tool_calls=false`, what does the model try immediately after first `<tool_call|>`?
- At a Jinja failure, what exact type/value reaches `role=tool` content?
- In a streaming failure, which raw special token or phase transition disappears first?

The user does not need to know every internal API. The valuable input is the observation that discriminates between parser, generator, template, streamer and API-policy failure.

## 13. Local-agent session checkpoint 2026-09-15 (evening)

Working branch HEAD after this session (all on `staging/gemma4-upstream-refit-clean-20260915`):

- `18de2c26c` (pre-existing RED) test(gemma4): cover parallel tool call policy at HTTP boundary
- `7be4b7aa4` (GREEN) fix(gemma4): plumb parallel_tool_calls into Gemma4 generation policy
- `447718b8d` (RED) test(gemma4): reject unsafe tool names in generation policy
- `547df8030` (GREEN) fix(gemma4): validate tool names before installing native grammar
- `fe894aad9` (RED only) test(gemma4): expose phantom tool-call publication on malformed input

Fetched HEAD at session start: `18de2c26cf80317113167712f40cd39b7e3b5987`.
Upstream `main`: `e338fb74b53dc8ac1c48707903b85e3901adcbdc` (one commit past pinned base `a5136cb...`; no rebase performed).

Evidence (Windows, `C:\opt\bazel.exe`, output root
`C:\opt\bazel-gemma4-upstream-refit-20260915`, tokenizer
`C:/llm/models/runtime/gemma4-26-heretic-google-current`):

- `bazel test //src/test/llm/gemma4_generation:gemma4_generation_policy_test --test_output=errors` => PASS (21/21) after `7be4b7aa4` and `547df8030`.
- `bazel test //src/test/llm/gemma4_generation:gemma4_phantom_tool_call_test --test_output=errors` => 4 PASS / 4 FAIL as designed:
  - FAIL (phantom REPRODUCED): MalformedNumber (1 header, want 0), MalformedNested (1, want 0), MalformedThenValid (2 headers + valid index 1, want 1 header at 0), StreamingSplit (1, want 0);
  - PASS: UnknownRegisteredTool (registry guard holds at header level), CanonicalTwoEnvelopes (2 calls idx 0,1), GarbageBetweenCalls (bare second `call:` IS executable, idx 0,1, garbage swallowed from content), AdjacentCalls (same).
- `git diff --check` => PASS. buildifier not installed in this environment (no binary); BUILD edits follow the existing `cc_test` block style.
- Broad parser/streamer regression via `//src:ovms_test` NOT run: binary was never built here and a full mediapipe/TF build is out of session scope. Only standalone `cc_test` targets under `src/test/llm/...` exist (the two gemma4_generation targets above).

Build-environment note: the bazel server must be started with
`BAZEL_SH=C:\opt\msys64\usr\bin\bash.exe`, `BAZEL_VS=C:\BuildTools`,
`BAZEL_VC=C:\BuildTools\VC` in the client environment (VS BuildTools
live at nonstandard `C:\BuildTools`), using `C:\opt\bazel.exe` with
`--output_user_root=C:\opt\bazel-gemma4-upstream-refit-20260915`. Do NOT
pass `--repo_env=BAZEL_SH=...` overrides; they invalidate the external
repo cache (`local_config_cc`/`local_config_python`) and break the
toolchain. If the server idles out, `shutdown`, delete a poisoned
`external/local_config_cc` + `external/local_config_python` if present,
and restart with the three variables set.

Deferred to Codex (do NOT implement without separate review):

- transactional delayed `ToolCallDelta` publication fix;
- any `Gemma4ToolParser` state-machine redesign from the phantom/multi-call findings;
- post-#4103 prompt-state grammar reconciliation;
- runtime-Jinja / Minja semantic refit;
- major `OVMSTextStreamer` changes; generic parser framework; `response_template` engine.

Next unfinished tasks: template-adaptation RED contracts (§6), full
`//src:ovms_test` parser-matrix execution, live Arc/Gemma4 acceptance,
final history/promotion review (§10).
