# Gemma4 protocol canon — 2026-09-18

Status: **CANONICAL COORDINATION DOCUMENT**

Scope: Gemma4 generation, reasoning, tool parsing, output routing, and streamer contracts relevant to the C5 -> C6 line.

This document resolves the two independent archaeology passes and defines which conclusions are safe to use for implementation work.

## 1. Authority set

Behavioral baseline:

- C5: `a671ddf9f10f31a8afda849b44400291c35148ea`

Parser archaeology:

- report commit: `89aadc03e5e2e81ebab25685a1296aaeaf0eb225`
- file: `docs/gemmamonster/parser-archaeology-20260918/LOST-FIX-MATRIX.md`

Generation-policy archaeology:

- report commit: `8399ed747a78c9e82568c8cf3cea3f1bae7736e2`
- files:
  - `docs/gemmamonster/generation-policy-archaeology-20260918/README.md`
  - `docs/gemmamonster/generation-policy-archaeology-20260918/POLICY-MATRIX.md`

Targeted characterization test:

- `0dd5f5c6593fe058a4b3a6e541a34a5a648e0caf`
- `ToolCallStartInsideOpenReasoningChannelImplicitlyEndsReasoning`

Historical implementation anchors:

- `0a537f089` — first generic reasoning -> tool transition
- `7b5b73be` — scoped `toolStartTerminatesReasoning` capability
- `52aee8bfe` — refined explicit-end/tool-start ordering and partial-opener holdback
- `62a3d71de` — reviewed regression test `StreamerTransitionsFromOpenGemmaReasoningToTools`
- `fd0c86c77` — first / runtime-proven Gemma4 generation-policy implementation

## 2. Evidence rules

The unit of preservation is a **behavioral contract**, not a commit hash.

A historical commit is evidence that a contract existed. It is not, by itself, evidence that current code is broken.

A contract is classified LOST only when both are true:

1. historical code/test proves the behavior existed;
2. current C5 lacks an equivalent implementation or regression guard.

Static archaeology and live/runtime evidence remain separate. Static code inspection can establish that an implementation seam is absent; it cannot establish model-side generation frequency or live acceptance.

## 3. Canonical parser verdict

### CONFIRMED LOST

**Gemma4 reasoning -> tool implicit handoff**

Historical contract:

```
REASONING
  + complete Gemma4 tool opener
  + no earlier explicit <channel|>
      ->
reasoning prefix emitted
tool opener retained
phase enters TOOL_CALLS_PROCESSING_TOOL
```

The capability was scoped through:

```cpp
OutputParsingConfig::toolStartTerminatesReasoning
```

with default `false`, and Gemma4 reasoning opted in.

Current C5 does not contain that capability. Its REASONING branch checks the reasoning end tag only.

Loss mechanism:

**lineage fork + incomplete refit/transplant.**

The contract was not reverted. The accepted staging lineage from which C5 descends never received the relevant PR4/parallel-line hunk and its regression tests.

This is a real product regression because it can convert a model-generated structural tool call into reasoning text / non-executable output.

### CONFIRMED LOST TESTS

At minimum restore semantic equivalents of:

- `StreamerTransitionsFromOpenGemmaReasoningToTools`
- `ReasoningImplicitlyEndsOnSplitToolStartWithoutChannelEnd`
- `StreamerKeepsNonGemmaToolExamplesInReasoning`

The third test is essential because the recovered transition must remain Gemma4-scoped and must not turn arbitrary tool-looking text inside other reasoning formats into executable calls.

### RETAINED / REIMPLEMENTED

The archaeology found that most of the surrounding parser stack survived or was replaced by stronger equivalents, including:

- explicit `<channel|>` reasoning termination;
- token-ID structural phase detection;
- special-token decode handoff;
- split structural-tag holdback;
- multi-tool sequencing;
- post-tool remainder ownership;
- malformed/truncated call fail-closed behavior;
- tool registry enforcement;
- boundary-gated bare/native recovery;
- numeric lexeme preservation;
- nested argument handling;
- tool-response / turn-token handling.

