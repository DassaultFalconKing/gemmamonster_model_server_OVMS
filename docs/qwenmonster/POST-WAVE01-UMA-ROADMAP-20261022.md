# GEMMAMONSTER — post-Wave01 / UMA roadmap correction

**Decision snapshot: 2026-10-22 evening (Europe/Berlin). Status: COORDINATOR_REVIEW; no production acceptance and no C6/OVMS runtime changes.**

This supersedes the *ordering of next experiments* in `HOT_COLD_EXPERTS_ARCHITECTURE.md`, not its long-term model objectives. Windows only; `LINUX_DEFERRED_NO_MACHINE`.

## A. Pinned evidence, not extrapolation

| Source | Pin | Supported conclusion | Not established |
|---|---|---|---|
| OpenVINO original cohort | `479219245f6f10b670367ad35af16513d72d2091` | known OTD pack v1 / one positional read per expert | new safety acceptance |
| [OpenVINO PR #7](https://github.com/DassaultFalconKing/openvino/pull/7) | `74003278a9c8925fcda7bc32ceb27320e59bbb1d` (linked test binary built from `99ee2c2c`) | combined CLD-01,01B,02,03,03B; linked Windows host `ov_gpu_unit_tests` 47/47; Python replay 33/33; publish repeat=200 | live Arc inference, long C1/C2/C4, perf or Linux; report says GPU_PENDING_AUTHORIZATION |
| [OVMS PR #20](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/20) | `8e03f6ae285b381a2abfb46c6c11d46be5079b27` | UMA ADR, third `memory_access_policy` axis | on-device allocation feasibility |
| [OVMS PR #21](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/21) | `e320a59c6b44e64945d1797495383be3873f1b75` | **on this host**, D3D12 UMA=true, CacheCoherentUMA=false; OpenCL GPU SVM coarse buffer only, host USM=0x3, shared-system USM=0; current residents `usm_device` | kernel bandwidth equivalence, generalization to other drivers |
| [OVMS PR #22](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/22) | `b79c4ce44d2590de6fc447f8e5bad060a08e5e16` | path-B `usm_host` nine-tensor CPU-scatter design and test specification | working production allocator or zero-copy proof |
| [OpenVINO PR #8](https://github.com/DassaultFalconKing/openvino/pull/8) | `d82f5f573dfb2b30a4cbf35b1cb8f75e4066c621` | scratch `OTD_RESIDENT_USM_HOST=1` (default OFF), host parity/negative and **short Arc GPU** G01–G03, UMA-03 synthetic benchmarks; new sweetspot 20/25/30 fixture tests | full MoE GEMM, overlapping kernel lifetime, model outputs, end-to-end benefit, production merge approval |
| [OpenVINO PR #6](https://github.com/DassaultFalconKing/openvino/pull/6) | `986a0d412322df6060f0672cacb327618f2ddcac` | independent streaming Python pack-v1 verifier 14/14 synthetic tests | Windows native C++ pack differential or integration |
| OVMS golden C6 | `ba6ec792c3121850fea167fa7d7e190b25fcdc76` | identity lock | **read-only** |

**Status precedence:** later test-specific evidence in PR #8 `UMA-02-HOST/GPU-LIVE.md` and `UMA-03-CYCLE/VERDICT.md` supersedes the stale early `UMA-02-HOST/VERDICT.md` (`G01–G03 blocked`) and stale PR body. Revise the docs and pin all evidence to the current **code** SHA and binary SHA; do not claim these are the same as the outdated `74c8ea0d` host-doc pin. The Wave-01 PR #7 remains GPU-live **NOT_RUN for combined/full inference**, even though PR #8 ran scratch GPU kernels.

## B. What the new UMA finding ACTUALLY means

Physical RAM = 31.54 GiB shared CPU/Arc LPDDR on MSI Claw 8 AI+ / Core Ultra 258V. The reported DXGI SharedSystemMemory 27.44 GiB equals `floor(physical bytes × GpuSystemMemoryPinninglimit(87)/100)` in the local evidence; measured idle LOCAL.Budget ~26.69 GiB. **Neither is additional VRAM, nor evidence of pre-reserved ~27.5 GiB.** WDDM dynamically changes budgets and the CPU, OS, fixed weights, U4 KV, experts, MTP and transient allocations compete for the same 32-GiB pool. Do not change pinning limit/BIOS/driver without an independent reason.

Access policy becomes a third dimension independent of `(layer, expert)` residency hotness and tensor quantization sensitivity:

- **A control:** packed NVMe read → CPU staging → verify → nine `usm_device` `copy_from` → published LRU slot.
- **B scratch:** packed NVMe read → CPU staging → verify → nine CPU scatters into **`usm_host`** → stream fence → published slot. It removes explicit device-copy calls **but is NOT disk-to-final-buffer zero-copy** and still retains staging plus nine CPU writes. Flag default off.
- **C mapped-file cold execution:** **BLOCKED** by arbitrary system pointer/USM capability + pack vs nine-tensor layout + paging/lifetime; no implementation.
- **D CPU cold-expert compute:** hypothesis only; defer until true GPU bandwidth, tail-latency and accepted-token traces exist. CPU and Xe2 share bandwidth.

Intel OpenCL `cl_intel_unified_shared_memory` `clHostMemAllocINTEL` host allocations are allowed without map/unmap but still require explicit host/compute coordination. D3D12 `CacheCoherentUMA=false` is **not a complete proof of OpenCL USM visibility requirements**: confirm the actual NEO contract experimentally and with the extension documentation.

## C. Critical new risk discovered in PR #8: CPU scatter vs in-flight GPU reads

The scratch helper `scatter_verified_record_to_residents()` performs CPU `std::memcpy` to existing slot bytes, and `fence_path_b_publish()` calls `stream.flush(); stream.finish()` **after** scatter. This later wait cannot by itself establish that earlier GPU commands have stopped reading the same slot *before the CPU overwrites it*. Path A's enqueued `copy_from` participates in stream ordering, whereas a host `memcpy` is not a queued GPU command.

`U2-G03` documents lease/overflow/eviction plus GPU digest parity, **not** a multistream or in-flight-overwrite proof. Its report explicitly disclaims overlapping-kernel safety. Thus a live GEMM may read partially overwritten weights in C2/C4/MTP without a new pre-write ownership fence or slot-in-flight protection.

**P0 STOP:** Do not deploy path B or claim GPU acceptance until tests deliberately keep a GPU reader in flight while the CPU tries to reuse the same slot; verify ordering and no data races for same queue, distinct queues, C2/C4 requests, and speculative verify. Fix the ownership protocol first (lease/event/refcount or narrow queue completion *before* host writes, without global `finish()` as the long-term design). A blocking pre-fence is acceptable for a correctness-only trial, not presumed performant. A post-write visibility fence remains a separate requirement.

Other non-promotion risks: `usm_host` default-off env parsing duplicated in allocator/runtime; `residents_are_path_b` selects based on live tensor allocation instead of compiled policy; `staging` is provider-owned and not generally MT-safe; a failed mid-scatter leaves the slot unfilled but physically partially modified, requiring all nine slices to be overwritten before reuse. Test unsupported device/alloc and mixed buffer kinds. None of these is cleared by host tests alone.

## D. Change of priority: next five gates

| Priority / owner | Exact work | Exit / STOP |
|---|---|---|
| **P0-W — Windows Wave-01 integrator** | Retain PR #7 as the pinned control; independently rerun linked tests against exact HEAD and source/binary SHA; review `cannot open` concurrent publication and corruption/require; GPU real pack inference only with operator permission | `WIN_HOST_PASS` is **not** `LIVE_PASS`; no merge to cohort/mainline or OVMS until actual correctness and full acceptance |
| **P0-B — GPU concurrency reviewer** | PR #8 pre-write slot ownership and post-write visibility review; new overlapped GPU-reader→eviction tests, two queues, simultaneous C2/C4 leases, failure injection; `usm_device` and `usm_host` must match | ANY overlapped mismatch/race is `B_BLOCKED`; fix or quarantine path B flag. Source+test SHA receipts required |
| **P1-BW — bench engineer** | Paired, randomized A/B tests on **actual** 0.5–4 MiB representative records (not 2-KiB digest) and real quantized MoE GEMV/GEMM `M=1,2,4,8,11`; measure steady kernel bandwidth, cold fill, verify CPU cost, `finish()` exposed wait, CPU/Arc LPDDR contention, WDDM budget/paging | Record p50/p95/p99 TPOT-like timings, bytes, copies, CPU/GPU utilization, windows of thermal/power drift; no decision from digest proxy. If steady host resident reads degrade enough to outweigh eliminated copy, keep A |
| **P1-S — quality/OVMS integrator** | *Only after P0 correctness and permission*: same models/export/driver, A vs B, `OFFLOAD_RATIO=20` baseline + 25/30 vicinity, r40/r75 only as stress; C1/C2/C4 and tool loops, plain/MTP/DFlash where eligible, context 512/2048/long KV U4, same accepted output | No logits/tool-call/agentic regression. Gate on real accepted tok/s, TTFT, p95/p99 TPOT, physical NVMe bytes/committed token, swap, memory pressure. C6 golden source immutable |
| **P2 — offline evidence / architecture** | Differential native C++ pack vs standalone #6 verifier; join trace sidecar OS counters with model identity, window/accepted token evidence, verify `policy_evidence_eligible`; only then replay LRU vs CLOCK/2Q | #6 merges to Windows integration branch only after accepted gates. **No CLD-04 scheduler, CPU lane, speculative prefetch or memory manager API until real eligible traces and provable improvement** |

All work is Windows-only for this stage; `LINUX_DEFERRED_NO_MACHINE` stays an explicit portability limit, not a Windows failure.

## E. Re-evaluate published measurements correctly

Scratch UMA-03 `BANDWIDTH.md` used a digest kernel reading 2048 bytes, not a MoE matmul: A `usm_device` ~55.1 µs p50 vs B `usm_host` ~50.3 µs. Ratios are launch/finish/noise dominated; derived ~0.037–0.041 GB/s are not Arc memory bandwidth. A cold-miss fixture (~12 iterations, small records) reported A ~179.3 µs, B ~85.2 µs p50 (52.5% lower in that **fixture**). It is *not* a validated full-model or multi-slot performance gain. A/B timing uses distinct primitive code and may include different fence costs. The experimental order and warmup may bias results; use randomized pairing with confidence intervals and repeated runs.

Newest `SWEETSPOT_PASS` at PR #8 HEAD `d82f5f` establishes 10/10 scaled N=40 pack/lease/ratio tests for 20,25,30 and path A/B byte-parity at ratio 20. It does not prove full 26B/35B/Flash-Next models fit or achieve desired TTFT. Do not confuse `OFFLOAD_RATIO` (% eligible expert weights offloaded) with an absolute 32-GiB GPU memory cap or hotness percentage of unrelated fixed tensors.

## F. Model-specific decision path

1. **Gemma 4 26B-A4B:** control for parsers, parallel tools and stable C1/C2/C4. Prefer near-full resident experts only if actual memory budgets after fixed weights/U4 KV/draft allow. Do not regress heretic C6 known-good.
2. **Qwen3.6 / Ornith:** production-priority agentic benchmark with prefix, repeated tool calls, context and MTP/DFlash; start memory-safe ratio 20 with 25/30 A/B. Real routing distribution and compiler eligibility override architecture estimates.
3. **Qwen3.8-Flash-Next:** separate PLE and native MTP footprints; stress target only after true export/loader/Arc memory feasibility, and based on its own routing trace. Never treat published Strata hot expert IDs or precision seeds as our measured cache admission rules.

### Promotion sequence (unchanged invariants, revised ordering)

`#7 host acceptance → source-bound Arc native full-model correctness → #8 race/lifetime fixes → representative A/B GEMM and real model benchmark → #6 verified offline evidence → optional integration decision → A3 trace-based offline replay → **separately authorized** CLD-04 policy/prefetch`.

No automatic PR merges into original cohort, C6 or OVMS. Drafts stay Drafts until human decision. Logs must distinguish `HOST_PASS`, `GPU_KERNEL_PASS`, `MODEL_PASS`, `PERF_PASS`, `NOT_RUN` and `BLOCKED`. Recheck HEADs before any cherry-pick; all pins above are a snapshot, not a floating license to merge.
