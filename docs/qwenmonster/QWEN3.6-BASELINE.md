# Qwen 3.6 + Unsloth MTP + Ornith + Qwen3.8 baseline

Date: 2026-10-21. Status: preparation / SOURCE ONLY; ACCEPTED: NO.

## Scope and integration

This document establishes a frozen baseline for serving Qwen 3.6 and Qwen3.8
models through the OVMS/Qwenmonster stack, using Unsloth MTP GGUFs as the
primary inference path and Ornith-1.x as the agentic-coding reference family
(post-trained on Qwen3.5/Qwen3.6 bases).

This is a design-and-pin document. No build, unit, API, live, or agentic
acceptance has been run against this baseline. It does not modify the C6
dependency source lock in `public-source-lock.json`.

## Model family

| Model | Variant | Parameters | Activated | Architecture | Context | MTP |
|-------|---------|------------|-----------|--------------|---------|-----|
| Qwen3.6 | 27B | 27B dense | 27B | Gated DeltaNet + Gated Attention | 262K native, 1.01M ext | Yes (Unsloth GGUF) |
| Qwen3.6 | 35B-A3B | 35B MoE | 3B active | Gated DeltaNet + MoE (256 experts, 8 routed + 1 shared) | 262K native, 1.01M ext | Yes (Unsloth GGUF) |
| Qwen3.8 | 27B | 27B dense | 27B | Qwen3.5-derived dense + vision | 262K native, 1.01M ext | Planned |
| Qwen3.8 | 2.4T-A95B | 2.4T MoE | 95B active | Qwen3.5-derived MoE | 1M | Planned |
| Ornith-1.0 | 9B / 31B / 35B / 397B | 9–397B | varies | Qwen3.5 / Gemma 4 post-train | 128K–256K | No |

## Inference stack

| Component | Role | Version / pin | Notes |
|-----------|------|---------------|-------|
| Unsloth Studio / llama.cpp | Local inference engine | llama.cpp with MTP support merged | `--spec-type draft-mtp --spec-draft-n-max 2` recommended |
| Unsloth GGUF | Quantized model weights | `unsloth/Qwen3.6-27B-MTP-GGUF`, `unsloth/Qwen3.6-35B-A3B-MTP-GGUF` | UD-Q4_K_XL recommended; ~1 GB extra VRAM for MTP |
| vLLM | Production serving | >= 0.19.1 | `--reasoning-parser qwen3 --tool-call-parser qwen3_xml` |
| SGLang | High-throughput agentic serving | >= 0.5.10 | `--speculative-algo NEXTN --speculative-num-steps 3` |
| Ornith-1.x | Agentic coding reference | deepreinforce-ai/Ornith-1.0-* | MIT licensed; Qwen3.5/Gemma 4 post-trains |

## MTP configuration

MTP (Multi-Token Prediction) predicts multiple future tokens in a single
forward pass; the main model verifies them in parallel. Only verified tokens
are kept, so accuracy is unchanged.

Recommended llama.cpp flags:

```bash
./llama.cpp/llama-server \
    -hf unsloth/Qwen3.6-27B-MTP-GGUF:UD-Q4_K_XL \
    -ngl 99 -c 8192 -fa on -np 1 \
    --spec-type draft-mtp --spec-draft-n-max 2
```

- `--spec-draft-n-max 2` is the best starting point; try 1–6 for hardware-specific optimum.
- Do not exceed 2 draft tokens: acceptance rate drops from ~83% to ~50% at 4 draft tokens.
- MTP adds ~1 GB VRAM headroom over the base GGUF.
- `-np > 1` and `--mmproj` are not yet supported with MTP.

Expected speedup: ~1.4–2.2× for dense models (Qwen3.6 27B), ~1.15–1.25× for MoE (Qwen3.6 35B-A3B).

## Tool calling and reasoning

Qwen 3.6 / Qwen3.8 / Ornith use XML-style tool calls (`<tool_call> ... </tool_call>`) and
`...` reasoning blocks.

