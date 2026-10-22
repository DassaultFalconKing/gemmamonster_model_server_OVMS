# HANDOFF-UMA-00 — Windows 11 / Arc 140V memory capability inventory

**Status:** investigation approved; runtime edits **not authorized**; Linux `DEFERRED_NO_MACHINE`. Depends on `ADR-UMA-01`, but does not block the existing CLD-01..03/Windows acceptance process.

## Mission

Capture machine-specific evidence distinguishing physical LPDDR sharing, WDDM resource budgets, API mapping capability, actual OpenVINO GPU allocator and GPU resident copy semantics. Do not assume that the user's observed `27.5 GiB GPU memory` value is pre-allocated physical VRAM. Do not confuse shared physical pages with a coherent shared pointer. Do not change drivers, BIOS/DVMT, local model deployment or power settings.

## 1. Source locks

- Architecture branch base: OVMS `integration/qwm01-otd-pack-20261022` @ `746dc833dc3bcccf64fabdb469feda9260582bae`.
- GPU code source for inspection: OpenVINO `research/ov-gpu-otd-cohort-b5bfb148` @ `479219245f6f10b670367ad35af16513d72d2091` plus separately evolving Wave-01 integration candidate. Do not mix unrecorded binary versions.
- Golden C6 @ `ba6ec792c3121850fea167fa7d7e190b25fcdc76`: read only.

## 2. Agent A: host-only topology and budget probe

Use PowerShell 7, Visual Studio Build Tools if available. Save a sanitized, UTF-8 report. Host-only property inspection should not launch inference or allocate large GPU buffers.

```powershell
$ErrorActionPreference = 'Stop'
Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,DriverDate,PNPDeviceID
Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,TotalVisibleMemorySize,FreePhysicalMemory,TotalVirtualMemorySize,FreeVirtualMemory
Get-ComputerInfo | Select-Object WindowsVersion,OsBuildNumber
Get-Counter '\Memory\Available MBytes','\Memory\Committed Bytes','\Memory\Commit Limit'
$dx = Join-Path $env:TEMP 'gemmamonster-dxdiag-uma.txt'
dxdiag /t $dx
```

A D3D12 probe compiled against Windows SDK must enumerate adapters and match the target Arc 140V adapter by DXGI LUID (record the correlation to the actual OpenCL device). Call `ID3D12Device::CheckFeatureSupport(D3D12_FEATURE_ARCHITECTURE1, ...)` for `UMA` and `CacheCoherentUMA`. Use `IDXGIAdapter3::QueryVideoMemoryInfo` for LOCAL and NON_LOCAL (`Budget`, `CurrentUsage`, `AvailableForReservation`, `CurrentReservation`) on the correct node. For OpenCL separately query `CL_DEVICE_HOST_UNIFIED_MEMORY`, `CL_DEVICE_SVM_CAPABILITIES`, Intel USM host/shared/device capabilities if extension/runtime supports them; record errors/unsupported properties explicitly. Do not infer one API's flags from another.

Test the `27.5 GiB` setting both ways **only when permitted**: record its source (application model config, OpenVINO property, DXGI budget, BIOS/firmware reserve or WDDM accounting). No changes to BIOS or paging settings in this task. `UMA=true` must not automatically become `zero_copy=true`.

## 3. Agent B: C++ source mapping, no GPU run yet

Trace real code (exact SHAs, file/line):

- `moe_otd_runtime.cpp::fill_weights_from_pack`: pack positional read, checksum, staging lifetime, nine `mem->copy_from` calls;
- `expert_weight_providers.cpp::acquire_slot`: LRU reserve/fill state and per-provider staging, concurrent requests;
- `cldnn::memory::copy_from` implementation for resident buffer allocation types and the OpenCL backend actually configured on this machine;
- allocation site for nine MoE tensor resident buffers, memory layout, offsets, aliasing/subbuffer support, CPU visibility and OpenVINO `cacheline_size`;
- `GPU RemoteTensor` input/output `CPU_VA`/file API versus **internal** `cldnn::moe_weights` compatibility.

Deliver a **source-bound feasibility decision** for path B `direct resident fill` and C `read-only mmap-backed cold record`. If the nine buffers cannot alias one contiguous record without extra scatter/compute, report this as a blocker, not an invitation to rewrite MoE kernels mid-acceptance.

## 4. Minimal proof gates after operator approval

Only after native GPU plugin correctness and operator GPU-compute approval:

1. Build a stand-alone scratch-only prototype, never production OTD.
2. Compare baseline `positional_read → staging → verify → 9*copy_from` with one CPU-visible GPU-readable allocation experiment of equal logical expert size and matched bytes.
3. Require exact bytes and tensor shape/layout parity after transfer; verify corrupt-record rejection **before** GPU consumer can access data.
4. Verify GPU fence/queue ordering, buffer lifetime, no use-after-eviction, concurrent C1/C2 requests, Windows file-handle replacement.
5. Measure real `read_us`, `checksum_us`, copy/wait/end-to-end `miss_us`, committed-token TPOT p50/p95/p99, GPU budget, process commit, working set, page faults and **OS physical NVMe bytes**.
6. Do not accept a shared-pointer demo unless **effective copy count or bandwidth** improves and complete serving correctness is retained.

## 5. Outputs

Publish a review branch and handoff under `docs/coordination/acceptance/UMA-00-WINDOWS-20261022/`:

- `SYSTEM.md`: OS, compiler, WDDM/driver, physical RAM, DXGI+OpenCL capabilities, exact target LUID/device mapping, source of 27.5-GiB limit.
- `SOURCE-MAP.md`: pinned code locations, actual allocations, nine views, copying, sync.
- `FEASIBILITY.md`: paths A/B/C and verdict `FEASIBLE | BLOCKED | UNKNOWN`, exact reasons and minimum API change.
- `RISKS.md`: coherence, eviction and Windows memory-pressure failure modes.
- `VERDICT.md`: `UMA-00 PASS|FAIL|BLOCKED`, with evidence; no GPU acceptance assertion from read-only probes.

Then tell coordinator **either** `UMA_B_PROTOTYPE_READY_FOR_DESIGN` with capability and source proof, **or** `UMA_B_BLOCKED` with precise missing support. **Do not merge, do not modify the Wave-01 integration branch or golden C6.**

## Operator note

The correct next step is capabilities + code tracing, **not** automatically increasing a VRAM slider or mapping entire NVMe packs into GPU address space. Linux work is deferred; no machine. Current Wave-01 local testers retain priority for build/integrity acceptance.
