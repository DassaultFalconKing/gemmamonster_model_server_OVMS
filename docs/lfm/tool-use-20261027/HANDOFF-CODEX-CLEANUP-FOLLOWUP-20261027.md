# HANDOFF — Codex follow-up after Hybrid-C cleanup retest (2026-10-27)

Audience: local Codex (or similar) digging into remaining reliability / merge questions.
Prior mission handoff (already executed): `C:\git\gemmamonster-lfm-2026.4\docs\lfm\tool-use-20261027\HANDOFF-LOCAL-CLEANUP-RETEST-20261027.md`
Validation receipt: `C:\git\gemmamonster-lfm-2026.4\docs\lfm\tool-use-20261027\HYBRID-C-CLEANUP-VALIDATION-20261027.md`

---

## 1. Problem (why this work existed)

Hybrid-C thought demotion on LFM2/LFM2.5 was accepted on an older binary, then source landed two semantic fixes that **invalidate** transferring that GPU PASS:

1. **JSON false positive:** syntactically valid standalone JSON (including `{"plan":[]}` and similar plan-like objects) was demoted into `reasoning_content` when tools were present. Clients saw empty `content` for legitimate JSON answers.
2. **SSE prose hold:** ordinary prose that does **not** start with candidate `{` or `[tool:` was buffered as if it were a tool/JSON candidate, delaying first visible content deltas.

Additional context (not fixed by parser):
- LFM2.5 **official** agent profile sometimes emits prose pseudo-tools like `[ cwd() ]` instead of native `tool_calls` / `<|tool_call_start|>…`. A parser **cannot** promote that prose into executable tools.
- KV `u4` vs `auto` was historically not a clear win; defaults on start scripts moved to `auto`.

Hard constraint: historical EXE SHA256 `d9663aa6ca29880ae6d3d85ff5f341a2461affd7bc539dd2c8cd3df9fa71136e` under `C:\gm\lfm-2026.4\hybrid-c-review-20261027` is an **immutable pin**. Do not overwrite that build tree. Do not touch port `8137`, Pack/CIB2, or unowned `ovms.exe`.

---

## 2. Work completed (cleanup retest)

