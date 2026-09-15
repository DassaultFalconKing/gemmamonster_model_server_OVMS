# Gemmamonster on Intel Arc: U4 KV cache

This is the recommended long-context profile for the Gemmamonster 2026.4 line on Intel Arc GPUs when the packaged OpenVINO runtime contains Intel GPU paged-attention U4 KV-cache support.

On the validated Arc setup, U4 materially reduces KV-cache pressure and can make long agent sessions much faster. The observed output quality was effectively indistinguishable from U8 for the tested Gemma 4 workload. Treat that as a workload-specific result: verify tool calls, long-context continuation, memory use, and throughput on every new model/runtime/driver tuple.

## What U4 changes

`KV_CACHE_PRECISION=u4` compresses the attention key/value cache. It does not quantize the model weights again and it does not change the OpenCode context limit. The client-side context budget and the server-side KV-cache capacity are separate:

- OpenCode may advertise the model's `131072`-token context window.
- OVMS allocates KV cache dynamically when `--cache_size 0` is used.
- A larger context can therefore show little immediate memory difference until a request actually fills the cache. Allocation granularity, prefix-cache reuse, graph buffers, and GPU driver reservations make memory growth nonlinear.

## Recommended launcher command on Windows

Use the packaged candidate launcher so the binary, OpenVINO libraries, GenAI, Tokenizers, and TBB modules are provenance-checked together. The backslashes in `$U4Config` are required: `Start-Process` must preserve the JSON quotes when it builds the Windows command line.

```powershell
$CandidateRoot = 'C:\gemmamonster-artifacts\candidates\2026.4\17064400-maintainer-rc2-whitespace-fix-20260914T172941Z'
$ModelPath = 'C:\llm\models\OpenVINO\Wondernutts\gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov'
$U4Config = '{\"KV_CACHE_PRECISION\":\"u4\"}'

& 'C:\git\gemmamonster-2026.4-unified-20260911\scripts\gemmamonster\launch-stable-candidate.ps1' `
  -CandidateRoot $CandidateRoot `
  -ModelPath $ModelPath `
  -ModelName 'gemma4-26-heretic' `
  -RestPort 18091 `
  -HealthcheckSeconds 120 `
  -OvmsArgs @(
    '--rest_port','18091',
    '--model_path',$ModelPath,
    '--model_name','gemma4-26-heretic',
    '--task','text_generation',
    '--pipeline_type','VLM_CB',
    '--target_device','GPU',
    '--tool_parser','gemma4',
    '--reasoning_parser','gemma4',
    '--enable_tool_guided_generation','true',
    '--cache_size','0',
    '--enable_prefix_caching','true',
    '--plugin_config',$U4Config,
    '--log_level','DEBUG'
  )
```

`-OvmsArgs` replaces the launcher's defaults, so keep the complete argument list above. Use a free port if another OVMS process is already listening; never terminate an unrelated listener just to reuse `18091`.

## Follow startup and verify U4

The launcher writes an acceptance directory under `$CandidateRoot\acceptance`. Follow the newest stdout log:

```powershell
$run = Get-ChildItem "$CandidateRoot\acceptance" -Directory |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

Get-Content "$($run.FullName)\ovms.stdout.log" -Wait -Tail 100
```

The log must contain all of the following before a semantic test:

1. `REST server listening on port 18091`.
2. A GPU plugin configuration showing `KV_CACHE_PRECISION` set to `u4` (or the corresponding OpenVINO GPU cache-precision field).
3. No `Failed to create plugin config`, `GPU_EXECUTION_FAILURE`, or executor-quarantine error.

Then check liveness:

```powershell
Invoke-RestMethod 'http://127.0.0.1:18091/v1/models'
```

HTTP liveness is not semantic acceptance. Run at least one normal chat, one forced tool call, one tool continuation, and a long-context probe. Preserve the raw request/response and the OVMS logs for U4/U8 comparison.

## U4 versus U8 comparison

Compare one variable at a time:

| Profile | `plugin_config` | `cache_size` | Purpose |
|---|---|---:|---|
| U4 | `{"KV_CACHE_PRECISION":"u4"}` | `0` | Recommended Intel Arc long-context profile |
| U8 | `{"KV_CACHE_PRECISION":"u8"}` | `0` | Quality/performance control |

Keep the candidate binary, model, driver, OpenCode settings, request corpus, concurrency, and context ladder fixed. Record first-token latency, decode throughput, peak/private GPU memory, finish reason, tool-call count, grounded continuation, and any runtime fault. Do not call U4 a PASS solely because `/v1/models` returns HTTP 200.

## Troubleshooting

- `Plugin config is in wrong format`: the JSON quotes were stripped by Windows argument parsing. Use the exact `$U4Config` form above, including the backslashes.
- `The request was canceled ... HttpClient.Timeout of 2 seconds`: this is the launcher's readiness probe timing out; inspect whether OVMS stayed alive and whether the REST listener came up. It is not evidence of a model-quality failure.
- `KV_CACHE_PRECISION` remains `u8` or `dynamic`: the U4 override did not reach the GPU graph. Stop the process, fix the argument quoting, and rerun; do not label that run U4.
- `CL_OUT_OF_RESOURCES` or `GPU_EXECUTION_FAILURE`: record the exact request and runtime log, then recreate the OVMS process before retrying. `/v1/models` may still answer after the executor has become unusable.

## Related files

- [`launch-stable-candidate.ps1`](../../scripts/gemmamonster/launch-stable-candidate.ps1)
- [`RC2-B-PARITY-ACCEPTANCE-RUNBOOK-20260912.md`](RC2-B-PARITY-ACCEPTANCE-RUNBOOK-20260912.md)
- [`KNOWN-GOOD-TOOL-CALLING-20260911.md`](KNOWN-GOOD-TOOL-CALLING-20260911.md)
