# Promotion delivery and live dogfood review

PROMOTION_HEAD: 239f70d95e5c4eb54fd911dbe438825bd7b47848
MAIN_BASE: 8f970d4236738ae800b01786af7ad5ad843a62c8
RC_SOURCE: 43bc254e8996f17b929afef79f310d0b0b0cc139
RUNTIME_DIFF_FROM_RC: NONE
DOC_ONLY_DIFFS: docs/gemmamonster/promotion-20260916/COMMITS.md, PR-CANDIDATE.md, REPORT.md

All 2074 accepted RC tree entries have identical Git blob ids and file modes. Main and staging are the two exact parents. No main-only files are retained. Production source and build configuration have no changes from RC. Main-only commits: 89; staging-only: 63, comprising 14 upstream lineage and 49 Gemmamonster-specific commits (13 documentation/evidence, 36 implementation/tests).

## Fresh semantic tests

Tested exact promotion HEAD: 239f70d95e5c4eb54fd911dbe438825bd7b47848. Six targets executed, 64 tests passed, zero failures, zero skipped, zero cached test results. Full command, Bazel build-event stream, log and per-target XML/logs are in this directory.

| Target | Result | Tests |
|---|---|---|
| gemma4_generation_policy_test | PASS | 27 |
| gemma4_phantom_tool_call_test | PASS | 12 |
| gemma4_chunk_invariance_test | PASS | 4 |
| gemma4_rendered_prompt_state_test | PASS | 11 |
| gemma4_f7_contract_test | PASS | 5 |
| gemma4_f10_guard_test | PASS | 5 |

git diff --check: PASS. RC-to-promotion documentation diff check: PASS. Whole-tree RC allowlist check: PASS.

## Accepted build provenance

BUILD_PROVENANCE_REUSED: YES, by complete runtime/build tree equivalence.
BUILD_SOURCE: b722aa440b5555041f24e6d6f7aea8bda100bdf7
EVIDENCE_HEAD: 43bc254e8996f17b929afef79f310d0b0b0cc139
BINARY_SHA256: 3DFC2D11E614BD03924E6730AD8053DB00A6E5564F41E11F966A0929B44F65FE

The accepted packaged binary was hashed again. The new promotion is not claimed as a new binary build. Test runtime DLL hashes also match the accepted package. Full live acceptance was not repeated; the user explicitly added a focused fresh tool-calling dogfood after tests passed.

## Fresh live dogfood

One warmup plus three measured rounds, temperature=0, max_tokens=512. Accepted 2026.5 package and unchanged VLM_CB/GPU/u4, prefix cache enabled, batch tokens=4096, sequences=4, cache_size=0, Gemma4 reasoning/tool parsers, guided tools and dynamic split fuse enabled. The old README's 2026.4 binary/profile was not used.

44 chat requests returned HTTP 200. Across them, 32 tool calls were inspected for id, name, JSON schema and grounded local paths, and executed as bounded local read/list operations. Raw requests, JSON responses, SSE streams, reconstructed messages and tool results are preserved under live/.

- Named unary plus tool-result replay: 4/4 PASS.
- Two parallel same-name read_file calls plus replay of both results: 4/4 PASS.
- Required streaming trajectory and replay: 4/4 PASS, list_dir -> read_file -> final grounded OVMS version.
- The original strict streaming probe expected read_file immediately. It instead got a protocol-valid list_dir("."). Its four FAIL receipts are retained. Separate continuation proves task completion; this was an overly strict first-tool expectation, not an invalid required-tool response.
- Auto agent: all four runs executed list_dir("."), read_file("binary-provenance.txt"), list_dir("logs") correctly. All four final answers were verbose file enumerations and reached exactly 512 completion tokens with finish_reason=length. Full agent completion is FAIL. No repeated tool-call cycle was observed; the payload shows a truncated substantive answer. No max_tokens or runtime tuning was performed to hide this outcome.

FULL_DOGFOOD: FAIL (agent final-answer completion).
TOOL_CALLING_AND_REPLAY: PASS within the stated bounded cases.

PID 3380 and executor thread 27048 continued through the campaign. The initial and final process/module snapshots show the accepted package's core runtime DLLs. The fresh server log contains no GPU_CONTEXT_FATAL, CL_OUT_OF_RESOURCES, quarantine or CANCELLED markers. This harness does not exercise real OpenCode delegation, so it does not independently reproduce parent cancellation or certify the OpenCode application.

## Known caveats and review boundary

- Existing non-blocking caveat: local Gemma/OpenCode can enter repetitive planning/delegation loops; this has not been shown to be an OVMS protocol/parser/runtime failure. Separate track: agent-loop termination / progress watchdog / plan-ledger policy.
- Expected parent-turn cancellation remains the documented delegation behavior when the same PID/executor survives, no GPU fatal/resource/quarantine occurs and the following request succeeds. Not triggered in this fresh harness; no claim of new cancellation evidence.
- Fresh additional dogfood limitation: correct tool execution followed by verbose final answer truncation at the fixed 512-token cap. Full end-to-end dogfood is not green.

PR_READY: YES for independent promotion review; this is not a claim of full dogfood completion.
BLOCKERS: No runtime-equivalence or semantic-suite promotion blocker. The incomplete agent final answer is disclosed as a separate agent/output-budget limitation; no evidence here demonstrates a server fault.

No PR is opened or merged. Main and staging must remain unchanged. Push only the authorized promotion branch after a fresh remote-ref check. Fresh receipts are kept outside the tracked promotion tree so its tested SHA does not change after verification.
