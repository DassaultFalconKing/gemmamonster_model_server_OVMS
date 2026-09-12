# Gemmamonster Worklog Current State

Updated: 2026-09-12

## Current objective

Produce a successful Gemmamonster RC2 candidate by preserving the proven 2026.4 runtime/dependency line while restoring the advanced Gemma4 protocol semantics already present in the historical refit lineage, then prove behavior and performance against immutable RC1 with a controlled A/B.

## Accepted authorities

- FAST runtime control: immutable RC1 package/benchmark evidence. RC1 is NOT semantic source authority.
- RC1 post-build clean carrier: `a43f644f10e55d741d5388e43580146c5203c196`.
- RC1 build-time Git HEAD, established by embedded OVMS version: `82a8a4ec72928abad78f9180e67fbb91563e1c08`.
- Strongest RC1 build provenance reconstruction: HEAD `82a8a4ec...` plus the three build-only working-tree changes later committed as `a43f644...`. This is STRONGLY_INFERRED, not exact shell-history proof.
- 2026.4 source substrate: `9eb93f15fecb848d399f17c7a6a6626e5a1498d7`.
- Advanced 2026.5 semantic provenance: `5d995cfafdb2ec90578678aa15714dedebc843b8` plus later accepted `fde0762ba314dc5f6448726dfce7c533bad9a8a6` behavior.
- Implemented 2026.4 semantic refit core: `9a1626260614f68a6282b6799842d5152f0dcdff`.
- Operational carrier: `8a54214fed2a0cb01ad17159364996f8787a92fa`. The 15 commits after `9a162626` do not modify `src/llm/**`; they are build/provenance/launcher/docs/test-envelope changes.
- Runtime dependency profile: OpenVINO `227c33757d1ef95d4da506d00686f923fdd2a535`, Tokenizers `a04accf6282d9b304214b492694b18c3979f667a`, GenAI `7ea2546852a382cd16bd22dea0cfad2db70ed744`, Windows GenAI package `2026.4.0.0rc2`.

## Active branch

`integration/gemmamonster-rc2-semantic-refit-20260912`

Created from exact operational carrier `8a54214fed2a0cb01ad17159364996f8787a92fa`.

No Gemma4 production-source changes have been made on this branch yet.

## Accepted decisions

1. Do not repair RC1 source in-place.
2. Do not wholesale cherry-pick the 2026.5 migration/runtime.
3. Treat `main/8a54214` as a semantic/reference carrier, not proof that every file is independently optimal.
4. Prefer the already-implemented 2026.4 semantic refit over reimplementing P/R/S/G/T from scratch.
5. RC1 forensic report `29ed198...` is evidence-bearing input, not unquestioned authority.
6. Do not repeat the report's false claim that `82a8a4ec7` is a fragment of `a43f644`; they are separate consecutive commits.
7. Historical immutable RC1 refs are not rewritten; provenance corrections are appended in later worklogs/reports.
8. Split the next experiment into `B-PARITY` and `B-CLEAN` so source semantics and dependency-root reproducibility are not changed simultaneously.
9. Runtime PASS never transfers between source SHA/package identities.
10. `required`/named forced tool-choice instability is secondary/non-blocking for the primary NovaClaw `auto` agentic use case.
11. Session continuity (`servable.*`) remains a separate high-risk variable unless runtime evidence proves it is required.

## Experiment matrix

### A: immutable fast control

- Existing immutable RC1 package only. Do not rebuild and silently call it the same control.
- Embedded build-time source identity: `82a8a4ec72928abad78f9180e67fbb91563e1c08`.
- Post-build clean build-patch carrier: `a43f644f10e55d741d5388e43580146c5203c196`.
- Purpose: performance/runtime baseline and negative semantic reference.

### B-PARITY: first RC2 causal candidate

- Source carrier: active RC2 branch descended from `8a54214...`.
- Semantic core identity: `9a162626...`.
- Runtime dependencies: same 2026.4 RC2 line as A.
- Target toolchain/build mechanics: Bazel 6.4.0 at `C:\opt`, Python 3.12.10, MSVC 14.44.35207, official Windows build/package scripts, RC1 three-hunk build-infrastructure parity patch.
- Purpose: change source semantics while holding build/runtime mechanics as constant as evidence permits.

### B-CLEAN: reproducibility candidate

Only after B-PARITY results are known. Build the same proven semantic source using a fresh isolated dependency root and full provenance/hash/module gates.

### Historical bisect only if B-PARITY fails semantically

- `9eb93f15...` pure 2026.4 substrate
- `16df6acd...` documented capital refit state
- later parser/generation/output fixes
- `e8c1220205a7aff6ce24ba9f1f6aca89c8b19b51` parser/grammar repair
- `9a162626...` final semantic core carried by main

## Current blocker before build

Existing `Enter-GemmamonsterEnv.ps1` hard-pins Bazel 6.1.1 and isolated `C:\g54r2`. RC1 parity requires Bazel 6.4.0 and shared `C:\opt` build/runtime root.

Do not weaken or bypass preflight. Add an explicit `rc1-parity` toolchain profile while preserving current default behavior.

Then port only the exact three build-only hunks from `a43f644` and verify no unrelated newer build-script behavior is lost.

## Acceptance gates for B-PARITY

- sanitized `rc1-parity` environment preflight: PASS
- build-only parity patch: exact/limited to intended hunks
- source/contracts: PASS
- official Windows build/package: PASS
- full package provenance/hashes/modules: PASS
- `tool_choice=auto`: PASS
- `tool_choice=none`: PASS
- streaming tool calls: PASS
- complex schema: PASS
- parallel distinct tools: PASS
- multi-turn tool-result continuation: PASS
- NovaClaw raw request -> raw OVMS response/SSE -> harness interpretation replay: PASS
- no “promise tool but no native tool frame” regression
- endurance target: at least 150 realistic requests without `CL_OUT_OF_RESOURCES`, `GPU_CONTEXT_FATAL`, executor quarantine, or restart
- performance: compare TTFT and pure decode against immutable RC1; short constrained calls are not sustained-speed baseline

## New evidence / report review

- Forensic report commit: `29ed19802aa095dc5277bac8f0dc8d2f785378ba`.
- Review/recipe: `docs/gemmamonster/RC1-FORENSIC-REVIEW-AND-B-PARITY-RECIPE.md`.
- The report's command sequence remains reconstructed, not exact shell-history proof.
- `ovms.zip` was not hashed in the forensic report, so package identity is incomplete there.
- XNNPACK performance impact is unproven; preserve it for parity, not because it is accepted as the speed cause.

## Next safe action

Implement and test the `rc1-parity` preflight profile first. Then apply/cherry-pick the exact build-only `a43f644` patch, inspect the resulting three-file diff, and only after those gates are green run B-PARITY build/package on the target Windows host.
