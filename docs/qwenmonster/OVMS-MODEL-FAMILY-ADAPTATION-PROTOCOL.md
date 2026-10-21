# OVMS Model-Family Adaptation Protocol — MFP-1

Status: **PROPOSED STANDARD**, distilled from Gemmamonster C5/C5fixed/C6 and current Qwenmonster work.
Scope: onboarding a model family to OVMS **without** confusing template, parser, generation policy, inference, and harness behavior.

## A0. Identity and isolation (must precede patches)

- Pin `BASE_SHA`, tree SHA, exact model checkpoint, official tokenizer revision, official chat-template hash, OVMS/GenAI/XGrammar versions, runtime DLLs/compiler/Bazel, OS/device/hardware and launch profile.
- Record whether `VLM_CB` or `LM_CB` actually works. Build-success is not device/runtime acceptance.
- Freeze current known-good, use fresh worktree + feature branch, never refactor the working family incidentally.
- Keep C5, C5fixed and C6 **different identities**. A known-good snapshot is not automatically an ancestor or equivalent to a new release.
- Start and maintain `STATE.md` and evidence paths before code mutation.

## A1. Canonical protocol contract

- Official model card, canonical Jinja/template, tokenizer, prompt examples, assistant/tool-role serializer, generation suffix.
- Native role markers; reasoning channel; tool opener/closer; argument wire types; empty args; multiple calls; tool response replay.
- Render golden no-tool, one tool, N tools, tool-result loop, thought ON/OFF, preserve_thinking ON/OFF, partial assistant prefix.
- Compare rendered **token IDs** in addition to decoded text; do not treat visually equivalent Jinja as token-equivalent.
- Classify by capability fixture rather than name substring. Family variants are explicit exceptions.

## A2. Peer implementation dossier

- Sources: vLLM (parser state & streaming), llama.cpp (generation & grammar), SGLang (independent detector and failure cases), original model template/Transformers, current upstream OVMS/GenAI.
- For every mechanism record pinned upstream source, commit/PR, exact known fail/success, our corresponding code/test and **KEEP/REFINE/PORT SEMANTICS/TOLERANCE ONLY/DROP/UNKNOWN**.
- Peer server behavior is not authority to redefine canonical model protocol. Import **semantics**, not unrelated frameworks.
- Always include at least one adversarial test from a known upstream incident.

## A3. OVMS architecture contract

- `ChatHistory/Jinja` owns request replay and rendered generation prefix.
- `GenerationConfigBuilder` owns tools policy and OpenVINO GenAI structured masks.
- `OutputParser` owns generic phase routing, flush/remainder and parser ownership.
- Family `BaseOutputParser` descendants own native FSM and argument normalization.
- `OVMSTextStreamer` owns token decode and ordered lifecycle flush/drain.
- `OpenAI API` owns tool_calls IDs/index, finish_reason and response contract.
- `Harness` owns *execution*, never the parser.
- No second parallel parser pipeline without evidence that the generic phase-owner path is insufficient.

## A4. Parser-first RED corpus and refit

- Streaming/unary and byte/token/chunk-split invariance.
- Canonical 1/N tool calls, repeated same function, 0 args, multiline and nested typed values.
- Reasoning→tool and content→tool, tool→tool, prompt already in reasoning.
- Malformed: bare start, missing close, dangling parameter, end-marker drift, quoted attributes, unknown tool, false-positive XML text.
- Preserve exact native text and emitted deltas before modifying code. `STOP`, `LENGTH`, cancellation, error must have different recovery obligations.
- No unknown tool or incomplete argument becomes executable. Reject invalid type instead of silently casting into an arbitrary string.
- Cross-request/choice reset and bounded buffer sizes; run anti-contamination tests.

## A5. Generation policy as independent component

Build a new family-specific builder only when its native wire differs. Explicit matrix:
- `none`: no guided tools; API must not publish executable tool call.
- `auto`: native unconstrained reference first; optional lazy constraints only after A/B and trigger analysis, never force a call.
- `required`: **at least one valid call**, from first constrained token, fail closed if unsupported.
- `named`: exactly specified registered schema, fail closed if unavailable.
- `parallel=false`: at most one call; `parallel=true`: multiple independent tool IDs permitted.
- Must pass reasoning-prefix compatibility (open `<think>` and tool-after-thought) and validate full JSON Schema including optional, required and nested object/array before claiming correctness.
- Compile/tag validation failure in a hard mode MUST be an explicit API error; never downgrade to `auto`.
- Preserve existing response_format when tools disabled; reject conflicting active constraints.

## A6. Runtime seam validation

- Check model and tokenizer actual token IDs for native markers (some are plain multi-token strings).
- Check GenAI/XGrammar version, structural-tag grammar compilation and runtime masks; raw serializer shape is not proof of successful compilation.
- Record `VLM_CB/LM_CB` lane and GPU device, TTFT/TG, memory, faults and executor quarantine.
- Keep parser syntax and inference/kernel errors separate. Do not misdiagnose `CL_OUT_OF_RESOURCES` as grammar fault.

## A7. Behavioral/differential evaluation

- Run the same pinned native output corpus against vLLM, llama.cpp and OVMS: compare semantic JSON and reasoning, then streaming event reconstruction. Classify disagreements with proof.
- Run equal OpenAI request schemas and sampling controls against real model.
- Track phases independently: tool visible → model chose → model emitted → parser extracted → API returned → harness executed → subagent finished.
- Separate autonomous delegation rate from successful native tool delivery. Scale long prompts, multi-agent loops and 1/2/4 sessions only after short protocol gate.

## A8. Acceptance ladder (no fake GREEN)

1. `SOURCE VERIFIED`: source locations and pinned versions confirmed.
2. `RED REPRODUCED`: failing baseline test/log preserved.
3. `STATIC PATCH`: code committed and scoped.
4. `BUILD GREEN`: exact binaries/toolchain, test target resolves.
5. `UNIT GREEN`: deterministic parser, policy, template and negative controls pass.
6. `API GREEN`: unary + SSE + Responses if applicable, correct finish/IDs/deltas.
7. `RUNTIME GREEN`: actual model/device/lane on identical pinned candidate.
8. `AGENTIC GREEN`: repeated multi-turn tool loops, no silent drops, no cross-session contamination.
9. `ACCEPTED`: all gates and Gemma/no-change negative controls, evidence paths and owner signoff.

A null/empty evidence file never counts as PASS. A patch from one model must not be promoted using another model's successful run.

## A9. Release and upstream contribution

- One mechanism per atomic commit: parser → generation → reasoning/template → acceptance.
- Independently revertible, short upstream PRs: `Problem → Reproducer → Root cause → Fix → Negative control → Live evidence`.
- No model weights/runtime dumps/local paths/secret tokens in PR.
- Before every upstream version bump, conduct three-way rebase by **behavior**: official model contract + current upstream OVMS + pinned accepted local implementation.
- Drift watch for template, tokenizers, XGrammar masks, GenAI API and model revisions.
- After each stage update `ACTIVE_STAGE, BASE_SHA, CURRENT_HEAD, LAST_GREEN_TESTS, CURRENT_FAILURE, NEXT_ACTION, REVERT_POINT, EVIDENCE_PATH`.

## Current application: Qwenmonster

A0 partially proven (C6 SHA), A1/official template token-level pin pending, A2 sourced and documented, A3 applied, A4 source patches only, A5 builder candidate, A6–A8 not yet run. No ACCEPTED status.
