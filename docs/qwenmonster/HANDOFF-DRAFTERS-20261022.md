# Agent handoff: Ornith drafters, 2026-10-22

**SUPERSEDED resume authorization, 2026-10-23:** the operator has frozen the historical parser-green 2026.5 basis and stopped work on it. Do not execute this document's resume sequence. Next direction is semantic refit preparation on known-good 2026.4; see [FROZEN-PARSER-GREEN-20261021.md](FROZEN-PARSER-GREEN-20261021.md). Historical measurements below remain scoped evidence only.

**PAUSED BY OPERATOR. ACCEPTED: NO.** The operator has active compilations and requested status commits/publication only. Do not start or resume models, benchmarks, exporters or builds from this handoff. No benchmark or OVMS process was active at the pause snapshot; an unrelated compiler was active and was left untouched.

## Source and runtime boundary

Branch: `qwm01-request-schema`, remote branch `feature/qwenmonster-qwm01-request-schema-20261021`. Source checkpoint before this documentation: `8f88ca704`.

Existing commits `3e3d38a8e` (skip metrics on stopped/cancelled generation) and `8f88ca704` (compile XML tool schemas once per request) are source changes from the other worker. They are not included in the executable used for the drafter measurements. Their build, focused regression and live acceptance are **NOT RUN by this coordinator**. Do not transfer earlier passing parser tests onto them.

Measured executable SHA-256: `3f4316ebc3c843c75215d120a2a542c5df685c1f2d4c3b12d9d1ccca67a3f527`.
Measured GenAI DLL SHA-256: `442452056e06c3a7e05d71ca082e9f30fd0034c8f6dcf5b2e56f04f140599e4d`.
GenAI source: `8f305a1c1bc11e348c8ad0cc37269a91ba21cc74`; XGrammar source: `5b0b7084a65a2059b44c03fbc6320ad7fcc41f33`.

Original C6, published dependency lock, staged runtime and original target model were not changed by the drafter work. The earlier operator-approved installed DLL exception remains in MASTER-PLAN.md. New IRs and diagnostics are private isolated candidates. Local machine paths, raw logs and weights must stay out of GitHub.

## Evidence and actual status

| Item | Status and boundary |
|---|---|
| Native MTP head | Export PASS; strict learned-weight load and paged-attention transform PASS. HF revision `7911821a81555cff24a60d5233f2cca5aa055fa6`. Original target contains no usable MTP IR. |
| MTP baseline/K1/K2/K3 | HTTP unary and SSE smoke completed with matching short deterministic content. Native timing smoke completed, exit 0. Input only 27 tokens, output only 64 tokens: **SMOKE ONLY**, no long-context speedup conclusion. |
| Long-context workload | Prepared exact 2048 token IDs including real chat template and open thinking prefix. SHA-256 of templated UTF-8 text: `21bbe71ddeafd40ccdd25db9fb0003196464d4f84f10be20273170c48364e99c`. |
| Long-context diagnostic | Private executable built. Worker reports encoded-ID API incompatibility for embedding-based MTP and switched to pre-templated string generation with runtime token-ID equality checks. Final executable's end-to-end validation is **NOT RUN**; reconstructed output IDs are not original generated IDs. |
| Long-context matrix | Baseline/MTP K1/K2/K3, output limits 2048/4096, two measured repeats per cell: **ALL NOT RUN**. No runner launched. |
| AEON DFlash | Strict export PASS, HF revision `49604b324a9bc626939efef966c8db2ce59b6b84`. Runtime startup FAILED: target lacked hidden-state metadata; fallback found 1 of 5 required outputs. |
| AEON target overlay | Metadata-only candidate XML identifies target layers 1/10/19/28/37. Original XML untouched; weights shared read-only. Retry, runtime validation and K4/K6 measurements **NOT RUN**. K denotes candidate-token budget, not quantization. |
| Existing ordinary EAGLE3 IR | Paged-attention transform reproduces an undeclared beam/mask parameter failure. This artifact is not automatically the Zenith MoE v5 model. No production transform patch accepted. |
| Zenith EAGLE3 v5 | Metadata/header feasibility only, revision `bcbabe2b66982920eb432790be65da3eea1a6f23`. Custom MoE32/top4/32K shortlist is not proven compatible. No large port or runtime test. |
| z-lab DFlash | Metadata only, revision `f181eece646affea2c38b2765f1aaa01a9734ccd`; NOT RUN. |
| Agentic acceptance with drafters | NOT RUN. Short protocol smoke does not establish useful autonomous work or 20 successful tool-result continuations. |

Matched smoke settings: GPU, OFFLOAD_RATIO=40, cache_interval_multiplier=256, prefix caching disabled, max_num_seqs=1, max_num_batched_tokens=32768. No persistent service was left running by the finite benchmarks; normal phase shutdown must not be reported as a crash.

## Resume contract, after operator releases compute

1. Inspect current processes and ownership first; preserve active compilations and any healthy service. Serialize model/GPU work and retain available-RAM startup floor 15463 MiB.
2. Validate the existing private diagnostic, including exact 2048 runtime input tokens and disabled template reapplication. Do not repeat broad discovery or rebuild dependencies.
3. Run durable logged baseline then MTP K3 first; extend K1/K2 after useful partial results. Thinking enabled, natural EOS, output limits 2048/4096. Limits are not actual output length or a separately enforced reasoning quota. Warm up, repeat, preserve failed and unfinished rows.
4. Report prefill/first inference, TTFT and decode separately. Verify metric units/SD batching semantics from the pinned source. TTFT is not pure prefill. Whole-response token rate is not decode throughput. If pure prefill is unavailable, report NOT_AVAILABLE. Keep raw timestamps, inference durations, token/batch counts, actual generated length, accepted/proposed draft counts and memory peaks. Label reconstructed output IDs explicitly.
5. Validate AEON overlay in the exclusive runtime slot before any performance claims. Native engine constraints include greedy decoding and one active sequence; do not promise concurrent DFlash throughput.
6. Prove actual generation policy, parser/SSE behavior and useful tool-result continuations on the chosen exact tuple. Operator manually stopped repetitive 100/100 required/named loops and says not to repeat them as the default workload; preserve that distinction from full acceptance.
7. Review evidence, then update this handoff, MASTER-PLAN.md and the top STATE.md checkpoint. No candidate promotion until its own gates pass.

## Worker and private evidence continuity

External harness: OpenCode 1.19.3, `opencode/deepseek-v4.1-flash-free`, provider session `ses_e9ed286ccffeIPtbdkxZwKn0Gu`. Worker exited 0 on step-limit exhaustion after preparing the diagnostic, **not** after completing measurements. Its status/report still described setup and are superseded by this pause checkpoint. Do not resume the session during operator compilations.

Private evidence is under `<PRIVATE_EVIDENCE>/drafters-20261022`: `MTP-BENCHMARK.json`, `NATIVE-PROCESSES.json`, `native-baseline.log`, `native-mtp.log`, `AEON-BENCHMARK.json`, candidate EXPORT/ANNOTATION receipts and `long-context/` source/prompt/diagnostic. Exact local locations stay in the operator's private task registry.
