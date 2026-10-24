# Trace reanalysis — Pack V2 r20 busy (2026-10-24)

`runtime_acceptance=NO`. Offline only. No new GPU benchmarks. Branch `diag/otd-trace-reanalysis-r20-20261024` from `6d5e4a5d5`.

Evidence JSON: [evidence/trace-reanalysis-r20-20261024.json](evidence/trace-reanalysis-r20-20261024.json).  
Source trace (local build-root, not committed): `moe-otd-trace-r20-busy.log` (66 282 817 bytes).  
Receipt (unchanged): [evidence/live-gpu-r20-metrics-busy-20261024.json](evidence/live-gpu-r20-metrics-busy-20261024.json).

## 1. Trace window validation

Receipt snapshots: before **9 418** E / after **1 183 151** E.

| Check | Expected | Got | Status |
|-------|---------:|----:|--------|
| Window E count | 1 173 733 | 1 173 733 | OK |
| Δ hits | 1 139 305 | 1 139 305 | OK |
| Δ misses | 34 428 | 34 428 | OK |
| hit_rate | 0.9707 | 0.9707 | OK |
| miss_bytes | 56 265 818 112 | 56 265 818 112 | OK |
| miss_read_s | 48.558 | 48.558 | OK |

`validation_status=OK`. Full file E count still equals receipt after (not truncated/extended). Window = E-records **(9418, 1183151]** by cumulative count.

Parser regressions covered by `scripts/cib2/live_gpu/tests/test_moe_otd_trace_parse.py` (E `copy_ns=parts[12]`, C `status=parts[6]`, delta helpers, streaming).

## 2. Corrected read / transform / copy (window)

| Metric | Value | Notes |
|--------|------:|-------|
| miss_read_s | **48.558** | Matches receipt delta |
| miss_transform_s | **0.0** | Pack `fill_weights_from_pack` does not attribute transform into E; verify is outside E |
| miss_copy_s | **36.571** | Was published as **0.0** (parser took `parts[11]`=transform) |
| read+transform+copy | **85.129** | Sum of instrumented miss-path timers |
| copy_us/miss | mean 1062 / p50 604 / p95 1815 / p99 5981 | Blocking `copy_from(..., true)` wall |
| read_us/miss | mean 1410 / p50 1347 / p95 2010 / p99 3197 | Pack record read wall |
| bytes/miss | 1 634 304 | Constant expert record size |
| logical read MiB/s | 1105 | `miss_bytes/miss_read_s` — **not** NVMe physical BW |
| effective copy MiB/s | 1467 | `miss_bytes/miss_copy_s` — **not** GPU physical BW |

**Copy vs read:** aggregate copy (36.6 s) is **~75%** of aggregate read (48.6 s). Copy is first-class cost, not free.

`copy_ns` measures host wall around synchronous `copy_from`; it **may include GPU queue wait**, not pure DMA.

## 3. Top bottleneck layers (by read+copy)

| Layer | hit_rate | misses | read_s | copy_s | eviction_reloads |
|------:|---------:|-------:|-------:|-------:|-----------------:|
| 2 | 0.914 | 2546 | 3.50 | 2.69 | 1841 |
| 0 | 0.911 | 2644 | 3.44 | 2.23 | 2036 |
| 1 | 0.929 | 2103 | 2.90 | 2.10 | 1588 |
| 26 | 0.969 | 921 | 1.51 | 3.12 | 677 |
| 3 | 0.955 | 1320 | 1.87 | 1.50 | 984 |

Global hit_rate **0.9707** hides early-layer hit_rates ~0.91 and layer 26’s high copy share.

## 4. Cache eviction / reload

- Eviction field present on misses; **24 655** misses reload an expert that was among the last 64 eviction victims on that layer (~**72%** of misses).
- Top reloaded experts per hot layer show repeated victims (e.g. layer 0 experts 12/3/6 with 21 misses each) — consistent with **capacity thrashing under top-k routing**, not a proof of LRU implementation bug by itself.
- Classification: **LIKELY** thrashing contributes to miss volume; policy change still **forbidden** this phase.

## 5. Stock OTD vs Pack V2 (source-confirmed)

From `cib2-packv2-ov-20261024` (not stock tree binary diff in this pass):

