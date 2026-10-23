# Evaluation state

## Current checkpoint: 2026-10-24

ACTIVE_STAGE: MEMORY_BLOCKED_LIVE; ACCEPTED: NO; MERGE_AUTHORIZATION: NO.
STARTING_HEAD: 16b239e417454b65e3c004fd5e2dcd33e7a6f222; current HEAD: resolve with git rev-parse HEAD.
Operator authorized memory reclamation and live scripts. Desktop working-set trims completed without closing apps, stopping services, purging standby or changing production runtime/cache.
Two actual nightly GPU constructor attempts (default threads and COMPILATION_NUM_THREADS=1) were stopped by the 3 GiB sampled RAM watchdog after 29.047 and 32.469 seconds. The second run sampled tree RSS/private peaks of 20.578/20.651 GiB and minimum available RAM 1.970 GiB before termination. Construction never completed; generation was NOT_RUN.
CURRENT_FAILURE: measured memory pressure during GPU VLMPipeline construction, not merely the old static admission threshold. No unsupported-op exception was obtained before the stop.
LAST_GREEN_TESTS: supervisor offline controls 3/3 PASS, covering unrelated worker exclusion, complete owned-tree timeout cleanup and native exit/phase preservation. These are not inference PASS.
EVIDENCE_PATH: docs/minicpm-v47/evidence/live-20261024; report: LIVE-MEMORY-20261024.md. Exact second-run script snapshot and SHA256 retained there. Final available RAM 22.587 GiB; no surviving Python/inference worker observed.
NEXT_ACTION: no extended retries after two memory-floor stops. Further reduce persistent desktop footprint or establish a supported memory-saving loading/compilation configuration before another isolated GPU test. Keep text/image/video/performance and OVMS acceptance gated.

## Historical checkpoint: 2026-10-23

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
