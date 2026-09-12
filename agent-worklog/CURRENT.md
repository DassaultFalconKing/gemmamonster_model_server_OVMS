# Gemmamonster Worklog Current State

Updated: 2026-09-12

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

## Next safe action

Build agent: follow `RC2-B-PARITY-BUILD-RUNBOOK-20260912.md` exactly and return one immutable package identity. Do not tune runtime.

Test agent, after package exists: follow `RC2-B-PARITY-ACCEPTANCE-RUNBOOK-20260912.md`, establish P0 correctness first, then profile P1→P5 one variable at a time.