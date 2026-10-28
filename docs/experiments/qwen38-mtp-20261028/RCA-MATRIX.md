# Qwen3.8 Dense MTP — controlled native RCA, 2026-10-28

## Scope and decision

**MTP remains HOLD for OVMS/RC4.** The native precision matrix and first-divergence raw-logit comparison are complete. The mismatch is a target-forward argmax flip, with identical internal prompt IDs, at the first verification pass before any earlier target rejection. The underlying KV/GDN/GPU-kernel cause remains unresolved. No OVMS product source has been changed.

Same full official `OpenVINO/Qwen3.8-27B-int4-ov`, existing model SHA lock, RC4 OpenVINO/GenAI/GPU DLLs, GPU, max sequences 1, batch 16384, cache_size 0, prefix OFF. Generation: greedy, seed 1234, 64 tokens, NAT=3 for MTP; two repetitions inside each independently launched target-only or MTP process. No model reduction or changed context/generation limit. These are correctness diagnostics, not a new performance acceptance matrix.

## Results on original RC4 DLLs

| Case | Target settings in both processes | Target-only versus MTP | First divergent output index (zero based) |
|---|---|---|---:|
| P0 | u4 + DQ128 | FAIL | 3 |
| P1 | u8 + DQ128 | PASS, 64/64 IDs | — |
| P2 | u4 + DQ0 | FAIL | 3 |
| P3 | f16 + DQ0 | PASS, 64/64 IDs | — |
| P4 | f16 + DQ128 | PASS, 64/64 IDs | — |
| P5 | u8 + DQ0 | PASS, 64/64 IDs | — |
| P6 | u4 + DQ128 + BY_TOKEN | BLOCKED_CAPABILITY, both processes | — |
| P6b | u8 + DQ128 + BY_TOKEN | FAIL | 23 |

Every successful process generated 64 tokens, FINISHED status (1), LENGTH reason (2). Both repetitions match within every successful mode. P0/P2 share output prefix `[32, 13540, 6297]`, then target-only emits **33793**, MTP **11602**. P6b first mismatch is target **23249** versus MTP **17128**.

P3 did fit on this 32 GiB machine for this short context, with the full original model. Available physical memory was sampled every second; minimum across P3 target/MTP processes was about 2.58 GiB. This is not a GPU-budget or peak-working-set measurement and does not grant admission for long context. Resource guard: abort if physical or commit availability remains below 512 MiB for 5 seconds; no guard was triggered in these runs.

P6's GPU error explicitly says 4-bit KV with PagedAttention does not support BY_TOKEN and recommends BY_CHANNEL or 8-bit KV. P6b therefore tests 8-bit BY_TOKEN as an additional configuration, against its own matching target-only control. It does not replace P6.

## What these results establish

- Changing u4 to u8 removes the observed short-prompt mismatch with default key quantization, both with DQ128 and DQ0.
- Disabling DQ alone does not remove the u4 mismatch.
- f16 controls pass with either DQ setting. Weights remain the original INT4; f16 denotes KV precision only.
- BY_TOKEN on u8 introduces a later mismatch on this prompt. It cannot be assumed to be a correctness fix.
- These results localize a precision/layout-sensitive path. They do **not** yet prove altered target logits, GPU kernel fault, GDN rollback corruption, or sampler error.

## Input/output boundary and harness failures

`input-ids.txt` is generated once from the same manually formatted prompt used by the previous native probe. Each process loads those IDs, decodes with `skip_special_tokens=false`, and asserts an exact tokenizer encode/decode roundtrip. Its external input-ID receipt SHA is identical within each target/MTP pair. Actual output IDs come from `GenerationHandle::read_all()`, not re-tokenized output text. `add_request(string)` with `apply_chat_template=false` is used.

**Internal VLM input IDs were subsequently observed in the isolated trace build.** All four receipts (baseline/MTP, repetitions 0/1) exactly match the same 26 input IDs in `input-ids.txt`. The direct encoded `generate(Tensor)` route is not usable here: baseline fails `Tensor was not initialized`; MTP expects embeddings `[1, seq_len>1, hidden_size]` and receives `[1,26]`. Those attempts are preserved under `rca/encoded-api-failed/`, excluded from precision results. A subsequent roundtrip guard correctly rejected default decode that stripped special tokens; those pre-generation failures are preserved under `rca/roundtrip-guard-failed/`. The guard was fixed explicitly, then the full matrix was rerun.

Draft property behavior matches the original probe: `draft_model` receives device and scheduler; target KV/DQ properties are passed at the CB constructor. Whether GenAI propagates them internally is a source/trace question, not an assumed property of the draft head.

## Target-logit investigation

