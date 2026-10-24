# CIB2 implementation delta and model layout audit (2026-10-24)

Status: SOURCE PATCHES ONLY; not GPU accepted. Parent integration: OVMS PR #29 and OpenVINO 2026.4 PR #10. This note corrects model lineage without rewriting historical static XML evidence.

## Verified upstream model structures

All figures are *language decoder* counts and NOT proof of OpenVINO compiled MOECompressed eligibility.

| Checkpoint/family | Decoder model type | Layers | MoE routed / top-k | Dense/shared | Attention and exceptions |
|---|---|---:|---:|---|---|
| Ornith-1.0-35B, finetune/repack of Qwen3.6-35B-A3B | qwen3_5_moe_text | 40 | 256 / 8 | shared FFN 512 | 30 DeltaNet + 10 attention, MTP |
| Qwen3.6-35B-A3B | qwen3_5_moe_text | 40 | 256 / 8 | shared FFN 512 | 30 DeltaNet + 10 attention, MTP |
| Gemma4-26B-A4B | gemma4_text | 30 | 128 / 8 | shared dense path | sliding/global attention; different expert layout |
| MiniCPM-V-4.7-35B-A3B | qwen3_5_moe_text | 40 | 256 / 8 | shared FFN 512 | vision tower 27 layers **separate** |
| Qwen3.8-27B | dense qwen3_5_text | 64 | 0 / 0 | dense FFN | 48 DeltaNet + 16 attention; NO routed pack |
| Qwen3.8-Flash-Next | qwen4_exp_text | 48 | 512 / 10 | shared FFN 640 | 36 DeltaNet + 12 QSA, external Engram 51.2B |

Primary config sources, read 2026-10-24:
- https://huggingface.co/ornith-ai/Ornith-1.0-35B/blob/main/config.json
- https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/main/config.json
- https://huggingface.co/google/gemma-4-26B-A4B-it/blob/main/config.json
- https://huggingface.co/openbmb/MiniCPM-V-4.7-35B-A3B/blob/main/config.json
- https://huggingface.co/Qwen/Qwen3.8-27B/blob/main/config.json
- https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/main/config.json
- https://github.com/ornith-ai/Ornith-1

**Important:** internal `qwen3_5_moe_text` is the HF architecture *class*, not the exact training model or proof of Qwen3.5 lineage. Ornith's local OpenVINO IR must be checked against its own pinned HF/config/export identity. The existing `P1-STATIC-ORNITH-20261024.md` correctly reports 40 blocks but only 3 of 9 naive Const-name slots; it has **zero complete static nine-slice blocks** and compiled eligibility UNKNOWN. Do not relabel this historical evidence as GPU PASS or Gemma.

## Patches in isolated review branches

- OVMS `dev/cib2-family-layout-20261024`: `scripts/cib2/model_layout_audit.py`, strict decoder config audit, fail-closed on dense/unknown/ambiguous config; no assumptions by model display name. `scripts/cib2/pack_cohorts.py`: deterministically partitions verified `plans.v2.json` logical expert placement into contiguous *advisory* hot/warm/cold spans. No file splitting and no fake Pack V2 shard compatibility. Unit tests in `tests/cib2/test_model_layout_audit.py` and `test_pack_cohorts.py`.
- OpenVINO `dev/cib2-n2n3-safety-ledger-20261024`: `LRUCache::set_recycle_guard` rejects a live GPU reader candidate **before** recycling its slot. Default callback empty, so synchronous fallback behaviour remains unchanged; actual terminal-event wiring is still required. `UmaAdmissionLedger::reserve_batch` admits CPU staging and GPU-visible resources atomically while applying overlapping WDDM+system caps, with host tests. No driver/allocator changes.

## Numbered checklist vs original task

1. **Model inventory:** actual upstream configs audited; structural local validator implemented. `inspect_config` is not a GPU compiled eligibility gate.
2. **N2 leases/residency:** LRU recycle guard source + negative tests added. GPU producer and terminal-consumer event attachment remains **NOT_DONE**. Do not enable asynchronous reuse.
3. **N4 scheduler:** pre-existing `plan_prefetch` remains a non-executing proposal. Runtime profile-driven dispatcher and concurrency tests remain **NOT_DONE**; prefetch **OFF**.
4. **N3 cache/UMA:** batch reservation helper added. Native live WDDM exact-LUID probe exists in PR #10, but *model-wide committed+pending ledger reconciliation and CPU+GPU+disk tier integration* are **NOT_DONE**. Do not count GPU and CPU budgets additively.
5. **Pack grouping:** verified-placement advisory physical spans implemented. *Actual variable V2 record ABI/shards and native serve-side manifest binding* are **NOT_DONE**; OTDPACK1 remains immutable.
6. **CLI:** build-only/require CLI in PR #29 already; local no-listener, eligibility and corrupt negative tests remain hardware gates.

## Repro commands, local isolated worktrees

```powershell
# OVMS source worktree: dev/cib2-family-layout-20261024
py -3 -m unittest tests.cib2.test_model_layout_audit tests.cib2.test_pack_cohorts -v
py -3 -m unittest discover -s tests/cib2 -p "test_*.py" -v
py -3 scripts/cib2/model_layout_audit.py C:\llm\models\ornith-35b-ov\config.json --model-id Ornith
py -3 scripts/cib2/pack_cohorts.py C:\path\to\verified\placement-directory --max-records 64

# OpenVINO isolated worktree: dev/cib2-n2n3-safety-ledger-20261024
cmake -S src/plugins/intel_gpu/tools/moe_otd_control_v2 -B C:\temp\cib2-host-controls
cmake --build C:\temp\cib2-host-controls --config Release
ctest --test-dir C:\temp\cib2-host-controls -C Release --output-on-failure
```

Expected native negative regressions:
- protected least-recently-used slot not evicted;
- all slots busy => no mutation + error, no stale-hit; released guard => progress;
- UMA staging+GPU-visible batch atomic admission, no half-commit, zero-byte and overflow rejected;
- N2 actual terminal-consumer event fence under C1/C2/C4 and cancellation (NOT tested by these host helpers);
- N3 WDDM exact-LUID under memory pressure; no GPU/OOM deadlock;
- P1 compiled nine-slice and P5 matching full payload + generation + require-mode fail-closed;
- Pack OFF/V1/V2, prefetch OFF/ON paired GPU runs only after N2+N3 gates;
- tool calling: literal VIN/part numbers, empty args, unary/SSE, multi-turn continuation.

Do not promote PR #29 or PR #10 or merge this review work merely because Python or host C++ tests pass.
