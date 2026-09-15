# Gemma4 Upstream Contribution Refit Plan

**Status:** SEMANTIC FEATURE WORK FROZEN pending Windows/live acceptance  
**Updated:** 2026-09-15 (freeze session)  
**Working branch:** `staging/gemma4-upstream-refit-clean-20260915`  
**Freeze HEAD:** `36beda81ef0261392cb4ad16b602dfcdae031270`  
**Upstream base:** `openvinotoolkit/model_server@a5136cb285482aaef5410a053b5ecd04ff9324ec`  
**Upstream main at freeze:** `e338fb74b53dc8ac1c48707903b85e3901adcbdc`  
**Authority dossier:** `docs/gemmamonster/COMPARATIVE-GEMMA4-PARSER-VERDICT.md`  
**Freeze record:** `docs/gemmamonster/GEMMA4-SEMANTIC-FREEZE-20260915.md`

This file is the recovery point for the post-#4103 Gemma4 upstream contribution refit. Semantic feature work for the freeze scope is complete. Do not open new P1/P2 implementation from edge-case curiosity; record backlog only and proceed to Windows/live acceptance.

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
- [x] HTTP boundary alphabet + reserved policy-keyword collisions (`none`/`auto`/`required`): RED `585a6af8e` → GREEN `355ae00c1`.

### Freeze-scope closure 2026-09-15 (STOP SEMANTIC FEATURE WORK)

- [x] P0-B hard HTTP intent: RED `76c486675` → GREEN `3755dc85b`.
- [x] P0-A transactional ToolCall publication: RED `fe894aad9` → GREEN `909e21f07` (+ F9 one-envelope multicall fail-closed).
- [x] P0-C rendered thought state: RED `3c05feb29` → GREEN `c746a9b97`; multi-turn H1/H2/H4/H5 `30dfdbfd3`.
- [x] P0-D chunk invariance / drain: GREEN `2b1dfb812` (`gemma4_chunk_invariance_test`).
- [x] F7 object-root schemas + upstream array matrix: RED `31985d037` → GREEN `079eb6f66`.
- [x] F10 bounded malformed candidates: RED `474bc82ac` → GREEN `36beda81e`.
- [x] Freeze record: `docs/gemmamonster/GEMMA4-SEMANTIC-FREEZE-20260915.md` at HEAD `36beda81e`.

### Generation validation matrix

- [x] no tools + `auto` => no tool grammar / inactive (HTTP normalizes to none when registry empty).
- [x] no tools + `required` => request error (HTTP InvalidArgument).
- [x] `tool_choice=none` + tools => no tool grammar; response format remains usable.
- [x] named tool absent from registry => request error.
- [x] empty / malformed tool schema in hard mode => request error, never unguided fallback.
- [x] empty / malformed schema in auto => optional fallback retained where GenAI validation fails.
- [x] direct `required` and thought-then-tool forms remain valid (incl. OPEN_THOUGHT residual).

## 6. Post-#4103 template adaptation TODO

Target architecture: #4103 prepares runtime Jinja separately from tokenizer/Minja, but both render paths converge on final `req.promptText`. Reconciliation must happen after that convergence.

- [x] Re-read current `ChatTemplateProcessor` before patching; do not transplant old constructor/wiring.
- [x] Add RED contract for rendered prompt ending inside open Gemma thought channel after a tool response.
- [x] Add RED contract for template-emitted closed empty thought block when thinking is disabled.
- [x] Refit `adaptGemma4ToolGrammarForRenderedPrompt()` as a post-render semantic operation.
- [x] Apply equally to prepared runtime-Jinja and tokenizer/Minja output (shared classifier on final prompt text).
- [x] Open-thought prompt + hard choice: allow thought continuation, but require eventual transition to an allowed native tool tag.
- [x] Closed/no-thought prompt: retain normal hard grammar.
- [x] Do not detect model state from model name alone when rendered prompt state is sufficient.

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

- [x] Import/translate current upstream Gemma array regression from merged #4532 into our clean test matrix where not already covered (`gemma4_f7_contract_test`).
- [ ] Verify cross-chunk false-positive case: prose suffix + next chunk `call:known_tool{...}` remains content.
- [ ] Verify actual logical newline + bare known call is recoverable.
- [x] Verify unknown tool never becomes executable.
- [x] Verify malformed numeric lexemes (`12foo`, `01`, `1.`, `1e`, `-x`) fail instead of becoming numbers/strings in executable calls.
- [x] Verify large integer lexeme remains byte-preserved.
- [x] Verify malformed call followed by valid call does not poison parser state / consume public index.
- [x] Verify structural markers never leak to client content for committed calls (F8 unknown-envelope content leakage remains backlog).
- [x] Chunk-invariant tool/reasoning semantics (`gemma4_chunk_invariance_test`).
- [x] Bounded malformed candidate guards (`gemma4_f10_guard_test`).

Note (2026-09-15 freeze): standalone `//src/test/llm/gemma4_generation:*` targets are the authoritative local gate. Broad `//src:ovms_test` remains a separate promotion gate.

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

## 13. Freeze session checkpoint 2026-09-15 (evening)

Working branch HEAD after freeze: `36beda81ef0261392cb4ad16b602dfcdae031270`.

See `docs/gemmamonster/GEMMA4-SEMANTIC-FREEZE-20260915.md` for the authoritative freeze record, closed scope, backlog, and next live-acceptance stage.

**STOP SEMANTIC FEATURE WORK.** Next work is Windows product build → Arc/Gemma4 live → NovaClaw/OpenCode dogfood.
