# Gemma4 C5 -> C6 recovery plan — 2026-09-18

Status: **CANONICAL EXECUTION PLAN**

This plan begins only after the protocol canon and contract registry are accepted.

It deliberately separates:

1. parser/routing recovery;
2. agentic-transition validation;
3. generation-policy characterization;
4. optional generation repair;
5. C6 fresh-head reconstruction.

No layer may use success in another layer as substitute evidence.

---

## 0. Frozen references

C5 behavioral baseline:

`a671ddf9f10f31a8afda849b44400291c35148ea`

Current docs/recovery branch:

`fix/gemma4-mid-thought-toolcall-c5-20260918`

Parser archaeology:

`89aadc03e5e2e81ebab25685a1296aaeaf0eb225`

Generation archaeology:

`8399ed747a78c9e82568c8cf3cea3f1bae7736e2`

Characterization test already written on the coordination line:

`0dd5f5c6593fe058a4b3a6e541a34a5a648e0caf`

Historical recovery anchors:

- transition origin: `0a537f089`
- scoped capability: `7b5b73be`
- refined handoff: `52aee8bfe`
- reviewed regression tests: `62a3d71de`
- generation-policy origin/runtime proof: `fd0c86c77`

Do not move C5, accepted evidence refs, tags, release refs, or known-good runtime slots.

---

# Phase A — documentation freeze

Required canonical documents:

- `protocol-canon-20260918/README.md`
- `protocol-canon-20260918/CONTRACT-REGISTRY.md`
- `protocol-canon-20260918/RECOVERY-PLAN.md`
- `protocol-canon-20260918/AGENTIC-TRANSITIONS.md`
- detailed parser `LOST-FIX-MATRIX.md`
- generation archaeology report/matrix

Acceptance:

- parser handoff is **CONFIRMED LOST**;
- generation “promise but no call” is **UNRESOLVED** until raw-token evidence;
- `0dd5f5c6` is test-only evidence, not a production repair;
- no canonical document claims that C5 already handles the implicit reasoning -> tool handoff;
- agentic transition sequences are explicit acceptance contracts.

No production files are changed in Phase A.

---

# Phase B — restore the lost parser contract on C5

Primary contract:

`P02: Gemma4 tool opener may implicitly close open reasoning`

## B1. Production scope

Expected minimal surface:

```
src/llm/io_processing/output_parsing_config.hpp
src/llm/io_processing/output_parser.cpp
src/llm/io_processing/gemma4/gemma4_reasoning_parser.hpp
```

Touch `gemma4_tool_parser` or `ovms_text_streamer` only when an actual contract requires it. Do not modify files for visual symmetry.

Historical semantics to restore:

- capability defaults false;
- Gemma4 reasoning explicitly opts in;
- while in REASONING, the earliest legal structural boundary wins;
- if explicit `<channel|>` occurs first, preserve the normal explicit path;
- if a legal tool start occurs first, emit preceding reasoning, retain the tool bytes, and transition to tool processing;
- an incomplete tool opener is held rather than leaked into reasoning;
- unrelated parser combinations remain unchanged.

Use `52aee8bfe` as semantic evidence, not as a blind cherry-pick source.

## B2. Required parser tests

Restore semantic equivalents of:

1. `StreamerTransitionsFromOpenGemmaReasoningToTools`
2. `ReasoningImplicitlyEndsOnSplitToolStartWithoutChannelEnd`
3. `StreamerKeepsNonGemmaToolExamplesInReasoning`

Also pin:

- explicit `<channel|>` -> tool;
- opener split across chunks;
- reasoning suffix + opener in the same decoded chunk;
- implicit rendered-prompt reasoning -> tool;
- unavailable/unknown tool remains non-executable;
- STOP immediately after recovered call;
- multiple tools after recovered reasoning;
- no structural marker leakage into reasoning/content.

## B3. Acceptance gate

Required evidence:

