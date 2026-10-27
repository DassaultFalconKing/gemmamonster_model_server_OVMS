# Hybrid-C cleanup validation — 2026-10-27

Evidence root: `C:\gm\lfm-2026.4\hybrid-c-cleanup-20261027`
Historical EXE pin (do not overwrite): `d9663aa6…` under `hybrid-c-review-20261027`.

## Identity
| Item | Value |
|------|-------|
| Branch HEAD | `055b5814431b15e65880520c56f9b34d99912113` |
| Build config | `win_mp_on_py_off` (+ local `/wd6313` for RapidJSON C6313 under `/analyze`+/WX) |
| New `ovms.exe` SHA256 | `d7ec623dbd82dae2f5e80f66c4446a7b650e086f3c7cc6da4806fa5aa68a4c3d` |
| New `ovms_test.exe` SHA256 | `52ecc4e41a4356d5364965b5245125c9480f593a602f331b10d8fa724c6e2ba0` |
| Port | `127.0.0.1:18147` only; OFFLOAD_RATIO=0 |

## Gate matrix
| Gate | Status | Notes / evidence |
|------|--------|------------------|
| BUILD | **PASS** | `build-py_off/COMPLETE.json` |
| PARSER_REGRESSION | **PASS** | 205 PASS / 2 SKIP / 0 FAIL — `unit-gate-exit.json`, `lfm-hybrid-c-cleanup.xml` |
| JSON_FALSE_POSITIVE | **PASS** | Units `HybridValidJsonPlanRemainsVisible*`; live LFM2.5 + 24B `{"plan":[]}` in **content** (`false-demotion-json/RESULT-v2.json`, `false-demotion-json-24b/RESULT.json`). Short `max_tokens=128` can hit `length` mid-think — not demotion. |
| SSE_LATENCY | **PASS** | First reasoning 0.21s; reason→content gap 0.0001s — `false-demotion-json/sse-latency-transition.json` |
| LFM25_PROTOCOL | **PASS** | Tool probe 8/8 — `smoke-auto/RESULT.json` |
| LFM24_PROTOCOL | **PASS** | Tool probe 8/8; deterministic agent 4/4 — `smoke-24b/`, `agent-det-24b/` |
| OFFICIAL_AGENT_RELIABILITY | **CONDITIONAL** | LFM2.5 official ×10: **unary 6/10**, **SSE 6/10** (`agent-official-x10-mt2048/`). Fail modes: prose `[ cwd() ]`, hallucinated results, out-of-scope write path, empty. Parser cannot promote prose to native tools. (×10 with `max_tokens=512` was invalid — all `finish=length`; ignore `agent-official-x10/`.) |
| PROSE_HANG | **PASS** | tool_choice=none after write/run context: DONE @ 3.77s, finish=stop — `prose-hang/RESULT.json` |
| U4_AB | **RECORDED** | auto p50 **54.01** tok/s; u4 p50 **56.14** (Δ +2.13). Not a clear win. `ab-summary.json` |

## Acceptance note
Cleanup source on EXE `d7ec623d…` fixes the confirmed `{"plan":[]}` content path and SSE prose hold. Official-agent flake remains a **model/format** reliability issue (improved vs historical 2/4 on the same profile, still not 10/10). Production merge needs an explicit call on remaining prose-pseudo-tool docs; `/wd6313` is a local build-tree edit not yet committed.
