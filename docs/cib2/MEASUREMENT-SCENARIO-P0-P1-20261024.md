# Measurement scenario — OTD r20 packed regression (+ P0/P1)

`runtime_acceptance=NO`.

## Canonical scenario (what regressed)

This is the **OTD OFFLOAD_RATIO=20 + Pack V2 packed** cohort that measured ~**10 tok/s** decode vs stock r20 **27.61** / r0 **32.65**. Full serve/client table: [LIVE-GPU-BUSY-R20-REPORT-20261024.md](LIVE-GPU-BUSY-R20-REPORT-20261024.md). Trace window: [TRACE-REANALYSIS-R20-20261024.md](TRACE-REANALYSIS-R20-20261024.md).

| Side | Spec |
|------|------|
| Runtime | CIB2 Pack V2 `ovms` (not stock `C:\llm\ovms`) |
| Model | Qwen3.6-35B-A3B INT4 OV |
| Pack | sealed `--moe_experts_pack_dir` (Path A) |
| Plugin | `OFFLOAD_RATIO=20`, `WEIGHTS_PATH=…/openvino_language_model.bin` |
| Batching | `max_num_batched_tokens=16384`, `cache_interval_multiplier=64` |
| Parsers | `qwen3coder` / `qwen3`; MTP off |
| Client | `scripts/cib2/live_gpu/live_gpu_correctness_metrics.py` — temp=0; medium ~817→320; long ~840→512; stream TTFT + non-stream e2e |
| Observed (busy) | TTFT ~14.2 s mean; decode ~**10.0** tok/s; e2e ~7.0; hit_rate ~0.97; miss_copy_s ~36.6 s (corrected) |

**Definition of done for A/B:** same client cells, same batching/parsers; only the arm knobs below change. Report deltas vs **32.65** (r0) and **27.61** (stock r20).

**Stock OVMS + unpacked model (operator-chosen, e.g. Ornith):** measure with this **same client methodology** (not a packed serve). Absolute tok/s are not the Pack V2 baseline; Ornith−vanilla lag is a constant offset when comparing families.

## P0 / P1 extensions on that scenario

| Pri | Work | Why | Against packed r20 |
|-----|------|-----|--------------------|
| **P0** | Time `SynchronousExecutionGate`, `onednn.wait`, `stream.finish` | Hit-path stalls invisible in E-miss timers | Diag counters on Pack V2 serve |
| **P0** | Free-host r20 **packed, no** `MOE_OTD_TRACE` | Drop seal/verify + trace overhead | Repeat canonical serve/client without trace |
| **P0** | CIB2 r20 **unpacked** vs **packed** | Price of PackV2 alone | Same binary/ratio; pack dir on/off |
| **P1** | `MOE_OTD_PERF_LOG` → `pack_verify_ns` | Checksum gap | On packed free arm |
| **P1** | Trace layer id → model layer name | PGP placement | From `register_layer` + `L,` lines |

## Arm matrix (all use OTD20 client protocol)

| Arm | OFFLOAD | Pack | Trace | Host | Role |
|-----|---------|------|-------|------|------|
| `pack-r20-busy` | 20 | yes | yes | busy | **Regression reference (done)** |
| `pack-r20-free-notrace` | 20 | yes | no | free | P0 engine vs contention |
| `pack-r20-free-perf-trace` | 20 | yes | yes | free | + PERF verify |
| `cib2-r20-unpacked` | 20 | **no** | optional | free | P0 PackV2 price |
| `stock-r20` | 20 | no | no | free | Stock OTD baseline 27.61 |
| `stock-r0` | 0 | no | no | free | Speed-first 32.65 |
| `ornith-control` | n/a | n/a | no | as-is | Same **client** only; family offset |

## Forbidden while measuring

No drain removal, no checksum off, no LRU/pack rebuild, no RC3B binary freeze break for “speed hacks”.
