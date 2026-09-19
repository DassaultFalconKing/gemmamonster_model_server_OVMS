# Session handoff — C5fixed -> post-C6 PR Discipline

Date: 2026-09-19

Status: **SESSION HANDOFF / NEXT-SESSION AUTHORITY SUMMARY**

This handoff closes the C5fixed recovery/evidence session and defines the starting
state for the next **post-C6 PR Discipline** session.

The next session may receive a larger execution prompt. That prompt may extend this
handoff, but it must not silently contradict proven evidence below without new,
executed evidence.

---

## 1. Repository / refs

Repository:

`DassaultFalconKing/gemmamonster_model_server_OVMS`

Evidence/docs branch at handoff start:

`fix/gemma4-upstream-evidence-triage-20260917`

Pre-handoff branch HEAD:

`1e7318c961b11714ca9522f9bccf7558ee765987`

C5fixed production authority:

`8c6f8b00912e8baa24fb1566a843b031584f1eaa`

C5 behavioral predecessor:

`a671ddf9f10f31a8afda849b44400291c35148ea`

Do not move `main`, tags, releases, accepted refs, or immutable runtime slots merely
to make history look cleaner.

Always re-resolve remote refs at the beginning of the next session.

---

## 2. C5fixed production contents

C5fixed contains two independently justified production repairs.

### P02 — implicit open-reasoning -> tool handoff

Canonical implementation line:

`5fa8b4c4efd851dead99b345c757bb45533074aa`

Behavior:

- `toolStartTerminatesReasoning` defaults false;
- Gemma4 opts in;
- in REASONING, earliest legal structural boundary wins;
- explicit `<channel|>` wins when earlier;
- legal tool opener before the explicit close publishes the reasoning prefix,
  preserves the tool remainder, and enters TOOL processing;
- incomplete opener is held and does not leak into `reasoning_content`;
- unrelated parser combinations remain unchanged.

This is a semantic restoration of the historical refined contract at
`52aee8bfe`, not a new policy invention.

Status: **LIVE PROVEN**.

### H03 — replayed OpenAI tool arguments -> strict template mapping

Implementation:

`8c6f8b00912e8baa24fb1566a843b031584f1eaa`

File:

`src/llm/apis/openai_api_handler.cpp`

Behavior:

- public OpenAI `function.arguments` remains STRING;
- only the copied template-bound ChatHistory is normalized;
- valid JSON object strings become OBJECT/MAPPING;
- already-object arguments remain object;
- malformed JSON and non-object roots fail with INVALID_ARGUMENT before graph
  execution;
- Gemma4-scoped to limit blast radius.

Status: **LIVE PROVEN**.

---

## 3. C5fixed reference runtime

Pinned recipe:

`docs/gemmamonster/upstream-fix-20260917/C5fixed-RECIPE-20260919.md`

Provenance:

`docs/gemmamonster/upstream-fix-20260917/C5fixed-PROVENANCE-20260919.md`

Working source:

`8c6f8b00912e8baa24fb1566a843b031584f1eaa`

Pinned runtime copy:

`C:\\llm\\ovms-C5fixed-pinned-20260919\\`

Mutable live runtime:

`C:\\llm\\ovms-C5fixed\\`

Key binary identities:

```text
ovms.exe
56AD64A0B09F8DC199BA07D073196E70BD5B5F78E25D345923FD88C39E1D9E9E

ovms_mediapipe_runtime_shared.dll
DD3B5D28F13147E53764F1BA5274A6EEBCE31CF8142AE4AB14963564052E4229

openvino_genai.dll
8C7F1F0CD4061EDD10CF30258EFEACDFA594A0A3A172947F9BBAEF29818C4115
```

Important build fact discovered during this session:

```text
//src:ovms alone is NOT sufficient for the history-normalization source change.

The relevant handler is linked through:
    //src:ovms_mediapipe_runtime_shared
```

Canonical cached incremental target:

`//src:ovms_mediapipe_runtime_shared`

Do not rewrite this as a clean/cacheless build recipe.

---

## 4. Runtime provenance / reproducibility verdict

Current verdict:

```text
REFERENCE-RUNTIME REPRODUCIBILITY:
    STRONG

HOST-BOUND REPRODUCIBILITY:
    YES

BEHAVIORAL REPRODUCIBILITY:
    YES

FULL CLEAN-ROOM REPRODUCIBILITY:
    NOT YET CLAIMED
```

Exact launch command, Python environment, model path, template/config hashes,
runtime DLL hashes, and request script locations are recorded in the recipe and
provenance documents.

Remaining clean-room gaps include at least:

- full model weight hashing;
- full OpenVINO install manifest;
- full system Python package freeze;
- exact complete Bazel transcript as a single portable recipe;
- one-command rebuild from a clean host.

These are reproducibility/package-discipline gaps, not evidence that current
C5fixed behavior is unproven.

---

## 5. Live evidence already accepted

C5fixed live evidence includes:

- exact history 2x2: STRING/STRING, STRING/OBJECT, OBJECT/STRING, OBJECT/OBJECT
  all HTTP 200 after fix;
