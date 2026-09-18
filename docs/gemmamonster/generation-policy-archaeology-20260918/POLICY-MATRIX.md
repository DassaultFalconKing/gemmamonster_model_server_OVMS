# Gemma4 Generation Policy Matrix

Chronological policy history from first implementation to C5.

## Epoch G0 — First Implementation

**Commit:** `fd0c86c77` (Sep 5 14:42) on `fix/gemma4-parser-generation-candidate`
**Files:** `gemma4/generation_config_builder.{cpp,hpp}` (new), `generation_config_builder.hpp` (wired)

| Aspect | `none` | `auto` (guided=false) | `auto` (guided=true) | `required` | named | response_format collision | schema validation failure |
|--------|--------|----------------------|---------------------|------------|-------|--------------------------|--------------------------|
| Grammar installed? | No | No | TriggeredTags | TagsWithSeparator | TagsWithSeparator | Throws | Silent unset |
| Tool syntax allowed? | N/A | Yes (native) | Yes (native) | Constrained | Constrained | N/A | N/A |
| at_least_one | — | — | false | true | true | — | — |
| stop_after_first | — | — | false | false | false | — | — |
| trigger token | — | — | `<\|tool_call>` | — | — | — | — |
| prose before tool? | — | Yes | Yes (free-text prefix) | No (constrained from token 0) | No | — | — |
| reasoning before tool? | — | Yes | Yes | No | No | — | — |
| structured_output_config | Preserved | Preserved | Set | Set | Set | Throws | Cleared |
| **Status** | RETAINED | RETAINED | **LOST** | RETAINED | RETAINED | **INTENTIONALLY_CHANGED** | **WEAKENED** |

### Key design decisions G0:
- `auto + guided=false`: Live 26B probe showed auto calling was healthy; preserve native path.
- `auto + guided=true`: TriggeredTags constrains after model emits trigger; free-text before trigger.
- `hard`: TagsWithSeparator from token zero; "do not use TriggeredTags here. TriggeredTags only takes control after the model emits `<|tool_call>` by itself, which still permits prose."
- `response_format + tools`: Throws `invalid_argument` — cannot share one `structural_tags_config`.
- **NOTE:** `enableToolGuidedGeneration` gated auto grammar. This was lost in later epochs.

---

## Epoch G1 — Isolated to gemma4/ directory

**Commit:** `7b5b73be5` (Sep 5 21:15) on same branch
**Files:** `gemma4/generation_config_builder.{cpp,hpp}` refactored into separate translation unit

Same policy as G0. Pure structural refactor: builder moved from inline in `generation_config_builder.hpp` to `gemma4/generation_config_builder.cpp`. Added `toolStartTerminatesReasoning` flag to reasoning parser config. Added first generation contract tests.

| Aspect | Change from G0 |
|--------|---------------|
| Policy | Identical |
| Structure | Builder isolated to own TU |
| Tests | `gemma4_generation_contract_test.cpp` added |
| **Status** | RETAINED |

---

## Epoch G2 — TriggeredTags REMOVED for auto

**Commit:** `f76f8f85e` (Sep 6 05:32) on `Gemmamonster-2026.4-RC1`
**Files:** `gemma4/generation_config_builder.cpp`

| Aspect | `auto + guided=false` | `auto + guided=true` | `required` | named |
|--------|----------------------|---------------------|------------|-------|
| Grammar installed? | No | **No** (was TriggeredTags) | TagsWithSeparator | TagsWithSeparator |
| at_least_one | — | — | true | true |
| prose before tool? | Yes | Yes | No | No |
| structured_output_config | Preserved | **Cleared** (`config.structured_output_config.reset()`) | Set | Set |
| **Status** | RETAINED | **REGRESSION_CANDIDATE** | RETAINED | RETAINED |

### Key design decision G2:
```
// Keep Gemma4 auto tool selection on the model's native protocol and let the
// Gemma4 output parser extract calls afterwards. Constraining auto generation
// after <|tool_call> is tempting, but real Gemma4 deployments have shown
// constrained-decoding token collapse/pad-token failures, especially with
// complex nested schemas used by coding agents. This also matches vLLM's
// default auto-tool policy: unconstrained unless a tool explicitly opts into
// strict schema enforcement.
```

