# Hybrid-C local validation RESULT — 2026-10-27

Status: **PASS** (with recorded known plan-JSON demotion FP)

## Identity
- Branch: `review/lfm25-design-c-semantic-refit-20261027`
- HEAD at validation: `1b8b31cd7f20240289790c4925ac4847a4cc6f8b`
- Output root: `C:\gm\lfm-2026.4\hybrid-c-review-20261027`
- `ovms.exe` SHA256: `d9663aa6ca29880ae6d3d85ff5f341a2461affd7bc539dd2c8cd3df9fa71136e`
- `ovms_test.exe` SHA256: `42a23f1ef67c07acfe59851b3920b8548128ee8808ce50669d7df8a6fd65e8fb`
- Build: `BUILD_PASS` (`build-py_off\COMPLETE.json`, config `win_mp_on_py_off`)

## Unit / regression filter
- Filter: `LfmThoughtDemotionReview.*:*LfmStrictOutputParserTest.*:*Lfm2*:*Lfm25*:*Gemma4*:*Qwen3Coder*`
- Result: **197 PASSED / 2 SKIPPED / 0 FAILED**
- Skips: intentional LFM2-24B `GTEST_SKIP` cases

## Live tool cycle (port 18147, Hybrid-C EXE, U4)
- Harness: `scripts\windows\lfm-tool-use-probe.py` → `smoke-u4\`
- Unary + SSE tool cycle: **PASS** (8/8 incl. `required-sse`)

## False-demotion JSON check
- Ordinary JSON `{"status":"ok","count":2}` with tools: **PASS** (content retained)
- Known FP `{"plan":[]}` with tools: **demoted to reasoning** (unary+SSE) — recorded risk

## U4 A/B (SSE decode, max_tokens=128 ×3, OFFLOAD=0)
| Profile | decode median tok/s | TTFT median s |
|---------|---------------------|---------------|
| u4 | 55.12 | 0.167 |
| auto | 56.24 | 0.166 |
| delta (u4−auto) | -1.12 | |

## Start-script pin (post-validation)
Default `scripts/windows/start-lfm25.ps1` / `start-lfm2-24b.ps1`:
- EXE: `C:\gm\lfm-2026.4\hybrid-c-review-20261027\build-py_off\bin\ovms.exe`
- SHA256: `d9663aa6ca29880ae6d3d85ff5f341a2461affd7bc539dd2c8cd3df9fa71136e`
- `KvPrecision=u4`, `OFFLOAD_RATIO=0`

Full machine evidence remains under the output root above (not in git).