- pre-fix STRING-arguments cells reproduced HTTP 400;
- public generated `function.arguments` remains STRING;
- malformed / array / scalar / boolean argument strings fail HTTP 400 with
  INVALID_ARGUMENT and parse information;
- no deep Mediapipe strict-template crash post-fix;
- mid-thought reasoning + real tool call works;
- multi-turn tool A -> result -> tool B -> result -> final works;
- dogfood session 03: 81 steps / 69 tools, no marker spam or obvious protocol
  corruption;
- no observed marker leaks, duplicate executable calls, fabricated calls, or
  swallowed observed valid structural calls in focused probes.

Do not downgrade these to unit-only evidence.

Do not upgrade them into proof for transition shapes that were never emitted.

---

## 6. Transition acceptance status at session close

Canonical report:

`docs/gemmamonster/upstream-fix-20260917/TRANSITION-VERDICT-20260919.md`

Proven live:

```text
A02  open reasoning -> tool
A03  explicit reasoning close -> tool
A04  reasoning -> content -> tool
C01  reasoning -> tool -> tool
C02  tool -> content
D02  think -> tool -> think -> tool -> final
D03  promise -> tool -> result -> answer -> tool
D04  tool result -> immediate tool
H01/H03 history roundtrip
P02 implicit reasoning -> tool
unknown-tool fail-closed
negative replay-argument validation
```

Still not fully proven:

```text
A01  promise/prose -> real call
      INCONCLUSIVE: model emitted call-only, so required prose-before-call shape
      was not observed.

C03  content -> tool -> content -> tool
      PARTIAL: first transition proven; model did not emit second half in one turn.

C04  reasoning -> content -> tool -> content -> tool
      PARTIAL: first sequence proven; second content/tool half not emitted.

D07  tool -> reasoning -> answer -> tool
      PARTIAL: batched two-call behavior proven; strict interleave not observed.
```

Cross-cutting gaps:

```text
B-series:
    live split/chunk invariance for newly repaired transitions not fully run.

F-series:
    raw-token correlation not captured for the focused live transition probes.
```

Important interpretation:

```text
model did not emit requested transition
    != runtime swallowed transition

raw valid opener emitted + parsed call missing
    = runtime/parser failure
```

No current evidence shows the latter on C5fixed.

---

## 7. Duplicate / superseded archaeology conclusions

Do not reopen these without new evidence.

### a9ae04188

Local archaeology showed `a9ae04188` production implementation is byte-identical
to `5fa8b4c4`.

Verdict:

`DUPLICATE IMPLEMENTATION — DO NOT PORT AS A SECOND FIX`

### e50ab9856

Contains 11 useful tests only.

Verdict:

`TEST VALUE HIGH — PRODUCTION VALUE NONE`

The tests are useful regression fences for C6 / PR preparation.

### local WIP after e50

Observed to remove the production P02 pieces while leaving tests that assert them.

Verdict:

`INCOHERENT WORKTREE STATE — DO NOT PORT / DO NOT USE AS BASE`

### 671f84c2 content-owned routing

Do not blindly cherry-pick.

Its historical CONTENT->TOOL contracts are largely reimplemented/superseded by
the current registry-aware OutputParser/Gemma4ToolParser routing:

- CONTENT checks complete/incomplete legal tool boundaries;
- split legal boundaries are held;
- registry-specific start/preamble tags prevent unknown bare tools from becoming
  executable boundaries;
- current AfterToolCall/remainder ownership supersedes older state machinery.

Use `671f84c2` as regression-contract evidence, not as mandatory production code.

---

## 8. Empty-args / whitespace status

Whitespace degeneration:

`CONFIRMED FIXED`

Empty-args persistent bug:

`NOT REPRODUCED`

Later canonical required calls produced filled arguments.

Do not resurrect the old empty-args hypothesis as justification for new production
changes unless a fresh reproducible defect exists.

F1-F5 remain valid hardening/API work where independently justified, not evidence
of a persistent empty-args root cause.

---

## 9. Context-capacity status

Do not mix context capacity with protocol acceptance.

Current honest ledger:

```text
~16K prefix:
    PROVEN healthy response behavior

~32K:
    PROVEN operational envelope / sustained live evidence
    previous bench evidence exists with degraded-host caveat

64K:
    NOT PROVEN
    OPEN CAPACITY PROBE
```

64K is not a canonical prerequisite for opening C6 reconstruction and must not be
invented as a PR acceptance fact.

---

## 10. C6 gate state

At session close:

```text
C5FIXED_REFERENCE_RUNTIME:
    ACCEPTED

C5FIXED_BEHAVIORAL_CONTROL:
    ACCEPTED

C5FIXED_FULL_TRANSITION_MATRIX:
    PARTIAL

C6_FRESH_HEAD_RECONSTRUCTION_GATE:
    OPEN

C6_ACCEPTANCE_GATE:
    CLOSED until C6 itself proves required contracts

C6_PROMOTION / PR-READY GATE:
    CLOSED until post-C6 validation + PR discipline
```

