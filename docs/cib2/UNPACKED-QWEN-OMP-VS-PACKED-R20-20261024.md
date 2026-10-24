# Unpacked Qwen on omp OVMS vs packed OTD r20 (2026-10-24)

`runtime_acceptance=NO`.

## Do **not** conclude “OFFLOAD_RATIO=20 is free”

| Arm | Decode (same client) | Offload / pack |
|-----|---------------------:|----------------|
| omp OVMS + **unpacked** Qwen R20 weights | **26.7** tok/s | none |
| Stock `C:\llm\ovms` r0 (busy host same day) | 26.3 | none |
| Stock OTD **r20** (prior campaign) | **27.61** | native OTD 20%, no Pack V2 |
| Stock speed-first **r0** | **32.65** | none |
| Pack V2 **packed** OTD r20 busy | **~10.0** | pack + OFFLOAD 20 |

- Unpacked on the ornith-class (omp) server ≈ stock — **no** evidence that this binary alone tanks decode.  
- Native stock r20 already costs ~**15%** vs r0 (32.65→27.61), not zero.  
- Pack V2 packed r20 busy is ~**2.7×** slower than unpacked/omp — miss path read+copy (~85 s timers) + unmeasured sync; **not** “safe 20% for free”.

Receipts (local hub; not all in git):  
`C:\gm\qwenmonster\semantic-refit-2026.4-hub\tasks\C12\reports\live-gpu-metrics-qwen-unpacked-omp-20261024.json`,  
`LIVE-QWEN-UNPACKED-OMP-20261024.md`.

Copied summary JSON below in `evidence/`.
