# Transition verdict vs AGENTIC-TRANSITIONS.md (2026-09-19, honest)

Rule applied: volume ("69 tool calls happened") is NOT a contract proof.
Each cell states its evidence layer (unit Layer-2 / live Layer-4 / none).

## Proven (with evidence pointers)

- A02 open reasoning -> tool: LIVE (G5/G6 5232-token gate, C2/C3/C4/C5 identical)
  + unit (ImplicitTransition* family exists only on mid-thought line, NOT in built
  trees — live is the proof here).
- A03 explicit close -> tool: LIVE (dogfood + gates use explicit closes throughout).
- C01 reasoning -> tool -> tool: LIVE (unicode probe: get_weather+get_weather, both paths).
- C02 tool -> content: LIVE + unit (PostToolContentSurvives; STOP-flush probe, no loss).
- D02 think -> tool -> think -> tool -> final: LIVE (c5fixed-agentloop T1/T2/T3,
  history replay, factually correct final).
- H01/H03 string->object->next-turn: LIVE (exact 2x2 4/4 on fixed binary).
- P02 (same as A02): LIVE.
- G03 unknown tool: LIVE fail-closed (HTTP400 INVALID_ARGUMENT, both paths).
- G06 negative args: LIVE fail-closed with parse position (4/4).

## Present in dogfood volume but NOT rated as contracts

- D01/D02 shapes occur throughout session 03 (81 steps/69 tools, text<->tool
  alternation healthy, 12 text-text transitions are final summaries).
- Prefix 1-3: 16K-context text answers, coherent, `stop`. Rated SANE as responses,
  NOT as transition contracts (no per-boundary delta audit).

## NOT proven (explicit gaps — do not stamp)

- A01 promise/prose -> real call: unit-adjacent (ThoughtPreamble, ContentAndSingleToolCall
  exist) but no dedicated live probe with a decoy promise. GAP.
- A04 reasoning -> content -> tool: NO dedicated case anywhere. GAP.
- C03 content -> tool -> content -> tool: partial (ThreeToolCallsWithContentInBetween
  at unit level); no live multi-alternation probe. GAP.
- C04 reasoning -> content -> tool -> content -> tool: NO case anywhere. GAP.
- D03 promise -> tool -> result -> answer -> tool: NO dedicated live run. GAP.
- D04 result -> immediate tool (no filler): NO dedicated live run. GAP.
- D07 tool -> reasoning -> answer -> tool: NO dedicated live run. GAP.
- B-series (chunk-split invariance) for the new transitions: NOT RUN live.
- F-series raw-token correlation: NOT captured live (usage only).

## Consequence for stamping

"ALL C5 GATES GREEN" is WITHDRAWN as a claim. Correct stamp:
"Listed gates green; transition matrix PARTIAL — 7 named gaps above."
Closing them = 7 focused live probes (A01/A04/C03/C04/D03/D04/D07) + B-split reruns,
estimated <1 hour on the live server. G2 pack stays as response-level evidence, not contracts.
