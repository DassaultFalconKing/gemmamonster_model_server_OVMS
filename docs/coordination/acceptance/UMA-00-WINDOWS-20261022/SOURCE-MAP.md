# UMA-01 SOURCE-MAP — fill_weights_from_pack → allocator → copy_from

**Gate:** `UMA-01` native allocator / copy semantics (source inspection; no GPU prototype run)  
**OpenVINO lock (cohort):** `479219245f6f10b670367ad35af16513d72d2091`  
**Checkout:** `C:\gm\otd-research\openvino-cohort`  
**Wave-01 integrity delta (inspection):** `C:\gm\otd-research\wt-integration` @ `74003278a9c8925fcda7bc32ceb27320e59bbb1d`  
**GitHub cohort tree:** https://github.com/DassaultFalconKing/openvino/tree/479219245f6f10b670367ad35af16513d72d2091

Citations below use `file:line` at the locked cohort SHA unless marked Wave-01.

## 1. End-to-end miss path (logical)

```text
OffloadExpertWeightProvider::acquire_slot
  └─ LRU miss → fill_weights_from_pack(...)
       ├─ (Wave-01) read_verified_record → staging  [fail-closed before any copy_from]
       ├─ (cohort baseline) pack_reader.read → staging
       └─ for t in 0..8 (nine tensors):
            mem->copy_from(stream, staging+tensor_offset, 0, slot*size, size, /*blocking=*/true)
  └─ LRUCache::set_filled(slot)   // only after successful fill
```

Publication after fill is intentional: a failed fill must leave the slot unfilled (Wave-01 / CLD-01 contract).

## 2. `fill_weights_from_pack` (cohort lock)

File: `src/plugins/intel_gpu/src/graph/impls/ocl_v2/moe/moe_otd_runtime.cpp`

| Item | Location |
|---|---|
| Function | L363–409 |
| Nine tensor list | L371–372: `gate_w, up_w, down_w, gate_s, up_s, down_s, gate_z, up_z, down_z` |
| Staging lifetime | L378–379: `staging.resize(payload)`; reusable `std::vector<uint8_t>&` owned by provider |
| Positional read | L383: `pack_reader.read(..., pack.record_offset(expert))` |
| Per-tensor `copy_from` | L386–394; call at **L393** |
| Slot addressing | `dst_offset = slot * size` (expert-major within each tensor buffer) |

Link: https://github.com/DassaultFalconKing/openvino/blob/479219245f6f10b670367ad35af16513d72d2091/src/plugins/intel_gpu/src/graph/impls/ocl_v2/moe/moe_otd_runtime.cpp#L363-L409

### Wave-01 integrity (not in cohort lock; required for fail-closed)

File (wt-integration): same path, `fill_weights_from_pack` L369–444  
- Pre-validates all resident tensor sizes/slots **before** read (L386–395)  
- `read_verified_record` + FNV before any `copy_from` (L401–412)  
- On `PackIntegrityError`: increment failure counter, rethrow; **no** `copy_from` (L407–412)  
- Then nine `copy_from` at L417–424  

This is the fail-closed integrity path ADR/CLD-01 describe. Cohort lock still shows the pre-integrity shape.

## 3. Provider / LRU ownership

File: `src/plugins/intel_gpu/src/graph/impls/ocl_v2/moe/expert_weight_providers.cpp`

| Item | Location |
|---|---|
| Bind resident `moe_weights*` | `bind` L73–78 |
| Fill routed views → nine resident ptrs | `fill_routed_weight_views` L81–92 |
| `acquire_slot` miss → `fill_weights_from_pack` | L95–120; pack call **L115** |
| Publish filled | L119: `_cache->set_filled(item.slot)` |
| Staging buffer | member `_pack_staging` passed into fill |

Link: https://github.com/DassaultFalconKing/openvino/blob/479219245f6f10b670367ad35af16513d72d2091/src/plugins/intel_gpu/src/graph/impls/ocl_v2/moe/expert_weight_providers.cpp#L95-L120

Runtime bind of the nine buffers from graph inputs:  
`moe_3gemm_swiglu_opt.cpp` L722–732 (`instance._weights.gate_w = instance.input_memory_ptr(WEIGHT_0)` …).

## 4. Allocator of the nine resident tensors

OTD partial upload creates the physical resident buffers:

File: `src/plugins/intel_gpu/src/plugin/ops/moe_offload_constant.cpp`

| Step | Location | Behavior |
|---|---|---|
| Compute resident expert count | L60–65 | `resident = max(1, num_expert * (100 - otd_ratio) / 100)` |
| Allocate | **L68** | `engine.allocate_memory(upload_layout, engine.get_preferred_memory_allocation_type(), false)` |
| Preferred type | `engine.cpp` L136–150 | prefers **`allocation_type::usm_device`** when USM device is supported |
| Reinterpret as full logical shape | L81 | `engine.reinterpret_buffer(*upload_mem, const_layout)` — smaller physical buffer, full logical layout |
| Skip full host→device transfer | comments L69–72; `skip_device_transfer` on partial upload | avoids copying full expert count |

Link: https://github.com/DassaultFalconKing/openvino/blob/479219245f6f10b670367ad35af16513d72d2091/src/plugins/intel_gpu/src/plugin/ops/moe_offload_constant.cpp#L43-L89

