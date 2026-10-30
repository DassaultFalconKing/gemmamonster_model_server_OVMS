# Memory lean + agent acceptance (2026-10-30)

Constraint: **one OVMS only**. Success = lower RAM pressure **and** multi-step tool agenting without errors (not speed alone).

## Harness

`agent-accept.py`: ping → single tool+replay → two-tool chain → recovery tool/final.  
`speed-probe.py`: 3× medium decode samples.  
Memory: free physical RAM samples via `sample-mem.ps1`.

## Gemma26

| Profile | Agent | Decode median | min free RAM | Notes |
|---|---|---:|---:|---|
| **lean: seqs=2, workers=4, batch=1024** | **PASS** | **24.04 tok/s** | idle **3.71** / after agent **4.03** GiB | WS ~15.6 GiB |
| prior default seqs=4/batch2048 | (earlier) | ~25–26 | often ~2.3 GiB class | vision risk historically |

New launcher defaults match **lean**. Use `-Seqs 4 -RestWorkers 8 -Batch 2048` when you need more parallel subagents.

## Ornith

| Profile | Agent | Decode median | min free RAM | Notes |
|---|---|---:|---:|---|
| o2 / batch2048 | **PASS** | 20.32 | idle 1.78 / after agent **0.75** GiB | still too tight |
| **o10 / batch2048** | **PASS** | **22.67 tok/s** | idle **3.95** / after agent **2.37** GiB | accepted lean |
| prior resident o0/batch4096 | (earlier) | ~32 | often &lt;1 GiB class | speed-first, not mem-first |

New launcher defaults: **Offload=10, Batch=2048, Seqs=1**.

## Verdict

Both models can agent correctly on lean profiles. Memory headroom becomes usable (~2–4 GiB free) instead of &lt;1 GiB. Ornith speed drops vs resident; Gemma26 speed stays near prior solo range on this host.
