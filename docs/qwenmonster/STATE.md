# QWENMONSTER checkpoint — comparative refit / model family protocol

Date: 2026-10-21
- ACTIVE_STAGE: **R2 refit candidate + R3 new generation policy candidate; ALL GATES UNVERIFIED**
- BASE_SHA: `ba6ec792c3121850fea167fa7d7e190b25fcdc76`
- M1_SOURCE_HEAD: `04eb7415f3ef760dfcd53be5fa4f6b33f51e7b01`
- WORK_BRANCH: `feature/qwenmonster-comparative-refit-20261021`
- LAST_CODE_SHA: `333a9893bbd0e4d06cd57c52e93141ddbc4ff7e7` (before this docs-only update)
- CURRENT_HEAD: resolve current tip of WORK_BRANCH (docs commit is newer than LAST_CODE_SHA)
- LAST_GREEN_TESTS: **none**; remote code and documentation commits are not build/run evidence
- CURRENT_FAILURE: no pinned build-machine GenAI/XGrammar version or compiling/running output; canonical template/generation suffix oracle unavailable; required/open think unresolved
- NEXT_ACTION: locate/pin local patched GenAI and XGrammar artifacts; compile focused Bazel gates; run four separate whitespace/empty-args defect-class controls (see WHITESPACE-DEFECT-TAXONOMY.md), including the open #650/#802 XML cases; only then Qwen unary/SSE and agentic
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
- Local patch IDs supplied for GenAI `bf3255153ee73faeee9c7da277853ab6aa9298e2` and XGrammar `f228574c0e7592f029407973092261a611f8ff61` are NOT resolved in the public upstream GitHub repos; verify local dependency repos and loaded binaries before asserting deployed fixes.
- An unresolved issue is a live risk, not a blanket claim every build is broken.
