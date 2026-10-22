# UMA-01 FEASIBILITY — paths A / B / C

**Machine:** Windows 11 / Ultra 7 258V / Arc 140V (this host)  
**Source lock:** OpenVINO `479219245f6f10b670367ad35af16513d72d2091` + Wave-01 integrity inspection `74003278`  
**Capability evidence:** `SYSTEM.md` + `evidence/uma-caps-probe.txt`

## Path A — baseline (control)

`positional NVMe read → CPU staging → (Wave-01 verify) → 9× usm_device copy_from(enqueue_memcpy) → set_filled`

| Criterion | Result |
|---|---|
| Implemented | **YES** (cohort + Wave-01 integrity) |
| Pack v1 | preserved |
| Nine-tensor layout | preserved |
| Fail-closed integrity | preserved on Wave-01 |
| Feasibility | **FEASIBLE** (accepted control; not redesigned here) |

## Path B — direct resident fill (CPU-visible GPU-readable)

ADR intent: one miss still does one positional payload read; bytes land in GPU-readable memory that the CPU can write; verify before publish; avoid redundant staging→device copy where possible.

### Direct-read question (hard constraint)

> Is a direct read into GPU-readable memory possible **WITHOUT** changing pack v1, nine-tensor layout, or fail-closed integrity?

| Interpretation | Answer | Why |
|---|---|---|
| Into **existing** nine `usm_device` residents as allocated today | **NO** | CPU cannot write `usm_device` without `enqueue_memcpy` / lock bounce (`ocl_memory.cpp` lock + copy_from). “Direct read” from NVMe into those pointers is not possible. |
| Keeping pack v1 + nine separate tensors + verify-before-publish, but allowing **allocation-type policy** change to CPU-visible USM (`usm_host`, which this Xe2 iGPU already special-cases) | **YES (design-level)** | Host USM capabilities exist (`HOST_MEM_CAPABILITIES_INTEL=0x3`). `can_use_host_usm_zero_copy()` is true for Xe2 iGPU. Fill can: read→staging→verify→**CPU scatter memcpy** into nine `usm_host` slot regions (or incremental hash-while-scatter), then fence/publish. Pack layout and nine-tensor **logical** layout unchanged; integrity remains fail-closed if `set_filled` stays after verify. |
| Single contiguous allocation aliasing one pack record as nine kernel views | **NO without layout/representation change** | Pack record is expert-major contiguous across nine slices; residents are per-tensor `[slot*]`. One pointer cannot satisfy both without subbuffer-parent redesign or kernel view changes — explicitly out of bounds for “no nine-tensor layout change”. |

**Direct-read feasibility (deliverable wording):** **NO** against today’s `usm_device` nine allocations; **YES** for a path-B prototype that keeps pack v1 / nine tensors / fail-closed integrity and only changes **how those nine buffers are allocated** (CPU-visible USM) plus post-verify CPU scatter instead of `gpu_usm::copy_from` device enqueue. That is an allocator/API design change, not a pack or MoE kernel layout rewrite.

### Path B gate summary

| Criterion | Result |
|---|---|
| D3D12 UMA | true (helps physically; does not alone enable zero-copy) |
| CacheCoherentUMA | **false** → explicit sync still mandatory |
| Intel USM host/device | present on GPU |
| Shared-system USM (`malloc`) | **unsupported** (`SHARED_SYSTEM_MEM=0`) |
| Engine `usm_shared` | disabled in `supports_allocation` |
| Current residents | `usm_device` via `moe_offload_constant.cpp:68` |
| Feasibility | **FEASIBLE for prototype design** with allocator policy change; **BLOCKED** if prototype is required to keep `usm_device` and eliminate copies with zero API change |

## Path C — read-only mapped cold record

Map pack / RemoteTensor `MMAPED_FILE`/`CPU_VA` and let GPU read cold experts without resident admission.

| Criterion | Result |
|---|---|
| API exists (external tensors) | documented; **not** wired to internal `moe_weights` |
| Nine views from one mapped record | same scatter/layout obstacle as B |
| `SHARED_SYSTEM_MEM` | 0 on GPU → cannot treat arbitrary file mapping as USM without explicit import path |
| Windows file replace / paging | undemonstrated; high risk |
| Feasibility | **BLOCKED** for production-shaped use without new binding + alignment/lifetime design; research-only later |

## Path D — CPU cold lane

Not evaluated in UMA-00/01 (deferred).

## Aggregate

| Path | Verdict |
|---|---|
| A | **FEASIBLE** (control) |
| B | **FEASIBLE** for scratch prototype **design** under constraints above |
| C | **BLOCKED** (missing internal binding + system-USM) until a separate design |

Minimum API change for a path-B experiment (design only; not implemented here):

1. Allocate OTD resident routed tensors with lockable/host USM (`usm_host`) instead of preferred `usm_device`, or add an explicit `memory_access_policy` switch.  
2. Keep Wave-01 `read_verified_record` before publish.  
3. Replace or bypass nine `mem->copy_from` with CPU memcpy into slot offsets when alloc is host-visible; keep blocking fence before `set_filled`.  
4. Do **not** change pack v1 bytes, nine logical tensors, or fail-closed reject semantics.  
5. Measure copy bytes / miss_us / WDDM budget vs path A on a scratch branch only.
