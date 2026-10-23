# MiniCPM-V 4.7 program state (persistent handoff)

DATE: 2026-10-23
CURRENT_STAGE: DOCUMENTED / awaiting local A0/E0 identity intake and model files
BASE_SHA: eb76a74f7aa39573d452d95443e189b1f5f4d9e8
WORK_BRANCH: feature/minicpm-v47-arc140v-eval-20261023
CURRENT_HEAD: to be resolved by local git fetch after document commits
LAST_GREEN: GitHub docs commits only; no local tests/GPU runs executed in this session
REVERT_POINT: eb76a74f7aa39573d452d95443e189b1f5f4d9e8
CURRENT_FAILURE: none reproduced; actual model/runtime eligibility UNKNOWN
NEXT_ACTION: local agent to capture SOURCE-LOCK.json, original/HF IR Jinja token IDs, DLL map, exact 2026.4 RC1 capability, then test E1/E2 and write MFP-1 RED fixtures
EVIDENCE_PATH: docs/minicpm-v47/ (future local evidence must be linked, not presumed)
MERGE_AUTHORIZATION: NO

## Gate ledger

| Category | Gate | Status | Evidence |
| --- | --- | --- | --- |
| SOURCE | download verified files and sha/tokenizer/Jinja revisions | NOT_RUN | local agent E0 |
| EXEC | pinned GenAI 2026.4 RC1 image pipeline | NOT_RUN | local E1/E2 |
| EXEC | separate newer GenAI sandbox | NOT_RUN | only if necessary |
| EXEC | Arc 140V full 35B-A3B INT4 GPU compile | NOT_RUN | local GPU |
| EXEC | text, image, video | NOT_RUN | local E3 |
| EXEC | memory fit, no swap, C1 throughput | NOT_RUN | local E4/E5 |
| API | OVMS VLM_CB | NOT_RUN | local E6 |
| PROTOCOL | exact canonical prompt/Jinja token-ID corpus | NOT_RUN | MCPV47-01 |
| PROTOCOL | native parser-retainer RED/GREEN | NOT_RUN | MCPV47-03/04 |
| PROTOCOL | lossless strings/numbers + schema fail-closed | NOT_RUN | MCPV47-04 |
| POLICY | none/auto/required/named/parallel | NOT_RUN | MCPV47-05 |
| API | unary/SSE, tool-result replay, think ON/OFF | NOT_RUN | MCPV47-06 |
| REGRESSION | MiniCPM5, Qwen3Coder, Gemma4, Ornith | NOT_RUN | MCPV47-07 |
| LIVE | multimodal agentic C1/C2/C4 | NOT_RUN | MCPV47-07 |
| RELEASE | operator acceptance | NOT_RUN | owner signoff |

## Operating rules

- Every local agent updates this file before code edits and after meaningful milestones: exact HEAD, tests/exit codes, log paths, named blocker, next command and last successful test.
- Keep MFP-1 `SOURCE VERIFIED → RED REPRODUCED → STATIC PATCH → BUILD GREEN → UNIT GREEN → API GREEN → RUNTIME GREEN → AGENTIC GREEN → ACCEPTED` distinct.
- Never mark tests PASS from GitHub source reading or earlier unrelated model/binary reports.
- Separate model checkpoint issue, OpenVINO 2026.4 runtime issue, parser/policy issue, and VLM_CB issue.
- Preserve frozen RC3B-postfix, active OVMS 2026.4 runtime and memory CIB2 branches.
