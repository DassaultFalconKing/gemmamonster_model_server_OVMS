# NEXT SESSION PROMPT — Windows-safe stress harness validation

Repository: `DassaultFalconKing/gemmamonster_model_server_OVMS`

Branch: `integration/gemmamonster-rc2-semantic-refit-20260912`

Expected predecessor at handoff: `ca9b8efa49c4eedc5f1b1ce94e817b2870b5fd77` or a strict fast-forward descendant.

Status: **SOURCE TEST-HARNESS FIX PRESENT; WINDOWS BUILD/RUNTIME VALIDATION REQUIRED; READY_FOR_ACCEPTANCE=NO**.

## Proven history

- Negative CLI 3/3 is closed: inherited `OVMS_MODEL_REPOSITORY_PATH=C:\llm\models` was the cause.
- Pre-fix full suite repeatedly crashes in `ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference` with `0xC0000005` EXECUTE AV to tiny addresses on stress worker threads during model unload.
- H1 callback-signal ordering was rejected experimentally.
- The async lifetime/guard-order patch (`4fa90bae` / `bcf476ee`) was also rejected experimentally: isolated 20/20 and family 20/20 passed, but full suite reproduced the same crash signature. It has been reverted by `4362e9b3d11e2dbde7049c0aa5fd086f4dd98c21`.
- `src/inference_executor.hpp` is back to blob `1092c82f7c60ab74fc97e26fb55b9215a48804bb`, the pre-experiment version.
- No evidence implicates `src/llm/**`.

## New root-cause evidence

Two independent Windows test-harness defects are now source-proven:

1. The legacy C-API stress harness executes GoogleTest assertions (`ASSERT_*`, `EXPECT_*`, `::testing::Test::HasFailure`) directly from 20 concurrent worker threads. GoogleTest documents that assertions from multiple threads are not supported on Windows.
2. OVMS upstream commit `64c19a510ca8b855f3cff7e8111dd203f35b85d2` / PR #3771 intended to disable CVS-176244 Windows-sporadic stress fixtures with `GTEST_SKIP()` in `SetUpTestSuite()`. Current GoogleTest documentation supports `GTEST_SKIP()` in test bodies and fixture `SetUp()`, not `SetUpTestSuite()`. Our RC2 runtime evidence proves the old hook ineffective: `ConfigChangeStressTestSingleModel.ChangeToEmptyConfigInference` actually executed and crashed on Windows despite that suite-level skip being present in source.

The harness also used a status macro that calls `OVMS_StatusCode(nullptr, ...)` on successful C-API calls and does not release the returned status object, creating cumulative test-process leaks.

These defects fit the observed discriminator: isolated/family runs are clean while the long-lived full-suite process crashes on a worker thread. This remains a test-harness hypothesis until Windows runtime validation passes.

## Patches under validation

- `5def2c3c0b12a31243a68e6c2d62f286cc2ea63d` — `fix(test): make async C-API stress Windows-safe`
  - changes only `src/test/c_api_stress_tests.cpp`;
  - preserves the exact fixture/test names;
  - all non-skipped async stress workers report failure through thread-safe state instead of invoking GoogleTest from worker threads;
  - assertions execute after worker `join()` on the main test thread;
  - C-API statuses are explicitly consumed/deleted;
  - all four async config-change tests use the safe runner.
- `dacc6c948ad19b8d7a968604b81d030e48eb7d66` — RED contract extending `tests/python/test_windows_stress_harness_contract.py` to pin the existing CVS-176244 Windows skip policy to supported fixture `SetUp()` hooks.
- `c3bbe1568053b3d35a11ae6b9c31b7251fbdea90` — moves the existing CVS-176244 Mediapipe stress skip from `SetUpTestSuite()` into the two concrete fixture `SetUp()` hooks; no new test is excluded.
- `ca9b8efa49c4eedc5f1b1ce94e817b2870b5fd77` — moves the existing CVS-176244 C-API stress skips from `SetUpTestSuite()` into fixture `SetUp()` and preserves the old non-Windows base setup calls; no new test is excluded.
- Contract: `tests/python/test_windows_stress_harness_contract.py` now contains 5 tests.

The implementation diffs for `c3bbe156` + `ca9b8efa` are intentionally tiny: only the lifecycle location of the already-existing CVS-176244 skips changes.

## Session start