| Step | Result |
|------|--------|
| Branch at origin HEAD | `055b5814431b15e65880520c56f9b34d99912113` on `review/lfm25-design-c-semantic-refit-20261027` |
| Fresh build | `win_mp_on_py_off` → `C:\gm\lfm-2026.4\hybrid-c-cleanup-20261027\build-py_off\` |
| New EXE SHA256 | `d7ec623dbd82dae2f5e80f66c4446a7b650e086f3c7cc6da4806fa5aa68a4c3d` |
| New TEST SHA256 | `52ecc4e41a4356d5364965b5245125c9480f593a602f331b10d8fa724c6e2ba0` |
| Build unblocker | Local edit `common_settings.bzl`: `/wd6313` (RapidJSON `reader.h` C6313 under `/analyze` + `/WX`). **Not committed.** |
| C++ filter | **205 PASS / 2 SKIP / 0 FAIL** (207 scheduled) |
| Live JSON FP | `{"plan":[]}` stays in **content** on LFM2.5 and LFM2-24B (needs enough `max_tokens`; 128 often `finish=length` mid-think) |
| SSE latency | First reasoning ~0.21s; reason→content gap ~0.0001s |
| LFM2.5 tool probe | 8/8 PASS |
| LFM2.5 official ×10 | unary **6/10**, SSE **6/10** (CONDITIONAL) |
| Prose hang | PASS (`tool_choice=none` after write/run context, DONE @ ~3.8s) |
| U4 A/B (n=5) | auto p50 54.01 tok/s; u4 p50 56.14 (Δ +2.13) — noise, not a claim |
| LFM2-24B probe | 8/8 PASS |
| LFM2-24B deterministic agent | 4/4 PASS |
| Owned server | Started/stopped only on `127.0.0.1:18147`; left stopped |

**Before → after (parser-relevant):**

| Gate | Historical EXE `d9663aa6…` | Cleanup EXE `d7ec623d…` |
|------|----------------------------|-------------------------|
| Units | 197/2 skip | 205/2 skip |
| Ordinary JSON | PASS | PASS |
| `{"plan":[]}` | demoted to reasoning (FP) | **content PASS** |
| SSE prose hold | known bug | **PASS** |
| Official LFM2.5 | 2/4 (50%) | 6/10 + 6/10 (60%), same flake class |
| U4 vs auto | u4 slightly slower | u4 slightly faster — inconclusive |

---

## 3. Absolute paths — trees and artifacts

### Repo / source
| Path | Role |
|------|------|
| `C:\git\gemmamonster-lfm-2026.4` | Git worktree for this branch |
| `C:\git\gemmamonster-lfm-2026.4\src\llm\io_processing\output_parser.cpp` | Hybrid-C demotion / JSON / prose fast-path |
| `C:\git\gemmamonster-lfm-2026.4\src\llm\io_processing\output_parser.hpp` | Per-segment plain-content state |
| `C:\git\gemmamonster-lfm-2026.4\src\llm\io_processing\lfm2\thought_demotion.hpp` | Demotion helpers |
| `C:\git\gemmamonster-lfm-2026.4\src\test\llm\output_parsers\lfm_strict_output_parser_test.cpp` | Strict/hybrid goldens (`HybridValidJsonPlanRemainsVisible*`, etc.) |
| `C:\git\gemmamonster-lfm-2026.4\src\test\llm\output_parsers\lfm_thought_demotion_review_test.cpp` | Demotion review suite |
| `C:\git\gemmamonster-lfm-2026.4\common_settings.bzl` | **Dirty:** `/wd6313` added for Windows analyze |
| `C:\git\gemmamonster-lfm-2026.4\scripts\windows\build-rc4.ps1` | Locked Windows build |
| `C:\git\gemmamonster-lfm-2026.4\scripts\windows\start-lfm25.ps1` | LFM2.5 serve (`-KvPrecision auto\|u4`, `-ExecutablePath`, `-ExecutableSha256`) |
| `C:\git\gemmamonster-lfm-2026.4\scripts\windows\start-lfm2-24b.ps1` | LFM2-24B serve (same pins) |
| `C:\git\gemmamonster-lfm-2026.4\scripts\windows\lfm-tool-use-probe.py` | API protocol matrix (8 cases) |
| `C:\git\gemmamonster-lfm-2026.4\scripts\windows\lfm-agent-loop.py` | Host tool loop; profiles `deterministic\|official\|native`; default `max_tokens=2048` |
| `C:\git\gemmamonster-lfm-2026.4\docs\lfm\tool-use-20261027\` | Specs, plans, handoffs, validation |

### Docs in this folder (read order for Codex)
1. `HANDOFF-CODEX-CLEANUP-FOLLOWUP-20261027.md` — **this file**
2. `HYBRID-C-CLEANUP-VALIDATION-20261027.md` — gate matrix for new EXE
3. `HANDOFF-LOCAL-CLEANUP-RETEST-20261027.md` — original cleanup TZ
4. `HYBRID-C-CODE-HANDOFF-20261027.md` / design+plan under `docs\superpowers\` if code semantics needed
5. Historical compare: `C:\gm\lfm-2026.4\hybrid-c-review-20261027\RESULT-SUMMARY.md`

### Immutable historical pin (BEFORE)
`C:\gm\lfm-2026.4\hybrid-c-review-20261027\`
- EXE: `build-py_off\bin\ovms.exe` → `d9663aa6…`
- Useful: `RESULT-SUMMARY.md`, `false-demotion-json\`, `agent-chains-lfm25\official\`, `ab-u4\`, `ab-auto\`, `parity-long-decode-20261027\`

### Cleanup evidence root (AFTER) — primary dig site
`C:\gm\lfm-2026.4\hybrid-c-cleanup-20261027\`

| Subpath | Contents |
|---------|----------|
| `build-py_off\COMPLETE.json` | Build receipt + source commit |
| `build-py_off\bin\ovms.exe` / `ovms_test.exe` | New binaries |
| `unit-gate-exit.json`, `unit-gate.log`, `lfm-hybrid-c-cleanup.xml` | C++ gate |
| `smoke-auto\` | LFM2.5 tool-use probe RESULT |
| `false-demotion-json\` | Live JSON FP + SSE (`RESULT-v2.json`, `sse-latency-transition.json`) |
| `agent-official-x10-mt2048\` | **Valid** official ×10 (`SUMMARY.json`, per-repeat `unary\|sse\<n>\*.request.json\|*.response.txt`) |
| `agent-official-x10\` | **INVALID** — ran with `max_tokens=512`, all `finish=length`; ignore for scoring |
| `prose-hang\` | none-after-tools hang |
| `ab-auto\`, `ab-u4\`, `ab-summary.json` | KV A/B |
| `smoke-24b\`, `false-demotion-json-24b\`, `agent-det-24b\` | 24B protocol |
| `start-lfm25.log`, `start-lfm25-u4.log`, `start-lfm2-24b.log` | Serve logs |

### Models / staging (do not delete)
| Path | Model id |
|------|----------|
| `C:\gm\lfm-2026.4\serving-models\LFM2.5-8B-A1B-int4-ov-port18147` | `lfm25-8b-a1b-int4` |
| `C:\gm\lfm-2026.4\serving-models\LFM2-24B-A2B-int4-ov-port18147` | `lfm2-24b-a2b-int4` |

### SDK / Python (for rebuild / `ovms_test`)
- OpenVINO/GenAI: under `C:\gm\qwenmonster\semantic-refit-2026.4-sdk\…` (see `COMPLETE.json` `action_env`)
- Python home for tests: `C:\gm\qwenmonster\semantic-refit-2026.4-tools\py-nupkg\tools` — set `PYTHONHOME` or units fail with filesystem codec error
- Runtime DLL package often: `C:\gm\qwenmonster\releases\gemmamonster-2026.4-rc4\extracted-py_off\ovms`

---

## 4. How testing was done (methods)

### 4.1 Build
```powershell
# From C:\git\gemmamonster-lfm-2026.4 @ 055b581…
$root = 'C:\gm\lfm-2026.4\hybrid-c-cleanup-20261027'
# build-rc4.ps1 -Python off -Output $root
# First attempt failed C6313; after /wd6313 in common_settings.bzl → BUILD_PASS
```

### 4.2 C++ regression
```powershell
$env:PYTHONHOME = 'C:\gm\qwenmonster\semantic-refit-2026.4-tools\py-nupkg\tools'
# PATH must include Python + OVMS DLL dir + OpenVINO Release bin
& $testExe --gtest_filter='LfmThoughtDemotionReview.*:*LfmStrictOutputParserTest.*:*Lfm2*:*Lfm25*:*Gemma4*:*Qwen3Coder*' `
  --gtest_output=xml:$root\lfm-hybrid-c-cleanup.xml
```
Goldens of interest: `HybridValidJsonPlanRemainsVisibleForBothModels`, plain-prose immediate delta, demotion of **malformed** pseudo-plans only.

