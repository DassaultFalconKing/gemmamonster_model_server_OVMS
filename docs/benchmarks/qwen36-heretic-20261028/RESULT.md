# Qwen3.6 heretic speed test, 2026-10-28

Existing server on127.0.0.1:8137, PID8040. No restart/configuration change.
Model: tvall43-Qwen3.6-35B-A3B-heretic-int4-ov; API qwen36-35b-a3b-heretic-int4.
Intel Core Ultra7 258V / Arc140V, driver32.0.101.9150; RC4 py_off, VLM_CB/GPU, offload20, KV u4, 2slots, batch4096, cache_size0, interval256, prefix cache ON.
Method: existing speed-20261024/run_ab.py request/timing implementation; C12 live-long-prompt; 2warmups excluded, 3measured runs, temperature0, enable_thinking=false, seed unset. Input1788/output256 tokens per run.

| Run | Decode tok/s estimate | TTFT s | Wall s |
|---|---:|---:|---:|
| 1 | 16.398 | 18.531 | 34.081 |
| 2 | 16.569 | 17.674 | 33.065 |
| 3 | 15.060 | 18.690 | 35.622 |

Median decode: 16.398 tok/s; median TTFT: 18.531s.
Decode=(usage.completion_tokens-1)/(last-first nonempty SSE delta). Client-observed estimate, not internal token timestamps. TTFT includes prefill/queue/transport; pure prefill throughput NOT_AVAILABLE.
All five requests, responses and per-run metrics are retained. Model-specific results only; no transfer to baseline/Fast/Ornith or different runtime settings. No agentic/tool acceptance claim.
provenance.json records actual process command, loaded-module paths/on-disk hashes and model metadata. Full weight hashes NOT_RUN. Server left unchanged and running.
