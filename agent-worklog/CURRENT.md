# Gemmamonster Worklog Current State

Updated: 2026-09-13

## Current objective

Produce a successful Gemmamonster RC2 by building the existing advanced Gemma4 semantic refit on the proven 2026.4 runtime/dependency line, first as a causal RC1-parity package and then, if green, as a clean reproducible package.

## Accepted authorities

- FAST runtime control: immutable RC1 package/benchmark evidence; RC1 is NOT semantic source authority.
- RC1 embedded build-time source identity: `82a8a4ec72928abad78f9180e67fbb91563e1c08`.
- RC1 post-build clean three-file patch carrier: `a43f644f10e55d741d5388e43580146c5203c196`.
- Strongest RC1 build reconstruction: HEAD `82a8a4ec...` plus the three dirty build-file changes later committed as `a43f644...`; STRONGLY_INFERRED, not exact shell-history proof.
- 2026.4 source substrate: `9eb93f15fecb848d399f17c7a6a6626e5a1498d7`.
- Advanced 2026.5 semantic provenance: `5d995cfafdb2ec90578678aa15714dedebc843b8` plus later accepted `fde0762ba314dc5f6448726dfce7c533bad9a8a6` behavior.
- Implemented 2026.4 semantic refit core: `9a1626260614f68a6282b6799842d5152f0dcdff`.
- Operational carrier: `8a54214fed2a0cb01ad17159364996f8787a92fa`; the 15 later commits do not modify `src/llm/**`.
- Runtime dependencies: OpenVINO `227c33757d1ef95d4da506d00686f923fdd2a535`, Tokenizers `a04accf6282d9b304214b492694b18c3979f667a`, GenAI `7ea2546852a382cd16bd22dea0cfad2db70ed744`, Windows GenAI package `2026.4.0.0rc2`.

## Active branch

`integration/gemmamonster-rc2-semantic-refit-20260912`

Created from exact operational carrier `8a54214fed2a0cb01ad17159364996f8787a92fa`.

No Gemma4 production-source changes have been made on this branch yet.

## Accepted decisions

1. Do not repair RC1 source in-place.
2. Do not wholesale cherry-pick the 2026.5 migration/runtime.
3. Prefer the already-implemented 2026.4 semantic refit over reimplementing P/R/S/G/T from scratch.
4. Preserve the RC1 three-file build patch for parity/build hygiene without claiming it caused decode speed.
5. Split work into `B-PARITY` then `B-CLEAN`.
6. Build and runtime tuning are separate causal stages; the build agent must not tune KV/scheduler/prefix cache.
7. Runtime tuning must reuse one immutable package and a fresh process per profile.
8. `required`/named forced instability is secondary/non-blocking for the primary NovaClaw `auto` use case, but must be recorded separately.
9. Session continuity remains a separate high-risk variable unless runtime evidence proves it required.
10. Runtime PASS never transfers across source/package/driver identities.

## Pinned execution documents

- `docs/gemmamonster/RC2-B-PARITY-BUILD-RUNBOOK-20260912.md`
- `docs/gemmamonster/RC2-B-PARITY-ACCEPTANCE-RUNBOOK-20260912.md`
- `docs/gemmamonster/RC1-FORENSIC-REVIEW-AND-B-PARITY-RECIPE.md`

## Build plan: B-PARITY

- active Bazel: 6.4.0 at `C:\opt\bazel.exe` while repository `.bazelversion` remains 6.1.1;
- Python 3.12.10;
- MSVC 14.44.35207 at `C:\BuildTools`;
- `OV_USE_BINARY=1` and exact 2026.4 RC2 pins;
- implement the already-specified `rc1-parity` preflight profile while preserving default `maintainer-rc2`;
- run the preflight contract RED/implementation/GREEN on the Windows host;
- port only the `.bazelrc`, `windows_build.bat`, and `windows_install_build_dependencies.bat` hunks from `a43f644...`;
- official dependency/bootstrap/build/package flow;
- build with Python and tests;
- run `ovms_test.exe`;
- full SHA256 for `ovms.zip`, `ovms.exe` and key runtime DLLs;
- no runtime tuning in the build session.

