# Agent instructions: OVMS parser integrity work

These are repository-level instructions for coding agents. Existing MFP-1 family rules remain authoritative; do not use this file to override system/developer instructions or the canonical protocol.

## Parser integrity work is permanently discoverable here

- [Parser Integrity program](docs/parser-integrity/README.md)
- [RLC: Reasoning Lossless Contract](docs/parser-integrity/RLC.md)
- [TLP-H: Tool Literal Preservation Hardening](docs/parser-integrity/TLP-H.md)
- [Incremental test matrix](docs/parser-integrity/TEST-MATRIX.md)
- [Checkpoint / evidence state](docs/parser-integrity/STATE.md)
- [MFP-1 A3.1: parser-retainer normative contract](docs/qwenmonster/OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md)

**Applicability trigger:** If modifying any `src/llm/io_processing/**` reasoning/tool/output parser, `src/llm/ovms_text_streamer.*`, or their tokenizer/template/SSE routing/tests, consult RLC and TLP-H first. If unrelated to these seams, do not expand scope merely because these documents exist.

## Working protocol

1. Pin current branch/HEAD, model and tokenizer/template, dependencies and exact failing fixture. Record status in `docs/parser-integrity/STATE.md`. Never change a running production worktree solely to test a patch.
2. **Drip-feed tests throughout development:** commit small test packets **with each change**, not a test dump at the end. Prefer 2–5 narrow tests: original repro, negative case, existing regression, then stream split/lifecycle as appropriate. Use existing test files and target registrations; discover real build commands, never invent target names.
3. For a reported bug, preserve **observed RED** first when feasible, then code, then GREEN. If the behavior cannot be reproduced, record `NOT_REPRODUCED` and evidence rather than claiming a repair.
4. Keep reasoning text distinct from tool structured data. RLC is decoded-text retention with structural framing; TLP-H is exact typed tool-argument preservation and completion/registry/schema checks. Neither verifies model-generated factual correctness.
5. Preserve family-specific channel ownership: Qwen tool-looking text while still in reasoning stays reasoning; Gemma4 has its own documented legal thought/tool handoff. Do not generalize one family to another.
6. Update `TEST-MATRIX.md` and `STATE.md` with the test IDs, exact commands, exit codes, logs, source/binary revision and `NOT_RUN` boundaries **alongside each test/code commit**. CI/source inspection != local runtime proof.
7. Protect established Gemma4 and Qwen baselines; use isolated worktrees/branches and scoped cherry-picks. This **documentation branch was based on the MiniCPM v4.7 evaluation branch**, so never merge it wholesale into unrelated release branches without reviewing inherited changes.
8. Never silently change tool-call publication semantics, normalized values or whitespace; preserve literal text. Abort/fail closed rather than invent a missing executable argument or repair an unfinished tool call.
9. No model launch, heavy GPU tests, build-environment surgery or live endpoint exposure without local-machine authorization and captured runtime identity.

## Next agent entry

Read `docs/parser-integrity/STATE.md` and `TEST-MATRIX.md`; begin **RLC-R0-01..04** or **TLP-T0-01..04** in test-only scoped commits. Mark all untouched gates `NOT_RUN`. For implementation, carry an exact failure + smallest fix + corresponding new test together. No acceptance/merge without independent actual evidence.
