# Gemma4 behavioral contract registry — 2026-09-18

Status: **CANONICAL CONTRACT INDEX**

Purpose: compact, reviewable inventory of the contracts that must survive future refits and forward-ports.

Detailed parser archaeology remains in:

`docs/gemmamonster/parser-archaeology-20260918/LOST-FIX-MATRIX.md`

This file is the smaller “must not disappear again” layer.

## Contract states

- **RETAINED** — current C5 has the contract and a reasonable guard.
- **REIMPLEMENTED** — old mechanism changed, semantic behavior remains.
- **LOST** — historical contract exists and current C5 lacks it.
- **TEST_LOST** — behavior may remain, but the exact regression guard disappeared.
- **WEAKENED** — current coverage/behavior is narrower.
- **INTENTIONAL** — changed deliberately; do not restore as a lost fix.
- **UNRESOLVED** — needs execution/raw-token evidence.

---

## P-series — parser / routing

| ID | Contract | C5 status | Canonical evidence / note |
|---|---|---|---|
| P01 | Explicit `<channel|>` closes reasoning | RETAINED | Current REASONING branch still handles explicit end |
| P02 | Gemma4 tool opener may implicitly close open reasoning | **LOST** | `0a537f089` -> `7b5b73be` -> refined `52aee8bfe`; absent in C5 |
| P03 | Implicit reasoning->tool transition is Gemma4-scoped | **TEST_LOST** | Historical non-Gemma guard `StreamerKeepsNonGemmaToolExamplesInReasoning` must return |
| P04 | Incomplete tool opener is held across chunks | RETAINED / exact E2E TEST_LOST | Generic holdback remains; exact historical probes disappeared |
| P05 | Split tool closer is held across chunks | RETAINED / exact E2E TEST_LOST | Same |
| P06 | Structural markers do not leak into content/reasoning | REIMPLEMENTED | Current lookup/boundary logic is stronger than early helpers |
| P07 | Token-ID structural phase detection | RETAINED | Current `getPhaseStartTagForToken` path survives |
| P08 | Special-token decode mode changes do not lose the phase opener | RETAINED | Current streamer reconciliation survives |
| P09 | Rendered prompt can imply open reasoning state | REIMPLEMENTED | Current centralized rendered-prompt classifier supersedes old suffix heuristic |
| P10 | First tool call after explicit reasoning close parses | RETAINED | Existing C5 regression coverage |
| P11 | Multiple / consecutive tool calls retain ordering and indices | RETAINED | Existing C5 multi-call tests |
| P12 | Tool call followed by normal content preserves both | RETAINED | Existing C5 tests |
| P13 | STOP after complete tool call publishes one atomic valid call | REIMPLEMENTED | Ownership moved into current tool parser |
| P14 | Truncated/incomplete call at EOF does not fabricate execution | REIMPLEMENTED | Current fail-closed parser behavior |
| P15 | Unknown registered tool is rejected | RETAINED | Current registry enforcement |
| P16 | Bare/native `call:name...` recovery occurs only at logical boundaries | RETAINED | Current boundary-gated recovery |
| P17 | Bare recovery does not substitute for canonical mid-thought `<|tool_call>` handoff | RETAINED AS DISTINCTION | Do not use P16 as evidence for P02 |
| P18 | Nested arrays/objects survive parsing | REIMPLEMENTED | Current recursive/container parser |
| P19 | Escapes/backslashes/quotes survive arguments | RETAINED | Existing parser tests |
| P20 | Numeric lexemes are preserved losslessly | RETAINED | Current number-preserving normalization |
| P21 | Tool-response / turn tokens terminate or route correctly | RETAINED | Existing Gemma4 tests |
| P22 | Tool parser owns validated envelope publication, router owns phase transition | REIMPLEMENTED | Current AfterToolCall protocol replaces old `ownsToolCallBoundaries` flag |
| P23 | Guided/native malformed JSON cannot silently become executable arguments | REIMPLEMENTED | Strictness moved layers; exact old probe lost |
| P24 | Every-byte guided JSON escape matrix | **WEAKENED** | Historical broader matrix narrowed to current native/canonical coverage |

### P02 required test set

The eventual recovery of P02 is not accepted without semantic equivalents of:

1. coalesced open reasoning + canonical tool opener;
2. tool opener split across chunks;
3. non-Gemma reasoning containing tool-looking text stays reasoning;
4. explicit `<channel|>` path remains unchanged;
5. tool unavailable / unknown name stays non-executable;
6. STOP immediately after the recovered call does not duplicate it.

