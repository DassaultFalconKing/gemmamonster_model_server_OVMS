# Gemma4 Upstream Contribution Refit Design

## Goal

Refit Gemmamonster's proven Gemma4 native tool-calling semantics onto the current OVMS `main` architecture after PR #4103, without replaying the historical 2026.4/early-2026.5 patch stack or duplicating behavior already accepted upstream.

Baseline: `openvinotoolkit/model_server@a5136cb285482aaef5410a053b5ecd04ff9324ec`.

Contribution branch: `integration/gemma4-upstream-contribution-refit-20260915`.

## Scope

The contribution covers one end-to-end contract: Gemma4 native agentic tool calls must be generated, rendered, streamed, parsed, and surfaced through the OpenAI-compatible API correctly on current OVMS `main`.

Included:

- recursive native Gemma4 argument parsing;
- request-registry validation;
- lossless numeric lexeme preservation;
- special-token-aware parser phase handoff;
- bounded malformed-call recovery;
- guarded bare `call:` recovery with true logical-boundary tracking;
- strict numeric lexical validation before `RawValue`;
- fail-closed handling of invalid executable native scalars;
- explicit generation policy for Disabled / Auto / Hard tool modes;
- lazy `tool_choice=auto` using OpenVINO GenAI `TriggeredTags`;
- fail-closed `required` and named-tool constraints;
- `parallel_tool_calls` semantics;
- post-render prompt-state grammar reconciliation;
- conservative Gemma4 tool-response template adaptation;
- regression absorption from current upstream Gemma4 fixes, including array parsing behavior;
- unit/contract coverage for stream splitting, false positives, malformed candidates, structural-token leakage, and multi-turn prompt-state behavior.

Excluded:

- session-store work;
- context-window changes;
- MTP tuning;
- inference performance tuning;
- deployment/operator-guide changes;
- evidence bundles or local runtime artifacts.

## Architectural Rules

### 1. Current upstream is authoritative

The refit starts from current `main`. Existing upstream Gemma4 behavior is preserved unless a targeted test demonstrates a protocol or safety gap. Changes already accepted upstream are absorbed rather than duplicated.

### 2. Semantic refit, not historical cherry-pick

Historical Gemmamonster commits are evidence and behavioral references only. Code is rewritten against current interfaces where necessary. No obsolete `OutputParsingConfig` members, old PyJinja wiring, or 2026.4-specific seams are reintroduced.

### 3. Parser execution is fail-closed

Only syntactically valid calls to request-registered tools become executable OpenAI tool calls. Recovery forms remain narrow. Plain prose that happens to contain `call:` must remain content, including when the text and `call:` prefix are split across streaming chunks.

### 4. Native values are parsed recursively and losslessly

Objects and arrays are recursive. Gemma4 native string delimiters and JSON strings are supported. Number lexemes are preserved byte-for-byte only after they pass strict JSON-number lexical validation. Invalid executable bare scalars are rejected rather than silently stringified.

### 5. Special-token ownership stays tokenizer-driven

Gemma4 parser activation must use tokenizer-resolved special-token semantics rather than hardcoded token IDs. Reasoning-to-tool phase transitions must preserve detection of an immediately adjacent tool marker across stream chunks and decode-mode changes.

### 6. Generation policy remains explicit

- Disabled: no active tool constraint when tools are absent or `tool_choice=none`.
- Auto: normal text remains legal until the native Gemma4 tool marker appears; then structured tool grammar activates.
- Hard: `required` and named-tool choices stay constrained and fail closed if a valid grammar cannot be built or validated.

`parallel_tool_calls=false` maps to a single-call structural policy; `true` keeps subsequent compatible tool calls legal.

### 7. Post-#4103 template architecture is preserved

PR #4103 introduced `PreparedRuntimeChatTemplate` and runtime-loaded chat-template execution. The refit must not restore old `PyJinjaTemplateProcessor` ownership. Gemma4 prompt-state reconciliation runs at the common post-render boundary after either runtime-Jinja or tokenizer/minja rendering has produced the final prompt.

The generation builder owns request-to-grammar construction. The render boundary owns prompt-state reconciliation because only that layer knows whether the rendered prompt ends inside an open Gemma4 thought channel.

### 8. Template adaptation is capability-driven and conservative

Tool-response JSON conversion is allowed only when detected template semantics support it. The decision must not be a model-name hack. Only `role=tool` string content that is a JSON object is eligible; arrays, scalars, invalid JSON, and non-tool messages retain string semantics.

### 9. Upstream reviewability is a deliverable

The contribution history is organized into small semantic commits. Tests live with or immediately precede the behavior they validate. The branch contains no generated evidence, binaries, runtime dumps, or unrelated refactors. License/style/Bazel checks are part of acceptance.

## Required Negative Contracts

The final branch must demonstrate all of the following:

1. An unknown tool name never becomes an executable call when request schemas are available.
2. `Documentation example: ` in one chunk followed by `call:bash{...}` in the next chunk remains content.
3. Valid bare-call recovery still works at a true logical phase/line boundary.
4. Invalid number-like lexemes such as `12foo`, `-x`, `01`, `1.`, and `1e` are not emitted as JSON numbers.
5. Large valid integer and decimal/exponent lexemes retain their original lexical representation.
6. A malformed call cannot poison a later valid call.
7. Structural Gemma4 framing markers do not leak into normal OpenAI `content`.
8. An adjacent reasoning close and tool opener survives chunk splitting and parser-phase handoff.
9. `tool_choice=auto` does not become equivalent to `required`.
10. `tool_choice=required` and named-tool choices cannot silently degrade to unconstrained generation.
11. Prompt-state adaptation applies after both runtime-template and tokenizer/minja rendering paths.
12. Existing upstream Gemma4 array behavior remains green.

## Commit Discipline

Target semantic sequence:

1. `test(gemma4): capture post-4103 tool protocol contracts`
2. `fix(gemma4): harden recursive native argument parsing`
3. `fix(gemma4): bound registry-aware bare-call recovery`
4. `fix(llm): preserve special-token phase boundaries`
5. `feat(gemma4): enforce native tool generation policy`
6. `fix(gemma4): reconcile hard grammar after runtime template render`
7. `fix(gemma4): preserve canonical tool-response template semantics`
8. `test(gemma4): cover upstream and streaming regressions`

The exact number may change if current upstream already satisfies one of these semantics, but commits must remain independently reviewable and must not reintroduce obsolete architecture.

## Acceptance

The contribution is ready for local Windows build/live testing only after:

- targeted Gemma4 parser tests pass;
- generation policy contract tests pass;
- chat-template and prompt-state contract tests pass;
- special-token streaming tests pass;
- relevant upstream Gemma4 regression tests pass;
- Bazel targets compile against current `main` interfaces;
- license/style checks pass;
- branch diff contains only scoped source/tests/docs required for the contribution.
