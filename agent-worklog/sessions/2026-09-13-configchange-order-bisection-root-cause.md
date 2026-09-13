# Worklog Session

SESSION_ID: 2026-09-13-configchange-order-bisection-root-cause
AGENT: opencode (Muse Spark root-cause session)
DATE: 2026-09-13
TASK: ROOT-CAUSE Windows 0xC0000005 EXECUTE AV (RIP 0xA0/0xC8) in ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference via order bisection. Production fix forbidden before proven root cause.
BRANCH: `integration/gemmamonster-rc2-semantic-refit-20260912`
EXPECTED_START_HEAD: `9f9a9edf7e4e62ceebfd4b6fd50386379db7ec88`
LOCAL_HEAD_AT_ARRIVAL: `d7b797cb97e0f8bdb8304b28c90a892ea3fa6b55`
REMOTE_HEAD_AFTER_FETCH: `689bbd512bf180d567599baf7155eaf0d514e4ee`
START_HEAD (fast-forwarded): `689bbd512bf180d567599baf7155eaf0d514e4ee`
END_HEAD: `19f432ef3` + evidence worklog commit (this file; no production/src/llm changes)

## HEAD movement handling

- `git fetch --all --prune`: origin branch advanced `d7b797cb9..689bbd512` (14 commits); upstream `build-with-token` also moved (irrelevant).
- Read all 14 new commits before acting; no history rewritten, no чужой work destroyed.
- Local tree at arrival: single `M src/version.hpp` build stamp (PROJECT_VERSION 2026.4.0.59189254e, BAZEL_BUILD_FLAGS --config=win_mp_on_py_on). No RACE_* markers present (grep empty). Diff preserved at `C:\Users\testc\AppData\Local\Temp\opencode\version_stamp_d7b797c.diff`, then `git checkout -- src/version.hpp`.
- Fast-forwarded `d7b797cb9 -> 689bbd512` via `git pull --ff-only` (7 files, +607/-230). Tree clean after.
- New commits summary: `4362e9b3d` reverts rejected async guard experiment (inference_executor.hpp back to pre-experiment blob); `5def2c3c0` makes async C-API stress Windows-safe (308+/60-, only src/test/c_api_stress_tests.cpp); `a0d1b6d8c`/`20f8d23a5`/`4a6666200` pin/parse stress worker contract; `dacc6c948` RED contract for CVS-176244 skip lifecycle; `c3bbe1568`+`ca9b8efa4` move existing CVS-176244 skips from unsupported `SetUpTestSuite()` to supported fixture `SetUp()` (no new exclusions); `689bbd512` worklog; `f2323dc5f` handoff (next-session-prompt.md validation gates).
- `src/llm/**`: untouched (verified, diff empty).

## Environment (Phase 1 baseline)

- Binary path: `C:\git\gemmamonster-2026.4-unified-20260911\bazel-bin\src\ovms_test.exe`
- Binary at arrival: 42,066,944 B, 2026-09-13 01:57:10 — STALE (built from guard-fix era, predates 5def2c3/c3bbe/ca9b8ef + revert). Rebuild on 689bbd5 required before any reproduction claim.
- Bazel: 6.4.0 at C:\opt\bazel.exe; PowerShell 7.7.0-preview.4 (Core); OVMS_MODEL_REPOSITORY_PATH=C:\llm\models (exists; inherited value, sanitized per prior verdict — NOT modified).
- OpenVINO/GenAI pins: per CURRENT.md — OpenVINO 227c33757, Tokenizers a04accf62, GenAI 7ea254685, Win GenAI pkg 2026.4.0.0rc2; runtime at C:\opt\openvino\runtime. Exact built-binary OVMS --version: TBD after rebuild.
- Gate 0 contract: `python -m unittest tests.python.test_windows_stress_harness_contract` → 5/5 PASS (this session, pre-build).

## Proven history inherited (not re-proven from zero)

