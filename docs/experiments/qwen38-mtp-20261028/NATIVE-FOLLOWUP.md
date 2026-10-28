# Qwen3.8 Dense MTP — native diagnostic follow-up, 2026-10-28

## Verdict

- Native GenAI CB load + text generation: **PASS** with the official full Qwen3.8 package and unchanged RC4 DLLs.
- Greedy baseline/MTP byte equivalence on one short prompt: **FAIL**, 0/25 measured MTP outputs match baseline.
- Existing OVMS deployment: **BLOCKED_CAPABILITY** at its VLM Fast Draft gate. No server fix or release acceptance claimed.
- MTP recommendation: **HOLD** pending investigation of the output divergence and an isolated OVMS fix.

## New evidence

The earlier stock OVMS DLL-missing result was resolved by its own `C:\llm\ovms\setupvars.ps1`. Its version command reports OVMS `2026.4.0.530dc63f`, OpenVINO `2026.4.0-22930-61afcb26271-releases/2026/4`, GenAI `2026.4.0.0-3401-5f7f1278107`. It then reproduces the VLM Fast Draft gate on port 18138. This existing installation is not asserted to be a pristine stock package.

Before changing product source, `probe_genai.cpp` directly exercised the same `draft_model` and `ContinuousBatchingPipeline` initialization as RC4. Full official model, GPU, KV u4, DQ128, sequences=1, batch=16384, cache_size=0, prefix caching OFF. The probe loads DLLs from the RC4 extracted package; paths and SHA256 are recorded in `native-loaded-modules.json`. SDK headers/import libraries are from the existing 2026.4.0.0rc1 SDK. No production source, model files, runtime DLLs or ZIPs were changed.

## Bounded native timing experiment

One manually formatted Qwen chat prompt: “Explain how a CPU cache improves program performance in one detailed paragraph.” Thinking is closed in the prompt; `apply_chat_template=false`. Greedy generation, 64 tokens, 2 warmups + 5 measured requests per configuration. Baseline and MTP use separate sequential processes; all MTP NAT settings share one loaded process. No concurrent GPU server. This is not the existing HTTP matrix and not a long-context benchmark.

| Mode | NAT | Median wall seconds | Tokens / wall second | Baseline time / MTP time | Output matches baseline |
|---|---:|---:|---:|---:|---:|
| Baseline, no draft | omitted | 10.054 | 6.366 | 1.000 | 5/5 |
| MTP | 1 | 7.017 | 9.120 | 1.433 | 0/5 |
| MTP | 2 | 6.175 | 10.365 | 1.628 | 0/5 |
| MTP | 3 | 6.046 | 10.586 | 1.663 | 0/5 |
| MTP | 5 | 6.369 | 10.049 | 1.579 | 0/5 |
| MTP | 8 | 7.654 | 8.361 | 1.314 | 0/5 |

Tokens / wall second includes prefill and detokenization; it is **not decode-only throughput**. NAT=3 is fastest only in this bounded experiment. NAT=0 in the CSV labels the no-draft baseline; it was not passed as an MTP generation option.

Baseline begins `A CPU cache improves program performance...`; MTP begins `A CPU cache significantly improves program performance...`. This fails strict output equivalence, not semantic correctness. Root cause is unresolved; no claim that MTP inherently changes greedy decoding. All rows report 64 generated tokens and LENGTH finish reason (2). The synchronous result's raw status remains RUNNING (0); terminal API semantics are not accepted on that evidence.

## Reproduction and artifacts

Build: `build-probe.cmd` (MSVC 14.44, /MD, C++17). Set PATH to the RC4 extracted `ovms` directory plus Windows system directories, then execute `C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\runs\probe_genai.exe baseline`, followed by `...\probe_genai.exe mtp`. Do not run concurrently. Each execution overwrites its native CSV/output files; archive existing results first before rerunning.

Run `summarize_native.py` using the existing Python 3.12 tool interpreter. It requires five measured rows per configuration and 64 tokens per row, computes medians and compares output bytes.

Evidence directory: `C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\runs\`:

- `stock-mtp-resolved-env.log`
- `probe-genai-rc4-mtp.log`, `probe-genai-rc4-mtp-generate.log`, `probe-genai-rc4-baseline-generate.log`
- `native-baseline.log`, `native-mtp.log`, `native-baseline.csv`, `native-mtp.csv`
- `native-*-nat*-rep*.txt`, `native-loaded-modules.json`, `native-summary.json`

Selected small evidence is also copied to this document's `native-evidence/` directory.

## Remaining gates

**NOT_RUN:** patched OVMS build; HTTP/SSE/tools; full existing A/B/C matrix; images; long context; NAT=0 on MTP; acceptance-rate counters; peak/paging/memory-cost comparison. No production enablement, merge, commit or push. Probe processes exited after tests.

The next useful investigation is the greedy divergence under fixed target settings, including whether MTP changes effective target numerics. A narrow VLM gate exception remains necessary for OVMS, but removing that gate alone is not correctness acceptance.

Official reference: https://huggingface.co/OpenVINO/Qwen3.8-27B-int4-ov documents the full-package MTP path, greedy decoding and disabled prefix caching. Its support statement does not override the observed OVMS gate or local correctness result.
