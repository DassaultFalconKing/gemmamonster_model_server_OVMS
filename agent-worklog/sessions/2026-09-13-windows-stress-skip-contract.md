# Worklog Session

SESSION_ID: 2026-09-13-windows-stress-skip-contract
AGENT: ChatGPT
DATE: 2026-09-13
TASK: Harden the existing Windows stress-test policy without touching production inference or `src/llm/**`.
BRANCH: `integration/gemmamonster-rc2-semantic-refit-20260912`
START_HEAD: `df4e99d004c829e528aabe9bcdc6b888b7f9550c`
RUNTIME_VERDICT: UNVERIFIED
READY_FOR_ACCEPTANCE: NO

## Trigger

The async C-API stress-harness candidate (`5def2c3c`) removed GoogleTest assertions from the four non-skipped async worker paths and fixed owned C-API status handling in that path. Scope review then found that other stress helpers still contain GoogleTest assertions in worker threads and the legacy status macro.

Those helpers appeared protected by Windows `GTEST_SKIP()` policy, but prior RC2 runtime evidence showed `ConfigChangeStressTestSingleModel.ChangeToEmptyConfigInference` actually executing and crashing on Windows even though its source contained the supposed suite-level skip.

## External authority

- OVMS upstream commit `64c19a510ca8b855f3cff7e8111dd203f35b85d2` / PR #3771 introduced the CVS-176244 Windows-sporadic policy for `StressCapiConfigChanges`, `ConfigChangeStressTestSingleModel`, and `StressPipelineConfigChanges` by putting `GTEST_SKIP()` in `SetUpTestSuite()`.
- Current GoogleTest documentation documents `GTEST_SKIP()` for individual test bodies and fixture/environment `SetUp()`, including fixture-wide skipping from `SetUp()`. It does not document `SetUpTestSuite()` as a supported skip location.
- Therefore this session does not add a new Windows exclusion. It repairs the lifecycle hook used to implement an already accepted upstream Windows policy.

## TDD evidence

### RED

Commit `dacc6c948ad19b8d7a968604b81d030e48eb7d66` extends `tests/python/test_windows_stress_harness_contract.py` with two source contracts:

- C-API CVS-176244 fixtures must use `void SetUp() override` with `GTEST_SKIP()` and must not use `SetUpTestSuite()`.
- Mediapipe concrete CVS-176244 fixtures must use their own `SetUp()` hooks with `GTEST_SKIP()`, while the old pipeline-base `SetUpTestSuite()` hook is forbidden.

The predecessor source is structurally RED against this contract:

- `StressCapiConfigChanges`: `SetUpTestSuite()`, no fixture `SetUp()` skip.
- `ConfigChangeStressTestSingleModel`: `SetUpTestSuite()`, no fixture `SetUp()` skip.
- `StressPipelineConfigChanges`: `SetUpTestSuite()`.
- `StressMediapipeChanges` and `StressMediapipeQueueChanges`: own `SetUp()` but no Windows skip.

The isolated cloud environment could not execute the repository unittest because it has no GitHub/DNS checkout path; RED is source-proven, not claimed as an executed Windows/Python test result.

### GREEN source changes

`c3bbe1568053b3d35a11ae6b9c31b7251fbdea90`:

- removes the misleading `StressPipelineConfigChanges::SetUpTestSuite()` skip;
- adds the unchanged CVS-176244 Windows skip to `StressMediapipeChanges::SetUp()`;
- adds the unchanged CVS-176244 Windows skip to `StressMediapipeQueueChanges::SetUp()`;
- leaves all non-Windows setup code unchanged.

`ca9b8efa49c4eedc5f1b1ce94e817b2870b5fd77`:

- moves `StressCapiConfigChanges` CVS-176244 skip from `SetUpTestSuite()` to `SetUp()`;
- preserves non-Windows behavior by calling `ConfigChangeStressTest::SetUp()` after the Windows guard;
- moves `ConfigChangeStressTestSingleModel` CVS-176244 skip from `SetUpTestSuite()` to `SetUp()`;
- preserves non-Windows behavior by calling `ConfigChangeStressTestAsync::SetUp()` after the Windows guard.

Diff verification from `dacc6c9..ca9b8ef`:

- `src/test/c_api_stress_tests.cpp`: +4 / -2 only.
- `src/test/ensemble_config_change_stress.cpp`: +7 / -8 only.
- no test names changed;
- no production source changed;
- no `src/llm/**` changed.

## Updated handoff

`f2323dc5f8a1a92bcc007f7f3e84c7e4c819e6f6` updates `next-session-prompt.md` so Windows validation starts from `ca9b8efa...` or a strict fast-forward descendant and requires:

1. contract 5/5 PASS;
2. successful exact RC2 B-parity build;
3. direct filters proving existing CVS-176244 tests now report SKIPPED on Windows;
4. non-skipped async blocker 20x;
5. all four non-skipped async tests repeated;
6. three consecutive full-suite PASS runs with skipped-test counts recorded;
7. negative CLI 3/3 and maintainer Windows gate PASS;
8. no new exclusions, no package until all gates are green.

## Current interpretation

The combined test-harness hypothesis is stronger than the rejected production lifetime hypotheses because it explains both discriminators already observed:

- worker-thread crash location;
- clean isolated/family runs versus repeatable full-suite crash in a long-lived process.

It is still a hypothesis. Source correctness does not substitute for Windows runtime evidence.

## Forbidden conclusions

- Do not call the crash fixed before Windows validation.
- Do not package.
- Do not mark `READY_FOR_ACCEPTANCE=YES`.
- Do not add another Windows exclusion if the same crash survives.
- Do not touch `src/llm/**` for this substrate issue.
