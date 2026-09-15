# Gemma4 Upstream Contribution Refit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refit Gemmamonster's proven Gemma4 native tool-calling semantics onto post-#4103 OVMS `main` with a small, reviewable commit stack and current architecture.

**Architecture:** Current upstream `main` is authoritative. Parser, generation policy, streamer/special-token handoff, and chat-template prompt-state reconciliation are changed only where current behavior fails explicit contracts. Runtime chat-template execution remains owned by `PreparedRuntimeChatTemplate`; Gemma4 reconciliation is applied only after final prompt rendering.

**Tech Stack:** C++20, OpenVINO GenAI StructuredOutputConfig/TriggeredTags, RapidJSON, OVMS OutputParser/InputProcessor, Bazel/GTest.

**Spec:** `docs/superpowers/specs/2026-09-15-gemma4-upstream-contribution-refit-design.md`

## Global Constraints

- Base commit: `openvinotoolkit/model_server@a5136cb285482aaef5410a053b5ecd04ff9324ec`.
- Do not restore old `PyJinjaTemplateProcessor` ownership removed/reworked by PR #4103.
- Do not add session-store, context-window, MTP, performance, deployment, or evidence-bundle changes.
- Existing upstream Gemma4 fixes are absorbed, not duplicated.
- Executable parser recovery is fail-closed and request-registry-aware.
- Numeric lexemes are preserved only after strict JSON-number validation.
- Special-token behavior remains tokenizer-driven, not hardcoded to model token IDs.
- Every behavioral change is covered by a focused contract test.
- License/style/Bazel checks are part of acceptance.

---

### Task 1: Freeze post-#4103 parser regressions

**Files:**
- Modify: `src/test/llm/` Gemma4 tool-parser test target(s) discovered on current `main`
- Modify as needed: `src/BUILD` or `src/llm/BUILD` only to register targeted tests

**Interfaces:**
- Consumes: current upstream `Gemma4ToolParser` and generic `OutputParser`
- Produces: failing tests for recursive native values, request registry validation, bare-call cross-chunk false positive, malformed-number rejection, malformed-call recovery, and no framing leakage

- [ ] Add focused tests for nested objects/arrays, native `<|"|>` strings, large valid number lexemes, invalid number-like lexemes, unknown tools, and cross-chunk `Documentation example: ` + `call:bash{...}`.
- [ ] Run only the affected Gemma4 parser tests and record which contracts are already green upstream and which fail.
- [ ] Do not modify production code until the failing contracts are isolated.
- [ ] Commit the contract-only delta as `test(gemma4): capture post-4103 tool protocol contracts`.

### Task 2: Refit recursive/lossless native argument parsing

**Files:**
- Modify: `src/llm/io_processing/gemma4/gemma4_tool_parser.cpp`
- Modify: `src/llm/io_processing/gemma4/gemma4_tool_parser.hpp` only if current interfaces need parser state/helpers
- Test: same Gemma4 parser tests from Task 1

**Interfaces:**
- Consumes: current upstream parser state machine and RapidJSON writer utilities
- Produces: recursive native value parser; strict JSON-number lexical validator; fail-closed executable scalar handling

- [ ] Implement recursive parsing of objects, arrays, JSON strings, Gemma4 native-delimited strings, booleans, null, and numbers.
- [ ] Validate number lexemes against JSON number grammar before `RawValue`; preserve accepted lexemes byte-for-byte.
- [ ] Reject invalid executable bare scalars instead of silently promoting them to strings.
- [ ] Preserve current upstream array semantics covered by PR #4532 regressions.
- [ ] Run the targeted parser suite until all Task 1 recursive/numeric tests pass.
- [ ] Commit as `fix(gemma4): harden recursive native argument parsing`.

### Task 3: Bound registry-aware recovery across stream chunks

**Files:**
- Modify: `src/llm/io_processing/gemma4/gemma4_tool_parser.cpp`
- Modify: `src/llm/io_processing/gemma4/gemma4_tool_parser.hpp`
- Test: Gemma4 tool-parser tests

**Interfaces:**
- Consumes: request tool registry from production parser construction
- Produces: true logical-boundary state for narrow bare `call:` recovery

- [ ] Track whether the current parser cursor is at a real logical phase/line boundary independently of chunk boundaries and buffer compaction.
- [ ] Require bare `call:` recovery to start only at that boundary, allow indentation, require sane registered tool name, and pass the normal structural argument parser.
- [ ] Verify split prose + bare call remains content while a true boundary bare call remains recoverable.
- [ ] Verify malformed candidate state cannot poison a later valid call.
- [ ] Commit as `fix(gemma4): bound registry-aware bare-call recovery`.

### Task 4: Preserve special-token parser phase boundaries

**Files:**
- Modify only if required after current-main audit: generic streamer/output-parser files under `src/llm/`
- Test: output-parser/streamer Gemma4 reasoning-to-tool transition tests

**Interfaces:**
- Consumes: tokenizer-resolved special-token start tags for Gemma4 reasoning and tool parsing
- Produces: reliable adjacent reasoning-close/tool-open handoff across chunk and decode-mode boundaries

