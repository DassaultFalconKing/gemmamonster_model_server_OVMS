# QWENMONSTER checkpoint

- ACTIVE_STAGE: R2 / M1 streaming protocol correctness, **AWAITING BUILD AND LIVE VALIDATION**
- BASE_SHA: `ba6ec792c3121850fea167fa7d7e190b25fcdc76`
- CURRENT_HEAD: branch `feature/qwenmonster-c6-20261021`; resolve exact tip using `git rev-parse HEAD` on checkout (this checkpoint is in the evolving branch)
- LAST_CODE_HEAD: `13ce7fbe274f935584e5853065979f7cdf168337` (before checkpoint commit)
- LAST_GREEN_TESTS: none measured on this candidate
- CURRENT_FAILURE: source inspection confirms single-chunk/multi-call delta loss or throw in original C6; new patch's runtime behavior not yet tested
- NEXT_ACTION: build `//src:qwenmonster_output_parser_test`, execute new and legacy suites, then Gemma negative controls; reproduce SSE with live Qwen
- REVERT_POINT: `ba6ec792c3121850fea167fa7d7e190b25fcdc76` for all branch work; individual commits for tests, queue, bounded recovery and Bazel registration
- EVIDENCE_PATH: `docs/qwenmonster/ACCEPTANCE.md`; raw transcripts/CI logs not collected
- ACCEPTED: **NO**

## Work completed in branch
- Dedicated Qwen `pendingDeltas` with name/id before argument deltas.
- `drainPendingDelta()` override; multi-call ordering across single decode chunks.
- Recovery limited to fully closed `</function>` missing only its outer envelope.
- Five added focused tests; two legacy STOP-recovery expectations changed explicitly.
- Isolated Bazel `//src:qwenmonster_output_parser_test` target.

## Safety
Do not switch the running C6 worktree or overwrite the base branch.
Do not claim GREEN without a compiler/runtime run. Keep failures and raw output.