### 4.3 Live serve (hash-locked)
```powershell
$exe = '…\hybrid-c-cleanup-20261027\build-py_off\bin\ovms.exe'
$sha = 'd7ec623dbd82dae2f5e80f66c4446a7b650e086f3c7cc6da4806fa5aa68a4c3d'
# start-lfm25.ps1  -Port 18147 -KvPrecision auto|u4 -ExecutablePath $exe -ExecutableSha256 $sha
# start-lfm2-24b.ps1 -Port 18147 -KvPrecision auto     -ExecutablePath $exe -ExecutableSha256 $sha
# Only one model on 18147 at a time. Stop owning PID on 18147 before switch. Never kill 8137 blindly.
```
Endpoint: `http://127.0.0.1:18147/v3/chat/completions`

### 4.4 Protocol probe
`lfm-tool-use-probe.py --url … --model lfm25-8b-a1b-int4|lfm2-24b-a2b-int4 --output <dir>`
Cases: auto-action, auto-no-action, required/named conflict, none, required-sse, required-no-tools (expect 400), named-unregistered (expect 400).

### 4.5 JSON FP live
Unary/SSE with tools present; prompt forces exact `{"plan":[]}` or ordinary `{"status":"ok","count":2}`.
**Pass** = object appears in `message.content` (or SSE content deltas), not only quoted inside long thinking.
Use `max_tokens>=512` for plan prompts; at 128 the model often exhausts budget in `reasoning_content` (`finish=length`) without emitting the JSON — that is **MODEL_BUDGET**, not demotion.

### 4.6 SSE latency
True streaming read; measure `first_any`, `first_reasoning`, `first_content`, and **last_reason → first_content gap**.
Thinking models stream reasoning first; gap ~0 after think ends proves content is not held as a candidate buffer.

### 4.7 Official agent reliability
```powershell
python lfm-agent-loop.py --url http://127.0.0.1:18147/v3/chat/completions `
  --model lfm25-8b-a1b-int4 --output <dir> --repeats 10 --profile official `
  --tool-policy auto --parallel-tool-calls --max-tokens 2048
```
Loop already runs unary then SSE per repeat. Seeds `1234+repeat`. Official sampling: `temperature=0.2`, `top_k=80`, `repetition_penalty=1.05`.
**Pass** = executed tools exactly `cwd → write → read`, file bytes match payload `O'Brien C:/llm/lfm-test 1.10`.
Classify FAIL by inspecting `0.response.txt`: native `tool_calls` vs prose `[ cwd() ]` vs hallucinated narrative vs `ValueError('out-of-scope file path')`.

### 4.8 Hang
Synthetic history: write + run_python tool results already in messages; final user asks for two-sentence summary with `tool_choice=none`, `stream=true`. Require `[DONE]`, finite duration, `finish_reason` stop/length.

### 4.9 U4 A/B
Clean restart between profiles; same prompt/seeds n=5; `OFFLOAD_RATIO=0`; compare completion_tokens/elapsed p50 only (content may sit in reasoning on short “count 1..20” prompts).

---

## 5. Protocols / gates that passed

