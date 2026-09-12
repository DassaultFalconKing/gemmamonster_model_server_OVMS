# OVMS Gemma4 Build Record — IMMUTABLE
# Frozen: 2026-09-12

## Source
repo_sha: a43f644f10e55d741d5388e43580146c5203c196
repo_msg: "build: fix Windows build scripts for VS 2022 BuildTools at C:\BuildTools"
repo_clean: yes (only untracked bazel output dir)

## Binary
path: C:\git\gemmamonster-2026.4-unified-20260911\dist\windows\ovms\ovms.exe
size: 22772224 bytes
last_write: 2026-09-12T03:55:57

## Model
path: C:\llm\models\OpenVINO\Wondernutts\gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov
name: gemma4-26-heretic
arch: Gemma4MoE 26B (A4B active, 4-bit quantized, int4-ov)
total_size: ~21.9 GB (language 14.8G + embeddings 0.7G + vision 0.6G + tokenizer 0.05G + detokenizer 0.004G)

## Launch Command
```
.\ovms.exe `
    --rest_port 8000 `
    --model_path "$model" `
    --model_name gemma4-26-heretic `
    --task text_generation `
    --pipeline_type VLM_CB `
    --target_device GPU `
    --tool_parser gemma4 `
    --reasoning_parser gemma4
```

## Hardware
gpu: Intel Arc 140V (16GB)
driver: 32.0.101.8991
platform: win32

## Baseline Bench (10 runs, 2026-09-12)
ttft_avg: 2.62s (range 2.35-2.97s)
gen_avg: 35.1 tok/s (range 22.9-63.5 tok/s)
tool_auto_gen: 62 tok/s
agentic_loop_gen: 28 tok/s
complex_schema_gen: 30 tok/s
parallel_tools_gen: 29 tok/s
success_rate: 80/80 (100%)
known_issue: tool_choice=forced/required causes 20-30% loop-fail
