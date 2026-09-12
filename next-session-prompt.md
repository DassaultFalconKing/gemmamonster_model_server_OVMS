# NEXT SESSION PROMPT — Windows async unload lifetime fix validation

Repository: `DassaultFalconKing/gemmamonster_model_server_OVMS`

Branch: `integration/gemmamonster-rc2-semantic-refit-20260912`

Source-fix HEAD: `bcf476ee60677b3764d4db61d9c04293f70dffaa`

Root-cause report predecessor: `9f9a9edf7e4e62ceebfd4b6fd50386379db7ec88`

Status entering this session: **SOURCE FIX PRESENT, WINDOWS RUNTIME VALIDATION REQUIRED, READY_FOR_ACCEPTANCE=NO**.

## Mission

Validate or falsify the async-inference lifetime-order fix on the exact Windows RC2 B-parity toolchain. Do not broaden scope. Do not touch `src/llm/**` unless new evidence directly proves involvement.

The previous full-suite blocker is:

`ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference`

with deterministic full-suite `0xC0000005` EXECUTE AVs to small addresses (`0xA0` / `0xC8`) on stress worker threads during model unload.

## What is already proven

1. The three negative CLI death-test failures were caused by inherited host env `OVMS_MODEL_REPOSITORY_PATH=C:\llm\models`. They pass 3/3 when the process env is sanitized. Do not reopen that investigation.
2. H1, the test-user-callback `signal.set_value()` ordering hypothesis, is rejected. Moving the signal to the end still produced the same crash; marker runs showed all callbacks completed.
3. The crash is full-suite/process-state dependent: isolated async crash test was 5/5 PASS and ConfigChange family runs were 3/3 PASS, while full suite crashed 4/4.
4. No evidence touches Gemma4 or `src/llm/**`.
5. The previous report's wording that `ModelInstanceUnloadGuard` is only sync-scope is incorrect. `modelInferAsync()` moves it into the OpenVINO callback capture as a `shared_ptr`, so it survives `OVMS_InferenceAsync()` return.

## Source invariant found after the report

Before `bcf476ee...`, `modelInferAsync()` captured these lifetime-dependent objects separately in the OpenVINO callback:

- `ModelInstanceUnloadGuard`
- `ExecutingStreamIdGuard`
- `OutputKeeper`

and the source comment claimed their destructors run "right to left".

That assumption is not portable C++. Lambda by-copy captures become unnamed closure data members whose declaration order is unspecified. Therefore the source cannot encode a required teardown dependency by capture-list position.

This matters because:

- `ModelInstanceUnloadGuard::~ModelInstanceUnloadGuard()` decrements `predictRequestsHandlesCount`.
- Model unload waits until that count reaches zero, then destroys `inferRequestsQueue` and other model components.
- `ExecutingStreamIdGuard` ultimately runs `StreamIdGuard::~StreamIdGuard()`, which calls `inferRequestsQueue_.returnStream(id_)`.

If the closure destroys the model unload guard before the stream guard, the unload thread may observe zero active inference handles and reset `inferRequestsQueue` while `StreamIdGuard` still needs that queue. That is a concrete use-after-lifetime race consistent with the Windows async+unload crash signature.

Latest upstream OVMS still contains the same separate-capture/right-to-left assumption, so treat this as a likely upstream lifetime bug, not a Gemmamonster parser regression.

## Patch under validation

`bcf476ee60677b3764d4db61d9c04293f70dffaa`

`src/inference_executor.hpp` now:

- groups the three lifetime-dependent resources in `AsyncInferenceLifetimeGuard`;
- releases `OutputKeeper` first;
- releases `ExecutingStreamIdGuard` second, while `inferRequestsQueue` is still pinned;
- releases `ModelInstanceUnloadGuard` last;
- captures one shared lifetime bundle instead of relying on lambda capture-member order;
- takes a local `shared_ptr` copy inside the callback so `request.set_callback(empty)` cannot destroy the final bundle while the callback is still executing.

Final diff from report HEAD is intentionally narrow: only `src/inference_executor.hpp`, 37 additions / 2 deletions. No `src/llm/**` changes.

## Session start discipline

