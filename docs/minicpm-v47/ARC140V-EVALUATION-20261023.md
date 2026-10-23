# MiniCPM-V 4.7 35B-A3B INT4 — Windows Arc 140V experimental evaluation

Date: 2026-10-23. Status: **PLAN / NOT_EXECUTED**. Independent of the production/accepted RC3B line.

## Immutable source and model identity

- OVMS source base: `freeze/rc3b-postfix-20261023-eb76a74f` @ `eb76a74f7aa39573d452d95443e189b1f5f4d9e8`.
- This evaluation branch: `feature/minicpm-v47-arc140v-eval-20261023`. The frozen branch, working `semantic-refit-2026.4`, C6/Gemma, Qwen3Coder, Ornith, CIB2 and production binaries are **read-only**.
- Model: `OpenVINO/MiniCPM-V-4.7-35B-A3B-int4-ov`, local directory `C:\llm\models\minicpm-v47-35b-a3b-int4-ov`.
- Official upstream: `openbmb/MiniCPM-V-4.7-35B-A3B`, tokenizer and chat template. Do not download BF16 or regenerate quantization unless the published IR is proved defective.
- Machine: Windows 11 / Core Ultra 258V / Arc 140V / 32 GiB unified LPDDR. GPU shared-budget figures are **not extra DRAM**.
- Baseline stack: OVMS/OpenVINO GenAI Windows `2026.4.0.0rc1`, **stock** 2026.4 GPU plugin. Any newer GenAI is a separate sandbox, never replace production DLLs.
- Upstream evidence: merged Optimum Intel [#2033](https://github.com/huggingface/optimum-intel/pull/2033) (IR export, 35B INT4 accuracy); merged GenAI [#4591](https://github.com/openvinotoolkit/openvino.genai/pull/4591) (VLM images/video). **Neither merge proves compatibility with pinned 2026.4 RC1 or Arc 140V.**

## Mission and scope

Find whether the **published** INT4 IR operates on Arc 140V in (1) the pinned SDK, (2) an independently isolated newer SDK only if necessary, (3) standalone `VLMPipeline`, then optionally OVMS VLM_CB. Quantify memory fit and text/image/video performance. Assess tool protocol **separately** under [MFP-1-FULL-COMPATIBILITY-PROGRAM-20261023.md](MFP-1-FULL-COMPATIBILITY-PROGRAM-20261023.md).

The evaluation may succeed in standalone GenAI but remain `OVMS_BLOCKED`. No PR/agent should claim full OVMS or tool compatibility from a generic text-only generate.

## Stages and exact artifacts

| Stage | Action | Artifact / exit gate |
| --- | --- | --- |
| E0 provenance | Enumerate model files/sizes, model `config.json` / `openvino_config.json` / tokenizer/template/generation revision and SHA256; record exact DLL import path, OpenVINO/GenAI version, Intel driver, GPU identity, model root, git HEAD. Verify no incomplete files. | `MODEL-IDENTITY.md`, `EVIDENCE.json`; missing source = `BLOCKED`. |
| E1 static capability | Enumerate all OpenVINO IR XMLs (language, vision, embeddings, tokenizer/detokenizer if present); inspect architecture/ops/processor and current VLM pipeline support. Do not assume specific filenames or that OpenVINO OTD/LES/DSpark is enabled. | `COMPATIBILITY-MATRIX.md` with 2026.4 vs optional sandbox results and source citation. |
| E2 isolated environment | First use pinned 2026.4 RC1 SDK under an independent test process. Only if E2 fails, construct independent newer GenAI `uv` environment and record package lock; no PATH/DLL overwrite; no shared plugin cache. | `PINNED_SDK` and `SANDBOX_SDK` distinct verdicts. |
| E3 correctness | With `VLMPipeline`, run one short text-only GPU response, then synthetic image QA/OCR, then screenshot, multi-image and bounded video after image PASS. Save deterministic fixtures, responses and process exit statuses. | `TEXT_GPU`, `IMAGE_GPU`, `VIDEO_GPU` independent PASS/FAIL/BLOCKED/NOT_RUN. CPU success ≠ GPU success. |
| E4 resource gate | Measure compile/load time, peak process RAM/commit, WDDM budget+usage, page faults, GPU utilization, temporary vision allocations and failure stage. Avoid WDDM eviction and Windows swap storms. | `MEMORY_FIT` and `RESOURCE.tsv` with sampled timestamps; stop unsafe runs. |
| E5 benchmark | C1, prompt 512/2048, max_new_tokens 128, >=1 warmup+3 runs per arm; cold and warm load distinct; image prefill separately. TTFT, decode tokens/s, TPOT p50/p95 where sufficiently sampled, accuracy fixture IDs, model & binary hashes. | `BENCHMARK.csv` + `BENCHMARK-METHODOLOGY.md`. Compare with Qwen3.6/Ornith only using matched harness or label historical baseline. |
| E6 OVMS seam | Check actual OVMS VLM_CB and multimodal OpenAI API request/response; verify processor hook, template/history, image tokens and plugin loading. Use localhost-only separate port and process. C2/C4 only when memory/CB supports them. | `OVMS_VLM_CB` independent status + failure code and precise unsupported seam. |
| E7 final handoff | Preserve runnable scripts, sanitized logs, source/IR/runtime identities, all gate outcomes and failure reproduction; push docs and scripts to this feature branch only. | `FINAL-REPORT.md`, updated `STATE.md` and owner-ready recommendation. |

## Fixture corpus (deterministic and self-contained)

- `TEXT-01` unambiguous factual one-line answer; `TEXT-02` short coding/output question.
- `IMG-01` synthetic colored objects/counts with answer key; `IMG-02` OCR text/numeric cell table with answer key.
- `IMG-03` synthetic UI screenshot and element relations; `IMG-04` multi-image comparison, if supported.
- `VIDEO-01` 4–8 synthetic frames with visible chronological change, only after IMG PASS; cap frame count, pixels and memory.
- `TOOL-01` only after model E3 PASS: native template tool-call transcript and tool-result replay, with `MFP1` acceptance independently recorded.

Keep inputs, exact prompt text, expected result predicates and generated text. Distinguish answer factual error, pipeline error and parser/transport error.

## Benchmark and resource interpretation

- The published IR is roughly 20 GB class (check actual local file total); it can exceed usable GPU budget after vision tower, activation buffers and KV, even though bare weights are smaller than 32 GiB. Never combine reported GPU memory + physical RAM as independent pools.
- Historical `Qwen3.6-35B-A3B INT4` decode ~32 tok/s on **stock** 2026.4, not a same-session MiniCPM A/B result.
- No entitlement to speculative, KV U4, native expert OTD, LES, async offload, 256K context or multi-slot based on upstream architecture alone.
- Identify memory-capability vs compilation-kernel vs tokenizer/processor vs unsupported API vs device error independently.
- Stop extended runs on swap storms, GPU resets, driver instability or sustained memory pressure. Do not mutate BIOS/driver, production endpoints, working `C:\llm` binaries or production model caches.

## Ready-to-run starting point (adapt if local CLI differs)

Download separately; source model remains immutable:

```powershell
uvx hf download OpenVINO/MiniCPM-V-4.7-35B-A3B-int4-ov --local-dir "C:\llm\models\minicpm-v47-35b-a3b-int4-ov"
Get-ChildItem "C:\llm\models\minicpm-v47-35b-a3b-int4-ov" -Recurse -File | Measure-Object Length -Sum
```

The standalone Python VLM example, processor API and supported `GenerationConfig` kwargs MUST be taken from the **installed, pinned** GenAI documentation/source, not invented. In particular, do not treat a `pipe.generate("text", ...)` candidate as proof of support before executing it.

## Acceptance ledger (each independent)

`MODEL_FILES / PINNED_2026_4_GENAI / SANDBOX_GENAI / GPU_COMPILE / TEXT_GPU / IMAGE_GPU / MULTI_IMAGE_GPU / VIDEO_GPU / MEMORY_FIT / PERFORMANCE / TOOL_FORMAT / OVMS_VLM_CB`. Allowed statuses: `PASS, FAIL, BLOCKED, NOT_RUN`. A saved previous-run log is not current evidence.

**Gate:** Evaluation is complete once every stage has an evidence-backed status and failures are reproducible; full model-support acceptance requires actual successful pinned-source Windows candidate runs and owner signoff. `MFP-1` protocol implementation follows an independent test/review ladder.
