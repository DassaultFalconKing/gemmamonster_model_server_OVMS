# QWENMONSTER / MoE OTD packs: frozen audit checkpoint
**Date:** 2026-10-22  
**State:** SOURCE/BUILD/UNIT/LIMITED-LIVE + PACK-BENCH EVIDENCE. **ACCEPTED: NO.**  
**Purpose:** reproducible, documentation-only review checkpoint; does not supersede the project's MASTER-PLAN or imply that unrun gates passed.

## 0. Immutable baseline, branch, and edit boundary

- Audited integration ref: `DassaultFalconKing/gemmamonster_model_server_OVMS:integration/qwm01-otd-pack-20261022` at **`85c37fcfb87a5d49d80a362930a5d261baf0ce0e`**.
- Frozen report branch: `checkpoint/qwm01-otd-pack-20261022`, created directly from that exact SHA. This checkpoint and the companion whitepaper are documentation-only commits; use their final full commit SHA as the stable snapshot, not the potentially moving branch name.
- Original accepted C6 ancestor: `c6-head-mainline-20261020` @ `ba6ec792c3121850fea167fa7d7e190b25fcdc76`.
- QWM01 protocol parent at audit: `feature/qwenmonster-qwm01-request-schema-20261021` @ `0c597075ca0078a84fbbfd4c01eb02adf7965acd` (integration ahead 5, behind 0).
- Packs source: `research/ovms-otd-pack-mode-2026` @ `1d9b497ea27221c51636af028e597e6c681d42b2`; integrated in OVMS merge `44d76afecbb7909ac696a2a13a930c57a7625334`.
- GPU plugin: `DassaultFalconKing/openvino`, measured cohort `research/ov-gpu-otd-cohort-b5bfb148` @ `479219245f6f10b670367ad35af16513d72d2091`; separate portability line `research/ov-gpu-otd-observability-2026` @ `956d5eca956f45b9b76a29daafc3642eb2d9520f`.
- Research-only related branch: `docs/moe-nvme-experts-research-20261021` @ `9dc49cb69b37b523d974ed6aa204f0a00ef3cf6a`. No code-line merge or runtime acceptance follows from that document branch.
- At this audit the OTD integration branch was **76 commits ahead of C6, behind 0**. `85c37fcfb` changed only four QWM documents; the pack code already existed before it.
- **No runtime, public-source-lock, source branches, original C6, model files, or operator processes were changed by this checkpoint.** The operator's compute pause remains in effect.

## 1. Measured binary identity (reported by handoff)

| Component | SHA-256 |
|---|---|
| OVMS pack executable | `1175bd25d6faf90e41c6591e23507cf6117895351462ff3b5648c8a6df08a760` |
| GPU plugin DLL | `1093b69f6314898238ffec06fb46631759526e89c90e3e3fd2fd29c122e8058e` |
| GenAI DLL (unchanged candidate) | `442452056e06c3a7e05d71ca082e9f30fd0034c8f6dcf5b2e56f04f140599e4d` |

These are hashes **reported in the handoff**; the reviewer had no access to the private binary files for independent checksum recomputation. The measured executable is not the pre-pack drafter executable and is not the accepted C6 or published dependency lock.

## 2. Pack construction and four benchmark rows

- `--build_moe_experts_pack --moe_experts_pack_dir` created **40 files × 434,118,656 bytes** at OFFLOAD_RATIO=40; a repeat build reported reuse. Packs are content-keyed by the expert layout/model and their identity does not encode the chosen offload ratio.
- Serve `--moe_experts_pack_dir` invokes plugin `require`, and the graph reached `AVAILABLE` with these packs, including at OFFLOAD_RATIO=75.
- Benchmark: `temperature=0`, **55 prompt / 384 completion tokens**; one warmup + three measured repeats per row, every result `finish_reason=length`. The rows establish ordinary generation, **not semantic correctness or protocol/tool calling**.
- GPU cache residence: 64 of 256 expert slots at ratio 75; 153 of 256 at ratio 40, per the measured handoff.