- F1: isolated target 5/5 PASS, family 3/3 PASS, full suite 4/4 CRASH → process-history contamination hypothesis.
- F2: H1 callback ordering REJECTED (signal-at-end still crashed, identical signature, 47/47 complete callbacks).
- F3: naive H2 unload-guard-dies-at-return REJECTED (guard moved into OV callback capture).
- F4: naive set_callback-self-replace REJECTED (OV copies m_callback to local shared_ptr before invoking).
- F5: src/llm/** not implicated.
- Guard-order fix (4fa90bae/bcf476ee) REJECTED: isolated 20/20 + family 20/20 PASS, full suite same-signature CRASH; reverted by 4362e9b3.
- New leading hypothesis (UNVERIFIED at session start): Windows test-harness defects — googletest assertions from 20 worker threads + ineffective SetUpTestSuite() skips; fixed in source by 5def2c3/c3bbe/ca9b8ef. Requires Windows runtime validation (next-session-prompt Gates 0-5).

## Baseline reproduction (Phase 2)

- Isolated target 5x (new binary, Windows-safe runner): 5/5 PASS, exit 0 (~300ms each). Original-crash baseline isolated: clean.
- ConfigChange family 3x (`ConfigChangeStressTestAsync.*:ConfigChangeStressTestAsyncStartEmpty.*:ConfigChangeStressTestSingleModel.*`): 4/4 executed async tests OK every run; SingleModel skipped-test → TearDown SEH 0xC0000005 → FAILED, exit 1, all 3 runs. Family exec path green; skip path red (see defect D1).
- Full suite run #1 (partial env — PATH only, no PYTHONHOME/PYTHONPATH): exit 3 (abort), 249 RUNs, died at ConfigReload.nonExistingModelPathInConfig setup; 32 test FAILEDs (13 CAPIInference path failures + 15 skip-TearDown SEHs + others); target #86 NOT reached?? — actually target ran OK (line 1155 RUN; suite continued past). Env-invalid for python tests (pyovms missing). DISCARDED as product signal except: proves suite passes #86 without worker AV.
- Controls with official env (PATH+PYTHONHOME=C:\opt\Python312+PYTHONPATH=bazel-out binding, OVMS_MODEL_REPOSITORY_PATH unset): ConfigReload.nonExistingConfigFile OK, ConfigReload.nonExistingModelPathInConfig OK (abort was env-cascade/contamination, not isolated defect); CAPIInference.Validation still FAILED isolated → pre-existing substrate defect D2 (Windows path rewrite gap), NOT contamination, NOT my change.
- Full suite run #2 (official env): exit 3 (abort), 1281/3152 RUNs, died in MediapipeStreamFlowAddTest.InferOnSleepingGraph area (OpenCV imdecode assert + "Mediapipe is not loaded yet"); 96 test FAILEDs across CAPIInference(13)/mediapipe/http/embeddings/listmodels families; 15 SEH all in TearDown (skip path D1); all 4 non-skipped async stress tests OK incl. target (308ms). Original worker-thread AV signature ABSENT — suite progressed 249→1281 tests past #86 in runs #1/#2 with no stress crash.
- STOP #1 status: original full-suite crash (worker AV RIP 0xA0/0xC8 at #86) NO LONGER REPRODUCES on pristine 689bbd5+compile-fix build. Old contamination hypothesis cannot be bisected (nothing to bisect); do not auto-continue it.

## DEFECT D1 (PROVEN, new, blocks Gate 1): skip-path TearDown AV

- Causal chain: `ca9b8efa` moved CVS-176244 GTEST_SKIP into fixture `SetUp()` → skipped tests never run `SetUpCAPIServerInstance` → members `ModelManager* manager; OVMS_Server* cserver;` (stress_test_utils.hpp:1102-1103, NO default init, only assigned at :1154) stay indeterminate → gtest still runs `ConfigChangeStressTest::TearDown()` (:1159) → `if (manager) manager->join()` reads garbage.
- Garbage non-null → SEH `0xc0000005 thrown in TearDown()`, FAILED, exit 1. Garbage null → clean `[ SKIPPED ]`.
- RED evidence (deterministic): single-filter SingleModel 1/1 SEH; single-filter StressCapi 1/1 SEH; family 3/3 SingleModel SEH.
- Full-suite run #2 shows the UB duality in one process: 16/17 StressCapi skips clean SKIPPED (null garbage luck), 1 SEH; SingleModel (#85, first skip) SEH; mediapipe skips 13 SEH / 2 SKIPPED. Total 15 SEH, all `thrown in TearDown()`.
- Old `SetUpTestSuite()` hook masked this: bodies executed (hook ineffective) so members were always initialized.

## D1 FIX (user-approved 2026-09-13, test-only, RED→GREEN proven)

- Fix (src/test/stress_test_utils.hpp, +3/-2 lines, no production/src/llm touch):
  1. `ModelManager* manager = nullptr; OVMS_Server* cserver = nullptr;` — existing `if (manager)` guard then yields deterministic SKIPPED; TearDown tail (fresh ServerNew + singleton shutdown-flag cycle) is the already-proven safe path from full-run #2's clean SKIPPED cases.
  2. `public:` on `ConfigChangeStressTestAsync::SetUp()` — compile fix required by ca9b8ef's explicit base-class call (C2248); access-specifier only, behavior-neutral (pre-authorized Gate 0 smallest correction).
- Rebuild: SUCCESS (4 actions incremental). Binary `bazel-bin\src\ovms_test.exe`, 42,072,064 B, 2026-09-13 15:33:23, SHA256 `07C870375924E04364FE259F9033541E6D0F4A280C7C518135D209565A6429A4`.
- GREEN validation (official env):
  - contract `tests.python.test_windows_stress_harness_contract`: 5/5 PASS.
  - single-filter SingleModel: SEH/FAILED exit 1 → `[ SKIPPED ]` exit 0.
  - single-filter StressCapi.AddNewVersionDuringPredictLoad: → `[ SKIPPED ]` exit 0.
  - single-filter StressMediapipeChanges/QueueChanges.AddGraphDuringPredictLoad: → `[ SKIPPED ]` exit 0 each (Gate 1 mediapipe spot checks).
  - family: exit 1 → exit 0 (4 PASSED + 1 SKIPPED).
  - isolated target 3/3 PASS exit 0 (post-fix regression check).
  - negative CLI 3/3 PASS exit 0.
  - full suite #4: exit 3 (same D3 abort, 1281 RUNs, same point), SEH 15/27 → 0, SKIPPED 83 clean, FAILED 96 → 81, target + 3 async siblings OK. D1 eliminated at full-suite scale; D2/D3 unchanged (out of scope).
- Causal proof of D1 mechanism additionally strengthened: SEH count varied 15 → 27 across runs #2/#3 (UB garbage), location always TearDown; after nullptr-init, exactly 0 across unit + full runs.

## DEFECT D2 (observed, out of scope): CAPIInference Windows path substrate

- `CAPIInference.*` (13 tests) fail isolated+full: config content base_path `/ovms/src/test/dummy` not rewritten → joined `.../src/test/configs//ovms/src/test/dummy` → "Directory does not exist" → model missing → wrong status codes. Deterministic, pre-existing (never observable before — suite always died at #85), unrelated to stress crash or this session's edits. Separate session material. NOT fixed here.

## DEFECT D3 (observed, out of scope): full-suite abort exit 3 in mediapipe area

- Run #2 aborts (MSVC abort() → exit 3) at 1281/3152 in MediapipeStreamFlowAddTest.InferOnSleepingGraph vicinity; run #1 aborted at #249 (env-cascade). Isolated ConfigReload controls pass. Needs procdump + separate triage (possible OpenCV/test-data substrate). STOP #6 territory for full-GREEN claims. NOT chased here.

- isolated target 5x: TBD
- ConfigChange family 3x: TBD
- full suite 2x: TBD
- STOP RULE: if full-suite crash no longer reproduces on pristine 689bbd5 build, STOP old hypothesis; do not write production fix; validate harness hypothesis per Gates instead.

## Bisection (Phase 3) — NOT APPLICABLE (STOP #1)

Order bisection requires a reproducing crash. Original signature (worker AV at #86) absent in 2/2 same-env full runs + 5 isolated + 3 family + 1 partial-env full run. No prefix table to build; constructing one against a non-crash would be theater. Historical constraint from old evidence: old-world family (with #85 executing) passed while full suite crashed → contaminator, if it ever existed as process state, was in tests 0..84 — but that world no longer exists (harness rewritten + #85 skipped). MINIMAL_CONTAMINATOR: NOT_FOUND.

## Full run #3 (same official env) — shape confirmed 2/2

- exit 3, 1281 RUNs, same abort point (MediapipeStreamFlowAddTest.InferOnSleepingGraph), target + 3 async siblings OK. SEH count varied 15 → 27 (UB garbage, always `thrown in TearDown()`), further confirming D1's uninitialized-memory mechanism.

| Candidate prefix | Target result | Runs | Crash rate |
|---|---|---:|---:|
| TBD | TBD | TBD | TBD |

## Minimal contaminator — TBD (NOT_FOUND so far)

## Mechanism — TBD (NOT_PROVEN)

## RED regression / fix / validation — NONE (forbidden before proof)

## Commits in this session

- `19f432ef3` fix(test): make Windows CVS-176244 skips skip-safe (src/test/stress_test_utils.hpp +3/-2 only).
- evidence worklog commit (this file + CURRENT.md factual note) follows; `src/version.hpp` build stamp left dirty uncommitted per RC1 mechanics.
- No production fix, no src/llm/** touch (diff verified empty), no new exclusions, no sleeps/retries/timeout changes.

## Remaining uncertainty

- Original worker-thread AV (RIP 0xA0/0xC8 at #86): GONE, mechanism unattributed — cannot distinguish (a) #85-execution contaminator removed by effective skip, (b) Windows-safe runner rewrite, (c) interaction of both. Bisection impossible post-hoc. If it ever returns, bisect tests 0..84 against target on the reproducing build.
- D3 abort (exit 3, mediapipe area): un-triaged; needs procdump + separate session. Blocks any full-GREEN claim.
- D2 CAPIInference path failures: deterministic substrate; needs Windows path-rewrite fix in c_api_tests fixture area; separate session.
- Full suite never reached tests 1282..3152 on this host in any run (aborts at mediapipe #1281); downstream suites uncharacterized.
- Package: NO (full suite red). READY_FOR_ACCEPTANCE: NO.

## Build on current HEAD (Phase 1 completion)

- First `windows_build.bat "" --with_python --with_tests` FAILED at `src/test/c_api_stress_tests.cpp(342)`: `error C2248: 'ConfigChangeStressTestAsync::SetUp': cannot access private member` (declared stress_test_utils.hpp:1962). The `ca9b8efa` skip move added an explicit `ConfigChangeStressTestAsync::SetUp()` call from derived `ConfigChangeStressTestSingleModel::SetUp()`, but base `SetUp()` is private (class default) while `ConfigChangeStressTest::SetUp()` is public.
- Mechanical test-only fix (pre-authorized by next-session-prompt Gate 0, smallest correction, no behavior change on any platform — access specifier only): +1 line `public:` in `ConfigChangeStressTestAsync` (stress_test_utils.hpp:1962). Fixture/test names unchanged, no new exclusion, no production touch, no src/llm touch. Alternative (duplicate `SetUpCAPIServerInstance(stressTestOneDummyConfig)` in the .cpp) rejected as larger and behavior-risky.
- Rebuild: SUCCESS (83s incremental, 14 actions). Binary: `bazel-bin\src\ovms_test.exe`, 42,072,064 B, 2026-09-13 14:53:30, SHA256 `47D3D5FFA3E3B0688D8B6BAC235A1E88F1F0348CE36893A5BDF82349B2CC5527`.
- Tree: `M src/test/stress_test_utils.hpp` (+1 line fix, uncommitted), `M src/version.hpp` (build stamp mechanics, uncommitted, will not commit), `?? this worklog`.
- Test-run env (0xC0000135 DLL-not-found without it): prepend `C:\opt\openvino\runtime\bin\intel64\Release;C:\opt\openvino\runtime\3rdparty\tbb\bin;C:\opt\opencv_4.14.0\x64\vc16\bin` to PATH. Shell-inherited `openvino_toolkit_windows_2026.2.1` PATH entry is a different OpenVINO line — must stay shadowed by C:\opt\openvino.
- Old-binary ordered list (stale binary, names unchanged per worklog so positions indicative): 3152 tests; target `ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference` at index 86; sole family predecessor at 85 is `ConfigChangeStressTestSingleModel.ChangeToEmptyConfigInference` (now Windows-SKIP via SetUp). Fresh list from new binary: TBD below.
