# C6 atomic commit map (upstream landing plan, 2026-09-18)

Principle (§19): one concern per PR, no history dumps. F3 evidence-only, debug
trace code, and audit pair `2489e342/b9f65b96` never ship. G2 pack
(`C:\git\artifacts\gemma4-frankenstein-20260917\C6-g2pack\`) is the C6 G2 gate evidence:
turns 1-4 unary `tool_calls`, g6 long `search_docs` SSE, prefix 1-3 SSE text `stop`
(~16K prompts). All present and sane at the time of writing.

## GenAI PR 1 — bounded JSON whitespace (generic prerequisite)

Base: upstream master at time of PR (re-resolve; was `3abf349b`).
1. `fix(structured-output): expose bounded JSON schema whitespace`
   (`generation_config.hpp`: `max_whitespace_cnt`, ctor, serialization, equality)
2. `test(structured-output): pin JSON schema whitespace bound contract`
   (4 cases: legacy-unset, format-level, zero-vs-unset, equality)

## GenAI PR 2 — fail-closed matcher advancement (F1, generic correctness)

1. `fix(xgrammar): fail closed on rejected generated token` (+ `AcceptToken` check)
2. `test(xgrammar): cover fail-closed matcher advancement`
3. `test(xgrammar): enable focused matcher regression coverage`
   (TokenIds-qualification fix folds into #3, Windows-only, no behavior change)

## GenAI PR 3 — tokenizer-aware structural tags (F2, generic)

1. `test(xgrammar): expose internal token-aware structural parser seam`
2. `test(xgrammar): centralize tokenizer-aware structural parsing`
3. `test(xgrammar): cover tokenizer-aware token structural tags`
4. `fix(xgrammar): plumb tokenizer info into structural tags`

## GenAI PR 4 — typed token structural API (F5, generic public API)

1. `feat(structured-output): add typed token structural tags`
   (`Token`, `AnyTokens`, `TokenTag`, `TokenTriggeredTags`; keeps string API compatible)
2. `fix(structured-output): add TokenTriggeredTags arm to structural_tag_to_json visitor`
3. `test(structured-output): replay typed token structural tags`
4. `feat(python): bind Token/AnyTokens/TokenTag/TokenTriggeredTags + model-free tests`
   (+ hand-maintained `.pyi` additions; stubgen output to be re-verified by maintainer CI)
5. `feat(js): add token structural tag types and factories`
   (types only; no JS runtime harness on our host — state this in the PR)

XGrammar dependency note for all GenAI PRs: validated against `1de42473`; stable
alternative `v0.2.7` already contains the needed token APIs — maintainer may take
either; our C6 pins `1de42473`.

## OVMS PR — Gemma4 guided-generation repair (downstream consumer)

Base: `upstream/main` (rebase only if clean; check was clean at `16ca1ac6`).
1. `fix(gemma4): restore escaped delimited string semantics` (parser, `2dc4e54c` equiv)
2. `test(gemma4): preserve number lexemes in streamer helper` (`d7e26e7d` equiv)
3. `fix(gemma4): bound tool JSON whitespace` (call-site `JSONSchema(schema, 2)`)
4. `test(gemma4): pin bounded tool JSON whitespace + required-field preservation`
5. `test(gemma4): stale hard-named tool expectation now requires INVALID_ARGUMENT`
6. `test(gemma4): reconcile streaming expectations with deferred STOP flush`
   (documents: post-call prose buffers to stream end, proven no-loss by STOP probe)

## Explicitly NOT shipped

- F3 `token_triggered_tags` experiment (evidence-only; dispatch-missing unresolved as
  product direction; superseded by HUNT verdicts).
- Debug trace instrumentation (`xgrammar_backend.cpp` trace block — worktree-only).
- `2489e342/b9f65b96` audit pair (net-zero, reviewer noise).
- `g5g6`/`livelike` harness scripts (track tooling, not product).