1. Fetch/re-resolve the branch and record actual `START_HEAD`.
2. Require `ca9b8efa...` to be an ancestor unless a newer fast-forward validation commit exists.
3. Confirm `git diff -- src/llm` is empty.
4. Clean only generated/instrumentation residue according to the established B-parity runbook. Preserve dumps/logs.
5. Use exact `rc1-parity`, Bazel 6.4.0, MSVC 14.44.35207, Python 3.12.10 and exact OpenVINO/GenAI 2026.4 RC2 pins. No upgrades/tuning.

## Gate 0 — contract + compilation

Run:

```powershell
python -m unittest tests.python.test_windows_stress_harness_contract
```

Require **5/5 PASS**.

Then build with the exact existing B-parity Windows build path. Compilation/linking must pass before runtime interpretation. If a test-harness helper has a mechanical C++ compile error, make the smallest correction preserving these invariants:

- no GoogleTest call from `runWindowsSafeAsyncWorker`;
- no legacy `triggerCApiAsyncInferenceInALoop` pointer used by the four async tests;
- owned `OVMS_Status*` objects are deleted in the new safe async path;
- the existing CVS-176244 Windows-sporadic fixtures skip from supported fixture `SetUp()` hooks, not `SetUpTestSuite()`;
- fixture/test names are unchanged;
- no new Windows exclusion is introduced.

Record binary identity after build.

## Gate 1 — prove existing CVS-176244 policy now works

Run these filters individually on Windows and record the GoogleTest disposition:

```powershell
.\bazel-bin\src\ovms_test.exe --gtest_filter=ConfigChangeStressTestSingleModel.ChangeToEmptyConfigInference
.\bazel-bin\src\ovms_test.exe --gtest_filter=StressCapiConfigChanges.AddNewVersionDuringPredictLoad
```

Both are already upstream-designated Windows sporadics by CVS-176244. Require exit 0 and **SKIPPED**, not PASS-through-execution and not CRASH.

When Mediapipe tests are compiled, also spot-check one `StressMediapipeChanges.*` and one `StressMediapipeQueueChanges.*` filter and require SKIPPED. Do not add any new skip.

## Gate 2 — exact non-skipped async blocker

Run `ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference` at least 20 times. Record every exit code.

This gate was clean before, so it is necessary but not sufficient.

## Gate 3 — non-skipped async ConfigChange family

Run all four async tests repeatedly, at least 20 family repetitions if practical:

- `ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference`
- `ConfigChangeStressTestAsync.ChangeToWrongShapeAsyncInference`
- `ConfigChangeStressTestAsync.ChangeToAutoShapeDuringAsyncInference`
- `ConfigChangeStressTestAsyncStartEmpty.ChangeToLoadedModelDuringAsyncInference`

Record pass/fail counts. These tests must execute; they are not part of CVS-176244 exclusion policy.

## Gate 4 — full-suite discriminator

Run the normal maintained Windows suite/gate environment, with inherited `OVMS_MODEL_REPOSITORY_PATH` sanitized and only the already-existing CVS-176244 policy now implemented through supported hooks.

Require **3 consecutive full-suite PASS runs** before claiming this hypothesis supported.

For each run, record skipped test names/count as well as passed/failed counts so we can verify no accidental exclusion broadening.

If any run still crashes:

- capture dump;
- record exact last running test;
- compare exception code, access type, target address, victim thread and module/offsets with prior dumps;
- mark this combined harness hypothesis REJECTED if the same signature survives;
- do not add a new exclusion.

If the suite progresses past the async blocker and exposes another test, distinguish an already-designated CVS-176244 fixture from a new defect. Do not silently broaden exclusions.

## Gate 5 — existing maintained gates

Require:

1. negative CLI 3/3 PASS;
2. `tests/windows/gemmamonster_rc2_ovms_test_gate.ps1` emits `GEMMAMONSTER_RC2_OVMS_TEST_GATE_PASS`;
3. `src/llm/**` remains untouched.

No package until all required gates are green.

## Required pushed report

Push a fast-forward evidence worklog containing:

- `START_HEAD` / `END_HEAD`;
- exact build command and binary identity;
- contract 5/5 result;
- compile result;
- CVS-176244 filter dispositions proving SKIPPED;
- exact async blocker 20x result;
- async-family repetition result;
- each full-suite result and skipped-test count/list;
- negative CLI result;
- maintainer gate result;
- any new dump signature;
- files changed during validation;
- package status;
- `READY_FOR_ACCEPTANCE` verdict.

If the patch fails the full-suite discriminator, leave the evidence explicit and do not pretend the bug moved merely because the test ran longer.