C6 is a fresh-head reconstruction.

It must port **behavioral contracts and proving tests**, not old branch ancestry.

Before construction or PR work, re-resolve exact current heads for:

- OVMS;
- OpenVINO GenAI;
- XGrammar.

Do not use stale preflight SHAs without re-resolution.

---

## 11. Required C6 carry set

At minimum C6 must carry and prove:

### Parser / routing

- P02 implicit Gemma4 reasoning -> tool;
- P03 non-Gemma guard;
- split opener / closer holdback;
- token-ID structural phase detection;
- special-token decode handoff;
- registry enforcement;
- boundary-gated native/bare recovery;
- atomic / fail-closed tool publication;
- current CONTENT->TOOL behavior;
- post-tool remainder ownership.

### History / template

- H01 response replay roundtrip;
- H02 public arguments remain STRING;
- H03 template-bound normalization;
- H04 object idempotence;
- H05 malformed/non-object rejection;
- H06 tool.content independence unless new evidence contradicts it.

### Generation

- auto remains optional;
- lazy trigger semantics preserved;
- required remains mandatory;
- named remains selected-tool-only;
- thought-then-tool hard path remains legal;
- hard validation fails closed;
- rendered OPEN_THOUGHT adaptation survives;
- parallel semantics survive;
- response_format conflict semantics survive.

### Whitespace

- bounded whitespace repair remains independently proven.

### Agentic

- at least the canonical A/B/C/D/F safety/transition contracts required by the
  post-C6 PR prompt;
- do not substitute long dogfood volume for named transition evidence.

---

## 12. Build / test discipline carried into next session

Project policy remains:

- **do not build `ovms_test` unless extreme necessity**;
- **do not perform cacheless/clean OVMS builds merely for surgical validation**;
- no `bazel clean` / `bazel clean --expunge` in the recovery lane;
- reuse known cache/output root/config/environment where valid;
- full/cacheless reproducibility work belongs to C6-B / pre-PR discipline, where
  it becomes meaningful acceptance evidence;
- heavy tests belong to the PR-preparation gate, not as ritual after every edit.

If the next session intentionally enters C6-B/pre-PR, it may tighten this policy
according to the explicit post-C6 PR Discipline prompt, but it must record why
the heavier build/test is now evidence-producing rather than gratuitous.

---

## 13. Next session: post-C6 PR Discipline

The next session's goal is not archaeology.

It is to turn a C6 candidate into a **reviewable, reproducible, evidence-backed PR
candidate** without losing the semantic contracts recovered here.

Expected discipline:

1. resolve exact C6 source/dependency heads;
2. verify C6 contains the intended production deltas only;
3. map every carried contract to:
   - historical source;
   - C5fixed proving evidence;
   - C6 implementation;
   - C6 proving test/evidence;
4. close remaining required transition/evidence gaps or explicitly classify them;
5. run the agreed C6 acceptance order;
6. produce reproducible binary/runtime provenance;
7. audit docs against actual executed evidence;
8. remove stale/overbroad claims;
9. prepare upstream-reviewable commit structure and PR narrative;
10. do not merge or move protected refs unless explicitly instructed.

A green build alone is not C6 acceptance.

A long dogfood session alone is not C6 acceptance.

A PR description is not evidence.

---

## 14. Canonical starting documents for the next session

Read before changing code:

- `docs/gemmamonster/protocol-canon-20260918/README.md`
- `docs/gemmamonster/protocol-canon-20260918/CONTRACT-REGISTRY.md`
- `docs/gemmamonster/protocol-canon-20260918/RECOVERY-PLAN.md`
- `docs/gemmamonster/protocol-canon-20260918/AGENTIC-TRANSITIONS.md`
- `docs/gemmamonster/upstream-fix-20260917/C5fixed-live-report-20260919.md`
- `docs/gemmamonster/upstream-fix-20260917/C5fixed-verbose-report-20260919.md`
- `docs/gemmamonster/upstream-fix-20260917/C5fixed-PROVENANCE-20260919.md`
- `docs/gemmamonster/upstream-fix-20260917/C5fixed-RECIPE-20260919.md`
- `docs/gemmamonster/upstream-fix-20260917/TRANSITION-VERDICT-20260919.md`

If older documents conflict with later executed evidence, preserve the old evidence
but use the newer explicit verdict.

---

## 15. Session-close verdict

```text
C5fixed:
    working behavioral known-good

P02 mid-thought repair:
    LIVE PROVEN

history/template normalization:
    LIVE PROVEN

reference runtime:
    PINNED / STRONG provenance

transition matrix:
    PARTIAL, with four named live gaps + B/F evidence gaps

32K:
    proven operational envelope

64K:
    open capacity probe

C6 reconstruction:
    authorized

C6 acceptance / PR readiness:
    must be proven on C6 itself

next session:
    POST-C6 PR DISCIPLINE
```

Do not carry forward unresolved historical hypotheses as facts.
Do carry forward the behavioral contracts and exact evidence boundaries.
