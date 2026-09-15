# Gemma4 semantic refit FROZEN — 2026-09-15

Branch: `staging/gemma4-upstream-refit-clean-20260915`  
**Behavioral freeze HEAD:** `36beda81ef0261392cb4ad16b602dfcdae031270`  
**(This docs commit extends the branch but does not change behavioral scope.)**  
Upstream `main`: `e338fb74b53dc8ac1c48707903b85e3901adcbdc`  
Status: **SEMANTIC FEATURE WORK FROZEN** pending Windows/live acceptance

## Session criterion (met)

Gemma4 tool protocol no longer:
- publishes phantom executable calls before envelope validation;
- erases hard HTTP tool intent when tools are missing/null/empty;
- depends semantically on `parseChunk` partition;
- mis-detects post-tool OPEN_THOUGHT after `rtrim`;
- promotes one-envelope garbage multicalls;
- grows unbounded malformed candidates without deterministic reject.

## Verified GREEN (this freeze HEAD)

```text
//src/test/llm/gemma4_generation:gemma4_generation_policy_test       PASSED
//src/test/llm/gemma4_generation:gemma4_phantom_tool_call_test       PASSED
//src/test/llm/gemma4_generation:gemma4_chunk_invariance_test        PASSED
//src/test/llm/gemma4_generation:gemma4_rendered_prompt_state_test   PASSED
//src/test/llm/gemma4_generation:gemma4_f7_contract_test             PASSED
//src/test/llm/gemma4_generation:gemma4_f10_guard_test               PASSED
git diff --check                                                    PASSED
```

## Freeze-scope commits since `4e5bb54a6`

| SHA | Subject |
|---|---|
| `76c486675` | test(gemma4): preserve explicit hard tool intent at HTTP boundary |
| `3755dc85b` | fix(openai): reject hard tool choice without usable tools |
| `585a6af8e` | test(gemma4): reject policy-keyword tool name collisions |
| `355ae00c1` | fix(gemma4): reserve tool policy names at request boundary |
| `909e21f07` | fix(gemma4): commit validated tool envelopes atomically |
| `3c05feb29` | test(gemma4): pin rendered thought continuation state |
| `c746a9b97` | fix(gemma4): reconcile rendered thought state before generation |
| `30dfdbfd3` | test(gemma4): cover multi-turn tool history contracts |
| `2b1dfb812` | fix(gemma4): drain parser progress independent of chunking |
| `31985d037` | test(gemma4): pin F7 argument contracts |
| `079eb6f66` | fix(gemma4): enforce object-root tool schemas |
| `474bc82ac` | test(gemma4): pin bounded candidate guards |
| `36beda81e` | fix(gemma4): bound malformed tool candidates |

## Closed in this freeze

- P0-A transactional ToolCall publication (T1)
- P0-B HTTP hard-intent preservation
- P0-C rendered thought state reconciliation
- P0-D chunk invariance + terminal drain
- F6 / F6.2 tool-name + reserved policy keyword contract
- F7 array matrix + object-root schema / no-params / duplicate-name contract
- F9 one-envelope garbage / adjacent multicall fail-closed
- F10 bounded malformed candidate guards
- §11.3 H1/H2/H4/H5 (via rendered-prompt state target)

## Backlog (DO NOT implement in this freeze)

- **H3** parallel prior calls + reordered tool responses / `tool_call_id` association (needs dedicated template fixture)
- **F8** unknown-tool envelope content leakage (markers may still appear in content path)
- Broader `//src:ovms_test` parser-matrix execution
- Shared `isSafeToolName` helper extraction (HTTP/builder/parser still duplicated intentionally)
- Typed `toolChoice` discriminant redesign (early InvalidArgument chosen instead)
- Style/buildifier pass; history rewrite for promotion PR
- Live Arc 140V / NovaClaw / OpenCode dogfood (next stage)

## Next stage (NOT semantic feature work)

```text
Windows product build
→ Arc 140V Gemma4 deployment
→ unary auto/required/named
→ streaming auto/required/named
→ parallel true/false
→ multi-turn tool response → second call
→ long NovaClaw/OpenCode agent loop
```

**STOP SEMANTIC FEATURE WORK.**
