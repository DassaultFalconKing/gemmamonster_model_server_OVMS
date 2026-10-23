# Evaluation state

Evaluation date: 2026-10-23, Europe/Berlin client context.
ACTIVE_STAGE: MEMORY_BLOCKED; ACCEPTED: NO.
BASE_SHA / REVERT_POINT: eb76a74f7aa39573d452d95443e189b1f5f4d9e8.
WORK_BRANCH: feature/minicpm-v47-arc140v-eval-20261023.
CURRENT_HEAD: use `git rev-parse HEAD`; commits contain this immutable checkpoint.
LAST_GREEN_TESTS: 20/20 file ETags; Core GPU and 5/5 graph reads on each SDK; six template render/tokenizer cases. These are not inference PASS.
CURRENT_FAILURE: pinned GenAI dispatcher rejects minicpmv4_7; nightly compile admission blocked.
NEXT_ACTION: make at least 21.368 GiB physical RAM available without changing production processes, then rerun supervised text-only candidate. Recheck GPU ownership and dynamic budget first.
EVIDENCE_PATH: docs/minicpm-v47/evidence; raw logs/path map retained privately.
No product source changed; no build, model conversion, server, endpoint, driver change, baseline benchmark or merge.

## Persistent MFP-1 ledger

MERGE_AUTHORIZATION: NO. This checkpoint advances the existing program state from remote commit 5c9ce4680; both roadmap documents and MFP-1 remain in force.
SOURCE: file inventory/revision/hash verification PASS; full original-vs-exported canonical prompt corpus NOT_RUN.
EXEC: pinned constructor FAIL; nightly GPU compile/text BLOCKED; image/video/performance NOT_RUN.
PROTOCOL: preliminary template/tokenizer evidence only; native parser-retainer RED/GREEN, lossless typed strings/numbers/schema validation NOT_RUN.
POLICY: none/auto/required/named/parallel NOT_RUN.
API: unary/SSE, tool-result replay, think ON/OFF and OVMS VLM_CB NOT_RUN.
REGRESSION: MiniCPM5, Qwen3Coder, Gemma4, Ornith NOT_RUN; no parser changes.
LIVE: multimodal agentic C1/C2/C4 NOT_RUN. RELEASE: operator acceptance NOT_RUN.
Each future phase must update exact HEAD, named failure, exit codes, log paths and next command. Source reading, file validation and template rendering never substitute for GPU, parser, API or agentic acceptance.
