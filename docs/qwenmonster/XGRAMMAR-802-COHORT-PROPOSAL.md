# XGrammar #802 cohort proposal (lock unchanged)

Status: **PROPOSAL ONLY. ACCEPTED: NO. LOCK NOT UPDATED.**  
Recorded: 2026-10-21  
Public lock remains `docs/qwenmonster/public-source-lock.json` → XGrammar `c77d5e0d62411d17d4cf55d280463eb5b3bec7ba`.

## Candidate (separate fork branch)

| Field | Value |
|---|---|
| Repository | `DassaultFalconKing/xgrammar` |
| Branch | `fix/qwenmonster-xml-empty-object-20261021` |
| Base (locked) | `c77d5e0d62411d17d4cf55d280463eb5b3bec7ba` |
| #802 epsilon | `3303659ec09c62c1d024a7d4eed1b0bc18b30cc3` |
| R1 residual | `b288dca18ee25d2f35197fb3971334ca049c8554` |
| Upstream refs | [#802](https://github.com/mlc-ai/xgrammar/issues/802), [PR #803](https://github.com/mlc-ai/xgrammar/pull/803) |

Do **not** merge [PR #837](https://github.com/mlc-ai/xgrammar/pull/837) on top of this candidate without a separate differential review.

## What is measured

- Native companion checks: emptySchemas / `maxProperties:0` accept epsilon and reject whitespace; open objects and nested braces unchanged; Qwen3-8B unit-tokenizer hard/lazy masks: 425 whitespace tokens, **0** allowed under candidate vs **422** under baseline; synthetic 1024-space path closed.
- R1: epsilon path requires `spec.required.empty() && spec.min_properties <= 0`. Native re-run after R1: `SUMMARY failures=0` (private hub log `xgrammar-802-native-checks-r1.log`).
- Candidate is statically linked into isolated native validation binaries only. Staged GenAI DLL was **not** rebuilt with this SHA.

## What remains open (blocks lock revision)

1. **XML #650** end-marker drift — separate issue; see `XGRAMMAR-650-NOTE.md`. Not fixed by #802.
2. **Inherited undeclared-required gap** — schemas like `{type:object, required:["a"]}` (no `properties` entry) still accept empty / whitespace native XML under both baseline and candidate. Parser `hasValidArguments` still fail-closes missing required values. Not claimed fixed by R1.
3. **Runtime cohort rebuild** — GenAI + XGrammar must be rebuilt and installed together before any lock SHA change.
4. **LIVE / agentic** — unary, SSE, tool-result loops, concurrency on the canonical target model: **NOT RUN**.

## Explicit non-actions

- Do **not** edit `public-source-lock.json` from this proposal.
- Do **not** mark ACCEPTED or RUNTIME VERIFIED.
- Do **not** silently swap the staged C6 XGrammar checkout.

## Promotion path (when operators choose)

1. Rebuild GenAI against candidate XGrammar with explicit `FETCHCONTENT_SOURCE_DIR_XGRAMMAR`.
2. Re-run matcher T-Q-ZERO and GenAI controls against the **installed** DLL cohort.
3. Close or consciously defer #650 with measured mask evidence.
4. Only then draft a lock revision PR that names the new XGrammar SHA and evidence paths.
