# TLP-H — Tool Literal Preservation Hardening

Stage: DOCUMENTATION / INCREMENTAL FAMILY ROLLOUT. New implementation on this branch: **NONE**.
Normative: [MFP-1 A3.1](../qwenmonster/OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md); sibling: [RLC.md](RLC.md).

## Purpose and boundary

TLP-H is the hardening and consistent **test enforcement** of the existing native tool parser-retainer, not a second tool parser. It makes published tool argument values provably faithful to the model-native body while preserving family-specific wire semantics.

The parser can promise `model-emitted identifier == published identifier` if the model emitted a valid registered call. It **cannot** promise `reasoning VIN == later tool VIN` or `part number fits vehicle`; those require explicit cross-span semantic verification or evidence-bearing tools, not ungrounded parser repair.

## Mandatory invariants

**TLP-INV-01 strings:** native literal strings are encoded into JSON **once**; backslashes are not globally unescaped. Keep `C:\tmp\foo`, `C:\\tmp\\foo`, `15400-PLM-A02`, `1HGCM82633A004352`, `#B4E8`, zero-prefixed IDs, `\\t` as two characters, embedded quotes and Unicode. Explicit ordinary JSON strings obey JSON escape syntax; do not confuse these with native literal delimiters.

**TLP-INV-02 numbers:** avoid numeric DOM re-serialization. Preserve lexical forms `1.10`, `1e3`, `-0`, `9007199254740993` and nested numeric lexemes when valid under the chosen supported schema profile. Keep separate validation and raw-payload paths; `RawValue(kNumberType)` may be needed for exact writers. No claim of arbitrary-precision numeric **comparison** from a RapidJSON DOM validator.

**TLP-INV-03 typed & nested:** validate declared string/integer/number/boolean/object/array/null against supported profile and reject invalid typed values, duplicate invalid parameters, over-limit nested/deep payloads, unsupported mandatory schema constraints; never degrade malformed typed data to string.

**TLP-INV-04 publication:** published identity/name/index/arguments must represent a **completed, registered, schema-eligible** tool call; no invented function, missing field or default, and no partial argument stream requiring later retraction. One call gets one identity; successive calls preserve order and indices. A family may require additional closure conditions before eligibility.

**TLP-INV-05 terminals:** a STOP recovery may tolerate only a family-documented outer transport delimiter after complete inner semantics. Incomplete parameter or payload on STOP/LENGTH/cancel is **not** executable. No unconstrained XML/JSON repair.

**TLP-INV-06 ownership & lifecycle:** native reasoning markers (and partial tool-looking drafts in reasoning) are not executable tool calls. Per-request/per-choice reset, finish handling, unary vs reconstructed SSE parity and bounded buffers are mandatory.

## Family baseline and rollout gates

| Family | Existing evidence from the 2026-10-23 handoff | TLP-H action |
| --- | --- | --- |
| Qwen3Coder / Qwen3.6 / Ornith selector | Recorded lossless change commit `5af105a04904713b58b13bbd82a421c6f15844fa`; focused `*VariousArgumentTypes*` 34/34, `*Qwen3Coder*` 81/81 (overlap); builds recorded. **No live model/API acceptance**. | PIN existing test receipt; verify current checkout actually carries equivalent semantics; add negative/partition regression, do not rewrite working Qwen parser blindly. |
| Gemma4 | Native `<|\"|>` string handling and raw numeric serialization exist. Its registry-aware path checks name/native structure, but does not use Qwen's full-argument schema validation. | Separate gap for schema/publication evidence; retain special reasoning→tool handoff and C5/C6 accepted behavior. |
| Hermes, Llama, Phi, Devstral | MFP-1 identifies potential DOM round-trips; no cross-family lossless acceptance yet. | Characterize each parser and its native template first; RED tests and one-family incremental port only if evidenced. |
| Onyx, MiniCPM5 | Existing parsers and fixtures, no new cross-family retainer gate. | Inspect active typed-argument conversions; avoid blanket replacement of protocol formats. |
| MiniCPM-V4.7 | MFP-1 program describes a prospective native retainer, execution blocked. | Do not conflate MiniCPM5 attribute-style wire and v4.7 Qwen-like wire. No PASS before real model/SDK evidence. |

Reference: [Qwen3Coder lossless handoff](../qwenmonster/QWEN3CODER-LOSSLESS-TESTING-HANDOFF.md) for tests, exact previous artifacts and **NOT RUN** gates. Success on that checkout cannot be relabelled PASS on a new revision.

## Implementation slices (one family at a time)

1. **TLP-H0 inventory:** pin source SHA, tool schema, native template render and tokenizer special-token IDs; capture raw generation fixture and expected exact JSON argument text. Classify supported schema keywords and unsupported hard modes.
2. **TLP-H1 RED:** add a failing precision/escaping/typed rejection or streaming case; include a negative control and at least one unchanged good fixture. Explicitly label synthetic vs observed live.
3. **TLP-H2 minimal fix:** preserve string bytes and raw number text without changing public schema or global stream policy. No unrequested type coercion.
4. **TLP-H3 atomic publication:** delayed public call identity until completeness and registry validation; audit STOP vs LENGTH and multiple calls.
5. **TLP-H4 integration:** unary vs SSE reconstructed `arguments` exact string equality; tool-result replay; mixed thoughts; regression suite; model live evidence if possible and authorized.

Tests are **not** postponed until TLP-H4: every H1–H3 patch lands with the two-to-five relevant focused cases plus existing controls and updates to [STATE.md](STATE.md) / [TEST-MATRIX.md](TEST-MATRIX.md).

## Explicit exclusions

- No VIN decoding, car-part fitment, filesystem truth verification or automatic matching of identifiers in reasoning versus tool calls. Model semantic correctness is a separate concern.
- No copying `normalizeJsonLosslessly` into the reasoning parser.
- No forced cross-family parser inheritance, generic grammar replacement or changes to production runtimes as a side effect of documentation.
- No claim of green unit, server, streaming, acceptance or supported schema keyword without executed evidence and pinned binary provenance.