### Related engine policy (Xe2 / LNL)

`engine.cpp`:

- L97–105: `supports_allocation(usm_shared)` is **hard-coded false** (engine never selects `usm_shared` today).
- L107–110: `can_use_host_usm_zero_copy()` is true for integrated GPU **and** `arch >= xe2` **and** `usm_host` — Arc 140V qualifies in principle.
- L112–134: lockable preferred → would be `usm_shared` if enabled, else **`usm_host`**.
- L136–150: preferred (used by MoE partial upload) → **`usm_device`**.

`program.cpp` `transfer_memory_to_device` L748–754: does **not** promote `usm_host`→`usm_device` on Xe2 iGPU (“usm_device memory does not provide performance benefits on the LNL platform”).  
**However**, MoE OTD residents bypass that path by allocating `usm_device` directly at L68 of `moe_offload_constant.cpp`.

**Conclusion:** the nine resident MoE weight/scale/zp buffers are **`ocl::gpu_usm` with `allocation_type::usm_device`** (preferred), CPU-invisible without an explicit map/copy. They are **nine separate allocations**, not nine views of one contiguous pack-shaped buffer.

`ocl_engine::allocate_memory` L173–186 constructs `ocl::gpu_usm` for USM types:  
https://github.com/DassaultFalconKing/openvino/blob/479219245f6f10b670367ad35af16513d72d2091/src/plugins/intel_gpu/src/runtime/ocl/ocl_engine.cpp#L173-L186

Subbuffer support exists (`ocl_engine::create_subbuffer` L209+) for USM byte offsets — relevant to a future single-allocation design, **not** used by current nine-tensor OTD fill.

## 5. Actual `memory::copy_from` implementation (OpenCL USM path)

Resident type is USM → `gpu_usm::copy_from(stream, const void*, ...)`.

File: `src/plugins/intel_gpu/src/runtime/ocl/ocl_memory.cpp`

| Item | Location |
|---|---|
| `gpu_usm::copy_from(void*)` | **L612–627** |
| Mechanism | L625: `usm_helper.enqueue_memcpy(queue, dst_usm_ptr, src_host_ptr, size, blocking, …)` |
| Blocking | `blocking=true` from fill → synchronous memcpy enqueue |
| `usm_device` lock path | L534–548 / L564–576: lock copies device↔host via another `enqueue_memcpy` (not used by fill; fill writes via copy_from) |

Link: https://github.com/DassaultFalconKing/openvino/blob/479219245f6f10b670367ad35af16513d72d2091/src/plugins/intel_gpu/src/runtime/ocl/ocl_memory.cpp#L612-L627

If a buffer were `cl_mem` (`gpu_buffer`), host→device would be `enqueueWriteBuffer` (L138–152). OTD residents are USM device, so the USM path applies.

**Physical meaning on UMA:** even with shared LPDDR, this is still an **explicit byte copy** between a CPU staging allocation and a device-USM allocation (driver may optimize, but the API contract is a copy; bandwidth still consumed). It is **not** a zero-copy publish of the staging pointer.

## 6. Pack layout vs resident layout (why nine copies)

Pack v1 (`moe_otd_pack.hpp` / `.cpp`): one **expert-major contiguous record** with `tensor_offset_in_record[t]` for up to nine slices + whole-record checksum (Wave-01).

Resident layout: for each tensor `T`, experts are stored as `[slot0|slot1|…]` inside that tensor’s allocation (`dst = slot * per_expert_size`).

Therefore one pack record is **scattered** across nine buffers. A single `mmap`/`USM` pointer to a pack record does **not** automatically yield nine correct GPU kernel views without scatter, subbuffers with a different parent layout, or kernel/layout changes.

## 7. RemoteTensor APIs vs internal `moe_weights`

Public GPU RemoteTensor `CPU_VA` / `MMAPED_FILE` paths live under `src/plugins/intel_gpu/src/plugin/remote_tensor.cpp` and are documented for external I/O tensors.  
Internal OTD fill operates on `cldnn::memory` inside `cldnn::moe_weights`, filled via `copy_from`. **No source path** currently wraps pack records as RemoteTensor inputs to MoE kernels. Reuse would require a new design binding remote/USM memory into the nine resident slots — out of scope for this map, recorded as unproven.

## 8. Code-map summary (required deliverable)

| Stage | File | Lines (cohort SHA `47921924`) |
|---|---|---|
| Fill entry | `moe_otd_runtime.cpp` | `fill_weights_from_pack` 363–409 |
| Allocator (nine residents) | `moe_offload_constant.cpp` | `try_prepare_partial_upload` 43–89; alloc **68** → `usm_device` |
| Preferred alloc policy | `engine.cpp` | 136–150 (`usm_device`); 107–110 (`can_use_host_usm_zero_copy`) |
| `copy_from` impl | `ocl_memory.cpp` | `gpu_usm::copy_from` 612–627 → `enqueue_memcpy` |
| Acquire / publish | `expert_weight_providers.cpp` | `acquire_slot` 95–120 |
| Integrity (Wave-01) | `wt-integration` same runtime file | `read_verified_record` before copy; SHA `74003278` |
