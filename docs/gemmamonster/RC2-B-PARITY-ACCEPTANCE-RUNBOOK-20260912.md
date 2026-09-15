# RC2 B-PARITY acceptance and tuning runbook — 2026-09-12

## Purpose

Test one immutable B-PARITY package built from the existing advanced 2026.4 semantic-refit source. Separate correctness from runtime tuning, then tune one variable at a time on the same package.

Never rebuild or edit production source during acceptance. A profile result belongs to one exact package SHA256, driver, model and launch configuration.

## Immutable inputs

Before testing record:
- candidate branch/full Git SHA/tree;
- full SHA256 of `ovms.zip` and `ovms.exe`;
- hashes of OpenVINO/GenAI/Tokenizers/GPU-plugin DLLs;
- model path and immutable model-file identity available to the harness;
- Intel GPU driver version;
- exact `ovms.exe --version` output.

Use VLM_CB and the existing Wondernutts Gemma4 model. Do not change driver before baseline/parity testing.

## Phase 1 — source and package gates

Required before expensive runtime tests:

1. Run `tests/windows/gemmamonster_env_preflight_profile_contract_test.ps1`.
2. Run the dedicated Gemma4 fast contract target:
   `//src/test/llm/gemma4_fast:gemma4_parser_contract_test`
   This target contains parser, reasoning-semantic-refit and recovery-contract tests and inherits `GEMMA4_TOKENIZER_PATH`.
3. Run:
   - `//src/test/llm/gemma4_overlay:gemma4_chat_template_overlay_contract_test`
   - `//src/test/llm/gemma4_overlay:gemma4_google_jinja_contract_test`
4. Run the complete built `bazel-bin\src\ovms_test.exe` suite if not already proven for the exact final build commit/package.
5. Run packaged `setupvars`, `ovms.exe --version`, and `ovms.exe --help`.

If a required source/package gate fails, do not compensate with runtime flags.

## Phase 2 — P0 semantic baseline

Launch the exact package with the RC1-equivalent baseline first, no new tuning:

- `--pipeline_type VLM_CB`
- `--target_device GPU`
- `--tool_parser gemma4`
- `--reasoning_parser gemma4`
- no U4 KV override;
- exact 2026.4 defaults for scheduler fields unless already explicitly part of RC1 launch;
- prefix caching remains OFF for the exact 2026.4 GenAI profile unless explicitly set otherwise.

Run cheap tests first:
1. plain completion;
2. `tool_choice=none`;
3. obvious `tool_choice=auto` native call;
4. tool-result continuation;
5. nested/complex JSON schema;
6. parallel distinct tool calls;
7. streaming auto tool call.

For streaming capture three layers whenever possible:
- exact request JSON;
- raw OVMS SSE/JSON;
- client/NovaClaw interpretation.

Failure localization:
- no native tool frame/raw API call and `finish_reason=stop` -> generator/template/history side;
- native marker exists but OpenAI `tool_calls` is absent -> parser/finalization/streamer side;
- API contains `tool_calls` but NovaClaw stops -> harness/client side.

## Phase 3 — NovaClaw-shaped continuity

Run a realistic 20–50-turn agentic sequence with repeated:
`assistant tool_call -> tool result -> assistant continuation -> next tool/final answer`.

Explicit failure criterion: assistant prose such as “I will use/call/check …” followed by `stop` or otherwise no executable native tool call when the trajectory clearly requires the announced tool.

Preserve the first adjacent PASS->FAIL pair with request, raw server response/SSE, server log slice and NovaClaw interpretation.

## Phase 4 — P0 performance and endurance

Only after semantic baseline is green:
- run the existing Gemmamonster benchmark harness with fixed prompts and at least 10 repetitions per measured case;
- distinguish TTFT, prefill-sensitive total latency and sustained long-response decode rate;
- do not compare the short constrained ~62 tok/s RC1 tool-call peak to sustained decode;
- RC1 sustained reference is roughly 26–31 tok/s under the frozen campaign;
- run at least 150 realistic mixed requests for the promotion endurance gate.

