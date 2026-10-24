# CIB2 Pack V2 N1/N2/N3 handoff: current-compile receipt and safety controls

Date: 2026-10-24. Source-only audit checkpoint. This is NOT native acceptance.

## Parallel ownership

- Local Windows operator owns matching OpenVINO 2026.4 CPU plugin build (existing work item 1) and subsequent actual-model pack-build / GPU parity (work item 3).
- This isolated OVMS branch implements work item 2: fail-closed current-compile native Pack build receipts. It is based on OVMS PR #29 at `13fabc185f90febdb0025f78acf82240ea286ab7`.
- OpenVINO sibling branch `feature/cib2-n2-n3-safety-20261024` is based on PR #10 at `b7105471c42fb8f33d607891651e67872697d15e`. It implements the matching native receipt emitter and N2/N3 safety primitives/tests for work item 4.
- Do not merge either branch or mark acceptance until Windows compilation, tests and evidence are reviewed. Do not touch dirty `mlas` / `onednn` submodules or untracked build-root files.

## Work item 2: pack-build false-PASS prevention

The old `checkCib2PackBuild` counted any `*.pack` in the destination directory, including unrelated stale packs. The new OVMS `src/server.cpp` creates an exclusive, per-invocation `.cib2-build-<128-bit nonce>/compiled-layers.receipt` inside the pack directory, initializes `CIB2_COMPILED_PACKS_V1`, and sets `OV_GPU_MOE_OTD_BUILD_RECEIPT` before the servable manager compiles the model.

The matching OpenVINO `expert_weight_providers.cpp` emits `LAYER <16-lowerhex-native-key> built|reused` only after a compiled eligible offload MoE layer has built/reused its native pack, `PackLayout::open` has succeeded, and the serving file handle has passed its metadata snapshot check. The emitter checks that the receipt is a regular file in the active pack directory and serializes parallel compile writes.

OVMS rejects an empty or malformed receipt, zero eligible compiled layers, non-existent/empty/symlinked referenced pack files and unavailable servables. It reports unique layer keys and built/reused counts. Multiple compilations of an identical native key are allowed but counted once. This is *current-compile attribution*, not a replacement for the independent full-payload V1 verifier and V2 generation seal.

**Dependency:** the OVMS and OpenVINO changes must be built together. An old GPU plugin intentionally yields zero receipt entries and fails closed. Native GPU pack eligibility still requires actual compiled MOECompressed/GEMM3 with nine routed tensor slices.

## Work item 4: N2/N3 code delivered, runtime wiring not yet accepted

OpenVINO adds `moe_otd_gpu_event_adapter.hpp`: a strong `cldnn::event::ptr` completion owner that rejects null events, designed for the existing `GpuSlotLeaseLedger`. Host controls now test stale generations, no-event refusal, pending readers, event-owner lifetime and release after completion.

The `UmaAdmissionLedger` adds all-or-nothing `reserve_batch` for model weights/KV/workspace/staging cohorts, `observe` for conservative updated OS/WDDM constraints, `gpu_reserved`, and a process-wide exact-16-hex-LUID keyed `GlobalUmaAdmission` registry. Windows `global_windows_uma_ledger` obtains exact-adapter OS/WDDM samples and returns the shared ledger. Host controls exercise cross-owner reservations, failed-batch atomicity, stale-budget rejection and invalid LUID.

**Do not call N2/N3 complete.** N2 still requires wiring *all* GEMM/GEMV/grouped-prefill consumer terminal events and slot generations to the provider; current `SynchronousExecutionGate` + `drain_or_fail_stop` remains mandatory. N3 still requires real model/KV/workspace/OTD allocator owners to acquire/release tickets before allocation and to reconcile actual WDDM/OS usage. The ledger alone does not intercept allocations. N4 prefetch remains OFF; Path B `usm_host` remains OFF.

## Local Windows validation sequence

1. Preserve exact current Git HEAD, source SHA, loaded DLL SHA and process module path for both repos. Build matching OpenVINO 2026.4 GPU + CPU plugins and OVMS in an isolated runtime directory. Do not use stock SDK CPU DLL unless provenance and ABI compatibility are verified.
2. Run host controls `otd_control_test`, `otd_lru_test`, `otd_execution_guard_test`, fail-stop subprocess, native pack tests and grouped-prefill GPU tests. Record commands, return codes and full test counts; no inferred PASS.
3. Rebuild OVMS and GPU plugin with BOTH receipt changes. Verify clean pack directory on eligible model produces >=1 `LAYER` receipt and successful pack-build exit; run the independent native verifier and V2 seal/verify before serving.
4. Negative controls: (a) stale foreign `otd-*.pack` only, dense-only E4B or other no-eligible model must reject; (b) wrong GPU DLL that never emits receipt must reject; (c) malformed receipt / missing pack / symlink pack must reject; (d) corrupted native payload must be rejected by independent verifier and REQUIRE; (e) no listeners in build-only.
5. Only after pack-build and native V2 verification: run same-cohort OFF vs REQUIRE real-model smoke, decode + grouped-prefill, then supervised r20/r40/r75 and actual tool calling with nonce-bearing tool result. Keep exact source/build/module attribution for every cell.
6. For N2, exercise C1/C2/C4, cancellation, early exception, per-expert fallback, grouped-prefill and MTP; no missing terminal event may be interpreted as completed. For N3, verify global budget ownership, physical LPDDR/WDDM overlap and admission refusal under pressure. Do not enable N4 until these gates pass.

## Evidence to return

Store in a stable `docs/cib2/evidence/` checkpoint or local artifact bundle: `source-build-modules.json` (full SHAs), `commands-and-exit-codes.json`, `host-tests.json`, `gpu-unit-tests.json`, `pack-build-receipt.txt`, `pack-verifier.json`, `generation-manifest.json`, `native-model-parity.json`, `tool-calling.json`, `memory-and-offload.json`, and `blockers.json`. Every gate is PASS / FAIL / BLOCKED / NOT_RUN, with actual observed evidence and environment. Do not promote historical 2026.5 OTD speedups to a 2026.4 same-cohort result.

## Current disposition

Source changes committed on isolated audit/feature branches; no compiler, GPU or Windows test execution by this GitHub-side author. Draft PRs only. The local operator's CPU plugin build continues independently; avoid merging during that build.