| Topic | Stock-style tensor fill | Pack V2 `fill_weights_from_pack` |
|-------|-------------------------|----------------------------------|
| Disk I/O | Per-tensor `weight_reader.read` (up to 9 ranges) | **One** `read_verified_record` (expert payload) |
| Integrity | N/A in that fill path | CPU checksum on staging; failures counted in `pack_verify_*` |
| GPU publish | Per-tensor `copy_from(..., true)` after optional transpose | **Nine** `copy_from(..., true)` from staging |
| E-line timing | read / transform / copy split | read + copy; **transform_ns=0**; verify timed only under `MOE_OTD_PERF_LOG` |
| Exec serialize | — | `SynchronousExecutionGate` + `drain_or_fail_stop(onednn.wait, stream.finish)` on offload scope exit |

**CONFIRMED (code):** Pack does **not** reread the whole pack file per miss; it loads one expert record.  
**CONFIRMED (code):** Sync `copy_from(..., true)` exists on both paths; Pack still issues nine blocking copies after verify.  
**CONFIRMED (code):** Gate + dual drain are Pack/OTD safety paths; duration **NOT_MEASURED** in this trace.

## 6. Latency contribution (limits)

Reference decode: stock r0 **32.65**, stock r20 **27.61**, Pack V2 busy r20 **10.02** tok/s ([SPEED-REFERENCE](SPEED-REFERENCE-QWEN36-STOCK-2026.4.md), [busy report](LIVE-GPU-BUSY-R20-REPORT-20261024.md)).

| Statement | Class |
|-----------|-------|
| Published `miss_copy_s=0` was false; window copy is **36.57 s** | **CONFIRMED** |
| Miss path instrumented sum (read+copy) = **85.13 s** inside E-window span **477.0 s** | **CONFIRMED** (timer sums ≠ exclusive wall) |
| Busy cohort had concurrent seal/verify | **CONFIRMED** (receipt `contention.seal_verify_pid_alive`) |
| Miss I/O alone fully explains 27.61→10.02 | **REJECTED** as proven — need same-cohort free A/B; timer sum is ~18% of E-span, while decode is ~2.8× slower than stock r20 |
| Sync gate / OneDNN·OpenCL drains add material stall | **LIKELY** (code always drains on scope exit when offloaded) but **NOT_MEASURED** |
| Checksum verify cost | **NOT_MEASURED** (`[OTD_PERF]` / `pack_verify_ns` absent in busy serve logs) |
| `MOE_OTD_TRACE` overhead | **NOT_MEASURED** |
| Seal/verify CPU share of the 10 tok/s | **UNRESOLVED** quantitatively |

**Answer to the main question:** Proven miss-path timers (read **48.6 s** + copy **36.6 s**) are a **large, previously invisible** cost and must stay on the critical backlog; they do **not**, by themselves, close the gap to stock r20. A **majority share** of the remaining 27.61→10.02 degradation is still **UNRESOLVED** among sync/drain serialization, GEMM/exec, verify, trace overhead, and host contention — and requires instrumented A/B, not inference from this file alone.

## 7. Unresolved delay sources

| Item | Status | Minimal instrumentation |
|------|--------|-------------------------|
| `pack_verify_ns` | NOT_MEASURED | Run with `MOE_OTD_PERF_LOG=1`; capture `[OTD_PERF]` stderr |
| Gate lock wait | NOT_MEASURED | Timestamp `SynchronousExecutionGate::Scope` ctor after `lock_` / dtor before/after `drain_` |
| `onednn.wait` + `stream.finish` | NOT_MEASURED | Wrap `drain_or_fail_stop` lambdas with steady_clock |
| Hit-path sync | NOT_MEASURED | Same gate still taken when `is_offloaded()`; separate hit vs miss drain samples |
| Trace fwrite cost | NOT_MEASURED | A/B identical serve with/without `MOE_OTD_TRACE` |
| Seal/verify contention | NOT_MEASURED | Free-CPU cohort (`LIVE_LOAD_LABEL=free`) |

Do **not** disable checksums or safety drains for speed.

## 8. Next minimal A/B plan (measurement only)

1. **Free Pack r20** — no seal/verify; `MOE_OTD_PERF_LOG=1` + `MOE_OTD_TRACE`; same prompts/seed as busy receipt.  
2. **Stock 2026.4 r20** — same prompts; OFFLOAD_RATIO=20; no packs.  
3. **Pack r20 PERF-only** — no trace file; compare tok/s vs (1) for trace overhead bound.  
4. **Optional micro-patch (diag only):** gate/drain timers → new counters; no policy/pack/binary freeze break for production RC3B.

Acceptance for a later phase: attribute tok/s delta with measured verify + drain + miss I/O on a free host before any architectural optimization.
