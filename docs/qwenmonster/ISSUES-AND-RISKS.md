# Qwenmonster issues and risks

1. **P0: build absent.** Remote GitHub source edits cannot prove the candidate compiles or runs. Next step: focused Bazel build/test.
2. **P0: STOP vs LENGTH upstream boundary.** `OVMSTextStreamer::end()` synthesizes STOP, so direct parser LENGTH tests cannot establish end-to-end LENGTH semantics. New recovery deliberately refuses open parameters under *any* STOP.
3. **P1: pending deltas during generation.** The streamer drains parser queues at final flush; when several envelopes arrive in one chunk, late deltas may wait for subsequent chunks or finalization. Verify SSE ordering and latency.
4. **P1: parser schema validation.** The source parser may accept unknown tool names and parses free-form parameter values. M1 fixes transport, not strict schema enforcement; leave to R2/R3 with safe pre-execution validation.
5. **P1: chunk invariance.** Deterministic name/index/arguments ordering needs more partitions and token-level tests than the first three added fixtures.
6. **P1: existing recovery expectations changed.** STOP in an open argument or partial parameter name is no longer executable by design; verify this against known-good traces.
7. **P1: qwen-specific isolation.** Code changes are Qwen-only; test all callers sharing `OutputParser` and `OVMSTextStreamer`.
8. **P2: model/harness behavior.** Delegation propensity must be measured separately from API/parser delivery. Do not optimize prompting before protocol correctness.

Do not silently downgrade failures to `auto` or mislabel source checks as LIVE PASS.
