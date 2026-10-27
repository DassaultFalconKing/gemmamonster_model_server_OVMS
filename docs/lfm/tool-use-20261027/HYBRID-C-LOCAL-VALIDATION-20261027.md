# Hybrid-C local validation RESULT — 2026-10-27

Status: **PASS** overall (LFM2.5 official agent profile has recorded flaky FAIL; known plan-JSON demotion FP)

## Identity
- Branch: `review/lfm25-design-c-semantic-refit-20261027`
- HEAD at initial unit/GPU smoke: `1b8b31cd7f20240289790c4925ac4847a4cc6f8b`
- Output root: `C:\gm\lfm-2026.4\hybrid-c-review-20261027`
- Serving EXE: Hybrid-C review build  
  `C:\gm\lfm-2026.4\hybrid-c-review-20261027\build-py_off\bin\ovms.exe`  
  SHA256 `d9663aa6ca29880ae6d3d85ff5f341a2461affd7bc539dd2c8cd3df9fa71136e`
- Machine evidence rollup: `AGENT-CHAINS-SUMMARY.json`

## Shared (EXE / tests — not weight-specific)
| Gate | Result |
|------|--------|
| Windows build `win_mp_on_py_off` | **PASS** |
| C++ filter `LfmThoughtDemotionReview.*:*LfmStrictOutputParserTest.*:*Lfm2*:*Lfm25*:*Gemma4*:*Qwen3Coder*` | **197 PASS / 2 SKIP / 0 FAIL** |

## By model (live GPU, Hybrid-C EXE, port 18147, KvPrecision=u4 unless noted)

### LFM2.5-8B-A1B-int4 (`lfm25-8b-a1b-int4`)
| Gate | Result | Evidence |
|------|--------|----------|
| Tool-use probe (8 cases, unary+SSE) | **PASS** | `smoke-u4\` |
| Ordinary JSON false-demotion | **PASS** | `false-demotion-json\` |
| Known FP `{"plan":[]}` | Demoted to reasoning | `false-demotion-json\` |
| U4 A/B short decode ×3 | u4 **55.12** tok/s; auto **56.24**; Δ −1.12 | `ab-u4\`, `ab-auto\` |
| Agent chain deterministic (cwd→write→read × unary/SSE ×2) | **4/4 PASS** | `agent-chains-lfm25\deterministic\` |
| Agent chain official | **2/4 PASS** | FAIL unary r1 + SSE r1: prose `[ cwd() ]…` instead of native `tool_calls` | `agent-chains-lfm25\official\` |
| Code write+execute (`demo.py` → OK_DEMO) | **PASS** (exit 0) | `agent-code-lfm25\` |
| Cursor subagent HTTP hammer (3 agent loops + 2 parallel chats) | **5/5 PASS**, server healthy | `cursor-subagent-hammer-lfm25\` |

### LFM2-24B-A2B-int4 (`lfm2-24b-a2b-int4`, long start profile + u4)
| Gate | Result | Evidence |
|------|--------|----------|
| Agent chain deterministic | **4/4 PASS** | `agent-chains-lfm2-24b\deterministic\` |
| Agent chain official | **4/4 PASS** | `agent-chains-lfm2-24b\official\` |
| Code write+execute | **PASS** (exit 0, OK_DEMO) | `agent-code-lfm2-24b\` |
| Cursor subagent HTTP hammer | **3/3 PASS** (2 parallel chats + 1 unary agent) | `cursor-subagent-hammer-lfm2-24b\` |
| Initial Hybrid-C smoke U4 A/B / tool probe | **NOT RUN on 24B** (first GPU pass was LFM2.5-only) | — |

## Cursor note
Cursor Task subagents cannot select the local LFM as their *own* chat model (fixed cloud/IDE model list). Stress was done by Cursor subagents **calling** the OpenAI-compatible OVMS HTTP API while Hybrid-C served LFM2.5 then LFM2-24B sequentially on GPU.

## OVMS final state
All owned listeners stopped after agent-chain pass; **8137/18147 free**.
