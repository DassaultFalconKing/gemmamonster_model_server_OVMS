# LFM tool-use refit, 2026-10-27

ACTIVE_STAGE: **SOURCE CLEANUP PUSHED / REBUILD REQUIRED**. Previous Hybrid C EXE is protocol-accepted only; current SOURCE fixes JSON false positives and SSE latency and has NOT been built or GPU tested. Startup scripts pin previous EXE, KV default now auto.
BASE_SHA: a13dff47929bd40e38ecbb654ce7014e9a635704
CURRENT_HEAD: use `git rev-parse HEAD`; new cleanup source and historical EXE are intentionally different revisions
LAST_GREEN_TESTS: HISTORICAL Hybrid C EXE d9663aa6...: 197P/2S, LFM25 det 4/4 + code PASS, official 2/4 FAIL; LFM2-24B 8/8 + code PASS; Cursor HTTP hammer PASS. **These results do not validate newer source cleanup.**
CURRENT_FAILURE: historical EXE still demotes `{"plan":[]}`; source guarded valid JSON but NOT_RETESTED. LFM2.5 official agent 2/4, prose hang NOT_RESOLVED, offload cliff unchanged.
STAFF_MODE: parallel_tool_calls=true (API default already; agent/probe harnesses aligned)
NEXT_ACTION: clean Windows rebuild in distinct output root, source cleanup GTests, 18147 GPU smoke (JSON preservation + early SSE + LFM2.5 official chains). Do not replace d9663aa6 pin or touch 8137 before retest.
REVERT_POINT: BASELINE-LOCK.json (A9 serving); A9 candidate-final EXE `95fb62b5…` still available for rollback smoke
EVIDENCE_PATH: C:/gm/lfm-2026.4/hybrid-c-review-20261027
CLOUD_HANDOFF: docs/lfm/tool-use-20261027/HANDOFF-CLOUD-REVIEW.md
CODE_HANDOFF: docs/lfm/tool-use-20261027/HYBRID-C-CODE-HANDOFF-20261027.md
NEXT_LOCAL_HANDOFF: docs/lfm/tool-use-20261027/HANDOFF-LOCAL-CLEANUP-RETEST-20261027.md
LOCAL_RESULT: docs/lfm/tool-use-20261027/HYBRID-C-LOCAL-VALIDATION-20261027.md
PR_FORK: https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/34
PR_UPSTREAM: https://github.com/openvinotoolkit/model_server/pull/4697

## Hybrid C — thought / tool separation

Historical Hybrid-C EXE built and GPU protocol validated 2026-10-27 on `review/lfm25-design-c-semantic-refit-20261027`. Current source cleanup requires a new build and acceptance.

- Spec: `docs/superpowers/specs/2026-10-27-lfm25-hybrid-thought-parser-design.md`
- Plan: `docs/superpowers/plans/2026-10-27-lfm25-hybrid-thought-parser.md`
- Default start pin: `C:\gm\lfm-2026.4\hybrid-c-review-20261027\build-py_off\bin\ovms.exe`
- EXE SHA256: `d9663aa6ca29880ae6d3d85ff5f341a2461affd7bc539dd2c8cd3df9fa71136e`
- KV default in NEW start scripts: auto (no property) + `OFFLOAD_RATIO=0`, lfm25 batch 1024. Historical Hybrid C GPU evidence used U4.

## Speed / memory pressure (LFM2.5)

- Cliff: r0≈55 → r20≈31.5 → r30≈24 tok/s
- Earlier separate u4 matrix suggested a resident-profile benefit, but the subsequent Hybrid-C A/B did not reproduce a decode speed advantage; r20+u4 never recovered the offload cliff.
- Local A/B on historical Hybrid-C EXE: u4 55.12 vs auto 56.24 tok/s (short decode, n=3). Therefore no U4 speed claim; auto is the conservative new launcher default.

## Plan
- [x] A0–A9 including commit/push and residual root-cause (read-only)
- [x] Design C spec + plan written / approved
- [x] Memory-pressure / u4 matrix + report
- [x] Cloud handoff docs
- [x] Hybrid C implementation (plan tasks 1–4)
- [x] Local Hybrid-C GPU validation (units + tool cycle + false-demotion + U4 A/B)
- [x] Keep start scripts pinned to historical Hybrid C EXE with SHA verification; new source cleanup defaults KV to auto and supports explicit `-KvPrecision u4`
- [x] Source fix: valid standalone JSON preserved, ordinary prose streamed incrementally; tests added
- [ ] Build and locally accept this newer source commit (historical PASS not transferable)

