# QWENMONSTER — C6 protocol, model-family adaptation and agentic reliability

**Status: R2/R3 experimental source candidate, NOT ACCEPTED (2026-10-21).**

- Baseline: `c6-head-mainline-20261020` at `ba6ec792c3121850fea167fa7d7e190b25fcdc76`.
- Completed initial M1 source branch: `feature/qwenmonster-c6-20261021` at `04eb7415` (no BUILD/LIVE PASS).
- Active comparative refit branch: `feature/qwenmonster-comparative-refit-20261021` (do not deploy over live C6).

## Read before continuing

1. `STATE.md`: branch, stage, next action, current blockers.
2. `COMPARATIVE-QWEN-PARSER-VERDICT.md`: pinned vLLM, llama.cpp, XGrammar, GenAI evidence, decision matrix.
3. `OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md`: reusable MFP-1 stage gates A0–A9 for any new model family.
4. `GENERATION-POLICY-DESIGN.md`: native Qwen XML builder and unresolved hard-choice/reasoning risks.
5. `WHITESPACE-DEFECT-TAXONOMY.md`: Gemma JSON whitespace vs historical unexpected empty arguments vs two distinct XGrammar XML bugs; dependency API compatibility.
6. `ACCEPTANCE.md`: exact Bazel and runtime gate checklist.
7. `C6-BASELINE.md`, `PROTOCOL-MATRIX.md`, `ISSUES-AND-RISKS.md`: inherited M1 provenance.

## Boundaries

Canonical template + tokenizer decide the native model protocol. vLLM informs parser-state behavior; llama.cpp informs native generation/grammar; GenAI/XGrammar owns constrained decoding; OVMS retains its OutputParser/Streamer/API boundaries. Do not replace the working Gemma4 stack.

Do not report BUILD or LIVE PASS on the strength of a GitHub commit. Preserve exact tests, logs, native tokens and model/device/version evidence.