| Parser | Purpose |
|--------|---------|
| `qwen3` | Reasoning parser — extracts `...` into `reasoning_content` |
| `qwen3_xml` | Standard XML tool-calling parser |
| `qwen3_coder` | Code-generation-optimized tool-calling parser |

SGLang example:

```bash
python -m sglang.launch_server \
    --model-path Qwen/Qwen3.6-27B \
    --port 8000 --tp-size 8 --mem-fraction-static 0.8 \
    --context-length 262144 \
    --reasoning-parser qwen3 \
    --tool-call-parser qwen3_coder \
    --speculative-algo NEXTN \
    --speculative-num-steps 3 \
    --speculative-eagle-topk 1 \
    --speculative-num-draft-tokens 4
```

vLLM example:

```bash
vllm serve Qwen/Qwen3.6-27B \
    --port 8000 --tensor-parallel-size 8 \
    --max-model-len 262144 \
    --reasoning-parser qwen3 \
    --speculative-config '{"method":"qwen3_next_mtp","num_speculative_tokens":2}'
```

## Memory budget (Qwen3.6 27B, 4-bit)

| Component | Memory |
|-----------|--------|
| Model weights (4-bit) | ~19 GB |
| MTP head overhead | ~1 GB |
| KV cache (8K context) | ~2–4 GB |
| OS/runtime reserve | ~4 GB |
| **Total minimum** | **~26 GB** |

Qwen3.6 35B-A3B 4-bit: ~24 GB weights + MTP overhead + KV.

## Baseline artifacts (to be captured)

- [ ] Model GGUF SHA256 for each variant
- [ ] llama.cpp / SGLang / vLLM commit SHA
- [ ] Build/runtime versions and DLL inventory
- [ ] Live Gemma / Qwen acceptance numbers (NOT CAPTURED — check on deployment host)
- [ ] MTP acceptance rate at draft-n=2 vs draft-n=4
- [ ] Tokens/s for 27B dense and 35B-A3B MoE on target hardware

## Direct code observations (OVMS side)

- The existing Qwen3Coder tool parser (`src/llm/io_processing/qwen3coder/qwen3coder_tool_parser.{hpp,cpp}`) handles `<tool_call> ... </tool_call>` XML tool calls.
- The streaming router (`src/llm/io_processing/output_parser.cpp`) and streamer (`src/llm/ovms_text_streamer.cpp`) support `drainPendingDelta()`.
- Gemma4 bounded repairs (branch `repair/gemma4-bounded-20261021`) are a separate, unrelated change set.
- No Qwen 3.6 / Qwen3.8 / Ornith parser integration exists yet in this worktree.

## Non-negotiable invariants (from AGENTS.md)

- Executable tool identity is published only after completed envelope, registered function name, and executable argument schema validation.
- Chunk partition must not change semantic tool calls, typed arguments, order, or SSE reconstruction.
- Native XML transport markers are reserved boundaries; malformed envelopes must not consume the next call.
- Unsupported or malformed schemas and arguments fail closed.
- Grammar mask correctness is separate from parser tolerance.

## Next gates

`SOURCE → BUILD → UNIT → MATCHER → API → LIVE → AGENTIC`

All stages are NOT RUN at this checkpoint. This document is SOURCE ONLY.

## Provenance

- Qwen 3.6 / Qwen3.8 model specs: QwenLM/Qwen3.8 (GitHub), Qwen.ai blog (2026-08-03)
- Unsloth MTP GGUFs and benchmarks: unsloth.ai/docs/models/mtp, unsloth.ai/docs/models/tutorials/qwen3.6
- Ornith-1.0 agentic coding models: ornith.ai, deepreinforce-ai/Ornith-1.0-* (Hugging Face)
- SGLang / vLLM serving recipes: unsloth.ai Qwen3.6 docs, Ornith-1.0-397B model card
- INDEPENDENT DESIGN: this baseline document is not derived from an upstream C6 or Qwenmonster baseline; it adapts the C6-BASELINE.md structure to the Qwen 3.6 / Ornith / MTP stack.
