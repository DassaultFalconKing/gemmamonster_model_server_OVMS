# TEST-MATRIX — Qwen3.8 MTP Arc 140V (2026-10-28)

## Scope clarification (native follow-up)

Stage 3 and Stage 4 tables below are the **OVMS HTTP matrix**, still NOT_RUN. A separate native GenAI experiment completed: 2 warmups + 5 measurements for baseline and NAT 1/2/3/5/8, 30 measured rows, one short prompt, 64 tokens. Load/generation PASS; greedy output equivalence FAIL (0/25 MTP matches). See `NATIVE-FOLLOWUP.md` and `native-evidence/`.

Controlled RCA P0–P6 is separate again and **complete**: u4/DQ128 and u4/DQ0 FAIL equivalence; default u8 and f16 pairs PASS on the short prompt; u4/BY_TOKEN BLOCKED_CAPABILITY. Additional u8/BY_TOKEN (P6b) FAILS at output index 23. Each target-only/MTP pair runs in separate processes with two repeats, a fixed tokenizer-ID roundtrip, real generated ID capture, and resource guards. A separate source-matched diagnostic build reproduces P0 and observes equal internal VLM IDs, a raw target-logit argmax flip at index 3, and rejection in the first target verification. These are measured through instrumentation, not inferred from output text. See `RCA-MATRIX.md`; raw results: `C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\rca\matrix.json`.

Statuses: `PASS` / `FAIL` / `NOT_RUN` / `BLOCKED_RESOURCE` / `BLOCKED_CAPABILITY`.  
Historical rows from other builds are labeled `HISTORICAL` and never count as PASS for this experiment.

## Identity

| Item | Value |
|------|-------|
| Branch / worktree | `experiment/qwen38-mtp-arc140v-20261028` @ `C:\git\gemmamonster-qwen38-mtp-20261028` |
| Runtime | RC4 py_off `extracted-py_off\ovms` |
| Model | `OpenVINO/Qwen3.8-27B-int4-ov` → `C:\llm\models\OpenVINO\Qwen3.8-27B-int4-ov` |
| Port | `18138` only |
| Start | `C:\Users\testc\.omp\agent\start-qwen38-mtp.ps1` |
| Bench | `C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\` |

## Launch recipes

| Profile | Script args | Draft | Prefix | Notes |
|---------|-------------|-------|--------|-------|
| A baseline | `-Profile baseline -PipelineType LM_CB` | no | OFF | Mode A |
| B/C MTP | `-Profile mtp -PipelineType LM_CB` | `--draft_source_model <model_path>` | OFF | Modes B/C/D |
| E prod-prefix | edit/start with prefix ON, no draft | no | ON | Separate from MTP compare |
| VLM probe | `-Profile mtp -PipelineType VLM_CB` | yes | OFF | Expect possible BLOCKED (Fast Draft≠VLM) |

RC4 CLI flag is `--draft_source_model` (docs call it `--draft_model_path`).

## Stage 1 — model lock

| Check | Status | Evidence |
|-------|--------|----------|
| `openvino_mtp_model.xml/.bin` present | PASS | local package complete |
| language + embeddings + tokenizer | PASS | 14.875 GiB / 55 files |
| HF revision `7b20ea8c…` + SHA256 lock | PASS | `model-lock.json` / `runtime-lock.json` / `source-lock.json` |

## Stage 2 — capability

| Check | Status | Evidence |
|-------|--------|----------|
| RC4 loads with draft=`.` | BLOCKED_CAPABILITY | VLM Fast Draft gate |
| Log proves MTP/draft path used | NOT_RUN | never loaded |
| `/v1/models` on 18138 | FAIL | no successful ready |
| VLM_CB + draft | BLOCKED_CAPABILITY | `...T135646685Z.log` |
| PA (`ATTENTION_BACKEND=PA`) | FAIL | unknown option; dropped from default |
| LM-only staging MTP | FAIL | GenAI still requires vision xml |

## Stage 3 — speed matrix (same model/runtime/prompts)

Warmups=2, measured≥5. Fixtures SHA-locked in `fixtures/FIXTURES.lock.json`.

| Mode | Meaning | NAT | Status |
|------|---------|-----|--------|
| A | target, no MTP server | omit | NOT_RUN |
| B | MTP | 5 | NOT_RUN |
| C | MTP sweep | 1,2,3,5,8 | NOT_RUN |
| D | no drafting | 0 | NOT_RUN (likely unsupported on Fast Draft path) |
| E | prod prefix ON, no draft | omit | NOT_RUN |

Loads: short≈42/256, medium≈1k/256, long≈8k/128, long-decode≈8k/512, ctrl 16k/128 optional.

Acceptance rate: only from runtime counters if exposed — never inferred from tok/s.

## Stage 4 — correctness / tools / VLM

| Check | Status |
|-------|--------|
| Greedy baseline vs MTP unary | NOT_RUN |
| Unary vs SSE | NOT_RUN |
| Adversarial literals (`C:\test`, `#B4E8`, `1e3`, nested JSON) | NOT_RUN |
| tool_choice none/auto/required/named | NOT_RUN |
| Unknown tool / bad schema / agent recovery | NOT_RUN |
| VLM image+text smoke | NOT_RUN |

## Cross-lineage (historical, not this PASS)

| Line | Origin | Status label |
|------|--------|--------------|
| Stock Qwen3.6-35B-A3B INT4 Arc140V decode ~32.65 tok/s | `docs/cib2/SPEED-REFERENCE…` / baseline report | HISTORICAL |
| Qwen heretic MoE ~16.4 tok/s | heretic RESULT | HISTORICAL |
| Gemma26 heretic pin batch16384 | gemma26-heretic RESULT | HISTORICAL |
| Qwen3.8-27B Uncensored Dense ~6.5 tok/s on 8137 | `qwen38-27b-20261028/RESULT.md` | HISTORICAL (no MTP head) |
| LFM Hybrid-C cleanup | `C:\gm\lfm-2026.4\hybrid-c-cleanup-*` | HISTORICAL / separate line |

## How to run (after model complete + GPU free)

```powershell
# locks
& C:\gm\qwenmonster\semantic-refit-2026.4-tools\py-nupkg\tools\python.exe `
  C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\make_locks.py

# Mode A server
Start-Process powershell -ArgumentList '-NoProfile','-File', `
  'C:\Users\testc\.omp\agent\start-qwen38-mtp.ps1','-Profile','baseline' -WindowStyle Hidden
# wait /v1/models then:
& ...\python.exe ...\run_matrix.py --mode A

# stop ovms; Mode B/C server
Start-Process powershell -ArgumentList '-NoProfile','-File', `
  'C:\Users\testc\.omp\agent\start-qwen38-mtp.ps1','-Profile','mtp' -WindowStyle Hidden
& ...\python.exe ...\run_matrix.py --mode B
& ...\python.exe ...\run_matrix.py --mode C
& ...\python.exe ...\run_matrix.py --mode D   # expect fail/BLOCKED if NAT=0 rejected
& ...\python.exe ...\run_correctness.py
```
