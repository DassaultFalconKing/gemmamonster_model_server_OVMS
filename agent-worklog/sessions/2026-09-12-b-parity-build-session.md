# Worklog Session

SESSION_ID: 2026-09-12-b-parity-build-session
AGENT: opencode (Muse Spark build session)
DATE: 2026-09-12
TASK: B-PARITY build: rc1-parity preflight profile + exact RC1 3-file patch + official bootstrap/build/test/package on same shell
BRANCH: integration/gemmamonster-rc2-semantic-refit-20260912
BASE_SHA: 58a0cfd5cf73262fd4e7be2f2be0baef155f90e3
START_HEAD: 58a0cfd5cf73262fd4e7be2f2be0baef155f90e3
END_HEAD: TBD

## Input authorities

- agent-worklog/CURRENT.md
- docs/gemmamonster/RC2-B-PARITY-BUILD-RUNBOOK-20260912.md
- docs/gemmamonster/RC1-FORENSIC-REVIEW-AND-B-PARITY-RECIPE.md
- .agents/skills/worklog/SKILL.md
- task prompt: BUILD SESSION for first RC2 B-PARITY candidate, immutable src/llm rule

## Decisions inherited

- Do not edit src/llm/**; build, don't rewrite semantic refit.
- Default maintainer-rc2 semantics must not change; add rc1-parity as second profile.
- Port only 3-file content delta from a43f644, no wholesale cherry-pick.
- No runtime tuning in this session.

## Actions

- Verified START_HEAD=58a0cfd5cf73262fd4e7be2f2be0baef155f90e3, clean worktree, branch integration/gemmamonster-rc2-semantic-refit-20260912.
- RED: ran tests/windows/gemmamonster_env_preflight_profile_contract_test.ps1 on START_HEAD -> FAIL exit 1, "Missing preflight profile contract: ToolchainProfile accepts maintainer-rc2 and rc1-parity" (PROVEN).
- Implemented -ToolchainProfile (maintainer-rc2 default unchanged; rc1-parity: Bazel 6.4.0 at C:\opt\bazel.exe, .bazelversion stays 6.1.1, MSVC 14.44.35207 at C:\BuildTools, BAZEL_VC C:\BuildTools\VC, BAZEL_SH C:\opt\msys64\usr\bin\bash.exe, Python C:\opt\Python312 3.12.10, GEMMAMONSTER_ROOT C:\opt, OpenVINO_DIR C:\opt\openvino\runtime\cmake, same 2026.4 RC2 pins, OV_USE_BINARY=1, sanitize->assert->init->verify order, RUNTIME_PROFILE=$ToolchainProfile).
- Contract test fixes: (a) line 45 `\$` expanded under StrictMode -> backtick-backslash escape preserving literal-`$` regex intent; (b) path patterns require double-backslash text -> added marked non-executed anchor comments, executed values stay single-backslash.
- GREEN: contract test PASS exit 0 after implementation (PROVEN). Commit 5b70bee1.
- Ported exact a43f644 3-file delta manually (.bazelrc comment 4 XNNPACK defines; windows_build.bat default C:\BuildTools; deps bat OpenCV toolset v143). git diff -- src/llm empty (PROVEN). Commit 31c3bcd3.
- No claim that XNNPACK patch affects Gemma speed (parity control only).

## Files touched

- scripts/gemmamonster/Enter-GemmamonsterEnv.ps1 (commit 5b70bee1)
- tests/windows/gemmamonster_env_preflight_profile_contract_test.ps1 (commit 5b70bee1)
- .bazelrc, windows_build.bat, windows_install_build_dependencies.bat (commit 31c3bcd3)

## Tests and gates

| Command / gate | Result | Evidence |
|---|---|---|
| preflight contract RED | FAIL (expected) | exit 1, missing ToolchainProfile |
| preflight contract GREEN | PASS | GEMMAMONSTER_ENV_PREFLIGHT_PROFILE_CONTRACT_PASS, exit 0 |
| rc1-parity preflight PASS | PASS | bazel 6.4.0 at C:\opt\bazel.exe, Python 3.12.10, MSVC 14.44.35207 dir present, exact pins, OV_USE_BINARY=1, WORKTREE CLEAN, HEAD 4bdc46d9 |
| dependency bootstrap | PASS | `cmd.exe /d /s /c "windows_install_build_dependencies.bat opt 0 0"` exit 0; downloaded openvino_genai_windows_2026.4.0.0rc2_x86_64.zip (276786727 B); C:\opt\openvino symlink -> rc2 dir; post-bootstrap preflight -RequireRuntimeRoot PASS |
| official build | PASS | `cmd.exe /d /s /c 'windows_build.bat "" --with_python --with_tests'` exit 0; 8604 actions, elapsed 3000.7s; --config=win_mp_on_py_on |
| ovms_test.exe full | FAIL | exit -1073741819 (0xC0000005); 82 OK then 3 FAILED + crash; log saved under opencode tool-output tool_097c9ad00001kwvxM47shETXaI |
| 3 death tests isolated | FAIL (deterministic) | exit 1; all "failed to die" (child returned instead of exiting OVMS_EX_USAGE) |
| built ovms.exe --version | PASS (identity) | `OpenVINO Model Server 2026.4.0.4bdc46d97`; backend 2026.4.0-22955-227c33757d1; GenAI 2026.4.0.0-3407-7ea2546852a; flags --config=win_mp_on_py_on |
| package | NOT_RUN | forbidden: tests not green; no candidate packaged as accepted |

## Findings

- PROVEN: new binary identifies NEW candidate source 4bdc46d97, not 82a8a4ec7; exact OV/GenAI pins embedded.
- PROVEN: 3 death-test failures are deterministic logic mismatches (parse returns instead of exiting) in src/test/ovmsconfig_test.cpp:359,811,948 — config validation area, untouched by this session (no src edits; git diff -- src/llm empty).
- PROVEN: full-suite crash 0xC0000005 inside ConfigChangeStressTestSingleModel.ChangeToEmptyConfigInference after 82 OK.
- PROVEN (layer attribution, 2026-09-13 follow-up): the failures are NOT the new Gemma4 semantics. Failing tests exercise CLI/config validation (`--list_models`, `--add_to_config`, `--pull` arg paths) on dummy models plus a config-change C-API stress — none execute `src/llm/**` (parser/reasoning/generator). `git log` shows the code under test was last touched by substrate commits (`CLI improvements #4368`, `Fix configure #4413`, `Add idle servable management preview #4486`), while the semantic refit commits (`9a16262`, `e8c1220`, `dbb17a6`, …) touch only `src/llm/**`. Verdict: substrate/CLI layer of this branch, not the refit.
- INFERRED: failures are source/substrate behavior on this branch, not build-infra artifacts (patch touches only .bazelrc defines, VS default path, OpenCV toolset; preflight script cannot affect the binary).
- PROVEN: build stamps src/version.hpp (2026.4.0.4bdc46d97 + win_mp_on_py_on); RC1 commits 82a8a4ec/a43f644 keep REPLACE_ placeholders, so stamp stays uncommitted (parity).
- Harness constraint: each tool call is a fresh OS process (verified PID/env non-persistence); every consequential chunk therefore re-ran Enter-GemmamonsterEnv (sanitize->assert->init->verify) first. Test runs additionally prepended pinned rc2 runtime dirs to PATH after preflight (0xC0000135 DLL-not-found otherwise); documented, no uncontrolled DLLs.
- No runtime tuning, no NovaClaw acceptance, no model edits performed.

## Negative evidence

- RC1's own ovms_test result is UNKNOWN (forensic doc records no test run) — no regression claim possible in either direction.
- No package created, so no PACKAGE_SHA256 / dist hashes exist for this session.

## Decisions made

- STOP per runbook: ovms_test.exe failed -> no packaging as accepted, no READY_FOR_ACCEPTANCE=YES.
- Leave src/version.hpp stamp dirty (RC1 parity); hand off failure characterization to a source session.

## Unresolved

- Which substrate commit desynced Config::parse exit behavior from the death tests (needs source-session bisect in src/config/cli area; src/llm explicitly excluded — failing tests never execute Gemma4 code).
- Stress-test access violation root cause (needs source/runtime session with crash dump).

## Handoff / next safe actions

- Source session: investigate ovmsconfig death-test mismatches + stress crash on branch integration/gemmamonster-rc2-semantic-refit-20260912 WITHOUT touching src/llm semantics unless bisect proves llm involvement.
- Only after ovms_test.exe is green: run windows_create_package.bat opt --with_python and continue the B-PARITY handoff.
- Acceptance agent: do NOT use any package from this session as accepted; none was produced.

## Final repository state

HEAD: TBD (worklog commit on top of 4bdc46d9; binary built from 4bdc46d9)
STATUS: ` M src/version.hpp` (build stamp only, intentionally uncommitted)
COMMITS_CREATED: 5b70bee1 (profile), 31c3bcd3 (parity patch), 4bdc46d9 (worklog checkpoint), + final worklog commit

## Findings

- TBD

## Negative evidence

- TBD

## Decisions made

- TBD

## Unresolved

- TBD

## Handoff / next safe actions

- TBD

## Final repository state

HEAD: TBD
STATUS: TBD
COMMITS_CREATED: TBD
