# RLC / TLP-H incremental test packets

All cases below are **SPECIFIED / NOT_RUN** on this documentation-only branch, unless an independent test receipt is linked with exact source SHA. Illustrative fixture inputs are synthetic. A model's decision to generate a given string is NOT an invariant of the retainer.

## Permanent regression corpus

Use these as literal **text**, not parsed numeric inputs:

~~~text
1HGCM82633A004352
15400-PLM-A02
0000015400
1.10
1e3
9007199254740993
-0
C:\tmp\foo
C:\\tmp\\foo
\\t
#B4E8
a"b 'quoted' = comma, [array] {brace}
Unicode: München / Київ / 漢字 / 😀
~~~

For tool tests: document whether each field is schema-declared `string`, `number`, `integer`, `object`, `array`, `boolean` or absent/unknown. Hashes, VIN and part numbers are `string` irrespective of their contents.

## Pack R0: baseline proof, no code patch

| ID | Focus | Expected / method |
| --- | --- | --- |
| RLC-R0-01 | Qwen explicit/implicit `<think>` and literal `<think>` embedded in body | Body bytes preserved under documented native framing rules; distinguish synthetic literal marker vs native special-token marker. |
| RLC-R0-02 | Gemma channel header `thought\n` vs `15400-PLM-A02\n...` vs degenerate `works\n` | Characterize header ownership and legacy recovery; **do not assume** the ambiguous examples can be resolved without native metadata. |
| RLC-R0-03 | GPT-OSS opener+body in one chunk vs opener alone then body | Same reconstructed reasoning if structurally equivalent; record baseline RED or counterevidence. |
| RLC-R0-04 | Qwen tool markup printed *inside reasoning* | No executable tool call; body retained. |

## Pack R1: each-family incremental reasoning tests

| ID | Focus | Expected / method |
| --- | --- | --- |
| RLC-R1-01 | Every split of a complete `opener + body + closer + content` string | Same `reasoning`, `content` and tool-call list as one-chunk reference. |
| RLC-R1-02 | Every split of close-tag suffix and incomplete closing marker | No leaked partial marker while undecided; terminal treatment documented. |
| RLC-R1-03 | Literal corpus inside body, including newline, leading/trailing spaces, Unicode | Exact decoded bytes after allowed framing removal. |
| RLC-R1-04 | Gemma legal reasoning→tool handoff, then renewed reasoning, content | Correct family-specific ownership without invented closer or duplicated text. |
| RLC-R1-05 | STOP vs LENGTH vs cancel with open thought; two requests reused parser | No fabricated closure, duplicate body or stale state. |
| RLC-R1-06 | `OVMSTextStreamer` tokenized decode with and without special tokens | Compare against same tokenizer/reference flags; avoid byte-vs-token category errors. |

## Pack T0: Qwen/Ornith reference freeze

| ID | Focus | Expected / method |
| --- | --- | --- |
| TLP-T0-01 | typed string IDs, paths, slashes and quote pairs | Correct literal JSON encoding **once**. |
| TLP-T0-02 | `1.10`, `1e3`, long integers inside nested JSON | Lexical value preservation and typed validation; compare **JSON argument text** before client reserialization. |
| TLP-T0-03 | Missing end, malformed JSON, unknown function, required field absent | No executable published call/name/ID; no default value invention. |
| TLP-T0-04 | Two adjacent tools, same name repeated, STOP/LENGTH | Stable independent IDs/index and exact argument bytes; no false recovery. |

## Pack T1: next family-by-family hardening

| ID | Focus | Expected / method |
| --- | --- | --- |
| TLP-T1-01 | Native literal delimiters vs real JSON-quoted strings | Distinct documented semantics, no blanket unescape. |
| TLP-T1-02 | Nested array/object numeric spelling, boolean/null and wrong typed values | Exact valid text or explicit invalidity; no silent coercion. |
| TLP-T1-03 | Every delimiter/parameter split and split inside UTF-8 sequence | Partition-invariant rebuilt tool arguments, no duplicate/missing text. |
| TLP-T1-04 | Tool-looking text in reasoning and comment/content; Gemma handoff exception | Non-executable drafts; only documented family-native handoff can publish. |
| TLP-T1-05 | Schema profile, unknown keyword, long payload, repeated request/choice | Fail closed where required, bounded retention, no cross-request carryover. |

## Pack I: integration (after unit gates)

- RLC-I-01: full decoded emission vs `reasoning_content` + `content` + exact tool extraction with provenance of removed structural markers.
- TLP-I-01: unary versus reconstructed SSE tool `function.arguments` **byte equality** (no test-client JSON reserialization) and correct IDs/indices.
- MIX-I-01: two/three thought→tool→result→thought transitions and reset; Qwen vs Gemma negative controls.
- LIVE-I-01: tagged runtime tuple (model, tokenizer, template, SDK/DLL, OVMS commit, binary, API route, OS/device) and actual output/exit status. Only when runtime is available and operator authorizes running models.

## PR / commit packet rule

Each implementation packet is small and self-contained:

1. One reproducer (RED when observed), one negative control, at least one unchanged regression.
2. Code change scoped to one family or shared seam; no speculative broad refactor.
3. Update this matrix row with `SPECIFIED → RED_OBSERVED → FIXED_UNIT_GREEN → INTEGRATION_GREEN → LIVE_GREEN`, or `NOT_REPRODUCED` / `BLOCKED`.
4. Evidence pointer: exact SHA, command, exit code, test count, OS, runtime binary/toolchain/SDK, fixture provenance and raw output for any claimed GREEN.
5. Merge only against authorized target branch after its own gates; test-only commits and documentation may be cherry-picked separately.

No synthetic fixture can be called LIVE. No passing unit test can be called agentic acceptance.
