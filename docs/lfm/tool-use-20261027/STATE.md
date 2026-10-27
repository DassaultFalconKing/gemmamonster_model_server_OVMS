# LFM tool-use refit, 2026-10-27

ACTIVE_STAGE: Hybrid C **GPU ACCEPTED** (local validation PASS); start scripts pin hybrid-c-review EXE + u4
BASE_SHA: a13dff47929bd40e38ecbb654ce7014e9a635704
CURRENT_HEAD: see branch tip after start-script pin commit
LAST_GREEN_TESTS: hybrid-c-review units 197 PASS / 2 SKIP; tool probe 8/8; ordinary JSON false-demotion PASS
CURRENT_FAILURE: known FP `{"plan":[]}` demotes to reasoning; offload cliff unchanged; A9 residuals
STAFF_MODE: parallel_tool_calls=true (API default already; agent/probe harnesses aligned)
NEXT_ACTION: cloud/PR review of Hybrid C; decide UX on plan-JSON FP; optional restore control 8137 with new pin
REVERT_POINT: BASELINE-LOCK.json (A9 serving); A9 candidate-final EXE `95fb62b5…` still available for rollback smoke
EVIDENCE_PATH: C:/gm/lfm-2026.4/hybrid-c-review-20261027
CLOUD_HANDOFF: docs/lfm/tool-use-20261027/HANDOFF-CLOUD-REVIEW.md
CODE_HANDOFF: docs/lfm/tool-use-20261027/HYBRID-C-CODE-HANDOFF-20261027.md
LOCAL_RESULT: docs/lfm/tool-use-20261027/HYBRID-C-LOCAL-VALIDATION-20261027.md
PR_FORK: https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/34
PR_UPSTREAM: https://github.com/openvinotoolkit/model_server/pull/4697

## Hybrid C — thought / tool separation

Implemented and locally validated 2026-10-27 on `review/lfm25-design-c-semantic-refit-20261027`.

- Spec: `docs/superpowers/specs/2026-10-27-lfm25-hybrid-thought-parser-design.md`
- Plan: `docs/superpowers/plans/2026-10-27-lfm25-hybrid-thought-parser.md`
- Default start pin: `C:\gm\lfm-2026.4\hybrid-c-review-20261027\build-py_off\bin\ovms.exe`
- EXE SHA256: `d9663aa6ca29880ae6d3d85ff5f341a2461affd7bc539dd2c8cd3df9fa71136e`
- KV default: `KV_CACHE_PRECISION=u4`, `OFFLOAD_RATIO=0`, lfm25 batch 1024

## Speed / memory pressure (LFM2.5)

- Cliff: r0≈55 → r20≈31.5 → r30≈24 tok/s
- u4 matrix: r0+u4 helps resident; r20+u4 does not fix cliff
- Local A/B on Hybrid-C EXE: u4 55.12 vs auto 56.24 tok/s (short decode)

## Plan
- [x] A0–A9 including commit/push and residual root-cause (read-only)
- [x] Design C spec + plan written / approved
- [x] Memory-pressure / u4 matrix + report
- [x] Cloud handoff docs
- [x] Hybrid C implementation (plan tasks 1–4)
- [x] Local Hybrid-C GPU validation (units + tool cycle + false-demotion + U4 A/B)
- [x] Wire start-lfm25 / start-lfm2-24b to hybrid-c-review pin + u4
