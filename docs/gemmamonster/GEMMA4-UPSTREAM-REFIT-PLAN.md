# Gemma4 Upstream Contribution Refit Plan

**Status:** ACTIVE / implementation in progress  
**Updated:** 2026-09-15  
**Working branch:** `staging/gemma4-upstream-refit-clean-20260915`  
**Current checkpoint before this document commit:** `27b66eda147ccbbf90ea5251da4bafdd7cfd3d91`  
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

## 3. Current exact implementation state

The builder half of the hard-validation contract is now implemented. The remaining unfinished boundary is `OpenAIApiHandler::extractInputRequest()`.

The generic API path still does this on structured-output validation error:

```cpp
catch (const std::exception& e) {
    SPDLOG_LOGGER_DEBUG(...);
    configBuilder.unsetStructuredOutputConfig();
}
```

That behavior remains acceptable for optional guided generation such as Gemma4 `auto`. It is a contract violation for `required` or named choice because it silently turns a hard constrained request into unconstrained generation.

### Next patch, do this first after recovery or local fetch

- [x] Add default `virtual bool requiresValidStructuredOutput() const { return false; }` on `BaseGenerationConfigBuilder`.
- [x] Track hard Gemma4 policy after request parsing: `required` or named choice => mandatory validation; `auto` => optional.
- [x] Expose the accessor through `GenerationConfigBuilder`.
- [x] Reject hard tool choice if no tool schemas are available.
- [ ] Add an API-boundary RED test around structured-output validation behavior if a narrow fixture can be built without distorting production code.
- [ ] Change `OpenAIApiHandler::extractInputRequest()` validation catch:
  - `configBuilder.requiresValidStructuredOutput() == true` => return `absl::InvalidArgumentError(...)` including validation cause;
  - optional policy => log and `unsetStructuredOutputConfig()` exactly as today.
- [ ] Verify that no upper-layer exception translation is needed; `GenAiServable::parseRequest()` already propagates `StatusOr` errors and `HttpLLMCalculator` already handles request failures.
- [ ] Run generation-policy tests and relevant API/input-processing tests.
- [ ] Commit the API-boundary GREEN separately with full provenance body.

Do not merely leave an invalid hard grammar installed and hope a later GenAI call fails. Fail at the request boundary where the contract violation can be explained.

## 4. Local-agent fetch and integrity gate

The local agent must verify the connector-written branch before continuing implementation.

- [ ] `git fetch --all --prune` and resolve `origin/staging/gemma4-upstream-refit-clean-20260915`.
- [ ] Confirm fetched parent chain contains `92a30faf -> 6eb48031 -> 27b66eda` in that order before any new local commit.
- [ ] Confirm current remote branch HEAD equals the SHA recorded at the top of this file or explain any later docs-only checkpoint commit.
- [ ] Confirm the tree does **not** contain `docs/gemmamonster/.noop`.
- [ ] Confirm the tree does **not** contain `src/llm/io_processing/gemma4/generation_policy.hpp`; a connector-only placeholder commit that created it was force-reset and must remain unreachable from the branch.
- [ ] `git status --short` must be clean immediately after checkout/reset to remote.
- [ ] Inspect the exact diff from `a5136cb285482aaef5410a053b5ecd04ff9324ec` before fixing anything.
- [ ] Check files written through the connector for truncation, duplicated blocks, malformed include order, stale comments, accidental whole-file rewrites or style drift.
- [ ] In particular inspect:
  - `src/llm/io_processing/base_generation_config_builder.hpp`
  - `src/llm/io_processing/generation_config_builder.hpp`
  - `src/llm/apis/openai_api_handler.cpp`
  - `src/test/llm/gemma4_generation/gemma4_generation_policy_test.cpp`
  - Gemma4 parser/reasoning files changed earlier in this branch.
- [ ] If connector-write damage is found, repair only the damage first and commit it as a dedicated hygiene commit. Do not mix semantic changes into that repair.

## 5. Generation TODO after hard-validation GREEN

### `parallel_tool_calls`

Current observation: `OpenAIRequest` / builder work existed in the old line, but current `parseTools()` does not yet propagate the HTTP `parallel_tool_calls` field into generation policy.

- [ ] Add HTTP/API RED contract: explicit `parallel_tool_calls=false` reaches the internal request as false; true/default semantics remain documented.
- [ ] Decide and document default using current OpenAI-compatible OVMS behavior rather than guessing from the old branch.
- [ ] Add internal request field only if not already present on the post-#4103 base.
- [ ] Required/named grammar: `parallel_tool_calls=false` => max one native call.
- [ ] `parallel_tool_calls=true` => native repeated calls allowed.
- [ ] Auto grammar must apply the same repetition policy after trigger.
- [ ] Add direct builder tests and an HTTP parsing test so laboratory-only field assignment cannot masquerade as API support.

Source: llama.cpp native Gemma policy plus OpenAI parallel-tool semantics. Do not copy SGLang generic JSON fallback.

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
