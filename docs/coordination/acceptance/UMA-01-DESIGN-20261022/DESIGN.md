# UMA-01 DESIGN — Path B: CPU-visible USM residents + verify-then-scatter

**Status:** scratch design only — **not** production code, **not** Wave-01/C6/OVMS runtime enablement  
**Verdict prerequisite:** `UMA_B_PROTOTYPE_READY_FOR_DESIGN` ([UMA-00 VERDICT](../UMA-00-WINDOWS-20261022/VERDICT.md))  
**Host facts retained:** D3D12 `UMA=true`, `CacheCoherentUMA=false`; Intel USM host/device present; `SHARED_SYSTEM_MEM=0`; ~27.5 GiB = WDDM pin 87% RAM  
**Source locks:**

| Tree | SHA | Role |
|---|---|---|
| OpenVINO Wave-01 (wt-integration) | `74003278a9c8925fcda7bc32ceb27320e59bbb1d` | Integrity path + `set_filled` contract |
| OpenVINO cohort baseline | `479219245f6f10b670367ad35af16513d72d2091` | Allocator / `copy_from` baseline |
| OVMS UMA-00 evidence PR HEAD | `e320a59c6b44e64945d1797495383be3873f1b75` | Host evidence pack |
| OpenVINO Draft PR #7 | tip contains `74003278` | OTD host PASS; GPU **PENDING_AUTHORIZATION** |

Local checkouts: `C:\gm\otd-research\wt-integration`, `C:\gm\otd-research\openvino-cohort`, evidence under `C:\gm\orchestration\uma-00-windows-20261022\`.

---

## 1. Problem statement (one paragraph)

Today a miss does `read → (Wave-01 verify) → 9× gpu_usm::copy_from → enqueue_memcpy` into **`usm_device`** residents allocated by `moe_offload_constant` via `get_preferred_memory_allocation_type()`. On this Arc 140V UMA host that memcpy is still an explicit API copy into CPU-invisible device USM, even though physical LPDDR is shared. Path B keeps pack v1, the nine-tensor logical layout, and fail-closed integrity, and only changes **where** the nine residents live (`usm_host` / CPU-visible) and **how** verified staging bytes reach slot offsets (CPU scatter + explicit fence before `set_filled`).

---

## 2. Proposed allocator policy switch

### 2.1 Recommendation

**Allocate the nine OTD routed-expert resident buffers as `allocation_type::usm_host`** when a scratch prototype flag / policy is enabled.

| Option | Verdict | Notes |
|---|---|---|
| **`usm_host` (recommended)** | Preferred for path B | CPU-visible (`buffer_ptr()` / lock returns native ptr); Xe2 iGPU already has `can_use_host_usm_zero_copy()`; HOST_MEM caps ACCESS\|ATOMIC on this adapter |
| `usm_shared` (single-device shared) | **Not available via engine today** | `engine::supports_allocation(usm_shared)` hard-coded `false` (`engine.cpp` ~L101–103). Do not depend on re-enabling it for UMA-02 |
| `usm_device` (status quo) | Control / path A | Remains the production default; path B does **not** claim zero-API-change into these pointers |
| System `malloc` / file map as GPU ptr | **Forbidden** | `SHARED_SYSTEM_MEM=0`; path C remains BLOCKED |

### 2.2 Where the switch lives (design locus — not implemented here)

Minimum change surface for a **scratch** prototype (isolated branch, non-shippable):

1. **`moe_offload_constant.cpp` `try_prepare_partial_upload` (~L68)**  
   Today: `engine.allocate_memory(upload_layout, engine.get_preferred_memory_allocation_type(), false)` → `usm_device`.  
   Path B: when policy enabled, pass `allocation_type::usm_host` (or `get_lockable_preferred_memory_allocation_type()` once `usm_shared` is still disabled — that already falls through to `usm_host` on this platform).
2. **Optional explicit policy flag** (e.g. config / env / compile-time `OTD_RESIDENT_USM_HOST=1`) gated **off** by default so Wave-01 production and golden C6 never see it.
3. **Do not** change `get_preferred_memory_allocation_type()` globally — that would retarget unrelated buffers.

### 2.3 What the kernels still see

- Same nine `cldnn::memory` objects bound via `OffloadExpertWeightProvider::fill_routed_weight_views`.
- Same per-tensor expert-major slot layout: `dst_offset = slot * per_expert_size`.
- Reinterpret-as-full-logical-shape behavior of partial upload **unchanged**.

---

## 3. Exact fill path (verify-then-scatter-then-publish)

### 3.1 Target sequence (path B)

```text
OffloadExpertWeightProvider::acquire_slot  // miss
  └─ fill_weights_from_pack(...)
       ├─ preflight: nine resident size/slot asserts (Wave-01 L386–395)
       ├─ read_verified_record → CPU staging   // FNV; PackIntegrityError → NO scatter, NO set_filled
       ├─ for t in 0..8:
       │     CPU memcpy into usm_host resident at (slot * size)
       │     // NOT gpu_usm::copy_from / enqueue_memcpy (unless used as explicit fence — see §5)
       ├─ visibility fence (required: CacheCoherentUMA=false)  // see §5
       └─ return success
  └─ LRUCache::set_filled(slot)   // ONLY after full successful fill + fence
