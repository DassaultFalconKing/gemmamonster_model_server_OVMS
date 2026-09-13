# NEXT SESSION PROMPT — Windows-safe async C-API stress validation

Repository: `DassaultFalconKing/gemmamonster_model_server_OVMS`

Branch: `integration/gemmamonster-rc2-semantic-refit-20260912`

Expected predecessor at handoff: `20f8d23a5edd8c892ef184dac06f39b55efb82ac` or a strict fast-forward descendant.

Status: **SOURCE TEST-HARNESS FIX PRESENT; WINDOWS BUILD/RUNTIME VALIDATION REQUIRED; READY_FOR_ACCEPTANCE=NO**.

## Proven history

- Negative CLI 3/3 is closed: inherited `OVMS_MODEL_REPOSITORY_PATH=C:\llm\models` was the cause.
- Pre-fix full suite repeatedly crashes in `ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference` with `0xC0000005` EXECUTE AV to tiny addresses on stress worker threads during model unload.
- H1 callback-signal ordering was rejected experimentally.
- The async lifetime/guard-order patch (`4fa90bae` / `bcf476ee`) was also rejected experimentally: isolated 20/20 and family 20/20 passed, but full suite reproduced the same crash signature. It has been reverted by `4362e9b3d11e2dbde7049c0aa5fd086f4dd98c21`.
- `src/inference_executor.hpp` is back to blob `1092c82f7c60ab74fc97e26fb55b9215a48804bb`, the pre-experiment version.
- No evidence implicates `src/llm/**`.

## New root-cause evidence

The C-API stress harness executes GoogleTest assertions (`ASSERT_*`, `EXPECT_*`, `::testing::Test::HasFailure`) directly from 20 concurrent worker threads. GoogleTest documents that assertions from multiple threads are not supported on Windows.

The same harness also used a status macro that calls `OVMS_StatusCode(nullptr, ...)` on successful C-API calls and does not release the returned status object, creating cumulative test-process leaks.

This is consistent with the observed discriminator: isolated/family runs are clean while the long-lived full-suite process crashes on a worker thread. It is a test-harness defect hypothesis, not a production inference change.

## Patch under validation

- `5def2c3c0b12a31243a68e6c2d62f286cc2ea63d` — `fix(test): make async C-API stress Windows-safe`
  - changes only `src/test/c_api_stress_tests.cpp`;
  - preserves the exact fixture/test names;
  - all async stress workers report failure through thread-safe state instead of invoking GoogleTest from worker threads;
  - assertions execute after worker `join()` on the main test thread;
  - C-API statuses are explicitly consumed/deleted;
  - all four async config-change tests use the safe runner.
- `20f8d23a5edd8c892ef184dac06f39b55efb82ac` — contract-test parser fix.
- Contract: `tests/python/test_windows_stress_harness_contract.py`.

Two empty service commits (`3e9bd432...` and `03e4a76f...`) exist in history from an API no-op write. Do not rewrite history to remove them; they change no tree content.

## Session start

1. Fetch/re-resolve the branch and record actual `START_HEAD`.
2. Require `20f8d23a...` to be an ancestor unless a newer fast-forward validation commit exists.
3. Confirm `git diff -- src/llm` is empty.
4. Clean only generated/instrumentation residue according to the established B-parity runbook. Preserve dumps/logs.
5. Use exact `rc1-parity`, Bazel 6.4.0, MSVC 14.44.35207, Python 3.12.10 and exact OpenVINO/GenAI 2026.4 RC2 pins. No upgrades/tuning.

## Gate 0 — contract + compilation

Run:

```powershell
python -m unittest tests.python.test_windows_stress_harness_contract
```

Require 3/3 PASS.

Then build with the exact existing B-parity Windows build path. Compilation/linking must pass before runtime interpretation. If the new test helper has a mechanical C++ compile error, make the smallest correction preserving these invariants:

- no GoogleTest call from `runWindowsSafeAsyncWorker`;
- no legacy `triggerCApiAsyncInferenceInALoop` pointer used by the four async tests;
- owned `OVMS_Status*` objects are deleted;
- fixture/test names are unchanged.

Record binary identity after build.

## Gate 1 — exact blocker

Run `ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference` at least 20 times. Record every exit code.

This gate was clean before, so it is necessary but not sufficient.

## Gate 2 — async ConfigChange family

Run all four async tests repeatedly, at least 20 family repetitions if practical:

- `ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference`
- `ConfigChangeStressTestAsync.ChangeToWrongShapeAsyncInference`
- `ConfigChangeStressTestAsync.ChangeToAutoShapeDuringAsyncInference`
- `ConfigChangeStressTestAsyncStartEmpty.ChangeToLoadedModelDuringAsyncInference`

Record pass/fail counts.

## Gate 3 — full-suite discriminator

Run the normal maintained Windows suite/gate environment, with inherited `OVMS_MODEL_REPOSITORY_PATH` sanitized and the existing intentional CVS-176244 treatment only.

Require **3 consecutive full-suite PASS runs** before claiming this hypothesis supported.

If any run still crashes:

- capture dump;
- record exact last running test;
- compare exception code, access type, target address, victim thread and module/offsets with prior dumps;
- mark this hypothesis REJECTED if the same signature survives;
- do not add a new exclusion.

If the suite progresses past the async blocker and exposes another Windows-sporadic fixture, distinguish an upstream CVS-176244 fixture from a new defect. Do not silently broaden exclusions.

## Gate 4 — existing maintained gates

Require:

1. negative CLI 3/3 PASS;
2. `tests/windows/gemmamonster_rc2_ovms_test_gate.ps1` emits `GEMMAMONSTER_RC2_OVMS_TEST_GATE_PASS`;
3. `src/llm/**` remains untouched.

No package until all required gates are green.

## Required pushed report

Push a fast-forward evidence worklog containing:

- `START_HEAD` / `END_HEAD`;
- exact build command and binary identity;
- contract result;
- compile result;
- exact-test 20x result;
- async-family repetition result;
- each full-suite result;
- negative CLI result;
- maintainer gate result;
- any new dump signature;
- files changed during validation;
- package status;
- `READY_FOR_ACCEPTANCE` verdict.

If the patch fails the full-suite discriminator, leave the evidence explicit and do not pretend the bug moved merely because the test ran longer.
