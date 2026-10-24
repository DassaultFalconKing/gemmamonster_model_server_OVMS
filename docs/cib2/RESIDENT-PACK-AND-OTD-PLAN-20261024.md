# CIB2 Resident Pack + native OpenVINO OTD: implementation program

Date: 2026-10-24. Status: **EXPERIMENTAL / OFFLINE_ONLY / runtime_acceptance=NO**.
Base: `diag/otd-trace-reanalysis-r20-20261024` at `8fde728eebba47607992dd692672b0d128ac3b3e`. No change to C6, production runtime, routing, cache policy, output numerics, or stock OVMS.

## Decision and boundaries

**Static by-design != expert hotness.** Compile-graph-owned embeddings, attention, Gated DeltaNet, layernorm, router, shared experts, LM head and any checkpoint-specific state must be inventoried as non-pageable *where they actually need residency*. Routed experts are handled by the native `OffloadExpertWeightProvider` + PackV2 + LRU. In native `moe_offload_constant.cpp`, only routed inputs 3..11 get partial upload, shared inputs 12..21 stay fully resident. Absence from E-traces does **not** prove GPU physical residency.

Static Resident Pack is a **storage/launch artifact**, never a second GPU allocation or a new execution engine. Until a native loader is proven, it is exclusively an **offline candidate**. OpenVINO already maps IR weights on demand and supports compiled-model caches; Resident Pack must beat those baselines. Do not ship a second, redundant copy into UMA. The physical machine has one ~32 GiB LPDDR pool shared by host, Arc 140V, KV, staging, OS cache and GPU allocations.

```
                          source checkpoint XML/BIN
                                    |
                 exact graph/constant inventory + SHA
                                    |
             +----------------------+-------------------+
             |                                          |
     STATIC REQUIRED DATA                        ROUTED MOE EXPERTS
   (graph-verified only)                       (256 IDs / MoE layer)
             |                                          |
    Resident Pack candidate                   PackV2 immutable records
 (cold-start comparison only)                   + placement/residency
             |                                          |
 OpenVINO's existing loader                     native OTD provider
 (no GPU duplicate allocation)                   GPU slot LRU arena
             +----------------------+-------------------+
                                    |
                           GPU execution graph
```

## Evidence checkpoint

- Qwen3.6-35B-A3B INT4 OV, Arc 140V, 40 MoE layers, 256 experts/layer, r20 => 204 GPU slots/layer.
- CIB2 busy r20 packed decode ~10.02 tok/s; stock r20 ~27.61 tok/s; stock r0 best ~32.65 tok/s. These are not yet same free-host A/B cohorts.
- Receipt window: 1,173,733 touches, 34,428 misses (97.07% hit), ~56.27 GB logical miss read, 48.558 s read + 36.571 s blocking copy. Sum is **not** exclusive wall time and `copy_from(true)` can include queue waits. Gate, drain, verify, trace and contention remain unmeasured.
- Residency evidence `(layer, expert)`: 1,195 hit-only, 8,620 had miss, 425 untouched, 5,096 thrash heuristic. None of these is a lifetime pin assertion. Ornith has separate checkpoint/profiles; never apply an assumed constant TPS gap without paired measurements.

## Implementation phases and hard gates

| Gate | Change | Deliverable | Stop condition |
|---|---|---|---|
| **P0 perf attribution** | Instrument `SynchronousExecutionGate` queue/hold, per-call `onednn.wait`, `stream.finish`, `copy_from`, checksum, trace overhead; free host A/B stock r0/r20, CIB2 r20 packed/unpacked with same exact client | time breakdown per layer/per token and loaded DLL provenance | Do **not** alter event/barrier lifecycle until hit-path cost proven |
| **R1 static inventory** | Inspect source IR *and* post-transformation GPU compiled graph with final tensor roles, dimensions, owner and allocation; stable checkpoint/export/quant/driver identity | reviewed non-routed allowlist; unknown stays unknown | No name-pattern-only auto-pinning, no E-trace inference |
| **R2 offline pack (implemented here)** | `scripts/cib2/resident_pack.py`: inventory IR Const byte ranges, build from explicit reviewed allowlist, SHA256-protected aligned `resident.pack`, manifest and independent verify | immutable offline generation for bench; negative tests | `consumption=OFFLINE_ONLY`, `runtime_acceptance=NO`; no modification to OpenVINO XML |
| **R3 native loading prototype** | *After R1/R2*: add optional compiled-graph loader bound to exact model generation; consume static records without duplicating source-weight and device allocations; retain OpenVINO cache as fallback | cold/warm load timings; total physical bytes / peak RAM; exact tensor parity | Fail closed on hash/offset mismatch, double allocations, incompatible weightless cache |
| **E1 OTD hit-path** | replace only proven redundant full-stream drains with producer/terminal consumer GPU completion-event leases; ensure slots cannot be replaced until all readers retire; keep synchronous fail-stop fallback | A/B decode/TTFT with stress concurrent C1/C2/C4 | Never remove safety waits or checksum simply to raise TPS |
| **E2 replay priorities and budgets** | Replay exact per-layer E-events with initial cache state, observed evictions and baseline reproduction; compare soft priority, 2Q/CLOCK/weighted policy; evaluate unequal compile-time per-layer slot capacities at same total unique bytes | Pareto frontier miss cost vs slot MiB, separately Qwen/Ornith and plain/speculative | Do not claim simulated benefit unless baseline reproduces measured misses; no runtime routing change |
| **E3 bounded prefetch** | Only after safe leases + coherent UMA reservations, source record pre-arm, scheduler demand priority; cancellation and multi-request correctness | controlled r20/r40/r60 + 32K contexts, physical NVMe bytes/token | reject paging, excessive staging, fairness/p99 regressions |

