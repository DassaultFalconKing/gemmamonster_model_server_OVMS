# ADR — LFM model-family roadmap and LFM2.5-24B OpenVINO status

Date: **2026-10-27**  
Status: **ACCEPTED as research/product direction; NO new runtime/model acceptance**  
Scope: GEMMAMONSTER OVMS 2026.4, Windows Core Ultra 258V / Arc 140V, offline agentic inference.  
Owner: LFM architecture program. This is a portfolio choice, not permission to rebuild the active production service.

## Decision

| Role | Exact model | Decision |
| --- | --- | --- |
| Primary fast local agent / first semantic-refit target | `OpenVINO/LFM2.5-8B-A1B-int4-ov` | **KEEP/PRIORITIZE**. Finish tool-use correctness, unary/SSE, reasoning and failure cases on our existing GPU build. |
| Strategic next-generation larger agent | `LiquidAI/LFM2.5-24B-A2B` | **PRIORITIZE FOR OPENVINO EXPORT FEASIBILITY AND FAIR A/B**; not yet a ready-to-serve OpenVINO IR. Do not replace our current agents until native export, tokenizer/template/parser, model load and measured end-to-end task completion have passed. |
| Existing larger model / known-good control and fallback | `OpenVINO/LFM2-24B-A2B-int4-ov` | **FREEZE AS CONTROL** with existing parser and test evidence. No expansive model-specific optimization unless reusable for the 2.5 generation. |
| Out of scope | CIB2 offload, shared runtime changes, production port 8137 | **NO CHANGE** in this ADR. |

Why: Our Arc 140V pinned U4 / OFFLOAD_RATIO=0 short-vs-long-input 512-output SSE median report records ~55.61/53.26 tok/s for 8B versus ~37.79/34.79 for old 24B (three runs per cohort). Historical Hybrid-C official agent evidence is 2/4 LFM2.5-8B versus 4/4 old 24B; those are small samples **not** comparative reliability estimates. 8B is the practical fast iteration target, not proof of higher task success. The new 24B is strategically interesting because Liquid AI explicitly trained it for reasoning and agents, but its value on this hardware is untested.

## OpenVINO release-status check — 2026-10-27

**Finding: no confirmed published official `OpenVINO/LFM2.5-24B-A2B-int4-ov` artifact, and no verified ready-to-load community OpenVINO IR was found in the public search.** This is a point-in-time **NOT_FOUND / NOT_VERIFIED** finding, not a claim that no private or unpublished export exists.

Evidence and distinctions:

1. Liquid AI released original **LFM2.5-24B-A2B** on **2026-10-13** (original model available):  
   https://www.liquid.ai/blog/lfm2-5-24b-a2b  
   https://huggingface.co/LiquidAI/LFM2.5-24B-A2B
2. OpenVINO's official Hugging Face LLM collection (checked 2026-10-27) lists **`OpenVINO/LFM2-24B-A2B-int4-ov`** and **`OpenVINO/LFM2.5-8B-A1B-int4-ov`**, **not** `LFM2.5-24B-A2B`:  
   https://huggingface.co/collections/OpenVINO/llm
3. The published old 24B IR clearly identifies its base model as **LiquidAI/LFM2-24B-A2B**, not LiquidAI/LFM2.5-24B-A2B. Do not conflate checkpoints:  
   https://huggingface.co/OpenVINO/LFM2-24B-A2B-int4-ov
4. OpenVINO's 2026 verified-model listing names old `lfm2-24b-a2b` and smaller LFM2.5 variants; it does **not** establish a validated new LFM2.5-24B checkpoint:  
   https://docs.openvino.ai/2026/documentation/compatibility-and-support/supported-models.html
5. OpenVINO / OVMS support for the **family** is not a pretrained-weight export. OVMS issue #4405 was resolved by support for lfm2/lfm2.5 as of 2026.3, but this does not attest new 24B IR loading:  
   https://github.com/openvinotoolkit/model_server/issues/4405

**Availability rule:** Update this ADR's status only after an exact model URL is reachable, with a `README`/metadata identifying `base_model=LiquidAI/LFM2.5-24B-A2B`, actual `openvino_model.xml` and `openvino_model.bin` (plus tokenizer/detokenizer artifacts where required), source revision/hash and conversion configuration. A repo named “24B” or model card claiming family support is insufficient.