```

### 3.2 Staging policy

| Choice | Decision |
|---|---|
| Keep `_pack_staging` vector | **YES** for UMA-02 — verify stays on a private CPU buffer; corrupt bytes never enter residents |
| Hash-while-scatter into residents | **Out of scope for first prototype** — would complicate rollback on mid-scatter failure; may revisit only after byte-parity PASS |
| Direct NVMe → usm_host | **NO** for v1 design — pack record is expert-major contiguous; residents are nine separate tensors; verify needs a complete payload image first |

### 3.3 Scatter mechanics

For each of nine tensors with `size > 0` and non-null `mem`:

1. Obtain host-visible destination: `char* dst = static_cast<char*>(mem->buffer_ptr()) + slot * size`  
   (For `usm_host`, OpenVINO `gpu_usm::lock` already returns `_buffer.get()` without device bounce — `ocl_memory.cpp` ~L547–549.)
2. `memcpy(dst, staging.data() + pack.tensor_offset_in_record(t), size)`.
3. Prefer a single helper (e.g. `scatter_verified_record_to_residents`) so timing counters can replace `copy_from` wall time with CPU scatter time.

### 3.4 Failure points (fail-closed)

| Failure | Residents mutated? | `set_filled`? | Next lookup of expert |
|---|---|---|---|
| Layout / slot preflight assert | No | No | N/A (hard fail) |
| `PackIntegrityError` from `read_verified_record` | **No** (scatter not started) | **No** | Miss again (`hit = m_filled_list[slot] == false` even if expert remains mapped — Wave-01 `lru_cache.cpp` L80) |
| Mid-scatter CPU exception / OOM | Possibly partial | **No** | Miss; next successful fill must overwrite **all nine** tensors before publish |
| Fence failure | Scatter may have completed | **No** | Treat as fill failure; do not publish |

**Invariant:** any path that does not complete all nine scatters **and** the visibility fence **must not** call `set_filled`. Wave-01 already wraps `fill_weights_from_pack` so `PackIntegrityError` skips `set_filled` (`expert_weight_providers.cpp` ~L145–154 @ `74003278`).

---

## 4. MUST NOT change vs MAY change

### 4.1 MUST NOT change

| Item | Reason |
|---|---|
| Pack format v1 bytes / header / checksum table | Integrity contract; CLD-01 |
| Nine-tensor logical layout (`gate/up/down` × `w/s/z`) | Kernel / `moe_weights` binding |
| Expert-major slot addressing inside each tensor (`slot * size`) | Existing GEMM views |
| `read_verified_record` before any resident mutation | Fail-closed |
| `set_filled` only after successful fill | No false LRU hits |
| Production default allocator (`usm_device` preferred) | Wave-01 / C6 / OVMS untouched until operator enablement |
| Golden C6 tree, production OVMS runtime, drivers, BIOS, pin limit | Explicit non-goals |
| Claiming COMPUTE_GO or running GPU soak/inference for acceptance | GPU still PENDING_AUTHORIZATION |

### 4.2 MAY change (scratch / prototype only)

| Item | Allowed change |
|---|---|
| Resident `allocation_type` for OTD partial upload | `usm_device` → `usm_host` under isolated flag |
| Fill transfer mechanism | `mem->copy_from(..., blocking=true)` → CPU `memcpy` into host USM + fence |
| Timing counters | Attribute scatter ns separately from `enqueue_memcpy` |
| Prototype harness / unit tests | Host-side byte-parity and corrupt-record tests (see UMA-02 plan) |
| Docs / Draft PRs | This tree |

### 4.3 Explicitly deferred (not MAY for UMA-02 coding)

- Subbuffer / single-parent allocation aliasing one pack record  
- RemoteTensor `MMAPED_FILE` / `CPU_VA` into `moe_weights` (path C)  
- Re-enabling engine `usm_shared`  
- Pack format or kernel layout changes to avoid nine scatters  

---

## 5. Non-coherent UMA fencing / visibility

**Host fact:** `CacheCoherentUMA=false`. Host stores into USM are **not** automatically GPU-visible.

### 5.1 Requirements before `set_filled`

1. Complete all nine CPU scatters into the slot regions.  
2. Ensure GPU consumers that later read those USM pointers observe the new bytes. On OpenCL/Intel USM with coarse-grain SVM only, that means an **explicit** synchronization on the execution stream used by MoE — not reliance on D3D12 UMA or CPU cache alone.  
3. Only then call `set_filled(slot)`.

### 5.2 Candidate fence mechanisms (prototype must pick one and test)

| Mechanism | Role | Notes |
|---|---|---|
| `stream.flush()` + `stream.finish()` (or equivalent blocking wait on the OCL queue used by MoE) | Primary candidate | Matches “blocking publish” spirit of today’s `copy_from(..., blocking=true)` |
| Zero-length or tiny `enqueue_memcpy` / marker event after scatters | Alternate | Only if finish alone is insufficient on NEO for `usm_host`→kernel visibility |
| Per-buffer `lock`/`unlock` no-op | **Insufficient alone** | For `usm_host`, unlock does not enqueue a device sync (`ocl_memory.cpp` unlock path) |

### 5.3 Ordering rule

```text
verify(staging) → scatter(CPU→usm_host[slot]) → fence(stream) → set_filled(slot) → allow hit
```

Any reordering that publishes before fence is a design defect under `CacheCoherentUMA=false`.

### 5.4 Concurrent eviction / in-flight kernels

Existing OTD hazard: eviction may recycle a slot while GPU still references it. Path B **does not** invent a new lease protocol; it inherits Wave-01 slot leasing / simultaneous acquire. UMA-02 tests that touch eviction remain **COMPUTE_GO-gated** if they require live GPU kernels.

---

## 6. Eviction / LRU interactions and failure propagation

### 6.1 Current contract (must preserve)

From `lru_cache.cpp` @ Wave-01:

- Miss inserts expert→slot mapping immediately; `hit` is `m_filled_list[slot]`.  
- Eviction clears `m_filled_list[slot]=false` and frees/recycles the slot.  
- `set_filled` flips the bit only after fill success.

From `acquire_slot` @ `74003278`:

- Integrity reject → throw; **no** `set_filled`.  
- Message asserts resident device memory was not modified (true for verify-before-copy; path B must keep that true for verify-before-scatter).

### 6.2 Path B failure propagation rules

| Event | Required behavior |
|---|---|
| Corrupt pack record | Staging may hold junk; residents **unmodified**; slot remains unfilled; no false hit |
| Scatter fails after N&lt;9 tensors | Slot stays unfilled; stale/partial bytes may exist **but must be unreachable via hit**; next successful fill overwrites all nine before publish |
| Fence fails | Same as fill failure — no `set_filled` |
| Eviction of unfilled mapped expert | Same as today — filled bit false; slot reusable |
| Successful path B fill | Fence then `set_filled`; subsequent lookup may hit |

### 6.3 What “no false LRU hit after failed verify” means

After a `PackIntegrityError`, a later `lookup(expert)` for the same expert must return `hit == false` (even if the map still holds the expert). Serving must not treat the slot as weight-ready. UMA-02 encodes this as a required negative case.

---

## 7. Non-goals

1. **No pack format change** (v1 layout, checksums, placement).  
2. **No nine-tensor layout change** and no single-allocation pack aliasing.  
3. **No integrity downgrade** (no publish without verify; no weaken FNV; no “best effort” fill).  
4. **No production enablement** — default remains path A (`usm_device` + `copy_from`).  
5. **No Wave-01 OTD production merge**, no golden C6 edits, no OVMS serving path changes.  
6. **No driver / BIOS / `GpuSystemMemoryPinninglimit` changes**.  
7. **No GPU soak / inference / performance claims** without COMPUTE_GO (there is none).  
8. **No Linux evidence** — label remains `LINUX_DEFERRED_NO_MACHINE`.  
9. **No claim that eliminating `enqueue_memcpy` improves miss latency** until UMA-03 measures it.

---

## 8. Relation to path A (control)

Path A remains the byte-oracle and production default:

`positional read → staging → verify → 9× copy_from(usm_device) → set_filled`

Path B must match path A **byte-for-byte** in the nine slot regions after a successful fill (UMA-02 parity), under the same pack and expert/slot indices.

---

## 9. Scratch prototype shape (if/when coding is authorized)

Only after operator approval of this design + UMA-02 plan:

| Attribute | Requirement |
|---|---|
| Branch | Isolated OpenVINO scratch (not C6, not production OVMS) |
| Flag | Default **off**; opt-in only |
| Docs | Mark every binary/log as `NON_SHIPPABLE` / `UMA_SCRATCH` |
| First coding target | Host-side harness or narrowly #ifdef’d fill/alloc — prefer tests before perf |
| Merge | **Forbidden** until separate enablement gate |

Default for the immediate next engineering session remains: **implement nothing production-facing; execute UMA-02 test specifications / tiny harness only if already expected.**

---

## 10. Open questions that block coding (see also HANDOFF)

1. Exact fence primitive validated on Arc 140V NEO for `usm_host` host-write → GPU-kernel read.  
2. Whether MoE GEMM kernels accept `usm_host` residents with acceptable bandwidth (measurement = UMA-03, needs COMPUTE_GO).  
3. Operator approval to start a non-shippable scratch branch vs wait for Wave-01 GPU authorization.  
4. Whether mid-scatter failure needs explicit slot scrubbing (zero/fill) beyond “unfilled + overwrite on retry” for defense-in-depth.

These do **not** block publishing this design; they block claiming a working prototype or enabling any production path.