- [ ] Add/identify RED tests for `<channel|><|tool_call>` adjacency and splits inside the semantic reasoning opener.
- [ ] Compare current-main decode-mode order with the proven Gemmamonster fix; carry only the missing semantic delta.
- [ ] Do not add hardcoded Gemma4 token IDs.
- [ ] Run generic output parser plus Gemma4 reasoning/tool streaming tests.
- [ ] Commit only if current main needs the change, as `fix(llm): preserve special-token phase boundaries`.

### Task 5: Refit explicit Gemma4 generation policy

**Files:**
- Modify/create current-main Gemma4 generation config builder files under `src/llm/io_processing/gemma4/`
- Test: current generation-config builder tests under `src/test/llm/`
- Modify BUILD targets only as required

**Interfaces:**
- Consumes: OpenAI request tool choice, tool schema map, `parallel_tool_calls`, response format, OpenVINO GenAI StructuredOutputConfig
- Produces: Disabled / Auto / Hard Gemma4 tool-generation policy

- [ ] Add contract tests for no-tools, `none`, `auto`, `required`, named tool, missing named tool, response-format coexistence, and both `parallel_tool_calls` values.
- [ ] Implement `auto` using native `TriggeredTags` so normal assistant text remains legal until `<|tool_call>` activates structured generation.
- [ ] Implement `required`/named tool as hard structural constraints, with optional reasoning represented without empty `ConstString` nodes.
- [ ] Keep hard choices fail-closed if a valid grammar cannot be constructed or validated.
- [ ] Keep generator accepted tool-name shape compatible with executable parser recognition.
- [ ] Run generation builder tests.
- [ ] Commit as `feat(gemma4): enforce native tool generation policy`.

### Task 6: Refit prompt-state grammar reconciliation to post-#4103 runtime templates

**Files:**
- Modify: `src/llm/io_processing/input_processors/chat_template_processor.cpp`
- Modify: `src/llm/io_processing/input_processors/chat_template_processor.hpp` only for a focused helper interface
- Test: `src/test/llm/input_processing/chat_template_processor_test.cpp` and Gemma4 prompt-state contract tests

**Interfaces:**
- Consumes: final rendered `req.promptText`, previously-built hard Gemma4 `GenerationConfig`, `PreparedRuntimeChatTemplate`/tokenizer rendering result
- Produces: `adaptGemma4HardToolGrammarForRenderedPrompt(...)` called at one common post-render boundary

- [ ] Add contract test where final rendered prompt ends in open `<|channel>thought` and hard tool grammar must be adapted to continue the same model turn.
- [ ] Cover both runtime-template and tokenizer/minja rendering paths through the common post-render behavior.
- [ ] Port the semantic grammar-shape recognizer from the historical branch against current StructuredOutputConfig interfaces.
- [ ] Apply reconciliation only when the existing structure matches the expected Gemma4 hard-tool grammar and the rendered prompt ends in an open thought channel.
- [ ] Revalidate adapted structured output and return an explicit invalid-argument status if validation fails.
- [ ] Do not restore old PyJinja constructors/wiring.
- [ ] Commit as `fix(gemma4): reconcile hard grammar after runtime template render`.

### Task 7: Refit conservative tool-response template adaptation

**Files:**
- Modify as required: current `src/llm/io_processing/chat_template/{analyzer,caps,probe}.{hpp,cpp}`
- Modify the current message/history adaptation layer discovered on `main`
- Test: chat-template analyzer/probe/input-processing tests

**Interfaces:**
- Consumes: detected chat-template capabilities and OpenAI `role=tool` content
- Produces: JSON-object conversion only when template semantics support it

- [ ] Add/retain regression demonstrating canonical Gemma4 parts-scanning templates break when tool-response string JSON is eagerly converted to an object.
- [ ] Keep conversion eligibility restricted to `role=tool`, string content, valid JSON object, and a capability that says object conversion is safe.
- [ ] Preserve arrays, scalars, invalid JSON, and non-tool messages as strings.
- [ ] Verify current upstream tool-definition adaptation is unchanged.
- [ ] Commit as `fix(gemma4): preserve canonical tool-response template semantics`.

### Task 8: Upstream parity and acceptance cleanup

**Files:**
- Modify: targeted tests/BUILD only where current upstream regressions are not already covered
- Modify: no production code unless an acceptance test exposes a scoped defect

**Interfaces:**
- Consumes: complete refit stack
- Produces: contribution-ready branch suitable for local Windows build/live acceptance

- [ ] Run targeted Gemma4 parser, reasoning, generation, input-processing, and chat-template tests.
- [ ] Run relevant upstream Gemma4 array regression tests.
- [ ] Run compile targets for all changed libraries/tests against current-main interfaces.
- [ ] Run repository license/style checks applicable to changed files.
- [ ] Inspect branch diff for generated evidence, binaries, operator guides, obsolete PyJinja wiring, hardcoded Gemma4 token IDs, or unrelated changes; remove any such material.
- [ ] Commit only additional regression coverage as `test(gemma4): cover upstream and streaming regressions`.
- [ ] Record exact branch HEAD and changed-file summary for the later local-machine build/test handoff.