**This is the PR5-equivalent change in our history.** The comment explicitly documents:
- Token collapse/pad-token failures with complex schemas
- Alignment with vLLM's auto-tool policy
- Decision to prefer native generation over constrained auto

**REGRESSION CANDIDATE:** This commit removed the TriggeredTags grammar that previously constrained auto tool calls after the trigger. Without it, auto mode relies entirely on the model choosing to emit `<|tool_call>` and the parser extracting it post-hoc. The "promise but no call" failure mode becomes possible: model verbalizes intent but never emits the structural trigger.

---

## Epoch G3 — Native auto (no grammar for auto at all)

**Commit:** `422627c4e` (Sep 6 06:17) on `Gemmamonster-2026.4-RC1`
**Files:** `generation_config_builder.hpp` (inline, replaces gemma4/ files)

| Aspect | `auto` | `required` | named | response_format collision |
|--------|--------|------------|-------|--------------------------|
| Grammar installed? | **Never** (`config.structured_output_config.reset()`) | TagsWithSeparator | TagsWithSeparator | Throws |
| at_least_one | — | true | true | — |
| prose before tool? | Yes | No | No | — |
| response_format collision | — | — | — | Throws |
| **Status** | INTENTIONALLY_CHANGED | RETAINED | RETAINED | RETAINED |

Same policy as G2 but code restructured. Auto always resets structured_output_config regardless of `enableToolGuidedGeneration`. Response format collision check added.

---

## Epoch G4 — Required-only with thought-then-tool grammar

**Commit:** `9c0b698e0` (Sep 15 16:30)
**Files:** `generation_config_builder.hpp` (inline)

| Aspect | `auto` | `required` | named |
|--------|--------|------------|-------|
| Grammar installed? | **No** (builder ignores auto) | Union{TagsWithSeparator, Concat{thought,TagsWithSeparator}} | (same as required) |
| at_least_one | — | true | true |
| thought allowed? | — | Yes (via Union alternative) | Yes |
| prose before tool? | Yes (unconstrained) | No (grammar from token 0, but thought channel allowed) | No |
| **Status** | INTENTIONALLY_CHANGED | **REIMPLEMENTED** | **REIMPLEMENTED** |

### Key innovation G4:
The thought-then-tool grammar: model can either call a tool immediately OR emit a complete `<|channel>thought...<channel|>` block and then call a tool. This is the correct Gemma4 behavior: reasoning before tool is legal, but unconstrained prose is not.

---

## Epoch G5 — Auto TriggeredTags restored + required retained

**Commit:** `5d8327cf6` (Sep 15 16:31) — same second as G4
**Files:** `generation_config_builder.hpp`

