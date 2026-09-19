# Transition verdict vs AGENTIC-TRANSITIONS.md (2026-09-19, honest)

Rule applied: volume ("69 tool calls happened") is NOT a contract proof.
Each cell states its evidence layer (unit Layer-2 / live Layer-4 / none).

## Proven (with evidence pointers)

- A02 open reasoning -> tool: LIVE (G5/G6 5232-token gate, C2/C3/C4/C5 identical)
  + unit (ImplicitTransition* family exists only on mid-thought line, NOT in built
  trees — live is the proof here).
- A03 explicit close -> tool: LIVE (dogfood + gates use explicit closes throughout).
- A04 reasoning -> content -> tool: LIVE (focused probe 2026-09-19).
- C01 reasoning -> tool -> tool: LIVE (unicode probe: get_weather+get_weather, both paths).
- C02 tool -> content: LIVE + unit (PostToolContentSurvives; STOP-flush probe, no loss).
- D02 think -> tool -> think -> tool -> final: LIVE (c5fixed-agentloop T1/T2/T3,
  history replay, factually correct final).
- D03 promise -> tool -> result -> answer -> tool: LIVE (focused probe 2026-09-19).
- D04 result -> immediate tool (no filler): LIVE (focused corrected probe 2026-09-19).
- H01/H03 string->object->next-turn: LIVE (exact 2x2 4/4 on fixed binary).
- P02 (same as A02): LIVE.
- G03 unknown tool: LIVE fail-closed (HTTP400 INVALID_ARGUMENT, both paths).
- G06 negative args: LIVE fail-closed with parse position (4/4).

## Present in dogfood volume but NOT rated as contracts

- D01/D02 shapes occur throughout session 03 (81 steps/69 tools, text<->tool
  alternation healthy, 12 text-text transitions are final summaries).
- Prefix 1-3: 16K-context text answers, coherent, `stop`. Rated SANE as responses,
  NOT as transition contracts (no per-boundary delta audit).

## Focused live probes 2026-09-19

Server: C5fixed `gemma4` (substitution recorded).

- A01: INCONCLUSIVE — model produced call-only output, so the required
  promise/prose-before-call transition was not emitted and cannot be stamped.
- A04: PASS.
- C03: PARTIAL — first content -> tool transition exact; model did not emit the
  required second content -> tool half in the same turn.
- C04: PARTIAL — first reasoning/content/tool sequence exact; model did not emit
  the required second content -> tool half in the same turn.
- D03: PASS.
- D04: PASS on the corrected request. The first harness attempt is VOID evidence:
  it accidentally sent tool content as an array and was correctly rejected with
  HTTP 400. That 400 is not the D04 PASS result.
- D07: PARTIAL — batched two-call behavior proven; strict
  reasoning -> visible answer -> tool interleave was not emitted by the model.
- Zero marker leaks, duplicate calls, fabricated calls, or swallowed observed
  structural calls in these focused probes.

Local full-detail artifacts exist as `C6-transitions/VERDICT.md` + raw captures,
but they are NOT committed in this repository at this HEAD. Treat this document
as the repository-backed canonical summary unless/until that artifact pack is
content-addressed and committed or otherwise archived with hashes. Initial inline
attempts voided by shell quoting remain non-evidence.

## Remaining transition gaps after focused probes

The original seven named live gaps are reduced to four:

- A01 promise/prose -> real call: INCONCLUSIVE.
- C03 content -> tool -> content -> tool: PARTIAL.
- C04 reasoning -> content -> tool -> content -> tool: PARTIAL.
- D07 tool -> reasoning -> answer -> tool: PARTIAL.

Cross-cutting evidence gaps remain:

- B-series chunk/split invariance for the newly repaired transitions: NOT RUN live.
- F-series raw-token correlation: NOT captured live (usage only).

A04, D03, and D04 are no longer open gaps.

## Consequence for stamping (updated)

"ALL C5 GATES GREEN" remains WITHDRAWN as a claim.

Correct stamp:

```text
Listed gates green.
Transition matrix PARTIAL.
Remaining named transition gaps: A01, C03, C04, D07.
Cross-cutting gaps: B-series split invariance, F-series raw-token correlation.
```

Closing the transition matrix now means focused evidence for the four remaining
named gaps plus B-series split reruns and F-series raw-token correlation.
G2 pack stays response-level evidence, not a substitute for transition contracts.
