# MiniCPM-V 4.7 / Arc 140V final checkpoint report

The exact working GenAI 2026.4 RC1 cannot construct this model: `Unsupported 'minicpmv4_7' VLM model type`, thrown in visual_language/vlm_config.cpp:45 before GPU compilation. This is a model dispatcher gap, not an allocation failure. Both SDKs see GPU and read all five IR graphs after tokenizer extension registration.
The independent nightly has source support but GPU execution remains unverified. Available RAM 14.601 GiB is below the conservative admission threshold 21.368 GiB (BIN 18.368 GiB + 3 GiB). The smoke supervisor also independently returned BLOCKED without starting an inference child. This policy does not prove the model cannot fit on an otherwise idle 32 GB machine; no swap storm, WDDM eviction or GPU reset was observed because compile/inference was not started.

| Gate | Verdict |
|---|---|
| `MODEL_FILES` | PASS |
| `GENAI_2026_4_COMPAT` | FAIL |
| `LATEST_GENAI_COMPAT` | BLOCKED |
| `GPU_COMPILE` | BLOCKED |
| `TEXT_GPU` | BLOCKED |
| `IMAGE_GPU` | NOT_RUN |
| `VIDEO_GPU` | NOT_RUN |
| `MEMORY_FIT` | BLOCKED |
| `PERFORMANCE` | NOT_RUN |
| `TOOL_PROTOCOL` | BLOCKED |
| `OVMS_VLM_CB` | BLOCKED |

## Identities and measurements

Base: `eb76a74f7aa39573d452d95443e189b1f5f4d9e8`; feature branch named in STATE.md.
HF revision: `8b28ee2fe3a13fe38826d615579141af1c6d406a`; all file sizes and hashes in MODEL-IDENTITY.md.
Pinned: OpenVINO `2026.4.0-22930-61afcb26271-releases/2026/4`, GenAI `2026.4.0.0-3401-5f7f1278107`.
Nightly: OpenVINO `2026.5.0-23594-7e507a4ca9a`, GenAI `2026.5.0.0-3556-73c4b0db060`; package versions locked in evidence/nightly-requirements.txt. Pinned SDK bindings are used directly from the unmodified extracted official SDK, not replaced by PyPI packages.
Host: Core Ultra 7 258V, Arc 140V, driver 32.0.101.9150, physical RAM 31.541 GiB, available at host sample 14.821 GiB; disk free 90.089 GiB. Pagefile allocated 96.0 GiB, used 0.164 GiB; pagefile is not a substitute for physical headroom.
DXGI adapter 0 local budget: 26.690 GiB at sample time. QueryVideoMemoryInfo CurrentUsage=0 pertains only to the inventory process, not total GPU load. Core reports GPU_DEVICE_TOTAL_MEM_SIZE=27224272896 bytes; this is a device property, not the dynamic DXGI budget. No ovms/model_server/python inference worker was seen in host inspection; no worker was stopped. Global GPU use/utilization was not measured.

All actual loaded OpenVINO/GenAI/GPU/driver module paths and SHA256 are retained privately; published probe paths use placeholders. The pinned probe uses stock RC1 GPU; no custom MoE plugin was copied. No runtime evidence transfers from historical Qwen results.

Model load/compile: NOT_RUN separately. IR read and rejected-constructor wall times are in probe JSON; neither is a successful full model load/compile measurement. TTFT, decode tok/s, TPOT median/p95, inference peak RAM, WDDM inference usage, GPU utilization, hard faults, CPU utilization and GPU error count: NOT_RUN. There are no answer examples or generated token counts because no model inference passed. Three reproducible PNG fixtures and TEXT-01/TEXT-02 prompts/expectations/hashes are in fixtures/manifest.json; their statuses remain NOT_RUN. VIDEO-01 is gated on image PASS and was not created/run. No benchmark or image-prefill timing was run; historical Qwen ~32.3 tok/s is context only, not fresh A/B.

## Reproduction

PowerShell from repository root, define $Model, $Sdk, $EvalRoot as absolute private locations. Use the same SDK archive selected by versions.mk, and create environments outside production. See private HANDOFF.md for exact physical paths and commands used on this host.