| Mode | Repeated TTFT s | Repeated decode tok/s | Hits | Misses | Disk reads | Disk bytes | Transform ms |
|---|---|---|---:|---:|---:|---:|---:|
| packed r75 | 4.43 / 4.18 / 4.20 | 5.75 / 5.94 / 5.97 | 426946 | 77576 | 77576 | 131549036544 | 0 |
| unpacked r75 | 5.23 / 5.23 / 5.23 | 5.32 / 5.31 / 5.35 | 426921 | 77572 | 698148 | 131542253568 | 11656 |
| packed r40 | 1.32 / 1.09 / 1.06 | 6.95 / 7.33 / 7.39 | 494685 | 9871 | 9871 | 16738689024 | 0 |
| unpacked r40 | 1.98 / 1.45 / 1.26 | 6.95 / 7.13 / 7.08 | 489410 | 15091 | 135819 | 25590472704 | 2408 |

Derived *means of the three measured repeats*, rounded: packed r75 TTFT **4.27 s** / decode **5.89 tok/s**, unpacked r75 **5.23 s** / **5.33 tok/s**; packed r40 **1.16 s** / **7.22 tok/s**, unpacked r40 **1.56 s** / **7.05 tok/s**. At r75, packed improves decode ~10.5%; at r40 ~2.4% for this short, fixed benchmark. The benefit in disk read **count** is ~9× for a miss; disk **bytes** are not reduced 9×. A smaller offload ratio itself drastically reduces misses and is a separate factor. Do not infer sustained throughput, 2048-token prefill, memory headroom, or agent quality from these rows.

**Measurement caveats:** available RAM at process start was packed r75 9824 MiB, unpacked r75 17667 MiB, packed r40 16765 MiB, unpacked r40 17835 MiB. r75 packed was below the drafter's 15463-MiB minimum. The first packed-r40 client attempt failed; its extra warmup and partial cancellation appear in the full-process trace, but the published counters are for the four successful-generation window. Three of four traces end with a truncated final record. **No `[OTD_PERF]` process-exit stderr summary was captured**: the process termination path did not run the atexit callback. Counters above are from offline `otd_sim.py summary` on the measured trace windows. Private raw traces are not in the public repository.

## 3. Parser / generation config / protocol: distinct evidence levels

| Component or gate | Evidence observed by audit | Classification |
|---|---|---|
| Qwen parser | 69/69 unit, 14 fixtures × 2340 partition runs | **UNIT GREEN** |
| Qwen generation-policy builder | 9/9 structural unit | **UNIT GREEN** |
| Generic parser | 29/29 focused unit | **UNIT GREEN** |
| Post-repair combined Qwen/Gemma parser controls | 148/148 in full `ovms_test` (including 79 Gemma), separate earlier 67/70 baseline was superseded | **UNIT GREEN** |
| QWM HTTP intake and tools | 2/2 QWM cases (12 internal intake cases), 11/11 tool controls | **UNIT GREEN** |
| HTTP 400 negative transport | 17/17 raw HTTP captures, 15 unary + 2 stream | **LIVE GREEN within negative scope** |
| Controlled weather-stub tool-result continuations | 20/20 semantically checked (10 unary + 10 SSE); wrapper final exit NOT CAPTURED | **LIMITED LIVE**, not autonomous loops |
| Ornith Qwen3.6 smoke | unary, SSE, valid no-arg `ping`, named/required city, none; one loaded-candidate `city=Paris` | **LIMITED LIVE** |
| `auto` unconstrained/guided A/B | guided OFF by default; structural unit passes but production comparison absent | **OPEN** |
| `required` and `named` 100/100 | only isolated successful live calls; 100/100 suspended by operator | **OPEN** |
| `parallel_tool_calls`, full multi-call, reasoning→tool phases, complete 50–100 history/template token-ID validation | no full matching live matrix | **OPEN** |
| `XGrammar #802` zero-args grammar | isolated native 29/29 and GenAI 31/31; baseline whitespace 422/425 vs candidate 0/425 | **CANDIDATE VALIDATED, installed runtime gate OPEN** |
| `XGrammar #650` XML end marker | 71/71 tokenizer native matcher PASS; actual `</parameter1>` Ornith live probe NOT RUN | **LIVE OPEN** |
| R1 schema native matrix | 24 PASS / 4 known OPEN (undeclared-required profile cases) | **NOT CLOSED** |
| Backend LENGTH | unary/SSE `length` at 16 tokens PASS; healthy follow-up `OK` | **LIMITED LIVE** |
| Client cancel and resource reclamation | executor saw requests drain but retained memory; `generation_stream.hpp:136` metrics-before-completion error reproduced | **NOT PROVEN** |
| 1/2/4 real session agent work | NOT RUN | **OPEN** |
| MTP K3 + packs | NOT RUN (unpacked K1/K2/K3 27-in/64-out smoke is not a pack result) | **OPEN** |
| `ovms_test --gtest_filter=*oeExpertsPack*` and GPU `moe_otd_*` / `moe_offload_*` | NOT RUN | **OPEN** |
| GPU standalone trace/LRU/pack tests | 43 PASS; 31,306-event synthetic C++/Python LRU replay zero mismatch | **STANDALONE UNIT GREEN** |

