# Gemma4 Generation Policy Archaeology — 2026-09-18

## Session Goal

Recover the complete history of Gemma4 tool-generation policy from the first written version to current C5. Identify which generation contracts were changed, which were intentionally replaced, and which were lost during port/refit/forward-port. Find the possible regression where Gemma promises to call a tool but does not generate the tool-call transition.

---

## FIRST_GENERATION_IMPLEMENTATION

```
Commit:  fd0c86c77ce6812fd6c77d9c8ee16a7dd7cb973b
Date:    2026-09-05 14:42:35 +0200
Branch:  fix/gemma4-parser-generation-candidate
Files:   src/llm/io_processing/gemma4/generation_config_builder.{cpp,hpp}
         src/llm/io_processing/generation_config_builder.hpp (wired)
```

Policy:
- `auto + guided=false`: unconstrained native generation (live probe healthy)
- `auto + guided=true`: TriggeredTags with trigger=`<|tool_call>`, at_least_one=false
- `required`/named: TagsWithSeparator at token zero, at_least_one=true
- `none`: no grammar
- `response_format + tools`: throws

---

## FIRST_RUNTIME_PROVEN

```
Commit:  fd0c86c77ce6812fd6c77d9c8ee16a7dd7cb973b  (same — was runtime-proven from PR3)
Branch:  fix/gemma4-parser-generation-candidate
Tests:   gemma4_streaming_hardening_test.cpp (330 lines)
         Gemma4GenerationContractTest (gemma4_generation_contract_test.cpp)
Evidence: NovaClaw/tool-loop evidence referenced in PR3 description
```

---

## C5 (Current)

```
Commit:  a671ddf9f10f31a8afda849b44400291c35148ea (pinned)
HEAD:    8f970d423 (main)
Files:   src/llm/io_processing/generation_config_builder.hpp (inline, 254 lines)
```

Policy summary:
- `auto`: always installs `token_triggered_tags` (TriggeredTags at token level), at_least_one=false
- `required`/named: token-level `or`{tools-only, thought-then-tools}, at_least_one=true
- `none`: no grammar
- response_format + tools: throws
- Hard choice validation failure: fail-closed (refuse to clear)
- Auto validation failure: silent unset (fail-open)
- `enableToolGuidedGeneration` is NOT checked for auto or hard — grammar always installed

---

## POLICY_EPOCHS

```
G0  fd0c86c77  Sep 5 14:42  First implementation (TriggeredTags for auto+guided)
G1  7b5b73be5  Sep 5 21:15  Isolated to gemma4/ directory (same policy)
G2  f76f8f85e  Sep 6 05:32  TriggeredTags REMOVED for auto (PR5-equivalent)
G3  422627c4e  Sep 6 06:17  Auto always unconstrained (no grammar at all)
G4  9c0b698e0  Sep 15 16:30  Required-only with thought-then-tool grammar
G5  5d8327cf6  Sep 15 16:31  Auto TriggeredTags restored + required retained
G6  653b18c93  Sep 16 20:25  Full transplant: rendered prompt state, validation
G7  2eda5165d  Sep 9  02:48  Forward-port to 2026.5 (same policy)
G8  dbda6931e  Sep 18 07:24  Token grammar boundaries (xgrammar token-level)
C5  a671ddf9   Sep 18 (pinned) Current state
```

---

## CONFIRMED_LOST_GENERATION_CONTRACTS

### 1. `enableToolGuidedGeneration` gating for auto mode

**Lost in:** `422627c4e` (G3) / `f76f8f85e` (G2)

In G0/G1, auto grammar was gated on `enableToolGuidedGeneration`:
```cpp
// G0 (fd0c86c77):
if (!hardToolChoice && !enableToolGuidedGeneration) {
    return;  // no grammar
}
// only then install TriggeredTags
```

In C5, this check is gone — auto always installs TriggeredTags. The flag still exists in the base class and proto but is ignored by Gemma4's builder. This is **NOT a regression** — it is an intentional simplification. The original gating was a conservative approach during initial validation.

### 2. TriggeredTags removed for auto (G2/G3)

**Removed in:** `f76f8f85e` (G2), `422627c4e` (G3)
**Restored in:** `5d8327cf6` (G5), `653b18c93` (G6)

For ~10 days (Sep 6-15), auto had NO grammar at all. This was the deliberate "PR5-equivalent" change to avoid token collapse with complex schemas. Restored with TriggeredTags in G5/G6.

**Status:** INTENTIONALLY_CHANGED then REIMPLEMENTED. Not currently lost.

---

## INTENTIONAL_POLICY_CHANGES