1. Re-resolve the remote branch and record actual START_HEAD.
2. Confirm `bcf476ee60677b3764d4db61d9c04293f70dffaa` is an ancestor of START_HEAD.
3. Preserve the previous dumps/logs before cleaning the worktree.
4. The prior local worktree may still contain uncommitted `RACE_*` instrumentation in `src/test/stress_test_utils.hpp` and a generated `src/version.hpp` build stamp. Remove the instrumentation before candidate build. Restore generated build-state files as required by the established B-parity runbook. Do not accidentally delete retained dump evidence.
5. Use the exact existing `rc1-parity` environment and exact 2026.4 RC2 dependency pins. No toolchain upgrades, no dependency refresh, no runtime tuning.

## Build gate

Build the patched source using the same B-parity build path recorded in:

`agent-worklog/sessions/2026-09-12-b-parity-build-session.md`

Compilation/linking must be GREEN before any runtime conclusion. Record the new `ovms.exe --version` / source stamp so stale binaries are impossible to confuse with the patched build.

If the patch fails to compile, make only the smallest mechanical correction necessary to express the same lifetime invariant. Do not redesign async inference.

## Runtime validation

### Gate 1 — exact async stress test

Run at least 20 times:

`ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference`

Record all exit codes and durations.

This test was already isolated-clean before the fix, so 20/20 PASS is necessary but **not sufficient**.

### Gate 2 — ConfigChange family

Run the relevant `ConfigChange*` stress family repeatedly, preferably 20 repetitions or an equivalent repeated-test invocation. Record pass/skip/fail counts.

### Gate 3 — full-suite discriminator

This is the important RED/GREEN check.

The pre-fix full suite crashed 4/4 with the same execute-AV family. Run the full `ovms_test.exe` suite with the existing intentional Windows CVS-176244 handling and with process env sanitized as in the maintained gate.

Require **at least 3 consecutive full-suite PASS runs** before calling the lifetime-order fix causally supported.

If any full-suite run reproduces `0xC0000005`, capture a new dump and compare:

- exception code;
- execute/read/write classification;
- target address;
- crashing thread role;
- unload log state;
- stack/module offsets.

If the same signature survives, mark this hypothesis REJECTED rather than adding another exclusion.

### Gate 4 — existing CLI and maintainer gates

Re-run the negative CLI gate and require 3/3 PASS.

Then run:

`tests/windows/gemmamonster_rc2_ovms_test_gate.ps1`

with the patched `ovms_test.exe`.

The gate must print its normal PASS marker.

## Interpretation

### If patched full suite is 3/3 PASS

Record:

- baseline: pre-fix full suite 4/4 CRASH;
- patched: full suite >=3/3 PASS;
- targeted/family counts;
- exact patched binary identity;
- no new Windows exclusions.

Then the teardown-order fix is supported by RED/GREEN runtime evidence.

Only after all required tests are green may packaging proceed through the existing B-parity runbook.

### If the same crash remains

Do not weaken or hide the test. Keep the source patch only if independent evidence shows it fixes a real invariant; otherwise revert it in a dedicated commit and report the falsification.

Next audit target is then the OpenVINO callback replacement/destruction boundary around `ov::InferRequest::set_callback()` and any remaining object whose lifetime spans model unload. Use the new dump, not speculation.

## Prohibited shortcuts

- No `src/llm/**` changes.
- No new test exclusion for `ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference`.
- No LM_CB/VLM_CB architectural detour.
- No dependency/toolchain changes.
- No packaging while any required gate is red.
- No `READY_FOR_ACCEPTANCE=YES` based on isolated tests alone.

## Required pushed report

Commit and push a new evidence worklog containing:

- actual START_HEAD and END_HEAD;
- exact build command and binary identity;
- whether the worktree was cleaned of old RACE markers;
- exact-test repetition result;
- ConfigChange family repetition result;
- three full-suite results;
- negative CLI result;
- maintainer gate result;
- any new dump signature;
- files changed during validation;
- package status;
- `READY_FOR_ACCEPTANCE` verdict.

Do not rewrite existing history. Push fast-forward only to `integration/gemmamonster-rc2-semantic-refit-20260912`.
