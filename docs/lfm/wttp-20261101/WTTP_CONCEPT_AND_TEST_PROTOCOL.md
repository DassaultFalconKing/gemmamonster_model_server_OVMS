# WTTP: Weighted Token-Path Tool Recognition

**Status:** experimental research harness; not an OVMS implementation, not a tool executor.  
**Target:** GEMMAMONSTER / OVMS, initially LFM2 and LFM2.5 tool calling with variable marker tokenization; the same recognition layer can be tested against LFM3 and other model profiles.  
**Date:** 2026-11-01.  
**Design principle:** evidence of a tool marker is not authority to execute a tool.

## 1. Problem statement and non-goals

Some models may emit the *same visible control marker* in different token-ID forms:

- `DEDICATED_ID`: one vocabulary token whose decoded text is `<|tool_call_start|>`;
- `COMPOSITE_TEXT`: multiple ordinary vocabulary tokens whose **joint decode** is the same string;
- `MIXED_ENVELOPE`: start delimiter uses one route and end delimiter uses the other.

The receiver must not require the operator to choose one route up front. A model-family hint may affect the **priority** among matching protocol hypotheses but cannot suppress other structurally plausible hypotheses. Two variants of LFM sharing identical delimiter text (LFM2/2.5) cannot be distinguished from that delimiter alone.

WTTP recognizes these representations and emits *candidate observations*. It does **not** infer hidden model intent from vectors, replace per-family argument parsers, rewrite output to repair a broken tool call, run an LLM classifier, modify XGrammar, or execute tools.

## 2. Boundary with Retainer and OutputParser

```
synthetic token IDs + exact incremental decoder
  -> token-ID scanner / text-prefix scanner (simultaneous)
  -> candidate delimiter + token-ID provenance + protocol hypotheses
  -> phase resolver (future OVMS integration; harness simplifies to CONTENT/TOOL)
  -> protocol-specific syntax *probe* (research-only)
  -> EXISTING RETAINER (future runtime)  <-- owns exact literal parsing and transaction
  -> schema + registered-tool validation
  -> API deltas (future runtime)
```

A single component should own undecided prefix bytes. The production `Lfm2ToolParser::parseRetainedChunk()` currently holds prefix text and buffers a whole LFM native list; an eventual refactor should move **only prefix recognition** out. Retainer still owns quote-aware envelope parsing, valid literal conversion, schema validation, atomic publication, and limits. Do not add a second independent public deltas buffer on top of it.

The **research harness intentionally does not invoke the real C++ Retainer**. Its `python_call_shape()` accepts a restricted Python AST to assert that a candidate *looks like* a registered function call. AST is **never evaluated**, numeric values are not serialized, and the raw candidate text is preserved. Production validation must remain in the real Retainer.

## 3. Evidence, weights and decision stages

The following are **not independent votes**: the raw ID observation and its decoded text are two representations of the *same underlying token stream*. Do not add their scores as though the model supplied two pieces of independent evidence.

| Signal | Interpretation | In prototype |
|---|---|---|
| `dedicated_id` | Exact vocabulary ID matched a configured marker | Recognized; strong structural evidence |
| `composite_text` | Incrementally decoded characters formed the configured marker | Recognized; provenance retained |
| `prefix_progress` | Portion of known marker observed | `matched_chars`, `progress_fraction` (not a probability) |
| `family_preference` | Model name suggests one protocol | Tie-break only; never a filter |
| `syntax_valid` | Bounded, read-only shape probe accepted tool name/arguments | Never sufficient for execution |
| `publication_eligible` | Candidate could **in principle** be sent for Retainer validation under current demo policy | No API publication and no execution |

Prototype phases: `CONTENT -> PREFIX_PROGRESS (not committed) -> ARMED -> TOOL_CANDIDATE -> [Retainer outside harness]`. For malformed or incomplete input the harness emits `syntax_valid=false` or `INCOMPLETE`, never a valid published call.

