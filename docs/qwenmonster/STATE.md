# QWENMONSTER checkpoint — comparative refit / model family protocol

Date: 2026-10-21
- ACTIVE_STAGE: **R2 refit candidate + R3 new generation policy candidate; ALL GATES UNVERIFIED**
- BASE_SHA: `ba6ec792c3121850fea167fa7d7e190b25fcdc76`
- M1_SOURCE_HEAD: `04eb7415f3ef760dfcd53be5fa4f6b33f51e7b01`
- WORK_BRANCH: `feature/qwenmonster-comparative-refit-20261021`
- LAST_CODE_SHA: `333a9893bbd0e4d06cd57c52e93141ddbc4ff7e7` (before this docs-only update)
- CURRENT_HEAD: resolve current tip of WORK_BRANCH (docs commit is newer than LAST_CODE_SHA)
- LAST_GREEN_TESTS: **none**; remote code and documentation commits are not build/run evidence
- CURRENT_FAILURE: canonical **public source** GenAI/XGrammar/OpenVINO/Minja/Tokenizers cohort now pinned; **actual build-machine checkout, loaded binaries, compilation and runtime still NOT verified**; canonical template/generation suffix oracle and required/open-think compatibility unresolved
- NEXT_ACTION: run `scripts/qwenmonster/verify_public_cohort.py` against locked component checkouts (see PUBLIC-COHORT-INTEGRATION.md), then build focused Bazel gates and run four separate whitespace/empty-args controls (especially still-open XML #650/#802); only then Qwen unary/SSE and agentic
- REVERT_POINT: M1 `04eb7415f3ef760dfcd53be5fa4f6b33f51e7b01` for new refit, original C6 `ba6ec792c3121850fea167fa7d7e190b25fcdc76` for full program
- EVIDENCE_PATH: `docs/qwenmonster/ACCEPTANCE.md` (plan only), code/tests in `src/test/llm/` (not executed)
- ACCEPTED: **NO**

## Current commits (read in order)

- `22a5fa5`: registry-check unknown names and typed argument fallback rejection; add two regression tests.
- `1afab75`: Qwen XML generation-policy builder using native GenAI `QwenXMLParametersFormat`; factory and build registration.
- `555d87e`: standalone generation-policy tests and Bazel target.
- `8e0c006`: vLLM/llama.cpp comparison + OVMS model-family adaptation protocol MFP-1.
- `333a989`: required-field checker and closing-marker test, positive zero-argument parser test.

## Guardrails
- No change to working `c6-head-mainline-20261020` or `gemma4` production parser.
- Source verified != build verified != runtime accepted.
- Do not merge/enable guided Qwen until GenAI pin and actual grammar acceptance pass.
- Upstream XGrammar #650 and #802 were OPEN as checked 2026-10-21; associated PR #651, #803 and #837 OPEN/unmerged.
- Gemma C5 historical verdict `24847c968`: JSON whitespace CONFIRMED FIXED; unexpected empty-args NOT REPRODUCED after 267 filled required calls. This is not evidence about zero-parameter XML tools.
- Public GenAI/XGrammar forks are now available with source-locked SHA in `public-source-lock.json`: GenAI `2decb9ec4bea827e01db47524352ad72d23b33ab`, XGrammar `c77d5e0d62411d17d4cf55d280463eb5b3bec7ba`. Historical XGrammar `f228574c...` is also public on a legacy branch, and its semantic empty `ExcludeToken()` handling is visibly carried in the new source. **No loaded binary or matcher run verified.**
- An unresolved issue is a live risk, not a blanket claim every build is broken.

## Public fork integration checkpoint
- PUBLIC LOCK: `docs/qwenmonster/public-source-lock.json`, authoritative original `DassaultFalconKing/openvino.genai:docs/public-cohort-20261021/docs/public-source-lock.json`.
- SOURCE PREFLIGHT: `scripts/qwenmonster/verify_public_cohort.py` (checks expected local checkout Git HEADs and select source markers; not run here).
- CURRENT WORKSTREAM HEAD: see branch `feature/qwenmonster-parser-invariants-20261021`. This branch contains independent parser invariant tests and published public-source lock updates, but acceptance remains **NOT ACCEPTED**.
- STAGE A0: **public dependency source identities verified**; A6 binary/runtime compatibility not verified.
