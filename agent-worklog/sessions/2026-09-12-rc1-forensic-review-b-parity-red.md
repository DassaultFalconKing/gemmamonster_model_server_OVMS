# Worklog Session

SESSION_ID: 2026-09-12-rc1-forensic-review-b-parity-red
AGENT: ChatGPT GPT-5.6 Sol
DATE: 2026-09-12
TASK: Critically review RC1 build forensic evidence, correct provenance, define B-PARITY/B-CLEAN experiment split, and establish RED contract for RC1-parity preflight.
BRANCH: integration/gemmamonster-rc2-semantic-refit-20260912
START_HEAD: 49e720b7fba42f14c82a7585237d5458a12d8763
END_HEAD_AT_LOG_CREATION: 44cb6b2d4d33b6936c0997d91dc24ace7115e0ae

## Inputs

- forensic report commit `29ed19802aa095dc5277bac8f0dc8d2f785378ba`
- immutable RC1 branch `Gemmamonster-2026.4-RC1`
- RC1 build carrier commit `a43f644f10e55d741d5388e43580146c5203c196`
- embedded binary version `2026.4.0.82a8a4ec7`
- active RC2 branch from `8a54214fed2a0cb01ad17159364996f8787a92fa`

## Verified Git findings

- Full object for embedded binary prefix exists: `82a8a4ec72928abad78f9180e67fbb91563e1c08`.
- `a43f644` is exactly one commit after `82a8a4ec`.
- `82a8a4ec -> a43f644` changes only `.bazelrc`, `windows_build.bat`, and `windows_install_build_dependencies.bat`.
- No Gemma4 production source changes occur in that commit.
- `a43f644` was created after the immutable RC1 binary timestamp recorded by the operator.
- Strongest reconstruction: build-time HEAD `82a8a4ec` with the three build-only worktree modifications later committed as `a43f644`.

## Forensic report corrections

- FALSE: `82a8a4ec7` is a fragment of `a43f644...`.
- INCOMPLETE: report calls package provenance complete while `ovms.zip` is explicitly un-hashed.
- RECONSTRUCTED, not exact: historical command sequence.
- STRONGLY SUPPORTED but not direct shell capture: `OV_USE_BINARY=1`.
- SPECULATIVE: XNNPACK patch as explanation for RC1 GPU decode speed.
- INCONSISTENT/UNRESOLVED: report's `C:/g54r2_new/...` external-cache claim versus reconstructed `windows_build.bat "" ...` selecting `C:\opt` output root.

## Decisions

- Do not rewrite immutable RC1 history; append an erratum in RC2 evidence.
- Split next experiment:
  - B-PARITY: same historical shared-root/toolchain mechanics as closely as possible, advanced refit source.
  - B-CLEAN: isolated reproducible dependency root only after B-PARITY result.
- Current canonical preflight cannot be used unchanged for B-PARITY because it asserts active Bazel 6.1.1 and `C:\g54r2`, while RC1 parity requires active Bazel 6.4.0 and `C:\opt`.
- Add a named `rc1-parity` profile; keep existing `maintainer-rc2` behavior as default.
- Port only the exact three build-only hunks from `a43f644`; do not replace whole build files with older blobs.

## Files added/updated

- `docs/gemmamonster/RC1-FORENSIC-REVIEW-AND-B-PARITY-RECIPE.md`
- `agent-worklog/CURRENT.md`
- `tests/windows/gemmamonster_env_preflight_profile_contract_test.ps1`
- this session log

## Test state

`tests/windows/gemmamonster_env_preflight_profile_contract_test.ps1` was written before implementation.

Expected current result on Windows: RED, because `Enter-GemmamonsterEnv.ps1` does not yet expose `-ToolchainProfile rc1-parity`.

Actual execution in this ChatGPT environment: NOT_RUN. No Windows PowerShell host is exposed here.

Do not call this test RED-proven until a Windows agent executes it and captures the expected failure.

## Next safe local action

1. Fetch/switch `integration/gemmamonster-rc2-semantic-refit-20260912`.
2. Run `tests\windows\gemmamonster_env_preflight_profile_contract_test.ps1` and capture expected RED.
3. Implement minimal `rc1-parity` profile in `Enter-GemmamonsterEnv.ps1` while preserving default `maintainer-rc2` behavior.
4. Re-run contract and capture GREEN.
5. Cherry-pick `a43f644...`; inspect that only the three intended build hunks apply.
6. Re-run profile contract and static/source gates.
7. Only then run the B-PARITY dependency/build/package recipe from `RC1-FORENSIC-REVIEW-AND-B-PARITY-RECIPE.md`.

No Gemma4 production-source file was edited in this session.
