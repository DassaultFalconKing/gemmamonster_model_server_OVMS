# Gemma4 Upstream Contribution Refit Plan

**Status:** ACTIVE / implementation in progress  
**Updated:** 2026-09-15  
**Working branch:** `staging/gemma4-upstream-refit-clean-20260915`  
**Current checkpoint before this document commit:** `92a30faf420110b143a613e85800e1db057fc49b`  
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

## 3. Current exact RED state

The branch currently intentionally fails the new hard-validation contract because production code has not yet implemented:

```cpp
GenerationConfigBuilder::requiresValidStructuredOutput()
```

and `Gemma4GenerationConfigBuilder` does not yet expose hard-policy state.

The generic API path currently does this on validation error:

```cpp
catch (const std::exception& e) {
    ...
    configBuilder.unsetStructuredOutputConfig();
}
```

That behavior is acceptable only for optional guided generation such as `auto`. For `required` or named choice it changes the caller contract into unconstrained sampling.

### Next patch, do this first after recovery

- [ ] Add a default `virtual bool requiresValidStructuredOutput() const { return false; }` on `BaseGenerationConfigBuilder`.
- [ ] Track hard Gemma4 policy after request parsing: `required` or named choice => mandatory validation; `auto` => optional.
- [ ] Expose the accessor through `GenerationConfigBuilder`.
- [ ] Reject `tool_choice=required` if no tools are available.
- [ ] Change `OpenAIApiHandler::extractInputRequest()` validation catch:
  - hard structured policy => return `InvalidArgumentError` with validation cause;
  - optional policy => log and `unsetStructuredOutputConfig()` as today.
- [ ] Preserve the RED/GREEN commit split and provenance body.

Do not merely leave an invalid hard grammar installed and hope a later GenAI call fails. Fail at the request boundary where the contract violation can be explained.

## 4. Generation TODO after hard-validation GREEN

### `parallel_tool_calls`

Current observation: `OpenAIRequest` / builder work existed in the old line, but current `parseTools()` does not yet propagate the HTTP `parallel_tool_calls` field into generation policy.

- [ ] Add HTTP/API RED contract: explicit `parallel_tool_calls=false` reaches the internal request as false; true/default semantics remain documented.
- [ ] Decide and document default using current OpenAI-compatible OVMS behavior rather than guessing from the old branch.
- [ ] Add internal request field only if not already present on the post-#4103 base.
- [ ] Required/named grammar: `parallel_tool_calls=false` => `stop_after_first=true` / max one native call.
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

## 5. Post-#4103 template adaptation TODO

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

## 6. Template capability TODO

- [ ] Preserve existing `requiresObjectArguments` replay adaptation for prior assistant tool calls.
- [ ] Preserve removal/handling of unsupported tool-definition fields through existing capability analysis.
- [ ] Do **not** unconditionally convert role:`tool` JSON strings to objects.
- [ ] If any tool-response object conversion remains necessary for non-Google templates, add a capability probe that excludes templates which iterate content parts via `part.get(...)`.
- [ ] Verify current Google template under both runtime Jinja and tokenizer/Minja paths.
- [ ] Keep full declarative `response_template` metadata support as follow-up scope, not this upstream PR.

## 7. Parser regression TODO

Core parser semantic work is implemented, but before promotion:

- [ ] Import/translate current upstream Gemma array regression from merged #4532 into our clean test matrix where not already covered.
- [ ] Verify cross-chunk false-positive case: prose suffix + next chunk `call:known_tool{...}` remains content.
- [ ] Verify actual logical newline + bare known call is recoverable.
- [ ] Verify unknown tool never becomes executable.
- [ ] Verify malformed numeric lexemes (`12foo`, `01`, `1.`, `1e`, `-x`) fail instead of becoming numbers/strings in executable calls.
- [ ] Verify large integer lexeme remains byte-preserved.
- [ ] Verify malformed call followed by valid call does not poison parser state.
- [ ] Verify structural markers never leak to client content.

## 8. Build / source hygiene TODO

The connector environment cannot run the Windows/Bazel build. Do not claim tests passed merely because source paths are logically consistent.

Before local handoff:

- [ ] Inspect `src/llm/BUILD` for new headers/sources. If Gemma generation builder remains header-only, ensure upstream style permits it; otherwise split into `gemma4/generation_config_builder.hpp/.cpp` and wire target cleanly.
- [ ] Ensure small `src/test/llm/gemma4_generation/BUILD` resolves all direct includes/deps.
- [ ] Run style/license/buildifier-oriented source audit.
- [ ] Compare clean staging against `a5136cb...` and remove accidental archaeology/runtime/docs unrelated to contribution.
- [ ] Check current upstream `main` again before final promotion for drift after `a5136cb`.

Local-machine acceptance after handoff:

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

## 9. Final history / promotion TODO

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

## 10. Recovery procedure after session loss

1. Resolve `staging/gemma4-upstream-refit-clean-20260915` from GitHub.
2. Read this file and `COMPARATIVE-GEMMA4-PARSER-VERDICT.md`.
3. Read the latest commit body; if it is a `test(...)` RED commit, finish that RED->GREEN pair before starting another concern.
4. At the checkpoint that created this plan, the active RED is `92a30faf` (`make hard tool validation fail closed`).
5. Re-check `OpenAIApiHandler::extractInputRequest()` and `generation_config_builder.hpp`; do not skip directly to `parallel_tool_calls` unless hard-validation GREEN already exists.
6. After every new semantic pair, update this plan's completed/pending sections and exact HEAD checkpoint.
7. Never infer success from old `integration/gemma4-protocol-hardening-2026.5`; it is evidence/reference only.

## 11. Questions that should be escalated to the user

Escalate semantic forks as **observable experiments**, not library trivia. Useful questions include:

- Given this exact rendered prompt suffix, which first raw tokens does the model emit?
- Under `required`, does live Gemma finish existing thought before `<|tool_call>`, or attempt prose/content instead?
- With `parallel_tool_calls=false`, what does the model try immediately after first `<tool_call|>`?
- At a Jinja failure, what exact type/value reaches `role=tool` content?
- In a streaming failure, which raw special token or phase transition disappears first?

The user does not need to know every internal API. The valuable input is the observation that discriminates between parser, generator, template, streamer and API-policy failure.