Exact public source commit resolved from the runtime version: `5f7f1278107d7eae3990ce906bbcfcb69ac3397f`. Snapshot, API commit/tree receipts and ZIP are under the external `rca/` evidence directory. Source snapshot acquisition was checked against GitHub's commit API; an initial raw-file request used a wrong path and returned 404.

`instrument_genai.py` adds an opt-in `RCA_TRACE_DIR` observer around target/draft forward and sampling in `continuous_batching/pipeline_impl.cpp`. It saves raw pre-sampler logits, shapes, pipeline instance, validation flag, internal prompt IDs and generated IDs before/after sampling, capped at 128 events per process. It does not modify tensors, sampler decisions, scheduler or recurrent state. Trace build is isolated and must reproduce the reference outputs before being used for RCA.

Public API logprobs expose only one selected-token logprob and cannot establish top-1/top-2 raw-logit margin. No margin or rejection chronology is inferred from those values.

### Measured first-divergence logits

`instrument_inputs.py` additionally records actual `new_input_ids` at the VLM tokenizer/embedding boundary. The second trace DLL reproduces both original P0 output sequences in both repetitions, and all four internal input-ID receipts match the fixed 26-token input. The common generated prefix is `[32,13540,6297]`.

| At output index 3 | Target-only | MTP target verifier |
|---|---:|---:|
| Raw logit for ID 33793 | 22.4794006 | 22.4699440 |
| Raw logit for ID 11602 | 22.2006302 | 22.4845390 |
| Top-1 ID | 33793 | 11602 |
| Top-2 ID | 11602 | 33793 |
| Top-1 minus top-2 margin | 0.2787704 | 0.0145950 |

Maximum absolute difference across the vocabulary at this position: **0.5927142**. Baseline raw tensor is `[1,1,248320]` (row 0); MTP verification is `[4,1,248320]` (packed row 2). Row alignment follows sampler's reverse-offset indexing and is checked against the same generated prefix; this is a comparison at the same causal position, not blindly the last row of each tensor.

Chronology: target prefill emits ID 32; draft produces `[13540,6297,33793]`; the first target verification rejects the third draft token and emits 11602. Thus draft initially proposes the same token as baseline. The verifier's raw-logit argmax has already changed before sampling. There is no earlier target verification/rejection whose rollback could have caused this first mismatch. This rules out the branch “identical logits, different sampler output” for this case and rules out prior-rejection rollback as its trigger. It does not rule out numerical differences inside GDN computation or KV handling during the verification pass.

Build: exact source SHA above, MSVC 14.44, Release, OpenVINO SDK matching RC4; Python/tests/samples/tools disabled; XGrammar disabled; GGUF enabled after an upstream build dependency failed with it disabled. This is an **instrumented diagnostic artifact**, not RC4 release acceptance. The copied runtime differs only in `openvino_genai.dll`, checked through actual loaded module hashes. No generated runtime files were installed into a release directory. Trace timings include disk output and have no performance meaning.

Data: `rca/logit-comparison.json`, `rca/trace-loaded-modules-v2.json`, `rca/trace-runs-v2/`, `rca/traces-v2/`. `analyze_trace.py` asserts reference reproduction, input IDs, causal prefix, exact tensor byte sizes, raw argmax, draft candidate and rejection chronology. Selected raw events and JSON are copied into `rca-evidence/`.

## OVMS upstream preparation

Exact upstream patch is saved as `upstream-5f09c40.patch`: https://github.com/openvinotoolkit/model_server/commit/5f09c405dd4d46e089ab7671b633149a035c6c1f . It covers strategy detection, servable properties, generation policy, CB and legacy initialization and tests. It has **not** been applied. A future bounded RC4 backport must retain ordinary Fast Draft rejection on VLM; no main merge and no gate-only bypass.

Long-context warning reference: https://github.com/openvinotoolkit/openvino.genai/issues/4483 . This experiment uses a short prompt only; no 98K/128K admission was attempted.

## Evidence and reproduction

Harness: `rca_probe.cpp`, `build-rca.cmd`, `run_rca.py`, `summarize_rca.py`, `instrument_genai.py` in this document directory. Run `run_rca.py` only with GPU exclusive. Optional argument `P6b` runs the supplementary BY_TOKEN pair. Existing filenames are overwritten on rerun; archive old evidence first.

Raw root: `C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\rca\`. `matrix.json` is the original P0–P6 matrix; `matrix-P6b.json` is supplementary. `rca-summary.json` includes assertions on token counts, FINISHED/LENGTH and repeatability. `loaded-modules.json` records actual loaded DLL paths/hashes. Per-process logs and per-repetition JSON retain exact IDs. Selected data is copied into `rca-evidence/` beside this report.

**NOT_RUN / pending:** long-context admission, HTTP/SSE/tools, OVMS MTP backport/build, negative Fast Draft regression on a patched server, complete GPU/GDN/KV causal trace. Strict production/OVMS acceptance remains unchanged.