### 1. Auto unconstrained for complex schemas (G2/G3)
**Commit:** `f76f8f85e`
**Reason:** "constrained-decoding token collapse/pad-token failures, especially with complex nested schemas used by coding agents. This also matches vLLM's default auto-tool policy."
**Impact:** Auto mode lost TriggeredTags for ~10 days.
**Current status:** TriggeredTags restored (G5/G6/C5). The concern about complex schemas is mitigated by TriggeredTags being lazy (only activates after trigger).

### 2. thought-then-tool grammar for hard choices (G4)
**Commit:** `9c0b698e0`
**Reason:** Gemma4 canonical behavior allows reasoning before tool call. "Permits canonical thought-then-tool or direct-tool generation."
**Impact:** Hard choices now accept thought channel as alternative prefix. This is correct Gemma4 behavior.
**Current status:** RETAINED in C5.

### 3. Rendered prompt state tracking (G6)
**Commit:** `653b18c93`
**Reason:** When a multi-turn conversation ends with an open thought channel (no `<channel|>`), the grammar must account for the residual thought state.
**Impact:** `adaptGemma4ToolGrammarForRenderedPrompt` prepends residual thought grammar.
**Current status:** RETAINED (renamed to `adaptGemma4HardToolGrammarForRenderedPrompt`).

### 4. Hard choice fail-closed validation (G6)
**Commit:** `653b18c93` / `fedbb0b9b`
**Reason:** "Refusing to clear structured output after validation failure for required/named tool_choice; keeping hard Gemma4 generation fail-closed."
**Impact:** `unsetStructuredOutputConfig()` refuses to clear for hard choices.
**Current status:** RETAINED in C5.

### 5. Token-level grammar boundaries (G8)
**Commit:** `dbda6931e`
**Reason:** Convert in-memory structural tag objects to xgrammar-compatible JSON token grammar for better reliability.
**Impact:** Grammar primitives expressed as token-level JSON. Same semantics, different representation.
**Current status:** RETAINED in C5.

---

## REGRESSION_CANDIDATES

### PRIMARY: Auto mode "promise but no call" failure

**Root cause:** In C5 auto mode, TriggeredTags grammar is lazy — it only constrains output AFTER the model emits `<|tool_call>`. If the model verbalizes intent ("I will call tool X") but never emits the trigger token, the grammar remains inactive and the response ends without tool calls.

