# Gemmamonster Worklog Current State

Updated: 2026-09-12

## Current objective

Produce a successful Gemmamonster RC2 candidate by preserving the proven 2026.4 runtime/build substrate while restoring the advanced Gemma4 protocol semantics already present in the historical refit lineage.

## Accepted authorities

- FAST runtime control: immutable RC1 source `a43f644f10e55d741d5388e43580146c5203c196` and its frozen package/benchmark evidence. RC1 is NOT semantic source authority.
- 2026.4 source substrate: `9eb93f15fecb848d399f17c7a6a6626e5a1498d7`.
- Advanced 2026.5 semantic provenance: `5d995cfafdb2ec90578678aa15714dedebc843b8` plus later accepted `fde0762ba314dc5f6448726dfce7c533bad9a8a6` behavior.
- Implemented 2026.4 semantic refit core: `9a1626260614f68a6282b6799842d5152f0dcdff`.
- Operational carrier: `8a54214fed2a0cb01ad17159364996f8787a92fa`. Git comparison shows the 15 commits after `9a162626` do not modify `src/llm/**`; they are build/provenance/launcher/docs/test-envelope changes.
- Runtime dependency profile on operational carrier: OpenVINO `227c33757d1ef95d4da506d00686f923fdd2a535`, Tokenizers `a04accf6282d9b304214b492694b18c3979f667a`, GenAI `7ea2546852a382cd16bd22dea0cfad2db70ed744`, Windows GenAI package `2026.4.0.0rc2`.

## Active branch

`integration/gemmamonster-rc2-semantic-refit-20260912`

Created from exact operational carrier `8a54214fed2a0cb01ad17159364996f8787a92fa`.

No Gemma4 production source changes have been made on this branch yet.

## Accepted decisions

1. Do not repair RC1 source in-place.
2. Do not wholesale cherry-pick the 2026.5 migration/runtime.
3. Treat `main/8a54214` as a semantic/reference carrier, not proof that every file is independently optimal.
4. Prefer the already-implemented 2026.4 semantic refit over reimplementing P/R/S/G/T from scratch.
5. Reconstruct RC1 build mechanics separately; transfer build/package methodology only after forensic evidence.
6. Runtime PASS never transfers between source SHA/package identities.
7. `required`/named forced tool-choice instability is secondary/non-blocking for the primary NovaClaw `auto` agentic use case.
8. Session continuity (`servable.*`) remains a separate high-risk variable unless runtime evidence proves it is required for the target harness.

## Experiment matrix

### A: immutable fast control

- Source: `a43f644...`
- Existing package only; do not rebuild and silently call it the same control.
- Purpose: performance/runtime baseline and negative semantic reference.

### B: first RC2 refit candidate

- Source carrier: `8a54214...`
- Semantic core identity: `9a162626...`
- Build mechanics: MUST be derived from the pending RC1 build-provenance forensic report, not guessed.
- Runtime dependencies/model/launch/benchmark should match A as closely as evidence permits.

Primary comparison: isolate source semantics from build/runtime variables.

### Historical bisect only if B fails

Use the existing refit history as checkpoints instead of inventing a new implementation immediately:

- `9eb93f15...` pure 2026.4 substrate
- `16df6acd...` documented capital refit state
- later parser/generation/output fixes
- `e8c1220205a7aff6ce24ba9f1f6aca89c8b19b51` parser/grammar repair
- `9a162626...` final semantic core carried by main

## Acceptance gates for B

- source/contracts: PASS
- official Windows build/package: PASS
- package provenance/hashes/modules: PASS
- `tool_choice=auto`: PASS
- `tool_choice=none`: PASS
- streaming tool calls: PASS
- complex schema: PASS
- parallel distinct tools: PASS
- multi-turn tool-result continuation: PASS
- NovaClaw long-loop replay: PASS
- no “promise tool but no native tool frame” regression
- endurance target: at least 150 realistic requests without `CL_OUT_OF_RESOURCES`, `GPU_CONTEXT_FATAL`, executor quarantine, or restart
- performance: compare TTFT and pure decode against immutable RC1; do not use short constrained tool calls as sustained-speed baseline

## Waiting for

RC1 build-provenance forensic report reconstructing the actual environment, dependency acquisition, Bazel invocation, official build script invocation, package command, and runtime setup that produced the immutable RC1 binary.

## Next safe action

When the forensic report arrives, critically validate it against scripts/logs/artifacts. Then derive an exact B build recipe. Do not build from reconstructed folklore or current-environment defaults.