| Aspect | `auto` (guided=false) | `auto` (guided=true) | `required` | named |
|--------|----------------------|---------------------|------------|-------|
| Grammar installed? | No | TriggeredTags | Union{TagsWithSeparator, Concat{thought,TagsWithSeparator}} | Same as required |
| at_least_one | — | false | true | true |
| trigger token | — | `<\|tool_call>` | — | — |
| thought allowed? | — | — (auto grammar doesn't include thought) | Yes | Yes |
| **Status** | RETAINED | **REIMPLEMENTED** | RETAINED | RETAINED |

**Critical:** Auto TriggeredTags restored but gated on `enableToolGuidedGeneration`. Required mode retains thought-then-tool grammar.

---

## Epoch G6 — Full transplant from accepted RC

**Commit:** `653b18c93` (Sep 16 20:25) — transplanted from `43bc254e`
**Files:** `generation_config_builder.hpp`, `rendered_prompt_state.{cpp,hpp}`, `openai_api_handler.cpp`, `servable.cpp`

| Aspect | `auto` (guided=false) | `auto` (guided=true) | `required` | named | response_format collision |
|--------|----------------------|---------------------|------------|-------|--------------------------|
| Grammar installed? | No | TriggeredTags | Union{TagsWithSeparator, Concat{thought,TagsWithSeparator}} | Same as required | Throws |
| at_least_one | — | false | true | true | — |
| stop_after_first | — | `!parallelToolCalls` | `!parallelToolCalls` | `!parallelToolCalls` | — |
| rendered prompt adaptation | No | No | Yes (Concat residual thought) | Yes | — |
| requiresValidStructuredOutput | — | — | true | true | — |
| **Status** | RETAINED | RETAINED | RETAINED | RETAINED | RETAINED |

### Key additions G6:
- `rendered_prompt_state` tracks NEW_TURN / OPEN_THOUGHT / CLOSED_THOUGHT
- `adaptGemma4ToolGrammarForRenderedPrompt`: when prompt ends in open thought, prepends residual thought grammar to tool grammar
- `parallelToolCalls` controls `stop_after_first`
- `requiresValidStructuredOutput()` prevents silent unset for hard choices
- Schema validation: `requiresObjectRoot`, safe tool names, duplicate detection

---

## Epoch G7 — Forward-port to 2026.5

**Commit:** `2eda5165d` (Sep 9 02:48)
Same policy as G6. Major code restructure for 2026.5 codebase.

---

## Epoch G8 — Token grammar boundaries

**Commit:** `dbda6931e` (Sep 18 07:24) — **current HEAD lineage**
**Files:** `generation_config_builder.hpp`

| Aspect | `auto` | `required` | named |
|--------|--------|------------|-------|
| Grammar type | `token_triggered_tags` | `or`{`tags_with_separator`, `sequence`[`tag`(thought), `tags_with_separator`]} | Same as required |
| trigger token | `<\|tool_call>` as token ID | — | — |
| TagsWithSeparator | Via token grammar | Via token grammar | Via token grammar |
| at_least_one | false | true | true |
| stop_after_first | `!parallelToolCalls` | `!parallelToolCalls` | `!parallelToolCalls` |
| thought channel | Not in auto grammar | `<\|channel>` as token, `thought\n` as const, `<channel\|>` as token | Same |
| **Status** | RETAINED | RETAINED | RETAINED |

### Key change G8:
All structural grammar primitives converted from in-memory C++ objects to xgrammar-compatible JSON token grammar. This enables xgrammar to compile the grammar at the token level rather than string level, improving reliability.

---

## C5 Current State

**Commit:** `a671ddf9` (pinned) / HEAD (`8f970d423`)
**Files:** `generation_config_builder.hpp` (inline, 254 lines)

### Complete C5 policy:

| Aspect | `none` | `auto` | `required` | named |
|--------|--------|--------|------------|-------|
| Grammar installed? | No | `token_triggered_tags` | `or`{tools-only, thought-then-tools} | Same as required |
| Trigger token | — | `<\|tool_call>` (token) | — | — |
| at_least_one | — | false | true | true |
| stop_after_first | — | `!parallelToolCalls` | `!parallelToolCalls` | `!parallelToolCalls` |
| prose before tool? | — | Yes (free-text prefix) | No (constrained from token 0) | No |
| thought before tool? | — | Not in grammar | Yes (Union alternative) | Yes |
| enableToolGuidedGeneration gated? | — | **No** (always installs) | **No** (always installs) | **No** |
| validated? | — | Yes | Yes (fail-closed) | Yes (fail-closed) |
| response_format collision | — | Throws | Throws | Throws |
| schema validation failure | — | Silent unset | **Fail-closed** (refuse to clear) | **Fail-closed** |
| rendered prompt adaptation | — | No | Yes (open thought handling) | Yes |
| **Status** | RETAINED | **RETAINED** | RETAINED | RETAINED |

### Critical C5 behaviors:

1. **Auto always installs TriggeredTags** — `enableToolGuidedGeneration` is NOT checked. This is a deliberate change from G0-G5 where auto grammar was gated.

2. **Hard choice fail-closed** — `shouldPreserveStructuredOutputOnValidationFailure()` returns true for hard choices. `unsetStructuredOutputConfig()` refuses to clear when hard.

3. **Validation path** (openai_api_handler.cpp:379-384):
```cpp
try {
    configBuilder.validateStructuredOutputConfig(tokenizer);
} catch (const std::exception& e) {
    SPDLOG_LOGGER_DEBUG(...);
    configBuilder.unsetStructuredOutputConfig();  // cleared for auto, refused for hard
}
```

4. **No `enableToolGuidedGeneration` gating for auto** — In C5, auto always installs TriggeredTags regardless of this flag. This means the distinction between "auto with guided" and "auto without guided" has been collapsed: auto ALWAYS gets the TriggeredTags grammar.
