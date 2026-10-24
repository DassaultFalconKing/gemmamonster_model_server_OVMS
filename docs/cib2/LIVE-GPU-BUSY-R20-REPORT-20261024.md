# Live GPU Pack V2 r20 — busy cohort report (2026-10-24)

`runtime_acceptance=NO`. Path A only. Compared to stock speed-first control in [SPEED-REFERENCE-QWEN36-STOCK-2026.4.md](SPEED-REFERENCE-QWEN36-STOCK-2026.4.md).

## Exact serve settings (this cohort — not stock control)

| Parameter | Value |
|-----------|--------|
| Runtime | `C:\git\cib2-packv2-build-20261024\ovms-runtime\ovms.exe` (CIB2 Pack V2, **not** `C:\llm\ovms`) |
| Model | `…\qwen36-35b-a3b-baseline\models\Qwen3.6-35B-A3B-int4-ov` |
| `--model_name` | `qwen` |
| `--target_device` / `--task` | `GPU` / `text_generation` |
| `--moe_experts_pack_dir` | sealed `packv2-generations\generation-06784763…` |
| `--plugin_config` | `OFFLOAD_RATIO=20`, `WEIGHTS_PATH=…/openvino_language_model.bin` |
| `--max_num_batched_tokens` | `16384` |
| `--cache_interval_multiplier` | `64` |
| parsers | `qwen3coder` / `qwen3` |
| ports | REST `8000`, gRPC `9000` |
| MTP / speculative | off (not passed) |
| `MOE_OTD_TRACE` | `evidence-live-gpu-busy-vs-free\moe-otd-trace-r20-busy.log` (restarted serve) |
| Client | `temperature=0`; medium ~817→320, long ~840→512; stream TTFT + non-stream |
| Load label | **busy** (RAM ~1.7 GiB free at times) |

Harness code: `scripts/cib2/live_gpu/`. Receipt: [evidence/live-gpu-r20-metrics-busy-20261024.json](evidence/live-gpu-r20-metrics-busy-20261024.json).

## Results (busy)

| Cell | Prompt→completion (tok) | TTFT | Decode TPS | E2E non-stream TPS |
|------|-------------------------|------|------------|--------------------|
| medium | ~817→320 | **17.4 s** | **10.6** | **6.5** |
| long | ~840→512 | **10.9 s** | **9.5** | **8.1** |
| overall | — | **14.2 s** | **10.0** | **7.0** |

Earlier short-prompt busy smoke (attempt1): TTFT ~1.09 s, decode ~12.2 tok/s, e2e ~9.8 (96-tok completions).

### Expert cache (`MOE_OTD_TRACE`)

- hit_rate **0.971** (≈1.14M hits / 34k misses in delta window)
- miss_bytes ~52 GiB logical, miss_read_s ~48.6 s accumulated in trace stats

### UMA (N3 probe)

- system available Δ ≈ **−0.67 GB** over speed cells
- WDDM process usage Δ ≈ 0 (probe still limited / not full OTD global accounting)

## Deltas vs stock control

| Reference | tok/s | This busy Pack V2 decode (~10.0) |
|-----------|-------|----------------------------------|
| Stock r0 (speed-first) | **32.65** | **≈ −3.3×** |
| Stock OTD r20 | **27.61** | **≈ −2.8×** |

Prefill 32K stock (~583 tok/s) **not** re-measured in this busy cohort.

## Next (search / free cohort)

1. Free-CPU re-run same harness (`LIVE_LOAD_LABEL=free`) after seal/verify idle and RAM headroom.
2. Stock r0 control relaunch from `C:\llm\ovms` for same-day A/B if needed.
3. Keep hunting decode regression on Pack/OTD head path (see `orchestration/decode-regression-20261022`).
