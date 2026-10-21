# XGrammar #650 end-marker note (OPEN)

Status: **OPEN. NOT FIXED by #802 candidate. LOCK UNCHANGED.**  
Recorded: 2026-10-21  
Upstream: [#650](https://github.com/mlc-ai/xgrammar/issues/650), proposed fix [PR #651](https://github.com/mlc-ai/xgrammar/pull/651) (unmerged as of this note).

## Defect

After the excluded close prefix `</parameter`, the Qwen XML string path can still accept a continuation that yields a malformed end marker such as `</parameter1>`. Taxonomy ID: **Q-END** in `WHITESPACE-DEFECT-TAXONOMY.md`.

This is a **decoder-mask / TagDispatch** defect. Parser rejection of malformed XML is a safety net only; it does not prove constrained decoding prevents the bad close.

## Measured relation to #802

- Native #802 candidate (`b288dca…` tip of `fix/qwenmonster-xml-empty-object-20261021`) closes the zero-argument whitespace loop (Q-ZERO).
- The same native harness and prior RESULTS inventory still record malformed-close acceptance as an incomplete prefix under **both** baseline and candidate libraries.
- #802 does not backport #651 and must not be treated as a substitute.

## What would close this gate

1. Compatible #651 (or equivalent) backport on a dedicated XGrammar branch.
2. RED→GREEN mask evidence: at every prefix of `</parameter>`, invalid continuations (notably `1` → `</parameter1>`) are disallowed by the actual tokenizer mask.
3. Separate parser fixtures remain required but are insufficient alone (`MALFORMED-ENVELOPE-RED.txt` / partition corpus).

## Explicit non-actions now

- No #651 backport attempted in this session.
- No lock or staged runtime change for #650.
- Live acceptance may proceed with #650 recorded as **known OPEN residual**, provided operators do not claim end-marker grammar repair.
