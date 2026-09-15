# Local Agent Handoff — Gemma4 Upstream Refit — 2026-09-15

## Mission

Verify, repair if necessary, compile and continue the Gemma4 upstream contribution refit in `DassaultFalconKing/gemmamonster_model_server_OVMS`.

This is an implementation/verification session, not a redesign session. Existing semantic decisions are intentional unless an executable test or current upstream API proves them wrong.

## Authority and refs

Repository: `DassaultFalconKing/gemmamonster_model_server_OVMS`

Working branch only:

`staging/gemma4-upstream-refit-clean-20260915`

Upstream base used for the clean refit:

`openvinotoolkit/model_server@a5136cb285482aaef5410a053b5ecd04ff9324ec`

Last behavioral GREEN before the latest documentation checkpoints:

`27b66eda147ccbbf90ea5251da4bafdd7cfd3d91`

Important prior RED:

`92a30faf420110b143a613e85800e1db057fc49b`

Read before changing code:

- `docs/gemmamonster/GEMMA4-UPSTREAM-REFIT-PLAN.md`
- `docs/gemmamonster/COMPARATIVE-GEMMA4-PARSER-VERDICT.md`
- this handoff

Do not move or merge `main`, release branches, tags, PR bases or the final integration branch. Push only the staging branch. Do not update PR #4525 in this session.

If Superpowers skills are available, use TDD/systematic-debugging/verification-before-completion discipline.

## Phase 0 — Fetch and prove the tree you are touching

Run:

```powershell
git fetch --all --prune
git switch staging/gemma4-upstream-refit-clean-20260915
git reset --hard origin/staging/gemma4-upstream-refit-clean-20260915
git status --short
git rev-parse HEAD
git log --oneline --decorate -25
```

Expected: clean worktree. Documentation commits may be above `27b66eda`; that is fine. The behavioral chain must still contain `92a30faf` followed later by `27b66eda`.

Prove ancestry:

```powershell
git merge-base --is-ancestor 92a30faf420110b143a613e85800e1db057fc49b HEAD
if ($LASTEXITCODE -ne 0) { throw "missing hard-validation RED" }

git merge-base --is-ancestor 27b66eda147ccbbf90ea5251da4bafdd7cfd3d91 HEAD
if ($LASTEXITCODE -ne 0) { throw "missing hard-validation builder GREEN" }
```

Two connector-only throwaway commits were force-reset before the current branch history. Prove their artifacts are absent:

```powershell
$tree = git ls-tree -r --name-only HEAD
if ($tree -contains 'docs/gemmamonster/.noop') { throw 'connector .noop artifact leaked into branch' }
if ($tree -contains 'src/llm/io_processing/gemma4/generation_policy.hpp') { throw 'placeholder generation_policy.hpp leaked into branch' }
```

Do not delete anything merely because it looks unfamiliar. First prove whether it belongs to the diff from the pinned upstream base.

## Phase 1 — Audit connector-written work before implementing more

Fetch current upstream main but do not rebase yet:

```powershell
git fetch upstream main --prune
git rev-parse upstream/main
git diff --check a5136cb285482aaef5410a053b5ecd04ff9324ec..HEAD
git diff --stat a5136cb285482aaef5410a053b5ecd04ff9324ec..HEAD
git diff --name-status a5136cb285482aaef5410a053b5ecd04ff9324ec..HEAD
```

Record how far current `upstream/main` moved from `a5136cb...`; do not mix a rebase into repair/verification work.

Inspect especially:

- `src/llm/io_processing/base_generation_config_builder.hpp`
- `src/llm/io_processing/generation_config_builder.hpp`
- `src/llm/apis/openai_api_handler.cpp`
- `src/test/llm/gemma4_generation/gemma4_generation_policy_test.cpp`
- `src/test/llm/gemma4_generation/BUILD`
- Gemma4 tool parser implementation/header and tests changed on this branch
- Gemma4 reasoning parser implementation/header and special-token streamer/phase logic changed on this branch

Look specifically for connector-write damage: duplicated blocks, truncated files, placeholder text, malformed include order, stale comments that contradict code, accidental full-file rewrites, missing newline, BUILD deps that do not match includes, or a file whose current contents do not match the semantic commit message.

If actual write damage exists, repair it before new semantics. Make one dedicated hygiene commit. Do not silently amend historical semantic commits yet.

Commit body for such a repair must say exactly what was mechanically damaged and prove no intended behavior changed.

## Phase 2 — Verify what is already implemented

The intended current generation semantics are:

1. `tool_choice=required` installs a native Gemma4 structured grammar and requires at least one tool.
2. `tool_choice=auto` uses lazy activation via `<|tool_call>` TriggeredTags; free text is allowed before the native tool marker.
3. named tool choice is hard and restricts grammar to exactly the selected registry tool.
4. active Gemma4 tools cannot silently overwrite `response_format`; the combination is rejected. `tool_choice=none` leaves response-format behavior intact.
5. hard `required`/named grammar is marked `requiresValidStructuredOutput()==true`; `auto` is optional.
6. no hard-coded Gemma token IDs. Special-token start detection is tokenizer-resolved.
7. parser hardening includes recursive native arguments, registry validation, lossless number intent, bounded malformed recovery and logical-line-aware bare-call recovery.

Run the exact generation target first:

```powershell
bazel test //src/test/llm/gemma4_generation:gemma4_generation_policy_test --test_output=errors
```

If this repository/machine uses Bazelisk or a wrapper, use the repository-standard equivalent but preserve the exact target.

Discover affected existing test targets rather than guessing target names:

```powershell
bazel query 'kind(".*_test", //src/test/llm/...)' | Select-String -Pattern 'gemma4|output_parser|input_processing|chat_template|streamer|special'
```

Run the relevant returned targets individually with `--test_output=errors`. Record every exact command and result.

Run repository-standard buildifier/style/license checks on changed BUILD/C++ files. Do not claim style PASS merely because code compiles.

## Phase 3 — Finish the currently incomplete hard-validation boundary

This is the first semantic task. Do not start `parallel_tool_calls` before it is GREEN.

Current problem:

`OpenAIApiHandler::extractInputRequest()` still catches any structured-output validation exception and unconditionally calls:

```cpp
configBuilder.unsetStructuredOutputConfig();
```

That fallback is allowed for optional guidance such as Gemma4 `auto`; it is forbidden for hard `required` or named choice.

Also notice that `configBuilder.parseConfigFromRequest(request)` currently sits outside the existing `std::invalid_argument` conversion. Because Gemma4 now rejects invalid hard policy there, `extractInputRequest()` should behave as a `StatusOr` boundary rather than relying on an upper generic exception catch.

### 3A — RED first

Find the narrowest existing test fixture that can exercise `extractInputRequest()` with a real tokenizer. Prefer `src/test/llm/input_processing/input_processing_integration_test.cpp` or an existing OpenAI-handler fixture.

Add tests proving:

- a hard Gemma4 request whose structured grammar validation fails returns non-OK `InvalidArgument` and does not continue unguided;
- optional `auto` validation failure retains the existing graceful fallback behavior;
- an invalid hard request raised from `parseConfigFromRequest()` is returned as `InvalidArgument` rather than escaping as an exception.

Before creating a new production seam solely for testing, inspect existing fixtures and GenAI validation tests. Use an actually invalid schema/structural-tag case that demonstrably makes `validateStructuredOutputConfig()` throw. Record the exact exception observed in the RED run.

If no narrow real validation fixture can trigger the failure without artificial production hooks, do not invent a mock-only architecture. Keep the existing builder RED contract, add the best API-level test available, and document why the remaining validation path is covered by local integration evidence.

Commit RED separately:

```text
test(gemma4): fail hard tool policy at validation boundary

Provenance:
- OpenAI required/named tool_choice hard semantics
- current OVMS extractInputRequest validation fallback
- Gemmamonster hard-policy builder contract

Driven by:
- exact RED observation and command

Fixes:
- pins expected API-boundary failure/fallback behavior

Decision:
- test request boundary rather than relying on later GenAI failure
```

### 3B — GREEN

Refit `OpenAIApiHandler::extractInputRequest()` so input errors are converted consistently. Preferred shape:

```cpp
try {
    configBuilder.parseConfigFromRequest(request);
    configBuilder.adjustConfigForDecodingMethod();
} catch (const std::invalid_argument& e) {
    return absl::InvalidArgumentError(e.what());
}

try {
    configBuilder.validateStructuredOutputConfig(tokenizer);
} catch (const std::exception& e) {
    if (configBuilder.requiresValidStructuredOutput()) {
        return absl::InvalidArgumentError(
            absl::StrCat("Structured output validation failed for required generation policy: ", e.what()));
    }
    SPDLOG_LOGGER_DEBUG(
        llm_calculator_logger,
        "Tool guided generation will not be applied due to JSON schema validation failure: {}",
        e.what());
    configBuilder.unsetStructuredOutputConfig();
}
```

The message at this generic API layer should not hard-code `Gemma4`; future builders may also implement mandatory validation.

Re-run the RED test and all generation-policy tests. Then commit GREEN separately with the required `Provenance / Driven by / Fixes / Decision` body.

Update `GEMMA4-UPSTREAM-REFIT-PLAN.md` immediately after GREEN with the new exact HEAD and evidence.

## Phase 4 — `parallel_tool_calls`, with API plumbing proven end-to-end

Only after Phase 3 is GREEN.

First inspect current post-#4103 types and old reference branch:

