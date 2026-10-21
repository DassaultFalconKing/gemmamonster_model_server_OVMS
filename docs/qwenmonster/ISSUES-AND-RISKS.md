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

## Whitespace defect separation (2026-10-21)

- **Gemma JSON whitespace:** CONFIRMED FIXED in C5 historical verdict `24847c968`; `JSONSchema(..., 2)` in current Gemma C6. Keep patched GenAI/XGrammar provenance attached to the accepted Gemma build. This is **not** a Qwen XML fix.
- **Unexpected Gemma empty args with required fields:** NOT REPRODUCED in `24847c968`, 267 later canonical filled calls. Not a valid argument for changing Qwen zero-argument behavior.
- **XGrammar XML end-marker drift:** issue #650, PR #651 open/unmerged (2026-10-21). Validate string parameter values and grammar prefixes; a C++ parser rejection is a safety mitigation, not constrained-decoding repair.
- **XGrammar genuinely empty XML parameter grammar:** issue #802, PRs #803 and #837 open/unmerged (2026-10-21). Schema declaring no properties is valid; it must terminate rather than self-loop whitespace. Parsing a completed XML empty call is only half the test.
- **Binary/header skew:** upstream GenAI header `6a35b97...` has only `JSONSchema(schema)`, whereas Gemma C6 code uses `JSONSchema(schema, 2)`. Exact local patched GenAI/XGrammar artifacts not yet retrieved. Compile/pin required.

Details and test IDs: `WHITESPACE-DEFECT-TAXONOMY.md`.

## Public dependency cohort (2026-10-21)
- New reproducible source identities: `docs/qwenmonster/public-source-lock.json`; setup `PUBLIC-COHORT-INTEGRATION.md`.
- Resolved at **source level**: Gemma `JSONSchema(schema, 2)` public GenAI API; empty `ExcludeToken()` support in published XGrammar C6 locked source.
- Still blocked: loaded library ABI and actual matcher/model tests; canonical Qwen schema grammar for XGrammar XML #650/#802; prompt-tail reasoning.
- Historical legacy→locked branches are DIVERGED. Do semantic carry-forward verification rather than assuming the new ref contains every prior change. Run offline source preflight against clean checkouts first.
