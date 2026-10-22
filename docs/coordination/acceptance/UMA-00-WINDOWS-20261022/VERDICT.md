# UMA-00 / UMA-01 VERDICT

**Date:** 2026-10-22  
**Host:** Windows 11 Build 26300 / Core Ultra 7 258V / Arc 140V (MSI Claw 8 AI+ A2VM)  
**Draft ADR PR:** https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/20  
**This docs branch:** `docs/uma-00-windows-evidence-20261022` (docs-only; **do not merge** without operator approval)  
**Independent of:** Wave-01 Windows acceptance; golden C6 untouched; no driver/BIOS/inference path changes

## Coordinator decision (exactly one)

# `UMA_B_PROTOTYPE_READY_FOR_DESIGN`

### Technical justification

1. **UMA confirmed on the target adapter:** D3D12 `ARCHITECTURE1.UMA=true` with OpenCL `HOST_UNIFIED_MEMORY=true` and LUID-matched Arc 140V device. Physical LPDDR is one pool; DXGI LOCAL budget (~26.7 GiB idle) sits inside shared system memory (~27.4 GiB), not discrete VRAM.
2. **~27.5 GB explained without treating it as a reservation:** `GpuSystemMemoryPinninglimit=87` yields `SharedSystemMemory = floor(RAM×0.87)` exactly; dxdiag Display Memory ~28227 MiB ≈ 27.57 GiB. Marketing “(16GB)” and WMI `AdapterRAM` are misleading. Not OpenVINO, not a BIOS carve-out proven here.
3. **USM capability exists for a CPU-visible resident design:** Intel USM host/device/single-device shared caps are non-zero; Xe2 iGPU already has `can_use_host_usm_zero_copy()`. Coarse-grain SVM only; `SHARED_SYSTEM_MEM=0` and `CacheCoherentUMA=false` bound the design (explicit USM + fences), they do not remove path B.
4. **Native path fully mapped:** `fill_weights_from_pack` → nine `usm_device` residents (`moe_offload_constant` preferred alloc) → `gpu_usm::copy_from` → `enqueue_memcpy`, with Wave-01 verify-before-copy. Blockers for “zero API change into current usm_device” are understood; they motivate a **bounded allocator-policy prototype**, not abandonment of path B.
5. **Constraints retained:** pack v1, nine-tensor logical layout, and fail-closed integrity can stay; prototype must not touch production OTD, C6, or OVMS runtime until designed and approved.

### What is *not* claimed

- Not `UMA-02`/`UMA-03` (no scratch prototype built; no GPU performance run).  
- Not zero-copy proven.  
- Not that `UMA=true` ⇒ drop staging.  
- Not Linux evidence (`LINUX_DEFERRED_NO_MACHINE`).

## Gate scores

| Gate | Result |
|---|---|
| UMA-00 topology / budgets / 27.5 GiB origin | **PASS** |
| UMA-01 source map + feasibility | **PASS** (path B design-ready; path C blocked) |
| GPU acceptance | **NOT_RUN** |
| Merge | **NO** |

## Artifact index

| Doc | Path |
|---|---|
| SYSTEM | `docs/coordination/acceptance/UMA-00-WINDOWS-20261022/SYSTEM.md` |
| SOURCE-MAP | `docs/coordination/acceptance/UMA-00-WINDOWS-20261022/SOURCE-MAP.md` |
| FEASIBILITY | `docs/coordination/acceptance/UMA-00-WINDOWS-20261022/FEASIBILITY.md` |
| RISKS | `docs/coordination/acceptance/UMA-00-WINDOWS-20261022/RISKS.md` |
| VERDICT | `docs/coordination/acceptance/UMA-00-WINDOWS-20261022/VERDICT.md` |
| Raw evidence | `C:\gm\orchestration\uma-00-windows-20261022\evidence\` |

## Key measurements (compact)

| Item | Value |
|---|---|
| D3D12 UMA | true |
| D3D12 CacheCoherentUMA | false |
| DXGI SharedSystemMemory | 29463970897 B (27.44 GiB) |
| DXGI LOCAL.Budget (idle) | 28658664529 B (26.69 GiB) |
| DXGI NON_LOCAL | 0 |
| 27.5 GB origin | WDDM shared/display reporting; pin limit 87% of RAM |
| OpenCL SVM | coarse-grain only |
| Intel USM host/device/shared | ACCESS\|ATOMIC; shared-system **0** |
| Driver / WDDM | 32.0.101.9150 / WDDM 3.2 |

## Code map (compact)

| Stage | File@SHA | Lines |
|---|---|---|
| fill | `moe_otd_runtime.cpp` @ `47921924` | 363–409 (`copy_from` @ 393) |
| allocator | `moe_offload_constant.cpp` @ `47921924` | 68 → `usm_device` |
| copy_from | `ocl_memory.cpp` @ `47921924` | `gpu_usm::copy_from` 612–627 |
| integrity | `moe_otd_runtime.cpp` @ `74003278` (wt-integration) | `read_verified_record` before copies |

## Direct-read feasibility

**NO** into current nine `usm_device` residents without a copy.  
**YES** for a design that keeps pack v1 / nine tensors / fail-closed integrity and switches residents to CPU-visible USM + post-verify CPU scatter (see `FEASIBILITY.md`).

## Risks (summary)

See `RISKS.md`: non-coherent UMA, WDDM overlapping budgets, nine-way scatter residual copies, concurrent miss races, Windows memory pressure.

## Recommended single next design step

**DONE (2026-10-22):** scratch design + UMA-02 plan published under  
[`../UMA-01-DESIGN-20261022/`](../UMA-01-DESIGN-20261022/) (`DESIGN.md`, `UMA-02-PLAN.md`, `HANDOFF.md`).  
Next engineering action: operator-gated host-only UMA-02 harness — still **no** GPU merge, **no** COMPUTE_GO, **no** production allocator switch.