The generation builder's source implements `none` (no grammar), `auto` default unconstrained / opt-in lazy `TriggeredTags`, and hard `required`/named through `TagsWithSeparator` and `QwenXMLParametersFormat`. **Builder shape passing gtest does not independently prove decoder masks, canonical thinking-prefix interaction or tool execution.** Parser output validation and XGrammar generation constraints are distinct. The four native R1 OPEN cases must not be relabelled as passing.

## 4. Next safe work and promotion gates

1. **Do not resume GPU work while compute pause remains.** Start with static review and inspect current processes/owners before any future exclusive inference session.
2. For pack acceptance, execute missing dedicated `ovms_test` and GPU filters and negative pack scenarios: missing, corrupted, wrong-model pack fail-closed. Compare original manifest/checksums and raw logs without publishing private machine paths.
3. After operator releases compute, compare MTP K3 with/without packs using exact binary/model/prompt identity, fixed RAM floor and 2048-input workloads. Report prefill separately if available, TTFT, decode, hit/miss/read bytes, tail latency, accepted/speculated tokens, peak memory, and trace errors. Do not conflate short smoke with speedup.
4. Resolve lifecycle CANCEL/perf assertion; demonstrate actual handle cancellation and resource behaviour after disconnect, then deterministic protocol tests.
5. Close reasoning/handoff, canonical Jinja token-ID history, #650 live marker, #802 installed cohort, undeclared-required fail-closed contract, guided auto decision-vs-parser-loss, 1/2/4 session agentic work. Keep accepted C6 and lock immutable until explicit promotion.
6. Update `STATE.md` top checkpoint and `MASTER-PLAN.md` only on a *future working branch*, after new evidence. This snapshot is frozen. The older opening lines of `MASTER-PLAN.md` and `HANDOFF-DRAFTERS` refer to an obsolete single packed row; prefer current upper `STATE.md` + `HANDOFF-MOE-OTD-PACK` before making scheduling decisions.

## 5. Canonical links and provenance

- [Audit baseline commit](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/commit/85c37fcfb87a5d49d80a362930a5d261baf0ce0e)
- [Pack handoff](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/docs/qwenmonster/HANDOFF-MOE-OTD-PACK-20261022.md)
- [QWM STATE](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/docs/qwenmonster/STATE.md)
- [MASTER PLAN](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/docs/qwenmonster/MASTER-PLAN.md)
- [Parser/policy test evidence](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/docs/qwenmonster/evidence/UNIT-RESULTS.json)
- [Post-repair OVMS test evidence](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/docs/qwenmonster/evidence/ovms-test-http-20261021/RESULTS.json)
- [Controlled continuation/HTTP400 evidence](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/docs/qwenmonster/evidence/followup-20261021/RESULTS.json)
- [Native R1 candidate gaps](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/docs/qwenmonster/R1-NATIVE-20261021.md)
- [Drafter handoff](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/docs/qwenmonster/HANDOFF-DRAFTERS-20261022.md)

**Review rule:** “PASS” always carries its scope; absent raw evidence stays “reported PASS”; no unit/short generation row is a substitute for full protocol or performance acceptance.