**This is by design** — auto mode is supposed to permit non-tool responses. But the symptom (model says it will call a tool, then doesn't) is indistinguishable from a generation failure.

**Historical context:**
- G0/G1: TriggeredTags for auto+guided=true — same lazy behavior
- G2/G3: No grammar at all for auto — worse (no post-trigger constraint)
- G5/G6/C5: TriggeredTags restored — same lazy behavior as G0

**The regression is NOT in the grammar but in the model behavior + grammar interaction:**
- The model decides verbally to call a tool
- The model enters reasoning/prose mode
- The model ends generation without ever transitioning to `<|tool_call>`
- The grammar was never activated because the trigger was never emitted

**Possible causes:**
1. Model probability distribution favors prose completion over tool transition
2. Temperature/sampling settings favor continuation of prose
3. Prompt template changes affect tool-transition probability
4. Thought channel interaction: model starts reasoning, decides to call tool, but reasoning takes too long and hits max_tokens
5. `parallel_tool_calls=true` with `stop_after_first=false` might affect trigger probability

**Evidence needed:**
- Raw token-level trace of auto mode generation
- Compare trigger emission rate across temperature settings
- Compare trigger emission rate with/without TriggeredTags grammar active

### SECONDARY: auto + guided=false path

**Observation:** In C5, `enableToolGuidedGeneration` is ignored — auto always installs TriggeredTags. But the `ToolConstraintMode::Auto` path in `parseConfigFromRequest` does NOT check `enableToolGuidedGeneration`. This means even when the server config says `enable_tool_guided_generation=false`, auto requests still get TriggeredTags.

**Is this correct?** The comment in G2 says "matches vLLM's default auto-tool policy: unconstrained unless a tool explicitly opts into strict schema enforcement." But C5 is more constrained than vLLM for auto (TriggeredTags vs fully unconstrained).

**Impact:** If TriggeredTags causes token collapse for some auto requests (the original G2 concern), there is no escape hatch.

---

## PARSER_HANDOFFS

### PARSER_HANDOFF #1: tool_call inside open reasoning channel

**Commit:** `0dd5f5c65`
**Test:** `ToolCallStartInsideOpenReasoningChannelImplicitlyEndsReasoning`
**Evidence:** Parser correctly handles `<|tool_call>` starting before `<channel|>` closing tag.
**Status:** Parser handles this case correctly.

### PARSER_HANDOFF #2: colon variant tool call prefix

**Commit:** `e8c122020`
**Change:** Parser now accepts both `call:name{` and `:name{` after `<|tool_call>`.
**Status:** Parser handles both variants.

### PARSER_HANDOFF #3: empty args in parallel tool calls

**Commits:** `e8c122020`, multiple whitespace fixes
**Issue:** xgrammar produces whitespace in tool JSON arguments, causing parser failures.
**Status:** Multiple fixes applied. Ongoing monitoring.

---

## TESTS_ADDED

| Commit | Test file | Coverage |
|--------|-----------|----------|
| `7b5b73be5` | `gemma4_generation_contract_test.cpp` | First generation contract tests |
| `62676e2e4` | `gemma4_generation_contract_test.cpp` | Tool-calling generation and parser contracts |
| `45891c27e` | Lazy native grammar for auto tools |
| `41efa8deb` | Named tool choice pinned to one native tag |
| `18de2c26c` | Parallel tool call policy at HTTP boundary |
| `eef19863c` | Hard tool grammar for prompt-open reasoning |
| `646b6f842` | Reconcile hard grammar after chat template rendering |
| `dbda6931e` (test) | Token-level auto tool grammar |
| `0dd5f5c65` | Tool call inside open reasoning channel |
| `6aa6fe348` | Schema whitespace bound in token grammar |

---

## RUNTIME_EVIDENCE

1. **NovaClaw/tool-loop evidence (PR3/fd0c86c77):** Runtime-proven agent loop with tool calling on 26B model.
2. **Token collapse evidence (G2/f76f8f85e):** "real Gemma4 deployments have shown constrained-decoding token collapse/pad-token failures, especially with complex nested schemas used by coding agents."
3. **vLLM parallel evidence:** llama.cpp infinite repetition loop with parallel tool calls (llama.cpp#21375) — same class of issue.
4. **vLLM required not enforced (vLLM#53363):** Same "promise but no call" symptom in vLLM with Gemma4. vLLM fixed with post-parse enforcement, not grammar change.

---

## RECOMMENDED_MINIMAL_REPAIR

### If "promise but no call" is confirmed as generation-policy defect:

**Option A: Strengthen auto grammar trigger assistance**
- Add a bias/weight towards `<|tool_call>` token when auto mode is active
- This is model-level, not grammar-level
- Requires understanding of logit bias API in OpenVINO GenAI

**Option B: Post-parse enforcement for auto**
- Like vLLM's fix: if model verbalized tool intent but produced no tool call, generate a synthetic error or retry
- This is orchestration-level, not generation-level
- Safer but doesn't fix root cause

**Option C: Hybrid auto grammar**
- Keep TriggeredTags for most auto requests
- For agent loops (detected by conversation pattern), temporarily switch auto to required
- This requires agent-loop detection heuristics

### DO NOT REVERT:
- `f76f8f85e` (G2 TriggeredTags removal) — the token collapse concern is real
- `dbda6931e` (G8 token grammar) — xgrammar token-level is more reliable
- `fedbb0b9b` (hard choice fail-closed) — correct contract
- `653b18c93` (rendered prompt state) — correct multi-turn handling

---

## DO_NOT_REVERT

1. **TriggeredTags removal for auto (G2/G3):** The concern about complex-schema degeneration is real and documented by vLLM, llama.cpp, and our own deployments. TriggeredTags restoration (G5/G6/C5) is the correct compromise.

2. **Token grammar boundaries (G8):** xgrammar token-level representation is more reliable than string-level.

3. **Hard choice fail-closed (G6):** Required/named are API contracts. Silent fallback is incorrect.

4. **Thought-then-tool grammar (G4):** Correct Gemma4 behavior. Model can reason before calling tool.

5. **Rendered prompt state (G6):** Multi-turn correctness requires tracking open thought channels.

---

## External Comparison Notes

### vLLM
- Auto: fully unconstrained native generation (no TriggeredTags equivalent)
- Required: `supports_required_and_named = False` — skips structured output, relies on post-parse enforcement
- Had same "promise but no call" bug (#53363) — fixed with post-parse check, not grammar
- **Our auto is MORE constrained than vLLM** (TriggeredTags vs fully unconstrained)

### llama.cpp
- Auto: lazy grammar with `zero_or_more` parallel calls (caused infinite loop, fixed in #21661)
- Required: grammar constrains tool names from token zero
- Schema-constrained decoding added (PR#23247) but causes HTTP 500 with enum properties
- **Our implementation avoids the enum issue** by using JSONSchema content rather than grammar-level enum constraints