Do not replace these with old implementations merely because older commits contain similar code.

## 4. Canonical generation-policy verdict

The generation archaeology establishes a useful chronology but **does not yet prove a current generation-policy regression**.

First known/runtime-proven policy:

`fd0c86c77`

Key epochs:

- G0/G1: native auto when guided disabled; lazy TriggeredTags when guided enabled; hard choices constrained from the beginning;
- G2/G3: auto TriggeredTags intentionally removed because of constrained-decoding degeneration with complex schemas;
- G4: hard choices gain direct-tool OR thought-then-tool grammar;
- G5/G6: lazy TriggeredTags restored for auto; rendered-prompt-state and hard fail-closed semantics added;
- G8/C5: structural grammar boundaries converted to token-level form.

Current C5 auto policy is lazy:

```
model must emit <|tool_call>
       ->
token_triggered_tags activates
       ->
arguments become constrained
```

Therefore TriggeredTags constrains a tool call **after the structural transition begins**. It does not prove or force that the model will emit that transition.

### REGRESSION CANDIDATE, NOT ROOT CAUSE

The live symptom:

```
"I will call tool X..."
[response ends]
```

can be generation-side only if the raw generation never emitted the tool opener token.

Until a raw-token A/B establishes that, “lazy TriggeredTags caused the failure” is a hypothesis, not a root-cause verdict.

### INTENTIONAL CHANGE, NOT A LOST BUG FIX

The old `enableToolGuidedGeneration` gating is not treated as a product regression.

Its removal/change is historically intentional. Do not restore it merely because the symbol-level contract disappeared.

## 5. Conflict resolution between archaeology reports

The generation archaeology contains a statement that the parser “handles” a tool call inside an open reasoning channel and cites `0dd5f5c6`.

That statement is **superseded by this canon**.

`0dd5f5c6` adds a characterization/regression test only. It is not a production fix.

Canonical status:

```
C5 production implementation:
    MISSING implicit reasoning -> tool handoff

0dd5f5c6:
    test evidence / intended contract
    NOT evidence that C5 is fixed
```

The parser archaeology is authoritative on the presence/absence of that current implementation because it explicitly inspected the C5 production paths and lineage.

## 6. Raw-token classifier

All live investigations must classify failures before assigning ownership.

```
PROMISE + raw tool opener present + parsed tool_calls absent
    => parser / routing / streamer defect

PROMISE + raw tool opener absent
    => generation / prompt / sampling / model-policy lane

REQUIRED or NAMED + raw tool opener absent
    => hard generation-contract failure

AUTO + no promise + raw tool opener absent
    => potentially valid no-tool choice
```

Do not infer generation failure from assistant prose alone.

Do not infer parser failure without proving the model emitted the structural transition.

## 7. C5 and C6 relationship

C5 remains the behavioral control for the already-accepted whitespace work.

The newly discovered parser regression does **not** invalidate the whitespace verdict. It identifies a contract that existing C5 gates did not exercise.

C6 must not be used to “discover whether the repair works.”

Order:

1. restore and validate the lost parser contract on the C5-derived lane;
2. characterize generation separately with raw-token evidence;
3. only then reconstruct C6 from fresh upstream heads while carrying the proven contract set.

C6 ports **semantics and tests**, not old branch ancestry.

## 8. Current canonical statuses

| Area | Status |
|---|---|
| bounded tool JSON whitespace repair | CONFIRMED / independent |
| Gemma4 implicit reasoning -> tool handoff | **CONFIRMED LOST** |
| exact reviewed regression tests for that handoff | **TEST_LOST** |
| surrounding parser contracts | mostly RETAINED / REIMPLEMENTED |
| auto TriggeredTags presence in C5 | RETAINED in token-level form |
| “promise but no call” generation root cause | **UNRESOLVED** |
| `enableToolGuidedGeneration` gating loss | INTENTIONAL CHANGE |
| C5 production parser repair | NOT YET IMPLEMENTED |
| C6 promotion of parser repair | BLOCKED ON C5 GREEN |

