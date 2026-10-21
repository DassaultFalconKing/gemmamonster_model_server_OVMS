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
- NEXT_ACTION: run focused Bazel compiler/tests; investigate GenAI QwenXML API and actual XGrammar pin; reproduce XGrammar #650/#802; run Qwen short unary/SSE; then template/phase and agentic
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
- Upstream XGrammar #650 and #802 were open at last research check; #651 unmerged.
- An unresolved issue is a live risk, not a blanket claim every build is broken.
