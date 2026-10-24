# Residency from OTD r20 packed trace (2026-10-24)

`runtime_acceptance=NO`. Offline from the same receipt window as [TRACE-REANALYSIS-R20-20261024.md](TRACE-REANALYSIS-R20-20261024.md).  
JSON: [evidence/residency-from-trace-r20-20261024.json](evidence/residency-from-trace-r20-20261024.json).

## 1. What the handoff metrics actually measured

| Bucket | Window value | Meaning |
|--------|-------------:|---------|
| Touches | 1 173 733 | Expert uses (hit+miss) |
| Hits | 1 139 305 (97.07%) | Expert **already in GPU LRU slot** — no pack read |
| Misses | 34 428 | Expert **not in GPU** → pack record read + `copy_from` into a slot |
| miss_read_s | 48.56 | Host wall of pack reads |
| miss_copy_s | 36.57 | Host wall of blocking GPU copies (may include queue wait) |
| miss_transform_s | 0 | Pack path does not split transform into E |
| Gate / drain / verify | NOT_MEASURED | Still open P0/P1 |

So the “regression timers” are almost entirely **miss path: pack → staging → GPU resident slot**, not the 97% hit path (those hits still may pay **unmeasured** sync/gate cost).

## 2. Permanent capacity vs demand-loaded (how to read it)

With `OFFLOAD_RATIO=20` every MoE layer registered:

```text
L,*,*,*, capacity=204, num_expert=256, top_k=8
```

| Where | What | Size cue |
|-------|------|----------|
| **GPU resident arena (fixed capacity)** | Up to **204** expert records **per layer** in LRU slots (Path A `usm_device`) | ≈204 × 1 634 304 ≈ **318 MiB / layer** expert weights |
| **Pack-backed / not in a slot** | The other experts (up to **52** “missing” from full 256) live in the pack until a miss brings them in (evicting someone) | Demand-loaded; E-line `hit=0` |
| **Always source-pinned (not in E-trace)** | Embeddings, attention, router, norms, shared dense, etc. | Stay mapped; **never** show as expert miss/hit |

Important vocabulary:

- **“Постоянно в GPU”** here means **slot capacity is permanent** (204 slots always allocated), **not** that the same 204 expert IDs stay forever. LRU swaps IDs; `evicted` on a miss names who left GPU back to pack-backed state.
- **Hit** = was in a GPU slot at touch time. **Miss** = was only in pack (or cold) and was copied into GPU.

## 3. What the busy window shows (40 layers × 256 IDs)

| Class (layer,expert) | Count | Reading |
|----------------------|------:|---------|
| Hit-only in window | 1 195 | Used, but never miss in this window (likely already resident before window or very hot) |
| Any miss | 8 620 | At least once brought from pack → GPU |
| Never touched | 425 | Stayed out of the working set (pack-only / unused) |
| Thrash heuristic (≥3 misses and ≥2 times victim) | 5 096 | Heavy pack↔GPU churn — main drivers of the 85 s read+copy sum |

End-of-window snapshot (layer 0): **204/204 slots filled**; only **9** of those end-residents were hit-only in-window — **195** had been miss-loaded during the window. Early layers (0–2) touch almost all 256 experts and thrash hardest.

## 4. How to answer “what stayed vs what went to GPU”

From **this** trace alone you can classify:

1. **Static:** 204 GPU slots vs 52 offload pressure per layer (from `L` + OFFLOAD_RATIO).  
2. **Dynamic working set:** hit vs miss vs never-touched vs thrash (from `E`).  
3. **Who left GPU:** `evicted` expert id on misses.  
4. **End occupancy:** last `slot→expert` map per layer.

You **cannot** yet claim lifetime pins or UMA host vs device without residency/placement plan logs + P0 sync timers (`MEASUREMENT-SCENARIO-P0-P1-20261024.md`).

## 5. Practical next probe (minimal)

1. Dump end-of-run slot maps (or reparse as above) → “who is in GPU now”.  
2. Join thrash top-N experts to PGP hot/warm/cold labels once layer-id→name map exists (P1).  
3. Free packed r20 **no-trace** + `MOE_OTD_PERF_LOG` to separate churn cost from host contention.