```
BUILD: PASS
focused Gemma4 parser tests: PASS
streamer handoff tests: PASS
neighbor non-Gemma guard: PASS
existing C5 parser/tool regression set: PASS
```

Then run live proof with raw output captured.

Positive live proof:

```
raw output contains canonical Gemma4 tool opener
reasoning has no explicit <channel|> before it
external response contains valid tool_calls[]
tool syntax is absent from reasoning_content/content
```

---

# Phase C — agentic transition acceptance

This phase is mandatory even if individual parser tests are green.

The system must preserve **semantic phase continuity** across an actual multi-step agent loop.

The canonical matrix is defined in `AGENTIC-TRANSITIONS.md`.

Minimum live sequences include:

```
promise/prose -> real tool call
reasoning -> real tool call
tool result -> reasoning -> real tool call
tool result -> reasoning -> final answer
reasoning -> answer/content -> real tool call
tool -> reasoning -> tool -> reasoning -> answer
tool -> reasoning -> answer -> tool
```

The exact surface syntax may differ by model output, but the ownership invariants do not:

- reasoning bytes stay reasoning;
- content bytes stay content;
- structural tool bytes become tool deltas;
- no tool marker leaks into prose;
- no valid tool call disappears;
- no prose promise becomes a fabricated executable call;
- tool indices/order remain stable;
- post-tool state is not accidentally frozen in TOOL or REASONING.

A model is not accepted for agentic use if valid structural transitions are routinely lost by the runtime. Otherwise we are benchmarking the defects of the harness rather than the intelligence of the model.

---

# Phase D — generation-policy characterization

Start only after parser/transition recovery is green, so parser loss cannot contaminate generation measurements.

No generation-policy code change at the start of this phase.

## D1. Capture fields

For each run record:

```
tool_choice
tools/schema
prompt
sampling params
max_tokens
rendered prompt state
raw token IDs
raw decode with special tokens
first tool opener token position or ABSENT
reasoning text
visible assistant content
parsed tool_calls
finish_reason
structured-output config / validation result
```

## D2. Minimum matrix

### auto / simple schema

Representative tools:

- calculator
- weather
- read_file

Tasks should genuinely require tool use.

Classify:

- tool call emitted;
- promise + tool call;
- promise + no opener;
- no promise + no opener;
- malformed opener.

### required

Same simple tools.

Any completion without a structural tool transition is a hard contract failure.

### named

Force one selected tool.

Verify selected tool and raw transition.

### auto / complex schema

Use at least one OpenCode-like nested schema.

Purpose:

- ensure later policy changes do not reintroduce PR5-era constrained-decoding degeneration;
- measure trigger reliability independently of argument grammar quality.

## D3. Ownership classifier

Only these ownership labels are allowed:

```
RAW_OPENER_PRESENT + NO_PARSED_CALL
    PARSER/ROUTING

RAW_OPENER_ABSENT + AUTO
    GENERATION/PROMPT/SAMPLING CANDIDATE

RAW_OPENER_ABSENT + REQUIRED/NAMED
    HARD GENERATION CONTRACT FAILURE

RAW_OPENER_PRESENT + VALID_PARSED_CALL
    SUCCESS
```

Assistant prose saying “I will call X” is metadata, not ownership proof.

---

# Phase E — optional generation repair

Enter only if Phase D proves a generation-side defect.

Do not preselect a repair.

Evaluate any candidate against both:

```
tool-transition reliability
AND
complex-schema non-degeneration
```

Potential intervention classes, least invasive first:

1. prompt/template correction if history shows a changed generation prefix or tool presentation;
2. stop/sampling correction if a deterministic runtime condition suppresses the opener;
3. generation-policy repair preserving lazy post-trigger constraint;
4. explicit hard-choice enforcement where API semantics require it;
5. retry/orchestration strategy only if model/policy cannot reliably satisfy auto.

Forbidden shortcuts:

- prose intent -> synthetic executable tool call;
- globally promote auto to required;
- blindly restore old `enableToolGuidedGeneration` gating;
- blindly revert to G2/G3 native-auto;
- blindly revert token-level grammar to old string grammar.

