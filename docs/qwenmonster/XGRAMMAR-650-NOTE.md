# XGrammar #650 end-marker note (source port measured, gate OPEN)

Status: **SOURCE PORT COMPILED. STRING AND SYNTHETIC-MASK CHECKS PASS. ACTUAL-TOKENIZER MASK AND LIVE NOT RUN. LOCK UNCHANGED. ACCEPTED: NO.**  
Recorded: 2026-10-22  
Upstream: [#650](https://github.com/mlc-ai/xgrammar/issues/650), proposed fix [PR #651](https://github.com/mlc-ai/xgrammar/pull/651) (unmerged; the fork carries an equivalent on its own Aho-Corasick builder).

## Defect

After the excluded close prefix `</parameter`, the Qwen XML string path can still accept a continuation that yields a malformed end marker such as `</parameter1>`. Taxonomy ID: **Q-END** in `WHITESPACE-DEFECT-TAXONOMY.md`.

This is a **decoder-mask / TagDispatch** defect. Parser rejection of malformed XML is a safety net only; it does not prove constrained decoding prevents the bad close.

## Measured relation to #802

- Native #802 candidate (`b288dca…` tip of `fix/qwenmonster-xml-empty-object-20261021`) closes the zero-argument whitespace loop (Q-ZERO).
- Before `5b0b708`, that same native harness and the prior RESULTS inventory recorded malformed-close acceptance under both the baseline library and the #802 candidate.
- #802 does not backport #651 and must not be treated as a substitute. The later `5b0b708` port is a separate change.

## What is now measured

The dedicated fork branch `fix/qwenmonster-xml-end-marker-lock-20261022` at `5b0b7084a65a2059b44c03fbc6320ad7fcc41f33` adds `lock_excluded_prefixes` and sets it on the XML `xml_string` rule. GenAI `8f305a1c1bc11e348c8ad0cc37269a91ba21cc74` fetches that revision. An isolated candidate DLL contains the string `lock_excluded_prefixes`; the staged DLL does not. The public lock and the staged runtime were not changed.

The native matcher linked to that candidate static library reported 43/43 PASS and `SUMMARY failures=0`:

- well-formed `</parameter>`, HTML `<div>`, shorter `</p>`, and a comparison expression are accepted
- `</parameter1>`, `</parameter_function>`, `</parameterX>`, and `</parameter/>` are rejected
- on a synthetic byte vocabulary, after the consumed prefix `</parameter`, bytes `1`, `X`, and `_` are masked off
- the previous #802 epsilon, declared-required, and Qwen3-8B unit-tokenizer whitespace results still pass (425 whitespace tokens, 0 allowed, hard and lazy)

Undeclared-required `{type:object, required:[a]}` still accepts empty XML. That residual is unchanged.

## What would close this gate

1. Compatible #651 (or equivalent) backport on a dedicated XGrammar branch. **Done** at `5b0b708`.
2. RED→GREEN mask evidence on the actual Qwen tokenizer: at every prefix of `</parameter>`, invalid continuations (notably `1` → `</parameter1>`) are disallowed. **Not measured.** The passing mask above is the synthetic byte vocabulary.
3. Separate parser fixtures remain required but are insufficient alone (`MALFORMED-ENVELOPE-RED.txt` / partition corpus).
4. A live probe that loads the candidate DLL, not the staged runtime.

## Explicit non-actions

- No public-lock edit and no staged-runtime swap.
- Do not treat the synthetic mask or the string accept/reject result as live acceptance.