| Gate | Status | Evidence |
|------|--------|----------|
| BUILD | PASS | `…\hybrid-c-cleanup-20261027\build-py_off\COMPLETE.json` |
| PARSER_REGRESSION | PASS | `unit-gate-exit.json` |
| JSON_FALSE_POSITIVE | PASS | units + `false-demotion-json\RESULT-v2.json` + `false-demotion-json-24b\RESULT.json` |
| SSE_LATENCY | PASS | `false-demotion-json\sse-latency-transition.json` |
| LFM25_PROTOCOL | PASS | `smoke-auto\RESULT.json` |
| LFM24_PROTOCOL | PASS | `smoke-24b\RESULT.json`, `agent-det-24b\RESULT.json` |
| PROSE_HANG | PASS | `prose-hang\RESULT.json` |
| U4_AB | RECORDED | `ab-summary.json` |
| OFFICIAL_AGENT_RELIABILITY | **CONDITIONAL** | `agent-official-x10-mt2048\SUMMARY.json` |

**Not re-run on cleanup EXE (still only on historical pin):** LFM2.5 deterministic agent, code write+execute OK_DEMO, Cursor HTTP hammer, LFM2-24B official ×N, long-decode parity tables.

---

## 6. Hardest spots (for Codex focus)

1. **Official agent flake (highest value dig)**
   Same seeds/profile as PASS runs still produce:
   - prose pseudo-tools `[ cwd() ]…` (parser correctly leaves as content; host never executes);
   - invented “cwd → /some/path …” without tools;
   - native tools but `write` with absolute/out-of-sandbox path;
   - empty / truncated finals.
   Dig: raw `0.response.txt` for FAIL reps 1,3,5,8 (unary+SSE); compare token text for `<|tool_call_start|>` vs prose; chat template / special tokens / stop; whether staff `parallel_tool_calls=true` correlates. Do **not** “fix” by regex-promoting prose into tools.

2. **`max_tokens` footgun**
   Official with 512 → 0/20 false FAILs (`finish=length` in reasoning). Always use harness default **2048** for agent loops. JSON plan live checks need ≥512.

3. **Build `/wd6313`**
   Without it, `/analyze` + `/WX` dies in RapidJSON. Decide: commit suppress, or narrower fix. Currently dirty only in worktree.

4. **Python env for `ovms_test`**
   Missing `PYTHONHOME` → `failed to get the Python codec of the filesystem encoding` before any suite runs.

5. **Demotion vs thinking quote**
   Naive “`plan` appears in reasoning” detectors false-alarm: model quotes the user prompt while thinking. Score on **emitted answer JSON in content**, or trailing demoted object heuristic.

6. **Serve process lifecycle**
   `start-*.ps1` blocks on child; stopping `ovms.exe` leaves the waiter with a non-zero exit — expected, not a model failure.

---

## 7. Suggested Codex missions (pick one; stay narrow)

**A. Official failure taxonomy (read-only + optional re-smoke)**
Produce a table: for each of 8 FAIL slots — finish_reason, presence of native tool_calls, prose markers, whether `tool_call_start` appears in raw body, seed. Recommend merge language: CONDITIONAL vs blocker.

**B. Minimal official hardening (product, not parser demotion)**
If evidence shows template/special-token gap vs PASS runs, propose smallest template or system-prompt delta; re-run official ×10 only; no CIB2.

**C. Commit hygiene**
Land `/wd6313` with one-line rationale **or** find a cleaner suppress scope; do not rebuild unless asked.

**D. Fill NOT_RUN gaps on new EXE**
Deterministic LFM2.5, code OK_DEMO, optional 24B official ×5 — only if A does not need the GPU.

### Safety / economy
- Port **18147** only; hash-lock EXE `d7ec623d…`.
- Do not delete `hybrid-c-review-20261027` or model trees.
- Token economy: prefer existing evidence files before new long GPU runs.
- Do not claim cleanup acceptance transfers from `d9663aa6…`.
- No push/commit unless the user explicitly asks.

---

## 8. Quick identity card

```
repo:     C:\git\gemmamonster-lfm-2026.4
branch:   review/lfm25-design-c-semantic-refit-20261027
HEAD:     055b5814431b15e65880520c56f9b34d99912113
new EXE:  d7ec623dbd82dae2f5e80f66c4446a7b650e086f3c7cc6da4806fa5aa68a4c3d
old EXE:  d9663aa6ca29880ae6d3d85ff5f341a2461affd7bc539dd2c8cd3df9fa71136e
evidence: C:\gm\lfm-2026.4\hybrid-c-cleanup-20261027
report:   docs\lfm\tool-use-20261027\HYBRID-C-CLEANUP-VALIDATION-20261027.md
dirty:    common_settings.bzl (/wd6313); scripts\windows\configs\*\command.json may refresh on start
port:     18147 (currently expected free)
```