## 9. Non-negotiable implementation rule

No production port should be justified with “this old commit used to work.”

Every recovery patch must identify:

- the behavioral contract being restored;
- the historical evidence for it;
- the current C5 evidence of absence;
- the new regression test that pins the behavior;
- neighboring contracts that must remain unchanged.

That rule exists because a branch can preserve a commit-shaped history while still losing the thing the commit was supposed to guarantee. We have now demonstrated that failure mode in this repository.


## 10. Canonical document set and execution status

The protocol canon is complete only as the following set:

- `README.md` — resolved parser/generation verdicts and evidence ownership;
- `CONTRACT-REGISTRY.md` — compact behavioral contracts that future refits must preserve;
- `RECOVERY-PLAN.md` — ordered C5 repair -> transition validation -> generation characterization -> C6 reconstruction plan;
- `AGENTIC-TRANSITIONS.md` — required single-generation, streaming, and real multi-turn agentic transition matrix.

Detailed source archaeology remains evidence, not the execution authority:

- `../parser-archaeology-20260918/LOST-FIX-MATRIX.md`;
- generation-policy archaeology at commit `8399ed747a78c9e82568c8cf3cea3f1bae7736e2`.

Current phase status:

```
PHASE A / DOCUMENTATION:
    COMPLETE

PRODUCTION PARSER PORT:
    NOT STARTED

AGENTIC TRANSITION IMPLEMENTATION/TESTING:
    NOT STARTED

GENERATION-POLICY PATCH:
    NOT AUTHORIZED WITHOUT RAW-TOKEN EVIDENCE

C6:
    BLOCKED ON C5 RECOVERY + TRANSITION GREEN
```

The next implementation session must treat these four files as one authority set. If an older report conflicts with them, this protocol canon wins unless new executed evidence explicitly amends it.


## 11. Newly exposed tool-history/template compatibility gap

Canonical diagnosis:

`TOOL-HISTORY-TEMPLATE-COMPAT-20260919.md`

Verdict:

```
NOT a confirmed lost historical OVMS fix.

OLD:
    string arguments in assistant tool-call history
    -> permissive model/template/runtime combination
    -> two-turn PASS at 7d00c5fe

CURRENT STRICT TEMPLATE:
    same OpenAI string history
    -> template requires mapping
    -> INVALID_ARGUMENT before generation
```

The preferred repair boundary is the copy of `ChatHistory` destined for chat-template rendering:

```
OpenAI/API domain:
    arguments = STRING

template domain:
    arguments = OBJECT/MAPPING
```

Do not alter public OpenAI serialization.

The historical exact-head `7d00c5fe63c5f81e6c06972a974cd57fd7180326` is important evidence: its two-turn live session passed while the source still lacked any string -> mapping adapter. That makes the current issue a compatibility gap exposed by stricter template semantics, not evidence of another silently dropped parser patch.


## 12. Tool-history 2x2 closed; repair authorized

Executed current-stack matrix:

```text
args STRING + tool.content STRING -> 400
args STRING + tool.content OBJECT -> 400
args OBJECT + tool.content STRING -> 200
args OBJECT + tool.content OBJECT -> 200
```

Therefore:

- `function.arguments` is the deciding axis;
- `tool.content` is not part of this reproduced defect;
- Sept-15 `str.get` is historical/non-reproduced on the current stack;
- template-bound string -> mapping normalization is now an evidence-backed required repair.

Implementation proposal:

`TOOL-HISTORY-TEMPLATE-FIX-PROPOSAL-20260919.md`

Preferred seam:

```text
OpenAIApiHandler::extractInputRequest()
    req.input = request.chatHistory
    -> normalize copied tool-call arguments
    -> ChatTemplateProcessor
```

Public OpenAI `function.arguments` remains a JSON string.