## Acceptance/tuning ladder on one immutable B-PARITY package

P0: exact semantic/runtime baseline, no new tuning.

P1: P0 + `--plugin_config '{"KV_CACHE_PRECISION":"u4"}'`.

P2: P1 + `--max_num_batched_tokens 4096`.

P3: P1 + `--max_num_batched_tokens 8192`.

P4: best safe P1/P2/P3 + `--enable_prefix_caching true`, with repeated-prefix stress at ~1k/8k/16k/32k and zero-token output as a hard failure.

P5 optional: best safe profile, `dynamic_split_fuse=true` versus `false`; DSF=false only when `max_num_batched_tokens` can contain the full tested prompt.

Keep GPU driver `32.0.101.8991` through this ladder. Driver changes are a later independent experiment.

The exact pinned OpenVINO line contains Intel GPU U4 Paged Attention KV-cache support. The exact OVMS line routes generic `plugin_config` to the continuous-batching/VLM pipeline, so U4 is a runtime profile variable, not a rebuild variable.

## Required tests

Cheap/source first:
- `tests/windows/gemmamonster_env_preflight_profile_contract_test.ps1`
- `//src/test/llm/gemma4_fast:gemma4_parser_contract_test` (parser + reasoning refit + recovery contracts)
- `//src/test/llm/gemma4_overlay:gemma4_chat_template_overlay_contract_test`
- `//src/test/llm/gemma4_overlay:gemma4_google_jinja_contract_test`
- complete built `bazel-bin\src\ovms_test.exe` for the exact final build.

Runtime layers:
- package identity/self-test;
- text and `tool_choice=none`;
- obvious auto tool call;
- tool-result continuation;
- complex/nested schema;
- parallel distinct tools;
- streaming raw SSE;
- NovaClaw 20–50 turn agent loop with raw request -> raw OVMS -> harness interpretation capture;
- benchmark, context ladder, and >=150-request endurance.

Promotion hard failures include promise-without-native-tool-call, GPU fatal/quarantine/restart, and selected prefix-cache profile producing reproducible zero-token completions.

## B-PARITY build session outcome (2026-09-12/13)

Session: `agent-worklog/sessions/2026-09-12-b-parity-build-session.md` (PROVEN).

- START_HEAD `58a0cfd5cf73262fd4e7be2f2be0baef155f90e3`, clean tree at start.
- Commits on `integration/gemmamonster-rc2-semantic-refit-20260912`: `5b70bee1` (rc1-parity preflight profile, contract test GREEN), `31c3bcd3` (exact a43f644 3-file parity patch, `src/llm` diff empty), worklog checkpoints.
- BUILD_HEAD `4bdc46d9` (docs-only worklog checkpoint on top of parity; binary-affecting source = `31c3bcd3` tree plus build-stamped `src/version.hpp` left dirty per RC1 mechanics).
- Preflight `rc1-parity` PASS: Bazel 6.4.0 at `C:\opt\bazel.exe`, Python 3.12.10, MSVC 14.44.35207, exact 2026.4 RC2 pins, `OV_USE_BINARY=1`.
- Bootstrap PASS: exact `openvino_genai_windows_2026.4.0.0rc2_x86_64.zip` (276786727 B), `C:\opt\openvino` -> rc2 dir.
- Official build PASS: 8604 actions, `--config=win_mp_on_py_on`.
- Built `ovms.exe --version`: `2026.4.0.4bdc46d97` (NEW source, not `82a8a4ec7`); backend pins exact.
- `ovms_test.exe` FAIL: exit 0xC0000005; 82 OK, 3 deterministic death-test "failed to die" (`ovmsconfig_test.cpp:359,811,948`), crash in `ConfigChangeStressTestSingleModel.ChangeToEmptyConfigInference`. No src edits in session; root cause unresolved, handed to source session.
- Layer attribution (PROVEN): failures are NOT the new Gemma4 semantics (`src/llm/**` never executed by failing tests). CORRECTION: the 3 death-test failures were environmental, not stale tests — host USER env `OVMS_MODEL_REPOSITORY_PATH=C:\llm\models` (intentional OVMS default) made those inputs valid; maintainer gate (`tests/windows/gemmamonster_rc2_ovms_test_gate.ps1`, commits a3957461/7fcb024f) clears it and all 3 PASS. Full suite minus upstream-known-sporadic `ChangeToEmptyConfigInference` (CVS-176244) still crashes 0xC0000005 in sibling `ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference` — same stress family, root cause open. No package; READY_FOR_ACCEPTANCE=NO.
- NO package produced (tests not green). READY_FOR_ACCEPTANCE=NO.

