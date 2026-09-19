# CPP preflight rerun — contract-fix verification (2026-09-19)

BASE_HEAD=1aa39decc (preflight ladder proven here)
CONTRACT_FIX_HEAD=5972368fe (75360103 hard+parallel contracts, 5972368fe API boundary)

STATIC_VERIFICATION=PASS (all items verified in-tree, no build needed):
- G12 request field `parallelToolCalls{true}` (openai_request.hpp:85)
- G12 parse: absent/null->true, bool->copy, non-bool->INVALID_ARGUMENT (handler 186-193)
- G12 mapping `stopAfterFirst = !request.parallelToolCalls` into both grammars (153)
- G09 base seam `requiresValidStructuredOutput()=false` (base hpp:103)
- G09 hard state: member false, reset at parse start, set only on hardChoice,
  override returns it; auto/none stay false (134-167)
- GEMMA4_BUILDER_ROUTING=PASS (gemma4 branch present, ctor 184-185)
- POLICY_EXCEPTION_API_BOUNDARY=PASS (both parse calls in one try/catch, 382-387)
- Validation flow: requires->INVALID_ARGUMENT else log+unset+continue (388-396)

FOCUSED_GENERATION_BUILD=PASS (26.6s, 9 actions: generation_config_builders + openai_api_handler)
FOCUSED_HANDLER_BUILD=PASS (same run)
GEMMA4_PARSER_BUILD=PASS (ladder rerun)
OUTPUT_PARSERS_BUILD=PASS (ladder rerun)
RUNTIME_SHARED_BUILD=PASS (132.6s, 26 actions, dll linked)

G09=STATIC PASS, runtime DEFERRED_UNTIL_FULL_BINARY (no covering unit test in tree)
G12=STATIC PASS, runtime DEFERRED_UNTIL_FULL_BINARY (same reason)
GEMMA4_BUILDER_ROUTING=PASS
API_EXCEPTION_BOUNDARY=PASS

FULL_BUILD=NOT_RUN (per task; clean checkpoint first)

## Live gates on preflight dist (post-reboot, PID 16292)

- G5/G6 (5232-token fixture): GREEN (unary tool_calls 23tok; streams 3/3 tool_calls).
- Live-like 6/6 behaviors match C5 (incl. emptyparams stop-empty, unknown 400).
- 7 focused probes: A04 PASS; D03/D04 PASS (D04 needed harness fix, recorded);
  D07 calculator+407ch content; A01 INCONCLUSIVE; C03/C04 PARTIAL (generation-side).
- G09 runtime: required/named+invalid-schema -> 400; auto+invalid -> 200-proceeds.
  (Malformed declarations -> 400 for all choices, correct fail-closed.)
- G12 runtime: omitted/true/false accepted (200); string form -> 400.
- Evidence: C6-preflight/g5-*.json, g6-*.sse.txt, livelike/, *-request/response.json.
- Incident: first 7-probe run clobbered C5fixed raws in C6-transitions/ (OutDir default);
  C5fixed numbers survive in VERDICT.md + pushed handoff. Fresh raws moved here.
