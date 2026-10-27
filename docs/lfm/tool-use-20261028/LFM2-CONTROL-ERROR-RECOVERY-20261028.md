# LFM2 control: same error-recovery probes, 2026-10-28

Evidence: `C:\gm\lfm-2026.4\control-lfm2-20261028\same-test`.
Server: `lfm2-24b-a2b-int4`, PID33788, loopback8137, GPU LM, KV auto,
cleanup EXE SHA256 `d7ec623dbd82dae2f5e80f66c4446a7b650e086f3c7cc6da4806fa5aa68a4c3d`.
The LFM2 serving configuration has no reasoning parser; this is the intended
non-thinking control, not a forced LFM2.5 reasoning configuration.

Reused the previous `error-recovery-20261028/probe.py`, with output root and
request model ID changed by `repeat-probes.py`. Same prompts, three simplified
tool schemas, sampling0.2/top_k80/repetition_penalty1.05, seeds1234/1235,
4096 output-token cap. SSE usage reporting is enabled for the control.

| Case | LFM2 control | Previous LFM2.5 |
|---|---|---|
| Fresh task | Native glob, read requirements, attempted prohibited install; bounded host rejects it; visible final | Native listing, then invented JSON action instead of a call |
| After real pygame error, history reasoning retained | stop,112 tokens,465 content characters,0 calls,4.18s | stop,117 tokens,empty content,0 calls,3.13s |
| Same history, reasoning dropped | stop,95 tokens,282 content characters,0 calls,3.32s | Visible JSON/prose plan without calls |
| Required control | Native bash pip-install call; instruction failure, not executed | Same prohibited native install |
| Native-envelope hint | Visible final,401 characters,0 calls | Native prohibited install |
| OMP-built candidate request | stop,105 tokens,visible explanatory final,0 calls | stop,207 tokens,JSON-like arguments,0 calls |

The final OMP-built requests compare equal after removing only the model ID.
Every control SSE response completed with DONE. No reasoning or leaked native
markers appeared in these control responses. Raw JSON/SSE and per-case requests
are retained in the evidence directory; SUMMARY.json covers the first five cases,
and omp-wire-live-analysis.json covers the OMP-built request.

The empty-content failure was not reproduced on LFM2. This is one bounded seed
per case, not a reliability estimate or proof of the LFM2.5 root cause. LFM2
still fails the requested autonomous recovery: it does not search/read manifests
after the replayed error, and forced tool choice does not enforce the prohibition
on installation. The fresh scenario exposes an existing limitation of the shared
probe: glob returns both fixture filenames irrespective of the requested pattern;
the same implementation was retained for comparison. It must not be treated as
strict filesystem-search acceptance or a fully executed Python-error chain.

No package installation occurred. No parser/product/global OMP configuration was
changed. LFM2 remains running on8137.