## Next safe action

Root-cause/validation chain (2026-09-13): `agent-worklog/sessions/2026-09-13-stress-crash-root-cause.md` proved the full-suite-only worker-thread AV and rejected callback signal ordering. The deterministic async guard-order experiment (`4fa90bae3`/`bcf476ee6`) then built cleanly but was FALSIFIED by the same full-suite crash signature and was reverted in `4362e9b3d11e2dbde7049c0aa5fd086f4dd98c21`; current `src/inference_executor.hpp` is back to the pre-experiment source. The active hypothesis is now a Windows test-harness defect: legacy async stress workers call GoogleTest assertions concurrently from 20 worker threads, which GoogleTest documents as unsupported on Windows, and the legacy status macro leaks owned `OVMS_Status*` objects on successful calls. Test-only fix `5def2c3c0b12a31243a68e6c2d62f286cc2ea63d` routes worker failures through thread-safe state, moves assertions to the main thread after join, consumes/deletes C-API statuses, and updates all four async ConfigChange tests; contract is `tests/python/test_windows_stress_harness_contract.py` (`20f8d23a`). This hypothesis is NOT runtime-proven yet. Next required action is exact RC2 Windows validation from `next-session-prompt.md`: contract 3/3, build, blocker 20x, async family repeated, >=3 consecutive full-suite PASS runs, CLI 3/3, maintainer gate PASS. No new exclusions, no package, READY_FOR_ACCEPTANCE=NO until those gates are green. `src/llm/**` remains untouched.

## Order-bisection root-cause session outcome (2026-09-13)

Session: `agent-worklog/sessions/2026-09-13-configchange-order-bisection-root-cause.md` (PROVEN where marked).

- START_HEAD `689bbd512` (fast-forwarded from `d7b797cb9`; 14 commits read, none destroyed). HEAD now includes reverted guard experiment (`4362e9b3`), Windows-safe async stress (`5def2c3`), and CVS-176244 skip-lifecycle moves (`c3bbe15`/`ca9b8ef`).
- Original worker-thread AV at `ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference` DOES NOT REPRODUCE on current HEAD: isolated 5/5 PASS, family exec 4/4 PASS, full suite 3 runs all pass #86 (2/2 same-env runs reach 1281/3152). Order bisection has no target; STOP #1 applied, no production fix, MINIMAL_CONTAMINATOR=NOT_FOUND.
- PROVEN new defect D1: `SetUp()`-level skip left `manager`/`cserver` uninitialized → TearDown SEH 0xC0000005 (RED isolated 5/5; 15–27 SEH in full runs, always in TearDown). Fixed test-only in `19f432ef3` (`nullptr` init + `public:` compile fix, RED→GREEN: skips exit 0, family exit 0, full-suite SEH 15/27→0, 83 clean SKIPPED).
- Observed, out of scope: D2 `CAPIInference.*` Windows path substrate failures (isolated RED, pre-existing); D3 full-suite abort exit 3 at `MediapipeStreamFlowAddTest.InferOnSleepingGraph` area (1281/3152, 2/2 deterministic).
- No package; READY_FOR_ACCEPTANCE=NO.