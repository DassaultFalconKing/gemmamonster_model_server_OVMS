"""Prepare sanitized documentation from measured evidence; never infer a runtime PASS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def run(private, repo, model, sdk):
    docs=repo/'docs/minicpm-v47'; public=docs/'evidence';public.mkdir(exist_ok=True)
    def load(name): return json.loads((private/name).read_text(encoding='utf-8-sig'))
    inv=load('inventory.json'); pinned=load('pinned-probe.json'); nightly=load('nightly-probe.json')
    host=load('host-memory.json');protocol=load('protocol.json');checks=load('local-verification.json')
    roots={str(repo):'<WORKTREE>',str(private.parent):'<EVAL_ROOT>',str(model):'<MODEL_DIR>',str(sdk):'<SDK_RC1>',str(Path.home()):'<USERPROFILE>',os.environ.get('WINDIR','C:\\Windows'):'<WINDIR>'}
    def clean(obj):
        if isinstance(obj,str):
            for root,value in roots.items(): obj=obj.replace(root,value).replace(root.replace('\\','/'),value)
            return obj
        if isinstance(obj,list):return [clean(x) for x in obj]
        if isinstance(obj,dict):return {k:clean(v) for k,v in obj.items()}
        return obj
    for name in ('inventory.json','pinned-probe.json','nightly-probe.json','host-memory.json','protocol.json','local-verification.json','sources.json','text-smoke-admission.json','cpu.json','driver.json'):
        (public/name).write_text(json.dumps(clean(load(name)),indent=2,ensure_ascii=False),encoding='utf-8')
    for name in ('pinned-requirements.txt','nightly-requirements.txt','latest-stable-requirements.txt'):
        (public/name).write_text((private/name).read_text(encoding='utf-16' if (private/name).read_bytes().startswith(b'\xff\xfe') else 'utf-8-sig'),encoding='utf-8')
    files={x['name']:x for x in inv['files']};cfg=inv['configs']['config.json'];text=cfg['text_config']
    states=[ET.fromstring(s).find('data').attrib for s in files['openvino_language_model.xml']['interfaces'] if 'type="ReadValue"' in s]
    (public/'state-shapes.json').write_text(json.dumps(states,indent=2),encoding='utf-8')
    bin_gib=inv['bin_bytes']/1024**3; available=nightly['admission']['available_ram']/1024**3;threshold=nightly['admission']['required_ram']/1024**3
    table='\n'.join(f"| `{x['name']}` | {x['bytes']} | `{x['sha256']}` |" for x in inv['files'])
    identity=f'''# Model identity

Repository: OpenVINO/MiniCPM-V-4.7-35B-A3B-int4-ov.
HF snapshot: `8b28ee2fe3a13fe38826d615579141af1c6d406a`.
20/20 local files match pinned download ETags (SHA256 for LFS; Git blob SHA1 for regular files); all metadata has the same snapshot revision. The pinned HF API response was also retrieved; source URL and digest are in evidence/sources.json. Original model artifacts were read, never written.
Total files: {inv['total_bytes']} bytes. BIN payload: {inv['bin_bytes']} bytes ({bin_gib:.3f} GiB).

Architecture: `{cfg['architectures'][0]}` / `{cfg['model_type']}`; text `{text['model_type']}`.
40 text layers: 30 linear attention and 10 full attention; hidden 2048, attention heads 16, KV heads 2, head_dim 256; 256 routed experts, top-8 per token, routed intermediate 512, shared expert intermediate 512. These are config values, not measured active execution.
Vision: MiniCPM-V 4.7 encoder, hidden 1152, intermediate 4304, 27 layers, 16 heads, patch 14, configured vision size 980 and outer image size 448; 2x2 merge, canvas M-RoPE, downsample 16x. Actual visual IR takes pixel_values, position_ids, window_index, merge_index and returns hidden size 2048.
Language IR takes inputs_embeds, attention_mask, 3-axis position_ids and beam_idx; emits logits of vocabulary 248144. IR opset census and all interfaces are in evidence/inventory.json.
Quantization: asymmetric INT4 language, group 64, ratio 1.0, INT8 symmetric backup; text and vision embeddings INT8 symmetric. Config dtype bfloat16 describes source; it does not describe every IR tensor.
Native context configured at 262144. No long-context test was run.

KV: actual IR declares 20 full-attention key/value state tensors, each FP32 [batch,2,sequence,256]. At C1 this is 40960 bytes/token: 20 MiB at 512, 80 MiB at 2048, 10 GiB at 262144, before allocator padding, image tokens, outputs and linear states. GPU may change precision/layout; these are graph-level arithmetic estimates, not measured VRAM. Remaining 60 ReadValue tensors belong to linear recurrent/conv state; exact shapes/types are in evidence/state-shapes.json. A naive 40-layer dense-KV estimate would be wrong.
MTP config has one prediction layer, but no dedicated draft/MTP IR is supplied. Speculative decoding on this exported VLM is NOT established. Native expert OTD is NOT established: no execution trace or per-expert residency evidence; OFFLOAD_RATIO property presence does not prove demand-driven expert loading. No such option was enabled.

| File | Bytes | SHA256 |
|---|---:|---|
{table}
'''
    (docs/'MODEL-IDENTITY.md').write_text(identity,encoding='utf-8')
    statuses={'MODEL_FILES':'PASS','GENAI_2026_4_COMPAT':'FAIL','LATEST_GENAI_COMPAT':'BLOCKED','GPU_COMPILE':'BLOCKED','TEXT_GPU':'BLOCKED','IMAGE_GPU':'NOT_RUN','VIDEO_GPU':'NOT_RUN','MEMORY_FIT':'BLOCKED','PERFORMANCE':'NOT_RUN','TOOL_PROTOCOL':'BLOCKED','OVMS_VLM_CB':'BLOCKED'}
    (public/'verdicts.json').write_text(json.dumps(statuses,indent=2),encoding='utf-8')
    (docs/'COMPATIBILITY-MATRIX.md').write_text(f'''# Compatibility matrix

| Stage | Pinned SDK RC1 | Isolated nightly |
|---|---|---|
| OpenVINO | `{pinned['openvino_version']}` | `{nightly['openvino_version']}` |
| GenAI | `{pinned['genai_version']}` | `{nightly['genai_version']}` |
| Core sees GPU | PASS | PASS |
| Read all five actual IR graphs | PASS | PASS |
| VLMPipeline creation | FAIL: unsupported minicpmv4_7 | BLOCKED: memory admission |
| Language/visual GPU compile | NOT_RUN: dispatcher rejects first | BLOCKED |
| First generation | NOT_RUN | BLOCKED |

PyPI initially resolved 2026.4.1 / 2026.4.1.0; that environment was then upgraded in place to the official nightly, still isolated from the pinned SDK. Stable 2026.4.1 was not given a pipeline verdict. Early tokenizer read errors were harness setup errors from missing extension registration, corrected before the final reads; they are not checkpoint incompatibilities. Initial pinned import needed process-local SDK TBB lookup; no DLL was replaced.

Nightly source at `73c4b0db060` contains minicpmv4_7 model dispatch, InputsEmbedderMiniCPMv4_7, and VisionEncoderMiniCPMv4_7. This verifies source routing, not GPU execution. GPU plugin versions and actual loaded DLL names, bytes, SHA256 are in probe evidence; physical paths remain in private evidence.
''',encoding='utf-8')
    markers='\n'.join(f"| `{k}` | `{v[0]}` |" for k,v in protocol['marker_ids'].items())
    (docs/'TOOL-PROTOCOL-FIT.md').write_text(f'''# Tool protocol fit

Verdict: BLOCKED for retainer acceptance. Native template rendering/tokenization was measured; native C++ parser RED/GREEN, matcher, streaming, live tool decision and continuation were NOT_RUN. Per mission, inference did not pass, so the requested post-inference acceptance remains gated. This is preliminary static/tokenizer work only.

6 native template cases render and tokenize: default/disabled thinking, empty arguments, multiple calls, tool response, reasoning. JSON-string arguments case fails with AttributeError; the template expects an object and iterates items. OVMS already has a dry-run capability probe (`src/llm/io_processing/chat_template/probe.cpp`) and `chat_template_adapter::funcArgsToObjectHistory` in input_processors/chat_template_adapter.cpp. Verify that adaptation fires for this exact template before proposing an adapter.

Native grammar is `<tool_call>\\n<function=NAME>\\n<parameter=ARG>\\nVALUE\\n</parameter>... </function>\\n</tool_call>`. Empty arguments produce no parameter tags; multiple calls are separated by a newline. Native tool role becomes a user turn containing `<tool_response>`. Default generation prefix opens `<think>`; enable_thinking=false writes an empty closed thought. Reasoning content can be reconstructed from reasoning_content or embedded think tags.
The frozen `ChatTemplateAnalyzer::analyze` (src/llm/io_processing/chat_template/analyzer.cpp) selects qwen3coder plus qwen3 reasoning from these markers. Qwen3CoderToolParser constants match the textual tags. `Qwen3CoderGenerationConfigBuilder` uses QwenXMLParametersFormat and closes open reasoning before tool grammar; this is a plausible retainer candidate, not an acceptance result. MiniCPM5 parser uses different attribute tags and is not a substitute.

Generation config EOS: 248044 and 248046; BOS 248045. Special-token boundaries must remain visible where parser policy requires them. Function/parameter headers are multiple tokens, so token/stream splits can occur inside names. Full rendered strings and IDs are in evidence/protocol.json.

| Marker | Actual tokenizer IDs |
|---|---|
{markers}

Required native RED/GREEN gates: empty args, schema invalid/unknown function, duplicate/missing parameters, multi-call order, every delimiter split, default/disabled reasoning, STOP/LENGTH truncation, tool-result continuation and guided/unguided policy. None was executed on the frozen production binary. No Gemma4, Qwen3Coder or LFM source was changed.
''',encoding='utf-8')
    verdict_table='\n'.join(f'| `{k}` | {v} |' for k,v in statuses.items())
    (docs/'STATE.md').write_text(f'''# Evaluation state

Evaluation date: 2026-10-23, Europe/Berlin client context.
ACTIVE_STAGE: MEMORY_BLOCKED; ACCEPTED: NO.
BASE_SHA / REVERT_POINT: eb76a74f7aa39573d452d95443e189b1f5f4d9e8.
WORK_BRANCH: feature/minicpm-v47-arc140v-eval-20261023.
CURRENT_HEAD: use `git rev-parse HEAD`; commits contain this immutable checkpoint.
LAST_GREEN_TESTS: 20/20 file ETags; Core GPU and 5/5 graph reads on each SDK; six template render/tokenizer cases. These are not inference PASS.
CURRENT_FAILURE: pinned GenAI dispatcher rejects minicpmv4_7; nightly compile admission blocked.
NEXT_ACTION: make at least {threshold:.3f} GiB physical RAM available without changing production processes, then rerun supervised text-only candidate. Recheck GPU ownership and dynamic budget first.
EVIDENCE_PATH: docs/minicpm-v47/evidence; raw logs/path map retained privately.
No product source changed; no build, model conversion, server, endpoint, driver change, baseline benchmark or merge.
''',encoding='utf-8')
    report=f'''# MiniCPM-V 4.7 / Arc 140V final checkpoint report

The exact working GenAI 2026.4 RC1 cannot construct this model: `Unsupported 'minicpmv4_7' VLM model type`, thrown in visual_language/vlm_config.cpp:45 before GPU compilation. This is a model dispatcher gap, not an allocation failure. Both SDKs see GPU and read all five IR graphs after tokenizer extension registration.
The independent nightly has source support but GPU execution remains unverified. Available RAM {available:.3f} GiB is below the conservative admission threshold {threshold:.3f} GiB (BIN {bin_gib:.3f} GiB + 3 GiB). The smoke supervisor also independently returned BLOCKED without starting an inference child. This policy does not prove the model cannot fit on an otherwise idle 32 GB machine; no swap storm, WDDM eviction or GPU reset was observed because compile/inference was not started.

| Gate | Verdict |
|---|---|
{verdict_table}

## Identities and measurements

Base: `eb76a74f7aa39573d452d95443e189b1f5f4d9e8`; feature branch named in STATE.md.
HF revision: `8b28ee2fe3a13fe38826d615579141af1c6d406a`; all file sizes and hashes in MODEL-IDENTITY.md.
Pinned: OpenVINO `{pinned['openvino_version']}`, GenAI `{pinned['genai_version']}`.
Nightly: OpenVINO `{nightly['openvino_version']}`, GenAI `{nightly['genai_version']}`; package versions locked in evidence/nightly-requirements.txt. Pinned SDK bindings are used directly from the unmodified extracted official SDK, not replaced by PyPI packages.
Host: Core Ultra 7 258V, Arc 140V, driver 32.0.101.9150, physical RAM {host['ram']['total']/1024**3:.3f} GiB, available at host sample {host['ram']['available']/1024**3:.3f} GiB; disk free {host['disk']['free']/1024**3:.3f} GiB. Pagefile allocated {host['swap']['total']/1024**3:.1f} GiB, used {host['swap']['used']/1024**3:.3f} GiB; pagefile is not a substitute for physical headroom.
DXGI adapter 0 local budget: {host['dxgi']['local']['Budget']/1024**3:.3f} GiB at sample time. QueryVideoMemoryInfo CurrentUsage=0 pertains only to the inventory process, not total GPU load. Core reports GPU_DEVICE_TOTAL_MEM_SIZE={nightly['stages']['core_gpu']['result']['GPU_DEVICE_TOTAL_MEM_SIZE']} bytes; this is a device property, not the dynamic DXGI budget. No ovms/model_server/python inference worker was seen in host inspection; no worker was stopped. Global GPU use/utilization was not measured.

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
'''
    (docs/'FINAL-REPORT.md').write_text(report,encoding='utf-8')
    exact_commands=f'''Private reproduction (PowerShell):
```powershell
$Model = '{model}'
$Sdk = '{sdk}'
$EvalRoot = '{private.parent}'
Set-Location '{repo}'
rtk proxy "$EvalRoot/venv-pinned/Scripts/python.exe" scripts/minicpm-v47/evaluate.py probe --model $Model --sdk $Sdk --reject-only --output "$EvalRoot/evidence/pinned-repeat.json"
rtk proxy "$EvalRoot/venv-latest/Scripts/python.exe" scripts/minicpm-v47/evaluate.py probe --model $Model --output "$EvalRoot/evidence/nightly-repeat.json"
rtk proxy "$EvalRoot/venv-latest/Scripts/python.exe" scripts/minicpm-v47/smoke.py --model $Model --output "$EvalRoot/evidence/text-smoke-repeat.json" --timeout 600
```
'''
    (private.parent/'HANDOFF.md').write_text('Private physical path map\n\n'+json.dumps(roots,indent=2)+'\n\n'+exact_commands+'\n'+report,encoding='utf-8')
    print('Prepared reports; verdicts:',statuses)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--private',type=Path,required=True);p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--sdk',type=Path,required=True)
    a=p.parse_args();run(a.private,a.repo,a.model,a.sdk)