Any generation patch gets a separate contract/test commit and separate live A/B.

---

# Phase F — C6 fresh-head reconstruction

C6 is a reconstruction, not a merge of archaeology branches.

Before starting, re-resolve current upstream heads for:

- OVMS
- OpenVINO GenAI
- XGrammar

Do not reuse a stale head snapshot just because the date in the filename looks reassuring.

## F1. Carry only proven contracts

### Parser

- P02 restored implicit reasoning -> tool handoff;
- P03 non-Gemma guard;
- split-marker holdback;
- special-token/token-ID handoff;
- C5 registry/bare-boundary/AfterToolCall semantics;
- C-series agentic transition invariants from `AGENTIC-TRANSITIONS.md`.

### Generation

- accepted auto/hard semantics;
- thought-then-tool hard grammar;
- rendered-prompt adaptation;
- hard fail-closed validation;
- token-level boundaries;
- any Phase E repair only if independently proven.

### Whitespace

- bounded whitespace repair remains an independent accepted requirement.

## F2. Transfer record

For every carried contract record:

```
historical source
C5 proven implementation
C5 proving test
C6 implementation location
C6 proving test
```

If a contract has no C6 proving test, it is not considered transferred.

## F3. C6 gates

Order:

1. compile;
2. contract-focused parser tests;
3. agentic transition tests;
4. generation-policy tests;
5. whitespace tests;
6. neighboring parser regression suite;
7. raw-token live parser case;
8. live auto/required/named matrix;
9. complex-schema auto sanity;
10. multi-turn real agent loop;
11. only then broader acceptance.

A green build is not evidence that protocol semantics survived.

---

# Phase G — canonical promotion

After C6 passes:

- freeze exact OVMS/GenAI/XGrammar SHAs;
- freeze runtime DLL/library hashes where applicable;
- update protocol canon statuses from C5 to C6;
- preserve the contract registry as a mandatory forward-port checklist;
- archive raw-token evidence for the live agent case;
- mark superseded working hypotheses explicitly rather than deleting evidence.

---

# Commit discipline

Recommended C5-derived sequence:

```
docs(gemma4): establish parser and generation protocol canon
docs(gemma4): define behavioral contract registry
docs(gemma4): define C5 to C6 recovery plan
docs(gemma4): define agentic transition acceptance matrix

test(gemma4): reproduce lost reasoning to tool handoff
fix(gemma4): restore reasoning to tool phase transition
test(gemma4): guard cross-parser and split-marker handoff
test(gemma4): cover multi-turn agentic phase transitions

docs(gemma4): record C5 parser recovery evidence
```

Generation work, if needed, starts in a separate commit series after raw-token characterization.

Do not mix parser recovery and generation-policy changes in one commit.

---

# Stop conditions

Stop parser recovery if:

- the supposed lost behavior cannot be made RED on C5;
- current C5 is shown to contain an equivalent contract after all;
- restoring it breaks a neighboring parser by design rather than implementation error.

Stop generation repair if:

- raw traces show the opener was generated and only parsing failed;
- auto no-call behavior is legitimate and no hard contract is violated;
- the proposed fix reintroduces complex-schema degeneration.

Stop C6 promotion if:

- P02/P03 are not pinned by tests;
- agentic transition matrix is not green;
- required/named can silently lose structured enforcement;
- raw-token/live evidence disagrees with the parser/generation ownership model.

---

# Current execution state

```
C5 baseline:
  a671ddf9f10f31a8afda849b44400291c35148ea

parser archaeology:
  complete enough to authorize parser recovery

generation archaeology:
  complete enough to authorize characterization
  NOT sufficient to authorize a generation patch

protocol canon:
  frozen on the C5-derived docs line

production parser recovery:
  NOT STARTED in this documentation phase

agentic transition implementation:
  NOT STARTED

C6:
  BLOCKED until C5 parser + transition gates are green
```
