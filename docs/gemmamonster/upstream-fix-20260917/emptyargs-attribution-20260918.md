# Empty required args (`calculator{}`) — attribution report

Date: 2026-09-18. Candidate: C5 (OVMS `a671ddf9f` + GenAI `15e8f897`/XGrammar `f6043f4`).
Status: ATTRIBUTED — guided-enforcement path implicated (step D); parser, schema
ingestion, and XGrammar semantics EXONERATED (steps A/B/C).
Parser left untouched per instruction (`{}` is syntactically valid JSON).

## Probe matrix (live, C5, `tool_choice=auto`, guided generation on)

| # | prompt | temp | result |
|---|--------|------|--------|
| 1 | "What is 17*23? Use the calculator tool." | 0.1 | `calculator{}`, 9 tok |
| 2 | same + thinking | 0.1 | reasoning 98ch + `calculator{}`, 40 tok |
| 3 | canonical "Calculate 17 * 23 using calculator." | 0.0 | `calculator{"expression":"17 * 23"}`, 22 tok |
| 4 | canonical 2x2 repeat | 0.0 / 0.1 / 0.0 / 0.1 | filled, {}, {}, {} |

Run-to-run variance on IDENTICAL input (rows 3 vs 4a, both temp 0.0) rules out
temperature as the determinant. The filled call in row 3 proves the parser and
serialization path deliver non-empty args faithfully when the envelope has them.

## Attribution ladder (final)

- A. Parser: EXONERATED. Filled envelope -> filled API (live row 3); empty envelope ->
  empty API pinned by `StreamingWithToolCallWithEmptyParams` (GREEN).
- B. Schema ingestion: EXONERATED. New `NamedToolSchemaPreservesRequiredFields`
  (GREEN): `required:["expression"]` reaches the rendered `JSONSchema` verbatim.
- C. XGrammar compiler semantics: EXONERATED. Offline matcher probe against XGrammar
  `f6043f4` with the EXACT C5 wire (`json_schema` + `max_whitespace_cnt: 2`):
  `<|tool_call>call:calculator{}<tool_call|>` -> REJECT;
  filled -> ACCEPT; present-but-empty-string -> ACCEPT.
  Probe: `C:\Users\testc\AppData\Local\Temp\opencode\xgprobe.cpp` (3/3 PASS).
- D. GenAI mask activation/application: IMPLICATED. Same canonical prompt, temp 0.0:
  guided OFF -> 4/4 filled `{"expression":"17 * 23"}`, deterministic;
  guided ON -> 1 filled / 3 empty across runs (plus 0.1/0.7/1.0 runs mostly empty).
  The grammar forbids `{}` (step C) yet ON intermittently emits it.
- E. Model native propensity: CLEARED as primary cause. With no enforcement the model
  fills correctly every time; "model decided to leave args empty" is REJECTED as the
  explanation for the ON-state `{}`.

Verdict: the `{}` escapes through the guided-generation enforcement path (mask
activation/application in GenAI structural-tag flow), not through the model, the
grammar, the schema ingestion, or the parser. Next probe if pursued: XGrammar
`fill_next_token_bitmask` trace at the `}` position under the live guided session.

## Gap (honest)

Pre-parser raw Gemma token text is not observable: DEBUG server log (257 lines,
`server-debug.log` in C5 artifacts) contains no per-request generation dump, only
graph/config lines. Attribution rests on the differential matrix + two pinned legs,
not on a captured raw envelope.

## Evidence

- `C5-frankenstein-newxgrammar/emptyargs-probe-request.json` (canonical, temp 0.0)
- `emptyargs-probe-response.json` (filled call), `thinking-tools-probe.json`
- `server-debug.log` (+`.err`), `emptyargs-cover.log` (new test GREEN)
- Coverage branch: `test/gemma4-emptyargs-coverage-20260918` (1 test added, no prod change)

## Recommendation

Keep parser untouched. If this is pursued: next probe is guided-generation OFF
vs ON on the same prompt (isolates grammar enforcement from sampling), then
XGrammar mask inspection for the empty-object path.
