# Gemma4 whitespace regression 2026-09-16 — repair handoff

This file is the interruption-safe work ledger for the named-tool streaming whitespace regression.

## Authority / starting point

- OVMS repair branch: `fix/gemma4-whitespace-regression-1609`
- Parent PR-prep branch: `upstream/gemma4-tool-calling`
- Parent head at start: `d582668e6405e5d4cffbf050e9ee7303f7b94ef0`
- Current OVMS GenAI pin: `fe818c0467feb17b87c5adfb3f7e28dd70b76e99`
- Current XGrammar pin through that GenAI commit: `v0.1.31`
- Historical working XGrammar repair revision: `9aa840b6d16abf094f3e8e2ac9c10465b77656c9`

## Evidence read

- Cursor `ROOT-CAUSE.md`: identifies an unbounded JSONSchema whitespace production after the native Gemma4 tool begin tag.
- Codex `streaming_named_degenerate_diagnosis.md`: independently places the bad token ids upstream of OVMS parser/SSE serialization and highlights the CB `read()` / `read_all()` observation.
- Original live capture: named streaming on the long prompt reaches `finish_reason=length` with `\n\t` only; unary on the exact same prompt completes `search_docs` in 23 tokens.

## Root-cause disposition

**Accepted working hypothesis / repair target:** the structural JSON schema permits unlimited inter-element whitespace. After `<|tool_call>call:search_docs`, `{` and whitespace are both grammar-legal; the model can greedily remain in the whitespace production until `max_tokens`.

The stream/unary observation is evidence of where the divergent legal branch surfaced, not evidence that OVMS `GenerationHandle::read()` owns the grammar bug. OVMS builds the same structured-output config before the response split, and the streamer sees ids only after generation.

## Confirmed dependency mismatch

Current `openvino.genai@fe818c04` exposes only `JSONSchema(schema)` and pins XGrammar `v0.1.31`. That XGrammar `JSONSchemaFormat` has no per-tag whitespace bound.

The previously validated 2026.4 repair used two coordinated changes:

1. GenAI typed API: `JSONSchema(schema, max_whitespace_cnt)`; serialize the bound into structural-tag JSON.
2. XGrammar revision `9aa840b6...`, which accepts and applies per-tag `max_whitespace_cnt`.
3. OVMS Gemma4 builder: every tool JSON schema uses `max_whitespace_cnt=2`.

The current 2026.5 repair must port that narrow dependency capability onto the exact `fe818c04` pin. It must **not** downgrade GenAI to the 2026.4 line.

## Explicit non-fixes

- Do not strip whitespace in `Gemma4ToolParser`; parse-time cleanup cannot prevent 512 generated whitespace tokens.
- Do not patch SSE serialization or `OVMSTextStreamer` to hide the residue.
- Do not special-case `read()` vs `read_all()` without evidence of a CB state-machine defect after the grammar is bounded.
- Do not change prompt wording.
- Do not import unrelated 2026.4 builder/parser changes.

## Work stages

- [x] S0 — resolve report branches and PR-prep branch.
- [x] S1 — read Cursor + Codex reports and original capture.
- [x] S2 — trace current OVMS builder, GenAI pin and XGrammar capability.
- [x] S3 — confirm historical repair shape and exact XGrammar support.
- [ ] S4 — create companion GenAI branch from exact `fe818c04`; add regression contract first.
- [ ] S5 — port typed whitespace-bound API + exact XGrammar repair revision; inspect diff.
- [ ] S6 — add OVMS Gemma4 regression contract for bound=2 before production change.
- [ ] S7 — change only Gemma4 `buildToolTag()` to apply bound=2.
- [ ] S8 — verify source-level contracts/diffs/statuses available in this environment.
- [ ] S9 — update this handoff with exact SHAs, build/runtime gates still requiring the Windows/Arc host.
- [ ] S10 — final commit/ref handoff.

## Current resume point

**Resume at S4.** Create the GenAI companion branch from `fe818c0467feb17b87c5adfb3f7e28dd70b76e99`; preserve legacy `JSONSchema(schema)` serialization and add bounded/zero/equality regression coverage before changing the API implementation.
