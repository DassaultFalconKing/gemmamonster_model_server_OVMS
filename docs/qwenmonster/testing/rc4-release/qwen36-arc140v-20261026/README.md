# Tested working combination: Qwen3.6 / Arc 140V

Recorded on **2026-10-26**, Europe/Berlin. The operator designated this tuple
as the working baseline for subsequent use. It is a **sequential-request
serving profile**, with measured speed on the published **RC4 Python Off**
package. This does not extend acceptance to other models, Python On,
simultaneous long contexts, agentic correctness or a different GPU binary.

## Configuration

| Parameter | Tested setting |
| --- | --- |
| Runtime | GEMMAMONSTER 2026.4 RC4, Windows x86_64 Python Off |
| Built source checkpoint | `b7812066afb35377ec9da2f3bc06fb3f1d261460` |
| Published tag checkpoint | `362b1d293b0461fa6b8772f1cf34d075c7ee23e4` |
| Python Off ZIP SHA256 | `75d9b677d5b7435f3057f92cea5e9d0b79e99549df70a98358d50d09eff5246a` |
| GPU plugin | Retained custom GPU DLL `21a2fd9f...`; exact loaded-module hashes in the lock |
| Model | `OpenVINO/Qwen3.6-35B-A3B-int4-ov`; local download manifest records revision `33648de852df51faf681ec3930ba72b58fa0eae5` |
| Hardware | Intel Arc 140V, 32 GB UMA (31.54 GiB OS-visible) |
| GPU driver | `32.0.101.9150` |
| Device / task | `GPU` / text generation |
| Pipeline | `VLM_CB` |
| KV precision | `KV_CACHE_PRECISION=u4` |
| Expert offload | `OFFLOAD_RATIO=20`, model's own weights file and writable cache directory |
| Scheduler slots | `max_num_seqs=2` |
| Prefill batch | `max_num_batched_tokens=4096` |
| Prefix cache | Enabled, `cache_interval_multiplier=256` |
| Dynamic split/fuse | Enabled |
| KV allocation | Dynamic, `cache_size=0` |
| Token eviction | Disabled |
| HTTP workers | `rest_workers=1`, mitigation for observed concurrent VLM input corruption |
| Tool / reasoning parsers | `qwen3coder` / `qwen3` |
| Tool guided generation | Enabled |
| MTP / speculative decoding | Off |
| Explicit graph output cap | `max_tokens_limit` omitted |
| OMP client budgets | `contextWindow=131072`, `maxTokens=32768`; these are budgets, not capacity acceptance |
| Host paging | 96 GiB allocated pagefile, 128 GiB configured maximum; observed host condition, not a proven minimum requirement |

The custom GPU source-to-binary attestation remains **NOT_REESTABLISHED**.
The pinned measured DLL is retained; no new GPU build or compute/parser
implementation change is part of this record.

`COMBINATION.lock.json` records the live process's critical loaded modules
and hashes, checked against the release manifest. Small model/configuration
files were hashed at capture time. The large language weights file's size
is recorded, but its hash was not recomputed during production operation.
The Hugging Face revision is a local download-manifest record, not a fresh
download verification.

## Measured speed on this package

Sampling: `temperature=0`, `seed=1234`, `enable_thinking=false`; one loopback
SSE request at a time, on an already warm worker. A 32-output-token warmup
was excluded from the short-run aggregate.

| Measurement | Result |
| --- | --- |
| Short input, 42 tokens; output 256; N=3 | **28.04 tok/s median**, range **23.42–28.26 tok/s** |
| Short request first-token latency | **0.45–0.61 s** |
| Short request median end-to-end output rate | **26.36 tok/s** |
| 8236-token input, first request; output 128 | **15.59 s TTFT**, **21.01 tok/s** output stream |
| Exact 8236-token repeat; output 128 | **0.67 s TTFT**, **26.67 tok/s** output stream |

All six responses, including warmup, returned HTTP 200 and finished at the
requested length. Short-run outputs matched across repeats; the two 8K
outputs also matched. Free system RAM sampled around 4 GiB.

Output-stream throughput is client-observed `(completion_tokens - 1) /
(last output event - first output event)`. SSE events can group tokens, so
it is an estimate of post-first-token throughput, not device kernel timing.
End-to-end rate includes TTFT. Token counts come from server usage fields.
The 8K repeat is a warm/prefix-reuse observation, not a cold-model benchmark;
cache-hit counters were not collected. See `benchmark-results.json`.

These are new measurements of the RC4 Python Off package, separate from
older benchmark-EXE results and the stock OVMS Fast reference.

## Capacity and correctness boundaries

| Check | Status and qualification |
| --- | --- |
| Sequential serving and speed above | PASS on the final one-HTTP-worker tuple |
| Two submitted short unary requests | PASS, each returned its own identifier with one HTTP worker |
| Two submitted short SSE requests | PASS, correct identifiers; 0.27 / 0.64 s completion in that small probe |
| 41006-token synthetic input, identifier from start | PASS in 102.01 s, minimum free RAM 5.789 GiB, on a precursor with identical model/pipeline/KV/batch/interval but **8 HTTP workers**; not rerun on the final one-worker tuple |
| Two distinct long inputs with 8 workers | FAIL: one request hit `Cannot access last message of an empty chat history`; short concurrent probes also showed cancellation/crossed responses |
| Eviction profiles with a 40K input | FAIL / memory-guard stop, including batch 4096 and SnapKV disabled |
| True simultaneous two-slot long-context inference | NOT ACCEPTED; two configured slots do not establish this |
| 128K input, 32K output, agentic tools, long soak | NOT_RUN in these acceptance probes |
| Python On speed for this model/profile | NOT_RUN |

GPU shared-memory counters refer to the same UMA RAM. Private committed
memory is not physical residency, and a large pagefile increases commit
headroom. This record does not claim fully resident operation without paging.

## Reproduce the settings

Use the unchanged published Python Off ZIP and its `setupvars.ps1`. Copy
`graph.template.pbtxt` to a separate host configuration directory and
replace `__MODEL_PATH__`, `__WEIGHTS_PATH__` and `__CACHE_DIR__` with absolute
forward-slash paths. The weights path must identify this model's
`openvino_language_model.bin`; create the writable cache directory first.
The template is a path-substituted rendering of the tested node options,
not a separately exercised launcher.

Create a server config referring to that graph:

```json
{
  "model_config_list": [],
  "mediapipe_config_list": [{
    "name": "qwen36-35b-a3b-int4-baseline",
    "graph_path": "C:/your-config/graph.pbtxt"
  }]
}
```

Then launch from the extracted runtime environment:

```powershell
& ./ovms.exe --rest_bind_address 127.0.0.1 --rest_port 8137 --rest_workers 1 --config_path C:/your-config/config.json --log_path C:/your-config/qwen.log
```

For remote OMP, retain loopback binding and an SSH tunnel. The companion
`omp-models.example.yml` uses client loopback port 18137. Merge its Qwen
override into the provider that actually owns the client's tunnel.
Main/default role assignments are independent of this worker override.
