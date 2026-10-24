# Speed-first control: Qwen3.6-35B-A3B INT4 on Arc 140V (stock OVMS 2026.4)

Canonical **baseline for CIB2 Pack V2 comparisons**. Not a proven hardware ceiling — best *measured* stock config.

Source: `C:\Users\testc\qwen36-35b-a3b-baseline\DEPLOYMENT_REPORT.md` (Phase 2A / 2D).

## Confirmed peaks

| Metric | Value | Notes |
|--------|-------|--------|
| Decode (median) | **32.65 tok/s** | No expert offload; max single run 32.83 |
| Prefill 32K | **~583 tok/s** | With `max_num_batched_tokens=16384` (was ~273 stock defaults) |
| TTFT @ 32K | ~54.7–59.0 s | After batching tune (was ~120 s) |
| Memory | ~19 GB GPU shared | Near machine limit |

Also recorded elsewhere in same campaign: stock **OFFLOAD_RATIO=20 → 27.61 tok/s** decode (not the speed-first control).

## Fast configuration

| Parameter | Value |
|-----------|--------|
| Runtime | OVMS **2026.4.0 stock** (`C:\llm\ovms`) |
| Model | `OpenVINO/Qwen3.6-35B-A3B-int4-ov` under baseline models dir |
| Device | `GPU` |
| Task | `text_generation` |
| `OFFLOAD_RATIO` | **omit / 0** (fully resident — no disk expert offload) |
| `max_num_batched_tokens` | **16384** |
| `cache_interval_multiplier` | **64** |
| Pipeline | `VLM_CB` (automatic) |
| MTP / speculative | **off** |
| Tool parser | `qwen3coder` |
| Reasoning parser | `qwen3` |
| Test sampling | `temperature=0`, `seed=1234` |

## PowerShell launch (stock)

```powershell
$env:PYTHONHOME = "C:\llm\ovms\python"
$env:PYTHONPATH = ""
$env:PATH = "C:\llm\ovms;C:\llm\ovms\python;$env:PATH"

$ovmsArgs = @(
    "--model_path", "C:\Users\testc\qwen36-35b-a3b-baseline\models\Qwen3.6-35B-A3B-int4-ov",
    "--model_name", "qwen36-35b-a3b-int4-baseline",
    "--target_device", "GPU",
    "--task", "text_generation",
    "--tool_parser", "qwen3coder",
    "--reasoning_parser", "qwen3",
    "--cache_interval_multiplier", "64",
    "--max_num_batched_tokens", "16384",
    "--rest_port", "8000",
    "--port", "9000"
)

& "C:\llm\ovms\ovms.exe" @ovmsArgs
```

Do **not** pass `OFFLOAD_RATIO` for this control.

## How CIB2 agents must use this

- Primary decode target to beat/match: **32.65 tok/s** at r0-equivalent (resident).
- Secondary stock OTD point: **27.61 tok/s** at r20 if comparing offload paths.
- Prefill target: **~583 tok/s** @ 32K with batching 16384.
- Do not claim KV U4 / MTP gains unless newly measured.
- Pack V2 / CIB2 head numbers (e.g. ~8–12 tok/s) are **not** this baseline; report deltas vs these figures explicitly.
