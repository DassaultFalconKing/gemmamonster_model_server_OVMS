# LOCAL-AGENT-BOOTSTRAP — New execution queue after UMA-03

**Read first:** `POST-WAVE01-UMA-ROADMAP-20261022.md`. Source repos: `DassaultFalconKing/openvino` (PR #7 @ `74003278a9c8925fcda7bc32ceb27320e59bbb1d`, PR #8 @ `d82f5f573dfb2b30a4cbf35b1cb8f75e4066c621`, PR #6 @ `986a0d412322df6060f0672cacb327618f2ddcac`); OVMS docs #20/#21/#22. Always recheck remote SHA before using.

## Agent assignments

- **Agent W (Windows production-control acceptance):** PR #7 on detached worktree; re-link `ov_gpu_unit_tests`, verify 47/47 C++ + 33/33 Python + 200 publication repeats, redo corrupt `PackMode::require` negatives, capture binary DLL identity. Host PASS does not permit a production merge. Before live inference, ask operator for an explicit compute authorization.
- **Agent B (UMA race gate, highest priority):** review PR #8 exact scratch commit, `scatter_verified_record_to_residents` and `fence_path_b_publish`; write a GPU in-flight read/evict regression with a deliberately delayed reader, plus a two-queue overlap test. Prove no host overwrite until previous GPU use of slot ended; also prove post-scatter visibility before next consumer. Reject any `finish()`-only argument that ignores ordering of host `memcpy` before the wait. Keep `OTD_RESIDENT_USM_HOST` default off.
- **Agent P (performance, after B passes):** use representative real expert record sizes and actual quantized kernels with `M=1,2,4,8,11`. Paired/randomized A/B order, warmup and repeats; capture full wall stage timings and host/device memory budgets. Build short end-to-end C1/C2/C4 only after approval. Report accepted tok/s rather than just a 2-KiB digest.
- **Agent E (evidence and docs):** reconcile outdated PR #8 host verdict and PR body with later GPU tests; produce source SHA and binary SHA binding for **the latest** code. Independently run PR #6 verifier against native C++-built pack and corrupt copies. No unverified PR #6 merge while gating incomplete.

## STOP / governance

Windows only; Linux not available. Do not modify `GpuSystemMemoryPinninglimit`, BIOS, GPU driver, C6 golden SHA or production OVMS. If GPU compute permission has not been explicitly granted for a new workload, do not infer it from existing short kernel reports. No long soak, no production auto-enable. Scratch changes and tests must stay on independent branches; pin precise artifacts in `docs/coordination/acceptance/`.

## Required output

Write a source-locked table: `test_id | repository/sha | binary_sha256 | exact command | GPU flags | result | path to local log | residual risk`. Distinguish unexecuted tests from a pass. Return (a) Wave-01 model acceptance, (b) path-B ownership/race verdict, (c) large-record/kernel A/B findings, (d) updated acceptance docs, (e) whether #6 is independently verified, and (f) a single next integration recommendation.
