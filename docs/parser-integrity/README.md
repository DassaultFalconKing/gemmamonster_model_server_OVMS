# Parser Integrity: RLC + TLP-H

Status: DOCUMENTATION / IMPLEMENTATION QUEUED (not code-accepted).
Created: 2026-10-24. Branch: `docs/rlc-tlp-h-20261024`.
Base: `feature/minicpm-v47-arc140v-eval-20261023` (selected because it contains the living 2026.4 MFP-1 / A3.1 contract). This branch is **not** a release or authorization to merge unrelated MiniCPM evaluation changes.

## Scope and names

- **RLC — Reasoning Lossless Contract**: retain the decoded *reasoning body* exactly, modulo recognized native framing; own boundary/phase integrity, not JSON or semantic inference. [RLC.md](RLC.md)
- **TLP-H — Tool Literal Preservation Hardening**: extend and verify existing native tool parser-retainers for exact strings, numeric lexemes, nested values and atomic valid publication. [TLP-H.md](TLP-H.md)
- **TEST-MATRIX**: staged RED, FIX, regression and live cases. [TEST-MATRIX.md](TEST-MATRIX.md)
- **STATE**: evidence ledger and handoffs. [STATE.md](STATE.md)

Normative parent: [MFP-1 A3.1](../qwenmonster/OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md). This effort complements MFP-1; it does **not** replace its family-specific contracts or policy/grammar gates.

## Data-flow ownership

`generated token IDs -> OVMSTextStreamer (decode) -> OutputParser (phase router) -> native ReasoningParser / ToolParser -> Delta -> API`

| Component | Promise | Not its responsibility |
| --- | --- | --- |
| RLC | Exact decoded reasoning body, legal framing removal and correct channel assignment | Reconstructing model-intended values; inferring schemas; truth |
| TLP-H | Exact tool argument literals, valid native structure and atomic eligible publication | Model's choice of correct VIN/part/file; tool execution authority |
| Shared seam | No phantom/lost/duplicated bytes across token, chunk, phase and finish boundaries | Retokenizing a decoded string into identical original token IDs |

**Anti-hallucination** is narrowly scoped to *parser-generated* false content. These controls cannot prevent the model from generating wrong facts, changing identifiers between thoughts and calls, or choosing the wrong tool.

## Working agreement

1. Before each code patch, add a small targeted **RED** fixture or explicitly record why it is not reproducible; preserve raw input, expected output, chunk layout and exact source SHA.
2. Deliver tests **incrementally with each implementation slice**, normally 2–5 focused positive/negative cases; do not bank all tests for the final acceptance.
3. RLC and TLP-H changes use separate implementation branches/worktrees or scoped commits; no global parser rewrite.
4. Run affected family regressions and unchanged controls; log executed command, exit code, pass/fail count, binary/dependency identities. Use `NOT_RUN` rather than guessed GREEN.
5. Family-native marker handling prevails: Qwen's tool-looking text inside unclosed reasoning is not a call; Gemma4's documented reasoning-to-tool handoff is a distinct exception.
6. Never touch working production binaries, models or long-running local sessions solely to satisfy a documentation gate.

## Proposed order

- **RLC-0:** characterize existing parser and streamer; add split-invariance and literal corpus before modifying logic.
- **RLC-1:** fix proven loss in small family-specific commits (Qwen3, Gemma4 header, GPT-OSS first-chunk), preserving current recovery controls.
- **TLP-H-0:** pin Qwen3Coder retention PASS evidence, then add systematic cross-family RED fixtures.
- **TLP-H-1:** harden one family at a time, carrying typed schema, publication and streaming controls together.
- **Integration:** mixed reasoning/tool traces, reconstructed SSE vs unary, model-specific live runs only after permission and a real machine.

Each packet updates [STATE.md](STATE.md) and [TEST-MATRIX.md](TEST-MATRIX.md) in the **same commit** that introduces corresponding tests or implementation. Keep this document and root [AGENTS.md](../../AGENTS.md) as discoverable entry points.