```powershell
rtk uv venv --python 3.12 "$EvalRoot/venv-pinned"
rtk uv pip install --python "$EvalRoot/venv-pinned/Scripts/python.exe" -r docs/minicpm-v47/evidence/pinned-requirements.txt
rtk proxy "$EvalRoot/venv-pinned/Scripts/python.exe" scripts/minicpm-v47/evaluate.py inventory --model $Model --output "$EvalRoot/evidence/inventory.json"
rtk proxy "$EvalRoot/venv-pinned/Scripts/python.exe" scripts/minicpm-v47/evaluate.py probe --model $Model --sdk $Sdk --reject-only --output "$EvalRoot/evidence/pinned-probe.json"
rtk uv venv --python 3.12 "$EvalRoot/venv-latest"
rtk uv pip install --python "$EvalRoot/venv-latest/Scripts/python.exe" --extra-index-url https://storage.openvinotoolkit.org/simple/wheels/nightly -r docs/minicpm-v47/evidence/nightly-requirements.txt
rtk proxy "$EvalRoot/venv-latest/Scripts/python.exe" scripts/minicpm-v47/evaluate.py probe --model $Model --output "$EvalRoot/evidence/nightly-probe.json"
rtk proxy "$EvalRoot/venv-latest/Scripts/python.exe" scripts/minicpm-v47/smoke.py --model $Model --output "$EvalRoot/evidence/text-smoke.json" --timeout 600
```

The supervised smoke is a candidate Python example, not a validated working inference sample. It uses VLMPipeline(model,"GPU"), GenerationConfig(max_new_tokens=32,do_sample=False), and generate(prompt,config). It stops its own child at <3 GiB available RAM or 600 seconds. Output requires semantic review; successful Python return is not correctness PASS. Run the bounded probe without --compile for read-only admission checks; do not bypass --reject-only version restrictions.

## OVMS fit and next code tasks

OVMS deployment was NOT_RUN because standalone GPU PASS is absent. Static boundary review: `ContinuousBatchingServableInitializer::initialize` in src/llm/language_model/continuous_batching/servable_initializer.cpp:257 constructs GenAI ContinuousBatchingPipeline; src/llm/servable_initializer.cpp routes VLM_CB to it. The pinned dependency's VLMConfig rejects minicpmv4_7 and lacks model-specific vision/embedder dispatch. This is the immediate capability gap. Generic image plumbing already exists: ImageDecodingProcessor in InputProcessor and VisualLanguageModelServable::addRequestToPipeline passes promptText/inputImages to add_request; validateEndpoint permits chat/completions and responses. Presence of these paths does not validate this model's visual preprocessing/canvas positions, API output, reasoning or tools.

Do not integrate into the working GEMMAMONSTER tuple yet. Lowest-risk next step is a standalone nightly GPU correctness run after memory becomes available. Follow with IMG-01/02/03 content validation, bounded frames only after image PASS, then C1 512/2048-token benchmarks (128 output, 1 warmup + 3 timed, cold/warm separate) and image-prefill. Keep Qwen unchanged; no contemporary A/B result exists.
Proposed later tasks, not implemented: (1) backport VLMConfig enum/dispatch plus MiniCPMv4_7 vision encoder, inputs embedder, crop grids and canvas M-RoPE onto an isolated 2026.4 dependency fork, or evaluate a separate new dependency cohort; HIGH risk, because 2026.5 performance and ABI cannot be assumed equivalent. (2) verify existing Qwen3Coder retainer using exact token/native parser/matcher/streaming fixtures; MEDIUM risk; introduce a minimal adapter PR only if those expose a concrete gap. (3) isolated loopback OVMS VLM_CB image/reasoning/tools tests with dependency and DLL provenance, then C2 only with measured memory headroom; HIGH risk until C1 is established. (4) validate speculative decoding and expert OTD separately; config fields and plugin property names alone do not establish either capability.

Official references: [export support PR 2033](https://github.com/huggingface/optimum-intel/pull/2033), [GenAI support PR 4591](https://github.com/openvinotoolkit/openvino.genai/pull/4591), [visual processing API](https://openvinotoolkit.github.io/openvino.genai/docs/use-cases/visual-processing/). Exact nightly source URLs/hashes are in evidence/sources.json.
