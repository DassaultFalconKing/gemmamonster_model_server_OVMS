# RLC — Reasoning Lossless Contract

Stage: DESIGN / SOURCE-BASED CANDIDATES; live/test status **NOT_RUN** on this documentation branch.
Owner seam: `src/llm/ovms_text_streamer.cpp`, `src/llm/io_processing/output_parser.cpp`, family `reasoning_parser.*`.

## Invariants

**RLC-INV-01 / decoded-body identity.** After excluding **only** proven native framing (opener, closer, recognized header), the concatenation of emitted `ReasoningDelta.text` is byte-identical to the reference **decoded** body. Do not `trim`, `unescape`, `JSON.parse`, normalize Unicode, whitespace, number spelling, quotes or backslashes. A string `9007199254740993`, `1.10` or `C:\\tmp\\x` remains textual; no type is inferred.

**RLC-INV-02 / phase ownership.** A tool-looking body span remains private reasoning unless the **family's canonical format** defines a legal handoff; Qwen requires its thought closing boundary, Gemma4 supports a specific native handoff. Repeated or partial markers must not create extra channels.

**RLC-INV-03 / partition invariance.** Processing the same decoded generation as one chunk, one-character chunks, all splits around delimiters and tokenized streamer chunks yields equivalent concatenated `reasoning/content/tool` output and call eligibility. Compare complete results, not individual delta sizes.

**RLC-INV-04 / lifecycle.** On STOP, LENGTH, cancellation/error, preserve only actually generated text; never synthesize a semantic closer or a tool call. Retain incomplete delimiter candidates until disambiguation or terminal resolution using a documented policy. No stale parser state between requests/choices.

**RLC-INV-05 / bounded retention.** A streaming reasoning retainer buffers only candidate native delimiters and incomplete header prefix plus necessary tokenizer delay state. No full-context buffering for 262K-token reasoning.

**RLC-INV-06 / evidence definition.** Reference is the chosen pinned tokenizer decoding of exact generated token IDs with explicitly recorded `skip_special_tokens` behavior and framing classification. Decoded-byte losslessness is **not** the same as recovering the original token IDs or original encoding of model text.

## Audited code candidates (not yet runtime-proven)

| ID | Source | Static observation and proposed RED |
| --- | --- | --- |
| RLC-Q3-01 | `qwen3/reasoning_parser.cpp` | First-entry `find(startTag)` plus `substr` can discard preceding text for an adversarial parser chunk such as `prefix<think>inside`. Verify phase ownership and canonical entry, not merely substr in isolation. |
| RLC-G4-01 | `gemma4/gemma4_reasoning_parser.cpp` | First-line single-word heuristic can treat `15400-PLM-A02\nCheck exact part` as a header and erase a real reasoning line when the header is already consumed. But malformed-header recovery tests intentionally discard lines. Test both cases separately. |
| RLC-GPT-01 | `gptoss/reasoning_parser.cpp` | `lastState` governs publication after the state update. An opener + body in one chunk risks losing the first body span. Confirm via router+parser test. |
| RLC-STREAM-01 | `ovms_text_streamer.cpp`, `output_parser.cpp` | Decode-mode switches, held suffixes, combined closer + next phase and terminal drains require partition-invariant checks, including UTF-8. |
| RLC-ONX-01 | `onyx/onyx_reasoning_parser.cpp` | Header accumulation until `<|message|>` and `rfind` of ending marker require marker-inside-body and arbitrary-split control. |
| RLC-MINI-LFM-01 | `minicpm5/*`, `lfm2/lfm25_reasoning_parser.hpp` | Both reuse Qwen3 reasoning parsing, but token ID/special-token configuration differs. Test separately before claiming inherited PASS. |

Existing tests already cover important cases: `qwen3_output_parser_test.cpp` implicit reasoning + split closer; `gemma4_output_parser_test.cpp` degenerate headers, repeated closer, handoffs and split partitions. **Do not change expected outputs merely to satisfy new assertions**. Classify each legacy recovery as KEEP, REFINE or incompatible with strict preservation.

## Allowed changes and design

Prefer a **bounded raw-span / marker holdback** in the existing phase router over cloning the tool retainer. Keep exact decoded body spans, defer ambiguous delimiter suffixes, consume only verified native structural framing and emit untouched body spans.

Token-ID recognition for **registered native special markers** is preferable when reliable; literal text that only resembles a marker must not silently acquire protocol authority. For ordinary-text delimiters, document ambiguity and protocol-specific handling.

Gemma4: retain its own legal thought→tool handoff, including legal tool-before-reasoning-closer. A generic Qwen-like mandatory `</think>` is forbidden.

## Acceptance

- Full literal corpus and marker negative controls under explicit/implicit start.
- Exactly equivalent reconstructed unary / SSE content where supported; no duplicate, missing or reclassified spans.
- `STOP`, `LENGTH`, cancellation and reset lifecycle cases, all relevant family controls.
- Preserve family-specific already-accepted behavior except where a recorded RED and operator-approved semantic change justify it.
- New source patch plus actual build/test logs; source inspection never earns GREEN.
