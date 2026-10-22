# UMA-00 / UMA-01 RISKS

## Coherence and visibility

- **CacheCoherentUMA=false:** host stores into USM host memory are not automatically GPU-visible; publish must follow a documented fence / blocking sync (today: blocking `copy_from` / stream finish semantics).
- **SHARED_SYSTEM_MEM=0:** ordinary `malloc`/anonymous maps are not GPU USM; importing wrong pointers will fail or silently force copies.
- **Coarse-grain SVM only:** fine-grain system SVM is unavailable on the Arc OpenCL device; do not design around fine-grain concurrent CPU/GPU mutation.

## Eviction / lifetime

- LRU `set_filled` must remain after successful verify; a path-B CPU scatter that mutates a slot before verify breaks fail-closed if a concurrent reader can observe the slot.
- Eviction during in-flight GPU use remains a fencing hazard (existing OTD concern; unchanged by UMA evidence).
- File-backed path C: Windows file replacement and lazy page-ins can desync checksum snapshots (CLD-01B pin contracts).

## Windows memory pressure

- DXGI LOCAL budget and process commit are **overlapping** constraints on one LPDDR pool. Growing expert cache or staging can starve KV / OS / UI without any “27.5 GiB reserved VRAM”.
- `GpuSystemMemoryPinninglimit=87` is a driver/OS policy knob observed read-only; changing it is **out of scope** and could destabilize the host.
- Under pressure WDDM may migrate/trim shared allocations; assuming pinned residency without measurement is unsafe.

## Performance / false wins

- Eliminating `enqueue_memcpy` but retaining nine CPU `memcpy` scatters may not improve end-to-end miss latency if NVMe or checksum dominates.
- `usm_host` residents may reduce GPU bandwidth vs `usm_device` for MoE GEMM consumers on some drivers — must be measured in UMA-03, not assumed from UMA=true.
- Dual accounting (shared GPU counters + process working set) can double-count the same physical pages in human reports.

## Process / governance

- Premature merge into Wave-01 / C6 / production OVMS remains forbidden.
- Linux absence must stay labeled `LINUX_DEFERRED_NO_MACHINE`, not a Windows fail.
- Prototype code must stay scratch-only until UMA-02 operator approval.
