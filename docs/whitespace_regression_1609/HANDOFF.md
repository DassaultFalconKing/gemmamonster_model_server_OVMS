# Gemma4 whitespace regression 2026-09-16 — repair handoff

This file is the interruption-safe work ledger for the named-tool streaming whitespace regression.

## Authority / starting point

- OVMS repair branch: `fix/gemma4-whitespace-regression-1609`
- Parent PR-prep branch: `upstream/gemma4-tool-calling`
- Parent head at start: `d582668e6405e5d4cffbf050e9ee7303f7b94ef0`
- Current OVMS GenAI pin: `fe818c0467feb17b87c5adfb3f7e28dd70b76e99`
- Current XGrammar pin through that GenAI commit: `v0.1.31`
- Historical working XGrammar repair revision: `9aa840b6d16abf094f3e8e2ac9c10465b77656c9`
- GenAI companion branch: `DassaultFalconKing/openvino.genai:fix/schema-whitespace-bound-fe818c04-2026.5`
- GenAI RED contract commit: `d636c405e9b822a7008d4475a0d550a82d52a02f`
- GenAI companion HEAD: `e00eada6f4cce794ac3b3f6053cdb0c9dc569e68`
- OVMS regression source commit: `c481b7f849254cfa9e8a3e36d0a2aab8d08be6db`
- OVMS regression BUILD registration: `7e44f53559ea6851327c007ab87b39ed44d30cdd`

## Evidence read

- Cursor `ROOT-CAUSE.md`: identifies an unbounded JSONSchema whitespace production after the native Gemma4 tool begin tag.
- Codex `streaming_named_degenerate_diagnosis.md`: independently places the bad token ids upstream of OVMS parser/SSE serialization and highlights the CB `read()` / `read_all()` observation.
- Original live capture: named streaming on the long prompt reaches `finish_reason=length` with `\n\t` only; unary on the exact same prompt completes `search_docs` in 23 tokens.

## Root-cause disposition

**Accepted working hypothesis / repair target:** the structural JSON schema permits unlimited inter-element whitespace. After `<|tool_call>call:search_docs`, `{` and whitespace are both grammar-legal; the model can greedily remain in the whitespace production until `max_tokens`.

The stream/unary observation is evidence of where the divergent legal branch surfaced, not evidence that OVMS `GenerationHandle::read()` owns the grammar bug. OVMS builds the same structured-output config before the response split, and the streamer sees ids only after generation.

## Confirmed dependency mismatch and companion repair

Current `openvino.genai@fe818c04` exposes only `JSONSchema(schema)` and pins XGrammar `v0.1.31`. That XGrammar `JSONSchemaFormat` has no per-tag whitespace bound.

The companion repair is now committed on top of the **exact** `fe818c04` pin:

1. GenAI typed API: `JSONSchema(schema, max_whitespace_cnt)`; serialize the optional bound into structural-tag JSON.
2. XGrammar revision `9aa840b6...`, which accepts and applies per-tag `max_whitespace_cnt`.
3. Four C++ contracts preserve legacy one-argument serialization, bound=2, explicit zero and equality semantics.

Diff audit `fe818c04...e00eada6`: exactly three files: `src/cpp/CMakeLists.txt` (1/1), `generation_config.hpp` (9/4), one 35-line test file. The pre-patch blobs of both production files are byte-identical between the historical 2026.4 base and current `fe818c04`, so the established patched blobs were transplanted without overwriting newer 2026.5 content.

The OVMS repository pin is intentionally not changed to the fork. Local validation should override the `?=` dependency variables to this companion branch/commit; the upstream-ready OVMS change remains dependency-gated until the GenAI capability is merged/pinned officially.

## TDD checkpoint

GenAI contract was added before its implementation. At `fe818c04` it is source-level RED because `JSONSchema` has no `max_whitespace_cnt` member/two-argument constructor.

OVMS now has `gemma4_whitespace_bound_test`: for a hard named `weather` choice it descends through `Union -> TagsWithSeparator -> Tag -> JSONSchema` and requires `max_whitespace_cnt == 2` plus serialized presence. With the companion GenAI API but before the OVMS production change, this is the intended RED assertion.

Native compilation/runtime execution is not available in this remote connector environment; do not relabel source/diff verification as a passed build.

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
- [x] S4 — create companion GenAI branch from exact `fe818c04`; add regression contract first.
- [x] S5 — port typed whitespace-bound API + exact XGrammar repair revision; inspect diff.
- [x] S6 — add OVMS Gemma4 regression contract for bound=2 before production change.
- [ ] S7 — change only Gemma4 `buildToolTag()` to apply bound=2.
- [ ] S8 — verify source-level contracts/diffs/statuses available in this environment.
- [ ] S9 — update this handoff with exact SHAs, build/runtime gates still requiring the Windows/Arc host.
- [ ] S10 — final commit/ref handoff.

## Current resume point

**Resume at S7.** In `Gemma4GenerationConfigBuilder::buildToolTag`, replace only `JSONSchema(toolSchemaWrapper.stringRepr)` with `JSONSchema(toolSchemaWrapper.stringRepr, 2)`. Do not touch parser, streamer, CB `read()`/`read_all()` or prompt handling in this repair.