**Default policy:** candidates whose *both* delimiters were dedicated IDs can be marked eligible for downstream Retainer validation. A composite delimiter remains *shadow-only*, because a pasted example of a tool call may decode identically. `--allow-composite` allows the **test output** to mark such candidates eligible, but still does not execute or publish anything. Never turn this diagnostic flag into an unguarded runtime default.

## 4. Tokenizer-derived fixture generation

The program needs only the tokenizer, not the weights:

1. Read local Hugging Face `tokenizer.json`, or download only that file with optional `huggingface_hub`.
2. Hash original file (SHA-256); store in fixture; replay refuses changed tokenizer.
3. Read both `model.vocab` and `added_tokens`, including dedicated markers whose `special=false`.
4. Find each marker as a **single decoded token ID**, if available.
5. Search base-vocabulary pieces for **alternative composite token-ID sequences** decoding to exactly the same marker. Exclude the dedicated ID from that search.
6. Encode **synthetic**, configurable body text and build cross-product: dedicated/dedicated, dedicated/composite, composite/dedicated, composite/composite.
7. Replay the real IDs through incremental decoding and record marker provenance, prefix progress, candidate shape and policy flag.
8. Store missing alternatives in `skipped`, never invent token IDs or claim a nonexistent path is available.

The optional `tokenizers` library is strongly recommended for real model files: `Tokenizer.decode` performs the *real decoder algorithm* (ByteLevel, Metaspace, etc.). A limited stdlib ASCII fallback exists for the included miniature tokenizer and common ASCII decoder subsets. If a decoder's behavior is unsupported or non-prefix-stable, the harness **skips/refuses** rather than asserting false equivalence. `decode([id])` is **not generally additive** over an arbitrary tokenizer; only verified joint decode proves a valid composite path.

These fixtures prove **representability by the tokenizer**, not that the model would sample those IDs, not that XGrammar permits them, and not that a real server emits them correctly.

## 5. Supported scope in v0

- Delimiter families: Pythonic envelope LFM2/2.5 and XML-like LFM3; a family hint changes precedence, not the set of candidates.
- Supported mixed start/end marker provenance; incremental one-token feed and decoded-text prefix buffering; `special=false` retained.
- A read-only Pythonic tool-call AST shape probe: list of calls, registered simple function names, keyword args with literal values, no runtime evaluation.
- A **deliberately narrow** XML-like LFM3 shape probe (one or more `<function=name>` elements and simple string-valued `<parameter=name>` elements). This is **not a complete LFM3 parser** and must not be used to certify the model's true protocol.
- No reasoning phase parser, no schema validation, no tool executor, no live SSE API, no per-request tokenizer cache, no CPU/GPU performance measurement, no recovery from context-dependent non-prefix-stable incremental decoding.
- No support for arbitrary nested XML, JSON schema inside tools, speculative execution, raw model outputs or OpenVINO IR tokenizer without `tokenizer.json`.

## 6. How to run

Run from the folder containing the script:

```powershell
# Standard library alone is enough for the miniature fixture.
python -m unittest -v test_wttp_token_fixture.py

# Use the shipped miniature tokenizer (a TEST ONLY synthetic vocabulary):
python .\wttp_token_fixture.py generate .\synthetic_tokenizer.json --family lfm25 -o .\synthetic_token_streams.json
python .\wttp_token_fixture.py replay .\synthetic_token_streams.json -o .\synthetic_replay_results.json

# Optional, real tokenizer from Hugging Face; fetches ONLY tokenizer.json:
python -m pip install -U huggingface_hub tokenizers
python .\wttp_token_fixture.py generate LiquidAI/LFM2.5-8B-A1B --family lfm25 -o .\lfm25.json
python .\wttp_token_fixture.py replay .\lfm25.json -o .\lfm25_replay.json

# Or point to an already downloaded local tokenizer:
python .\wttp_token_fixture.py generate "C:\\models\\LFM2.5-8B-A1B\\tokenizer.json" --family lfm25 -o .\lfm25.json
python .\wttp_token_fixture.py replay .\lfm25.json --tokenizer "C:\\models\\LFM2.5-8B-A1B\\tokenizer.json"
```