```powershell
git grep -n "parallel_tool_calls" HEAD -- src
git grep -n "parallelTool" HEAD -- src
git grep -n "parallel_tool_calls" origin/integration/gemma4-protocol-hardening-2026.5 -- src
```

If the old reference branch is not fetched, fetch it without merging.

Do not blindly port the old implementation. Use it as evidence, then fit current upstream architecture.

Required behavior to pin with RED tests:

- HTTP `parallel_tool_calls=false` reaches `OpenAIRequest`/generation policy as false.
- explicit `true` reaches it as true.
- determine the omitted/default value from current OVMS/OpenAI-compatible behavior; do not guess.
- false means at most one native call can be produced by required/named grammar.
- true allows repeated native tool calls where GenAI StructuralTags supports it.
- auto applies the same repetition policy after lazy trigger.

Inspect the exact current OpenVINO GenAI `StructuredOutputConfig` API installed/checked into dependencies before naming fields such as `stop_after_first`. Grep headers and existing users; use the actual API, not memory.

Add both builder-level tests and an HTTP parsing test. A field manually assigned in a unit test is not proof that the REST API supports it.

Keep RED and GREEN commits separate and update the plan after the pair.

## Phase 5 — Post-#4103 template adaptation

Do not transplant old `PyJinjaTemplateProcessor` wiring.

Read current `ChatTemplateProcessor` and PR #4103-era code. Identify where runtime Jinja and tokenizer/Minja rendering converge on final `req.promptText`.

Pin with RED tests at least:

1. rendered Gemma4 prompt ends inside an open thought channel after a tool response;
2. thinking-disabled template emits a closed/empty thought block;
3. hard tool grammar is adapted after rendering, identically for runtime-Jinja and Minja paths;
4. open-thought + hard tool choice permits continuation of thought but still requires eventual transition to an allowed native tool tag;
5. closed/no-thought prompt retains normal hard grammar.

Preserve current capability analysis such as `requiresObjectArguments`. Do not unconditionally coerce role=`tool` JSON strings into objects. If conversion is needed for a non-Google template, prove it with a capability probe and a test that excludes content-part templates using `part.get(...)`.

Keep declarative `response_template` metadata support out of this PR unless current upstream architecture makes it unavoidable.

## Phase 6 — Parser regression gate

Before declaring source-ready, make sure the clean parser matrix covers:

- upstream merged #4532 array regression semantics;
- chunk split: prose ending without newline, next chunk begins `call:known_tool{...}` => remains content;
- actual logical newline + bare known call => recoverable;
- unknown tool => never executable;
- malformed numeric lexemes `12foo`, `01`, `1.`, `1e`, `-x` => reject executable call;
- large integer lexeme => byte-preserved;
- malformed call followed by valid call => parser state recovers;
- structural markers => never leak to client content;
- reasoning-close -> tool-open special-token handoff across chunk boundaries.

Run exact targets and record results. If a test fails, diagnose before patching. Do not weaken a contract to make the suite green.

## Phase 7 — Build and evidence

Run the repository-standard Windows build/packaging path needed for OVMS, plus focused Bazel tests. Start narrow, then broaden.

Minimum evidence report must contain:

- fetched remote HEAD;
- current `upstream/main` SHA and drift from pinned `a5136cb...`;
- every new commit SHA and subject;
- `git status --short` at finish;
- `git diff --check` result;
- exact test/build commands;
- PASS/FAIL for every command;
- first relevant failure excerpt for any FAIL;
- files repaired as connector damage, if any;
- semantic changes made;
- remaining unchecked items from the plan;
- whether source is ready for live Arc/Gemma4 runtime acceptance.

Do not call the branch accepted merely because compilation passes. Runtime acceptance is a later gate: unary/streaming required/named/auto, multi-turn tool response -> follow-up call, parallel false/true, then NovaClaw/OpenCode agent loop.

## Commit discipline

Every behavioral commit body must contain these literal sections:

```text
Provenance:
- where the solution/evidence came from

Driven by:
- exact observed failure or contract

Fixes:
- exact behavior changed

Decision:
- chosen design and meaningful rejected alternative
```

Keep unrelated concerns separate. Do not squash RED/GREEN pairs during implementation. Do not rewrite historical commits just to make the log pretty until the whole staging branch has passed review.

Push only:

`origin/staging/gemma4-upstream-refit-clean-20260915`

## Stop conditions

Do not ask the user library-trivia questions that can be answered from code/tests.

Escalate only when a live-model observation distinguishes competing implementations, for example:

- exact raw token sequence after a specific rendered prompt suffix;
- whether required mode continues open thought or emits prose instead of `<|tool_call>`;
- what appears immediately after first `<tool_call|>` with `parallel_tool_calls=false`;
- exact role=`tool` value/type at a template failure;
- first missing/leaked special token in a streaming failure.

When escalating, provide the exact probe command/request and the two or more interpretations its result distinguishes.
