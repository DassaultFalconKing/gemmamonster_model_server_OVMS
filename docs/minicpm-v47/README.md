# MiniCPM-V 4.7 / GEMMAMONSTER — execution and MFP-1 program

**23 October 2026. DOCUMENTED / NOT ACCEPTED / no GPU run in this branch.**

Target: [OpenVINO MiniCPM-V-4.7-35B-A3B INT4](https://huggingface.co/OpenVINO/MiniCPM-V-4.7-35B-A3B-int4-ov), experimental Windows Arc 140V / 32 GiB unified-LPDDR.

## Two independently gated tracks

1. [ARC140V-EVALUATION-20261023.md](ARC140V-EVALUATION-20261023.md) — model file verification, pinned 2026.4 RC1 GenAI vs independent sandbox, compile, standalone text/image/video, memory, throughput and OVMS VLM_CB compatibility.
2. [MFP1-FULL-COMPATIBILITY-PROGRAM-20261023.md](MFP1-FULL-COMPATIBILITY-PROGRAM-20261023.md) — **full** native model protocol onboarding per MFP-1: official template/token IDs, reasoning, anti-hallucination parser-retainer, lossless typed arguments, schema validation, tools generation policy, SSE, multi-turn tool results, image/video history, acceptance and concrete code PR work packets.
3. [STATE.md](STATE.md) — durable handoff and evidence/status ledger. Update before and after each code phase.

The canonical umbrella protocol is [MFP-1](../qwenmonster/OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md). The source baseline `eb76a74f7aa39573d452d95443e189b1f5f4d9e8` is read-only. Use this branch only for the MiniCPM V4.7 program, evidence and self-contained future feature work.

**Do not confuse `MiniCPM-V-4.7` with existing `minicpm5`**: the former has a Qwen-like `<function=x><parameter=y>` tool-call envelope; the latter's supported parser uses `<function name="x"><param name="y">`. Reuse `qwen3coder` only with canonical template/token/phase/typed-argument tests. Do not modify Gemma/Qwen/Ornith or CIB2 memory/OTD as incidental refactoring.

### Operator launch command (Windows PowerShell 7)

```powershell
uvx hf download OpenVINO/MiniCPM-V-4.7-35B-A3B-int4-ov --local-dir "C:\llm\models\minicpm-v47-35b-a3b-int4-ov"
```

Do not automatically download BF16 source. The experiments may be blocked at full VLM or GPU even when tool parser tests pass; report independent gate outcomes honestly.

### Upstream evidence

- Optimum Intel merged [#2033](https://github.com/huggingface/optimum-intel/pull/2033) — v4.7 VLM IR export.
- OpenVINO GenAI merged [#4591](https://github.com/openvinotoolkit/openvino.genai/pull/4591) — v4.7 image/video pipeline.
- Original [v4.7 official template](https://huggingface.co/openbmb/MiniCPM-V-4.7-35B-A3B/blob/main/chat_template.jinja); pin its actual downloaded revision before implementation.
