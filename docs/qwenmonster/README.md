# QWENMONSTER — C6 protocol and agentic reliability

Status: **M1 IMPLEMENTED, NOT VERIFIED** (2026-10-21).
Base: `c6-head-mainline-20261020` at `ba6ec792c3121850fea167fa7d7e190b25fcdc76`.
Working branch: `feature/qwenmonster-c6-20261021`. No changes to the base branch.

## Contract
- Correct native Qwen XML tool calls: `none/auto/required/named` and multi-call.
- Preserve reasoning -> tool -> result -> continuation without leaking or duplicating deltas.
- Isolate Qwen parsers and policies from Gemma4, Hermes3 and generic paths.
- Deterministic protocol correctness must precede behavioral tuning and agent delegation.
- Accept only with real build + API/SSE + harness evidence. A GitHub commit is not a live pass.

## Work stages
- **R0:** provenance, dependencies, upstream parser archaeology and known-good C6 (open).
- **R1:** canonical template, token-level equality, history/preserve_thinking (open).
- **R2/M1:** XML streaming ordering, multi-call, bounded recovery (patches landed; gates pending).
- **R3/M2:** Qwen generation config builder, lazy `auto`, strict `required/named` (not started).
- **R4:** reasoning/tool phase ownership and chunk invariance (not started).
- **R5:** multi-turn, agent delegation, concurrent sessions and context acceptance (not started).
- **R6:** post-3.6 capability profiles and small upstream PRs (not started).

See `STATE.md` before making changes. Continue only after running focused tests from `ACCEPTANCE.md`.