---

## G-series — generation policy

| ID | Contract | C5 status | Canonical evidence / note |
|---|---|---|---|
| G01 | `tool_choice=none` installs no tool grammar | RETAINED | Historical and current policy |
| G02 | `auto` may choose no tool | RETAINED | Fundamental auto semantics |
| G03 | C5 auto uses lazy token-triggered grammar after `<|tool_call>` | RETAINED | Token-level TriggeredTags form |
| G04 | Auto grammar does not itself force the first tool opener | RETAINED / design fact | Must be considered when diagnosing “promise but no call” |
| G05 | Required choice enforces at least one tool path | RETAINED | Hard grammar |
| G06 | Named choice restricts generation to the selected tool | RETAINED | Historical hard-choice contract |
| G07 | Hard choices allow canonical thought-then-tool OR direct-tool | RETAINED | Origin G4; retained through C5 |
| G08 | Rendered OPEN_THOUGHT state adapts hard grammar | RETAINED | G6 onward |
| G09 | Required/named structured-output validation fails closed | RETAINED | Do not silently clear hard grammar |
| G10 | Auto structured-output validation may fail open | RETAINED CURRENTLY | This is a policy seam, not presently a confirmed bug |
| G11 | `response_format` collision with tool grammar is rejected | RETAINED | Existing policy |
| G12 | Parallel policy controls stop-after-first semantics | RETAINED | Existing generation policy |
| G13 | Token-level grammar boundaries replace older string representation | RETAINED | G8/C5 |
| G14 | `enableToolGuidedGeneration` gates auto grammar | **INTENTIONAL REMOVAL** | Do not restore merely as archaeological symmetry |
| G15 | Auto TriggeredTags removed during G2/G3 complex-schema mitigation | INTENTIONAL HISTORICAL CHANGE | Later reimplemented lazily; do not blindly revert PR5-era decisions |
| G16 | “Promise but no call” is caused by generation policy | **UNRESOLVED** | Requires raw-token proof |

### G16 ownership classifier

```
assistant promises tool
+ raw <|tool_call> token exists
+ no tool_calls externally
    => parser / routing / streamer

assistant promises tool
+ raw <|tool_call> token absent
    => generation / prompt / sampling / model policy

required/named
+ raw <|tool_call> token absent
    => hard generation-contract violation
```

No generation-policy patch is authorized by prose-only evidence.

---

## S-series — streamer / phase bridge

| ID | Contract | C5 status | Note |
|---|---|---|---|
| S01 | Streamer reconciles special-token decode mode before phase handoff | RETAINED | Protect against losing opener during mode change |
| S02 | Hidden structural start token can be recognized by token ID | RETAINED | OutputParser supplies phase start tag |
| S03 | When special tokens are already visible, textual parser boundary owns the handoff | RETAINED DESIGN | Relevant to Gemma4 reasoning mode |
| S04 | Pending bytes are flushed exactly once across phase transition | RETAINED / verify with recovered P02 | Must be execution-tested after port |
| S05 | Streamer must not synthesize Gemma4-only transition for unrelated parser combinations | GUARDED BY P03 | Recovery gate |

---

## Cross-layer invariants

### X01 — no semantic ambiguity at tool start

For Gemma4, once a legal canonical tool opener is accepted as a phase boundary, its bytes belong to the tool parser, never to reasoning/content.

### X02 — parser does not manufacture model intent

Parser recovery may recognize a structural call the model emitted. It must not convert ordinary prose like “I will call X” into an executable tool call.

### X03 — auto remains optional

Any attempt to improve auto reliability must preserve the semantic possibility of a legitimate no-tool response.

### X04 — hard choices remain hard

Required/named must never silently degrade into ordinary unconstrained prose because structured-output setup failed.

### X05 — evidence stays layered

Whitespace, parser handoff, generation trigger probability, and empty-args behavior are independent tracks unless an executed A/B proves a causal connection.

---

## Forward-port gate

Every future Gemma4 forward-port/refit must answer, at minimum:

```
P02 present?
P03 test present?
P04/P05 holdback present?
P08 special-token handoff present?
P13/P14 atomic/fail-closed publication present?
P15 registry enforcement present?
P16 boundary-gated bare recovery present?

G03 lazy auto trigger present?
G05/G06 hard choice semantics present?
G07 thought-then-tool present?
G08 rendered prompt adaptation present?
G09 hard fail-closed present?
G12 parallel semantics present?

S01/S02 preserved?
```

A green build without this contract check is insufficient evidence for a Gemma4 forward-port.