### Current code limits (deliberate)

`resident_pack.py inventory` understands IR `Const` nodes with explicit `offset`, `size`, and **direct** consumer edges. Direct `MOECompressed` routed inputs 3..11 are classified as `routed` and refused by `build`; direct shared inputs 12..21 are `shared`. Most exported source IRs will have unfused graphs, so many real static constants are `unknown`; they **require compiled GPU graph review** to be allowlisted. This is deliberately fail-closed at the deployment boundary: a reviewed JSON annotation is an offline assertion, **not** runtime proof or automatic injection. Do not feed unknowns to a production GPU loader. IR input-port numbering must be validated against the actual target graph before treating even `shared` as authoritative.

Pack records contain unmodified source byte ranges with SHA256 and 4096-byte alignment; manifest links source XML/BIN hashes. No reshaping, recompression, quantization, contiguous-device allocation, model `.xml` rewrite, or GPU execution occurs. `resident.pack` provides no runtime speed-up without R3. Generated output directories are single-writer, never overwritten by the tool; carry immutable build IDs in directory name. Existing PackV2 remains authoritative for routed experts.

## Offline commands (Windows PowerShell, from OVMS checkout)

```powershell
$Xml = 'C:\models\Qwen3.6-35B-A3B-int4-ov\openvino_language_model.xml'
$Bin = 'C:\models\Qwen3.6-35B-A3B-int4-ov\openvino_language_model.bin'
python scripts/cib2/resident_pack.py inventory --xml $Xml --bin $Bin --out C:\tmp\resident-inventory.json
# Review the inventory against the compiled GPU graph; manually create C:\tmp\resident-selection.json:
# {"schema":"cib2.static_resident_selection.v1", "source_xml_sha256":"<inventory value>",
#  "source_bin_sha256":"<inventory value>",
#  "selections":[{"layer_id":123,"evidence":"Compiled GPU graph confirmed constant non-routed requirement"}]}
python scripts/cib2/resident_pack.py build --inventory C:\tmp\resident-inventory.json --selection C:\tmp\resident-selection.json --bin $Bin --out-dir C:\tmp\resident-gen-001
python scripts/cib2/resident_pack.py verify --pack-dir C:\tmp\resident-gen-001 --bin $Bin
python -m unittest discover -s scripts/cib2/tests -p test_resident_pack.py -v
```

Do not run `build` with a guessed layer ID. In R1, the local agent should first produce a real reviewed mapping and compare to OpenVINO `CACHE_MODE=OPTIMIZE_SPEED` / `OPTIMIZE_SIZE`, `ENABLE_MMAP` behavior and the existing OVMS cache startup path. Verify the actual plugin settings on compiled OpenVINO 2026.4.

## Measurements, acceptance and handoff

Required baseline config: `max_num_batched_tokens=16384`, `cache_interval_multiplier=64`, KV baseline held constant, MTP off, exact model hashes, driver DLL attribution, same prompt set, host free. Metrics: load compile time, time-to-ready, TTFT, decode tok/s, end-to-end tok/s, LRU hit/miss, per-layer gate/wait/drain, `pack_verify_ns`, physical disk read, per-process allocations + WDDM shared budget, OS pagefile use and peak physical memory. Measure with and without trace separately.

**Performance gates**: R3 must lower actual cold-start or warm-start latency vs OpenVINO cache while preserving numerical outputs, without extra steady-state UMA cost. E1 must regain stock r20 ~27.61 tok/s in a *same-cohort* fair comparison before proposing r40 speed preservation. E2/E3 must improve measured decode and p95 at equal physical footprint and no correctness or C1/C2/C4 regression.

Local agent: start by running unit tests of R2 and collecting R1 compiled graph inventory. Run the already approved `MEASUREMENT-SCENARIO-P0-P1-20261024.md` before GPU code changes. Never merge into canonical C6, PR #10 or PR #29 until their independent gates pass. Produce a dated report with exact artifacts and negative-test evidence; mark `runtime_acceptance=NO` until live GPU parity and performance are independently verified.

Sources: [OpenVINO Core/read_model](https://docs.openvino.ai/2026/api/c_cpp_api/classov_1_1_core.html), [2026 device caching props](https://docs.openvino.ai/2026/api/c_cpp_api/group__ov__runtime__cpp__prop__api.html), [memory mapping](https://docs.openvino.ai/nightly/openvino-workflow/running-inference/optimize-inference/optimizing-memory-usage.html); our `docs/cib2/RESIDENCY-FROM-TRACE-R20-20261024.md`, `TRACE-REANALYSIS-R20-20261024.md` and OpenVINO fork `moe_offload_constant.cpp`, `moe_otd_residency_v2.hpp`.