## Rationale and compatibility boundaries

Manufacturer's announced new 24B profile: ~24B total, **2.45B active**, 40 blocks (30 gated-convolution + 10 GQA), 64 routed experts/top-4, **131,072-token context**, **128K vocabulary**, reasoning-centric post-training and tool-use RL. It evolves the old LFM2-24B but the tokenizer, templating and potentially generated graph artifacts differ: **NEVER reuse old 24B tokenizer, template, token IDs or parser acceptance results automatically.** Source: https://huggingface.co/LiquidAI/LFM2.5-24B-A2B

Reusability is a *hypothesis*: the shared `lfm2_moe` architecture and expert geometry favor reusing retainer principles, template-roundtrip suite, model-family probing and hot/cold inventory. Compatibility of OpenVINO export, OpenVINO GenAI/OVMS 2026.4 pipeline, conv state / GQA KV, Q4 weights and CIB2 expert pack must each be tested independently.

Reasoning-only output may consume substantially more tokens than the old non-reasoning model. Optimize **verified completed agent tasks per minute / resident memory**, not just decode tok/s. Evaluate realistic host tool results, false tool prose, literal integrity, SSE continuity, TTFT, token counts, loop success and failure classifications.

## Execution gates and priority

**P0 — preserve known-good agents.**
- Finish current Hybrid-C cleanup and its local 8B/old-24B validation on the latest source HEAD. Current historical GPU smoke does not automatically validate new cleanup commits. Maintain rollback pins and unchanged port 8137.
- Keep the 8B as fast default; use old 24B as reference/fallback for tasks where it has actually been more reliable.

**P1 — new 24B model acquisition/export (only after P0 is stable).**
- Recheck official OpenVINO collection, HF model metadata and verified-model catalogue for the **exact** LFM2.5-24B name; pin exact revision and licenses.
- If no published IR exists, create an **isolated research conversion experiment** from LiquidAI's original checkpoint using pinned OpenVINO/Optimum Intel/NNCF versions. Do not assume older INT4_ASYM group_size=128 ratio=0.8 will be correct or performance-optimal. Keep source/downloaded models immutable. Log memory and conversion errors without declaring success.
- Verify the IR's tokenizer (128K vocab), EOS/BOS, native tool markers, chat template and reasoning channels. Do not mislabel a repackaged LFM2-24B as LFM2.5.

**P2 — export + serving gate.**
- Graph compile and actual generation on Arc 140V under honest UMA admission, with exact EXE/DLL/IR hashes; report compile/initialization, one-token generation, SSE, full native tool cycle, and reasoning separately.
- First test full-GPU/offload ratio 0; do **not** bring in Pack V2/CIB2 or offload until proven necessary for memory and until baseline measurements exist. Offload cliff for current LFM2.5-8B remains unresolved, so importing it would confound quality tests.

**P3 — fair adoption decision.**
- Use the same 20–50 real agent tasks and a repeated seeded request matrix across 8B, old 24B and new 24B (when it runs), including identical schemas, retries, prompt, tool history, seeds, output/context limits and hardware memory conditions.
- Separate `protocol_pass`, `agent_task_success`, `SSE_parity`, `false_tool_claims`, `reasoning_content`, `latency`, `memory`, `token_cost` and `task_success_per_minute`.
- Promote new 24B to a default only if it **demonstrably** outperforms the appropriate fast/fallback model on real work without unacceptable memory, streaming or tool-call failure cost. If not, keep it as optional specialist.

## Non-goals

- No automatic download, export, GPU build or inference started by documenting this decision.
- No claim that OpenVINO 2026.4 already supports the exact new export just because `lfm2_moe` is supported.
- No production server switch, no claims about 128K operating on Arc 140V, no reuse of old 24B model files.
- No permanent abandonment of old 24B: its validated agent behavior makes it a useful control.

## Revisit trigger

Recheck if OpenVINO publishes `LFM2.5-24B-A2B-*-ov`, Optimum Intel explicitly confirms conversion/GenAI serving, or a version-locked local export passes the first GPU load+generate gate. Update the artifact URL, revision and test receipts in this same ADR; do not silently replace the accepted portfolio decision.
