# HANDOFF — Qwen3.8 MTP Arc 140V (2026-10-28 ~15:13 local)

> Latest RCA: `RCA-MATRIX.md`. P0–P6/P6b completed; f16 controls fit and pass on the short prompt, u4 fails regardless of DQ. An isolated GenAI trace reproduces P0 with identical internal input IDs and proves a pre-sampler target-logit argmax flip at index 3, in the first target verification before prior rejection/rollback. KV/GDN/kernel-level cause remains unresolved; OVMS backport is not applied, MTP remains HOLD.

> Follow-up on 2026-10-28: see `NATIVE-FOLLOWUP.md`. Native GenAI MTP load/generation works with unchanged RC4 DLLs; a bounded NAT sweep completed, but greedy output equivalence failed. OVMS remains blocked. The stock DLL-missing probe is now resolved and reproduces the same OVMS gate. Original handoff below is historical.

## Verdict (one line)

**Stage 1 PASS. Stage 2 BLOCKED_CAPABILITY on RC4:** official `Qwen3.8-27B-int4-ov` is VLM; RC4 rejects non-EAGLE3 `draft_models_path` on `VLM_CB`. No successful `/v1/models` on 18138. Stages 3–6 **NOT_RUN**.

## Do not confuse

| Asset | Path | Role |
|-------|------|------|
| Official MTP package (keep) | `C:\llm\models\OpenVINO\Qwen3.8-27B-int4-ov` | HF `OpenVINO/Qwen3.8-27B-int4-ov` rev `7b20ea8c…`, **14.875 GiB**, has `openvino_mtp_*` |
| LM staging (experimental) | `C:\llm\models\OpenVINO\Qwen3.8-27B-int4-ov-lm-mtp` | hardlinks minus `openvino_vision_*`; `config.json` edited `language_model_only=true` — **still fails** (GenAI asks for vision xml) |
| Uncensored Dense (no MTP) | `C:\llm\models\Qwen3.8-27B-Uncensored-int4-awq-g128-ov` | previously on **8137**; **stopped** |

## Identity

| Item | Value |
|------|-------|
| Experiment worktree | `C:\git\gemmamonster-qwen38-mtp-20261028` |
| Branch | `experiment/qwen38-mtp-arc140v-20261028` @ RC4 `362b1d293…` |
| User worktree | `C:\git\gemmamonster-lfm-2026.4` — **do not modify** |
| Runtime under test | `C:\gm\qwenmonster\releases\gemmamonster-2026.4-rc4\extracted-py_off\ovms` |
| Port | **18138** only (8137/18137 free) |
| Locks | `docs/experiments/qwen38-mtp-20261028/{model,runtime,source}-lock.json` + `C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\locks\` |

## Failed launches (chronological)

| # | UTC~ | Profile | Error | Status |
|---|------|---------|-------|--------|
| 1 | 13:55 | MTP `LM_CB`, `--draft_source_model C:\llm\...` | protobuf **Invalid escape** in pbtxt (`draft_models_path` Windows `\`) | **FIXED** → use `--draft_source_model .` |
| 2 | 13:56 | MTP `LM_CB`, draft `.`, full package | VLM dir + non-VLM pipeline | expected |
| 3 | 13:56 | MTP `VLM_CB`, draft `.` | **Fast Draft not supported for VLM** | **BLOCKED_CAPABILITY** (primary) |
| 4 | 13:57 | baseline `VLM_CB` | **Option not found: ATTENTION_BACKEND** | **FIXED** in start script (PA opt-in only) |
| 5 | 13:58 | MTP `LM_CB`, lm-mtp staging | GenAI still opens `openvino_vision_embeddings_model.xml` | staging workaround **FAIL** |
| 6 | ~13:59 | stock `C:\llm\ovms` 2026.4.0 + draft | process exit **-1073741515** (DLL missing) | stock probe inconclusive |

Logs: `C:\Users\testc\.omp\agent\logs\qwen38-mtp\`

Code gate (RC4):

```568:571:C:\git\gemmamonster-qwen38-mtp-20261028\src\llm\servable_initializer.cpp
            if (!nodeOptions.draft_models_path().empty() && !nodeOptions.draft_eagle3_mode()) {
                SPDLOG_LOGGER_ERROR(modelmanager_logger, "Fast Draft speculative decoding is not supported for VLM pipelines. Use EAGLE3 (draft_eagle3_mode: true) with a matching EAGLE3 head model instead.");
                return StatusCode::LLM_NODE_RESOURCE_STATE_INITIALIZATION_FAILED;
            }
```

OVMS treats bundled MTP (`draft_source_model .` + `openvino_mtp_model.*`) as the same Fast Draft path. Official docs expect MTP on this VLM model on OVMS **2026.4+**; RC4 py_off does not distinguish MTP vs Fast Draft for VLM.

## What already works (harness)

| Artifact | Path |
|----------|------|
| Start script | `C:\Users\testc\.omp\agent\start-qwen38-mtp.ps1` (`-Profile baseline|mtp|prod-prefix`, `-PipelineType`, `-ModelPath`, `-AttentionPA`) |
| Matrix A–E | `C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\run_matrix.py` |
| Correctness/tools | `...\run_correctness.py` |
| Fixture SHA lock | `...\fixtures\FIXTURES.lock.json` |
| Docs | `STATE.md`, `TEST-MATRIX.md`, `failures.md`, this `HANDOFF.md` |

**No** `measurements.csv` / `benchmark-results.json` yet (server never ready).

## Machine state at handoff

- OVMS: **not running**
- Ports 8137 / 18138: **clear**
- ~18 GB free RAM
- Official model on disk: intact
- User LFM worktree: untouched

## Next agent — ordered options

1. **Minimal RC4 experiment patch** (preferred for Stage 2 on this box): in `servable_initializer.cpp` VLM_CB branch, allow `draft_models_path` when draft dir contains `openvino_mtp_model.xml` (MTP ≠ Fast Draft). Rebuild **only** what RC4 py_off packaging needs; **do not** merge to main/prod. Retest `#3` on full official path + `VLM_CB` + `--draft_source_model .` + **no** `ATTENTION_BACKEND`.
2. **Official OVMS ≥2026.4.1** (docs image), separate install, no DLL mix with RC4. Prove MTP load; then compare vs patched RC4.
3. After any successful MTP load: Mode **B** smoke → full matrix A/B/C (D only if NAT=0 accepted) → `run_correctness.py` → VLM image smoke on **full** package → `FINAL-REPORT.md` + push **experimental branch only**.

## Explicit non-goals (still)

- No merge C6 / CIB2 / Pack V2 / PR#34
- No edits to user worktree `gemmamonster-lfm-2026.4` or release ZIPs
- No blind MTP-head / tokenizer transplant onto Uncensored
- Do not claim tok/s wins without Stage 3 medians

## Answers so far (TZ finale checklist)

1. MTP on RC4? **No — blocked at load (VLM Fast Draft gate).**
2. Time save? **NOT_RUN**
3. Best `num_assistant_tokens`? **NOT_RUN**
4. MTP memory cost? **NOT_RUN**
5. Unary/SSE/tools preserved? **NOT_RUN**
6. OOM/paging? **No** (never loaded). Incompatibilities: **yes** (above).
7. Enable MTP in next RC? **No recommendation until patch or newer OVMS proves load + speedup.**