To **test-only** mark valid composite delimiter candidates eligible for a hypothetical Retainer, add `--allow-composite` to replay. This does not execute tools.

## 7. Executable acceptance matrix (next gate)

| Case | Expected |
|---|---|
| dedicated opener + dedicated closer | Valid candidate; eligible for Retainer check |
| composite opener + composite closer | Valid candidate; shadow by default |
| dedicated/composite and composite/dedicated | Both parse; shadow by default |
| `special=false` but dedicated vocabulary ID | Recognized as dedicated ID (not confused with HF special flag) |
| family says LFM2, actual markers XML LFM3 | XML remains a candidate; family preference does not forbid it |
| LFM2 and LFM2.5 identical opener | Multiple hypotheses preserved; hint breaks tie |
| closing marker within quoted argument | Remains argument text, not boundary |
| unfinished marker or tool envelope at finish | Never becomes published tool |
| malformed/unknown tool/unsafe Python AST | `syntax_valid=false` |
| tokenizer SHA mismatch | Replay fails |
| composite tool call quoted in documentation | May be identified as candidate, but **shadow-only** by default |
| tokenizer lacks full or composite path | Fixture absent and reason recorded, not fabricated |

There are 12 local `unittest` cases and 12 generated token-ID scenarios using the **included artificial tokenizer**, as of the initial prototype. Do not present these as performance benchmarks or live LFM results.

## 8. What existing implementations teach us

- [vLLM StreamingParserEngine](https://docs.vllm.ai/en/latest/api/vllm/parser/engine/): token-ID scan, incremental lexer, per-protocol transitions. The token-ID-vs-text policy is stricter than this proposal for declared ID terminals. Use the mechanics, do not silently inherit the policy.
- [vLLM engine tests](https://github.com/vllm-project/vllm/tree/main/tests/parser/engine): `test_token_id_scanner.py`, incremental/state and replay test patterns. These are **references**, not a universal cross-family tokenizer corpus.
- [XGrammar structural tags](https://xgrammar.mlc.ai/docs/latest/structural_tag/structural_tag.html): the distinction between string triggered tags and token-triggered tags; useful for testing *generation constraints* but is not the receiver-side recognizer.
- [XGrammar token markers](https://xgrammar.mlc.ai/docs/latest/structural_tag/tool_calling_and_reasoning.html): string markers may be generated from ordinary subtokens; `token_markers=True` requires dedicated markers.
- [llama.cpp PEG parsing](https://github.com/ggml-org/llama.cpp/blob/master/docs/development/parsing.md): incremental AST-oriented parsing of model output, including Pythonic tool-call syntax.
- GEMMAMONSTER `src/llm/io_processing/lfm2/lfm2_tool_parser.cpp` and `python_literal.hpp` in branch `review/lfm25-design-c-semantic-refit-20261027`: transactional Retainer and literal handling **stay authoritative**.

## 9. Critical research questions, not proven root cause

1. Does OpenVINO's tokenizer decoder preserve identical incremental text for real LFM2.5 dedicated and composite marker paths? Test token IDs, not just string equality.
2. Does XGrammar constrained decoding allow the composite path? What happens with ID terminal vs string terminal? Test generated token masks separately.
3. For each real model and tokenizer SHA, does the model **actually emit** the alternate path? Only inference can answer this.
4. Are ambiguous quoted examples distinguishable by independent protocol boundaries? If not, do not auto-execute composite candidates.
5. Do mixed markers break `OutputParser` phase ownership or cause duplicate/lost SSE content? Test live Windows Arc 140V after a separate C++ implementation.

**Do not modify or merge production parsers based solely on these synthetic fixtures.** They test the WTTP idea and tokenizer representability, not the asserted cause of any real-world LFM bug.
