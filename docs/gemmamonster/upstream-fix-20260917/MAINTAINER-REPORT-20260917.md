# Gemma4 structured-output whitespace bound — live verification report

Date: 2026-09-17. Author: DassaultFalconKing (GEMMAMONSTER track).
Scope: does the bounded-whitespace repair fix the reported live degeneration
(streaming named `tool_choice` emitting whitespace to `max_tokens` instead of
a tool call) without any parser changes? Answer: **yes**, proven below.

## 1. Failing behavior (baseline, 2026-09-16)

Binary: stock `openvino.genai` base `fe818c04` (XGrammar `v0.1.31`), OVMS PR base.
Request: `POST /v3/chat/completions`, `temperature: 0.0`, `max_tokens: 512`,
tools `get_weather` / `search_docs` / `calculator`, named
`tool_choice: {"type":"function","function":{"name":"search_docs"}}`,
single user message ~5234 prompt tokens (long runbook context).

- unary (`stream: false`): `finish_reason: tool_calls`,
  `search_docs{"query":"dead-letter prefix handling"}`, 23 completion tokens.
- streaming (`stream: true`): ~100 tokens of newline/tab spam,
  `finish_reason: length`, zero `tool_calls`.

## 2. Repair under test (single axis, no parser changes)

- GenAI: `DassaultFalconKing/openvino.genai @ e00eada6`
  (`StructuredOutputConfig::JSONSchema` gains optional `max_whitespace_cnt`,
  serialized at schema-format level; XGrammar pinned to `9aa840b6`).
  Base: upstream `fe818c04`. C++ contract tests 4/4 PASS
  (`LegacySerializationDoesNotSetWhitespaceBound`,
  `BoundIsSerializedAtSchemaFormatLevel`, `ZeroBoundIsNotTreatedAsUnset`,
  `EqualityIncludesWhitespacePolicy`).
- OVMS: unmodified PR base `d582668` + whitespace call-site only
  (`JSONSchema(schema, 2)`); parser/validation untouched.
- Runtime: `--version` reports OpenVINO `2026.5.0-23084-4977f92a234`,
  GenAI `2026.5.0.0-3447-e00eada6f4c`.
  Fingerprints: `ovms.exe C96E7819…E333C2`,
  `openvino_genai.dll 92AB145C…F35AED`.

## 3. Live result (2026-09-17, fresh reboot, isolated caches)

Reconstructed fixture calibrated to prompt=5232 tokens (original paragraph text
was not archived; tools/choice/params/temperature identical; fixture request
SHA256 `117525BB…D70AA1`).

- unary: `finish_reason: tool_calls`,
  `search_docs{"query":"dead-letter prefix handling"}`, 22 completion tokens.
- streaming, 3/3 runs: `tool_calls` observed in-stream, `finish_reason:
  tool_calls`, zero whitespace-only chunks, 22–23 completion tokens.
- Server healthy throughout; no GPU errors; no OOM.

Raw evidence (request JSONs, unary JSON, 3× raw SSE) is retained alongside the
gate script in the program artifact store and available on request.

## 4. What this proves / does not prove

Proves: the bounded-whitespace repair alone converts the reported live
degeneration into correct streaming tool calls; parser hardening is not
required for this symptom.
Does not prove: upstream-master compatibility (separate C4 experiment with the
20-commit `fe818c04..438e061` delta is queued), XGrammar-main compatibility
(queued C5), or performance deltas (not measured; not claimed).

## 5. Next

Replay of the same contract + implementation on GenAI master `438e061`
(C4), then XGrammar `f6043f4` (C5), then a retained-delta ledger and clean
reviewer-facing series (C6) as the basis for the upstream PR(s).