Watch logs for:
- `CL_OUT_OF_RESOURCES`;
- `GPU_CONTEXT_FATAL`;
- executor quarantine;
- zero-token outputs;
- restart/reload requirement.

After GPU fatal/quarantine, kill the process and treat that profile as failed. Never reuse a quarantined executor for later measurements.

## Runtime tuning ladder — same binary, fresh process per profile

Change exactly one logical dimension at a time. Preserve P0 as the causal baseline.

### P1 — U4 KV only

Add GPU plugin configuration:
`--plugin_config '{"KV_CACHE_PRECISION":"u4"}'`

Reason: the exact pinned OpenVINO `227c337...` contains Intel GPU Paged Attention INT4 KV-cache support; the exact OVMS line has generic `plugin_config`, while it does not expose a dedicated `kv_cache_precision` calculator field.

Measure correctness, memory, TTFT and sustained decode before proceeding.

### P2 — U4 + batched tokens 4096

Keep P1 and set:
`--max_num_batched_tokens 4096`

This targets local/low-concurrency prefill and long-context TTFT.

### P3 — U4 + batched tokens 8192

Keep P1 and set:
`--max_num_batched_tokens 8192`

Compare against P2 on identical prompt lengths and decode lengths. Reject if memory pressure/endurance materially worsens.

### P4 — prefix caching on the best P1/P2/P3 profile

Add:
`--enable_prefix_caching true`

The exact 2026.4 scheduler default is false, so this is a real experimental variable. Stress repeated-prefix conversations at approximately 1k, 8k, 16k and 32k input-token scales. Any reproducible zero-token completion or corrupted continuation fails this profile regardless of TTFT improvement.

### P5 — optional low-concurrency DSF A/B

Only after identifying the best safe `max_num_batched_tokens` profile, compare `dynamic_split_fuse=true` versus `false`.

When DSF is disabled, the configured batched-token limit must be large enough for the full tested prompt because prompt splitting is no longer available. Do not test DSF=false with a prompt longer than the configured limit and call the resulting failure a model regression.

## Cache-size policy

Do not introduce a fixed `cache_size` in the first parity profiles. Start from the same/dynamic behavior as baseline, record actual memory use, then consider a bounded cache only if endurance data shows uncontrolled memory pressure. A hard cache cap is a separate variable.

## Driver policy

Keep RC1 driver `32.0.101.8991` through P0–P5. A newer driver is a separate post-parity experiment and must use the already-selected binary/runtime profile.

## Context ladder

After semantic correctness, run context probes at increasing input sizes with deterministic unique nonces so prefix-cache hits cannot accidentally fake an uncached run. Suggested ladder: 512, 2k, 8k, 16k, 32k, then larger only while memory and model limits allow.

For prefix-cache tests, separately repeat identical prefixes to measure the intended cache hit.

## Promotion gates

RC2 candidate promotion requires:
- exact source/package/dependency provenance;
- dedicated Gemma4 contracts PASS;
- full built test suite PASS for the final build;
- official package self-test PASS;
- `auto`, `none`, streaming, complex-schema, parallel and multi-turn continuation PASS;
- NovaClaw long-loop replay PASS;
- no promise-without-native-tool-call regression in the acceptance corpus;
- >=150 realistic requests with no GPU fatal/quarantine/restart;
- no zero-token prefix-cache regression if prefix caching is selected;
- TTFT and sustained decode compared against immutable RC1.

`required` and named forced-tool instability remain secondary/non-blocking for the primary NovaClaw auto-tool deployment, but record them separately rather than hiding failures inside an overall request-success count.

## Required output

Produce a profile table containing, for P0 and every tested P-profile:
- exact command line;
- package SHA256;
- driver;
- pass/fail by semantic test family;
- TTFT distribution;
- sustained decode tok/s;
- context length;
- peak memory observations available from the host;
- runtime-fault count;
- NovaClaw long-loop result.

Conclude with exactly one of:
- `PROMOTE <profile>`
- `KEEP P0 / NO TUNING WIN`
- `REJECT PACKAGE`

Do not modify source to rescue an acceptance profile.