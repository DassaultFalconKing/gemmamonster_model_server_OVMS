# Comparative Gemma 4 Parser and Generation Verdict

**Status:** post-#4103 refit authority document  
**Date:** 2026-09-15  
**Target:** `staging/gemma4-upstream-refit-clean-20260915`  
**Upstream base:** `openvinotoolkit/model_server@a5136cb285482aaef5410a053b5ecd04ff9324ec`  
**Supersedes:** 2026-09-09 comparative verdict on `integration/gemma4-protocol-hardening-2026.5`

This document decides what Gemmamonster should preserve, port, reject, and own while refitting Gemma 4 agentic tool calling onto current OVMS `main`. It deliberately separates four concerns that are easy to conflate: **parser semantics**, **generation policy**, **special-token transport**, and **chat-template capability**.

Evidence labels:

- **AUTHORITY**: canonical protocol or model metadata.
- **VERIFIED**: directly observed in current source or a reproduced project contract.
- **EVIDENCE**: peer-runtime behavior/failure useful for our design, but not protocol authority.
- **OWN**: Gemmamonster policy chosen to satisfy the authority and OVMS/OpenAI contracts.

## 1. Source snapshot

The comparison is pinned to these source snapshots so future reviewers can distinguish drift from folklore:

| Source | Snapshot | Role in this verdict |
|---|---:|---|
| OVMS | `a5136cb285482aaef5410a053b5ecd04ff9324ec` | Target architecture after PR #4103 runtime chat-template split |
| vLLM | `e6960af33b379d502f409e3e2241bbf2b2c2f68d` | Parser FSM, prompt-state and token-boundary evidence |
| SGLang | `832ec39cc0324cb0e7823dc8385e27a30c356bdd` | Two-phase constraint behavior and generic-fallback failure evidence |
| llama.cpp | `d1d3c3396aa13a5f239109a822666c4870490ad5` | Native Gemma generation-policy reference and replay transform |
| Transformers | `3f162ca5fd2daef9cb36841be1337ad657addbfe` | Declarative `response_template`, prefix-aware response parsing |
| Google Gemma 4 | current 2026-09-15 docs/template/model metadata | Canonical wire and prompt-state authority |

Primary references:

- Google prompt formatting: https://ai.google.dev/gemma/docs/core/prompt-formatting-gemma4
- Google function calling: https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4
- Google/HF Gemma 4 model template: https://huggingface.co/google/gemma-4-31B-it/blob/main/chat_template.jinja
- vLLM Gemma parser: https://github.com/vllm-project/vllm/blob/main/vllm/parser/gemma4.py
- vLLM Gemma tool adapter: https://github.com/vllm-project/vllm/blob/main/vllm/tool_parsers/gemma4_engine_tool_parser.py
- SGLang detector: https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/function_call/gemma4_detector.py
- llama.cpp Gemma parser: https://github.com/ggml-org/llama.cpp/blob/master/common/parsers/gemma4.cpp
- Transformers Gemma response template: https://github.com/huggingface/transformers/blob/main/src/transformers/models/gemma4/convert_gemma4_weights.py

## 2. Authority hierarchy

The implementations are not interchangeable authorities.

1. **Google prompt format, current chat template and model metadata are protocol authority.** They decide canonical delimiters, reasoning/tool ordering and prompt continuation after tool responses.
2. **Transformers is the strongest current reference for model-declared response parsing.** It now consumes a declarative `response_template` carried by the tokenizer/model and parses raw special-token output with a decoded prompt prefix.
3. **vLLM is the strongest parser-state and streaming failure reference.** Its current Gemma4 ParserEngine has accumulated explicit handling for prompt-seeded reasoning, token-ID terminals, partial delimiters, `()` arguments and malformed/tolerated transitions.
4. **llama.cpp is the strongest current native generation-policy reference.** Its Gemma4 PEG path models native tool syntax, lazy auto triggering, hard required policy and the `parallel_tool_calls` repetition bound.
5. **SGLang is useful both positively and negatively.** It confirms two-phase reasoning/constraint semantics, but its Gemma4 detector currently has no native structural-tag generator and can fall back to generic JSON constraints. That is specifically not our target.
6. **OVMS/OpenVINO GenAI owns the implementation mechanism.** We port semantics into `OutputParser`, `OVMSTextStreamer`, `GenerationConfigBuilder`, `StructuredOutputConfig` and the post-#4103 template runtime instead of embedding another runner's parser framework.

## 3. Canonical protocol facts that drive implementation

### 3.1 Wire format

Canonical Gemma 4 tool calls are native syntax, not ordinary JSON:

```text
<|channel>thought
...reasoning...
<channel|><|tool_call>call:function_name{key:<|"|>value<|"|>,count:42}<tool_call|>
```

Relevant markers include `<|channel>` / `<channel|>`, `<|tool_call>` / `<tool_call|>`, `<|tool_response>` / `<tool_response|>`, `<|tool>` / `<tool|>`, and `<|"|>` for native structured strings.

**Consequence:** OpenAI-compatible JSON is an external API representation. The parser and generator must preserve Gemma-native boundaries on the model side.

### 3.2 Tool-loop reasoning continuity

Google's current template preserves reasoning on assistant tool-call turns. Between calls in the same tool-use turn the reasoning state is part of protocol continuity, not disposable debug text.

After a tool response with thinking enabled, the current template can end the rendered prompt in an **already-open** thought channel. With thinking disabled, larger Gemma variants may render a closed empty thought channel before generation to suppress ghost-thought behavior.

**Consequence:** a generation grammar built before rendering cannot assume every request begins at a new model-turn boundary. Hard generation policy must be reconciled with the **rendered prompt state**.

### 3.3 Current model metadata now describes response parsing

Current Gemma4 Transformers conversion/model metadata includes a declarative response template with:

- `start_anchor`: `<|turn>model\n` or `<tool_response|>`;
- `thinking`: `<|channel>thought\n ... <channel|>`;
- repeated tool calls matching `<|tool_call>call:(name)` ... `<tool_call|>`;
- unquoted native keys;
- `<|"|>` string delimiters;
- content terminators including `<turn|>`, `<|tool_response>` and `<eos>`.

Transformers resolves tokenizer-provided `response_template` before its model-type fallback and supplies the decoded prompt as parser `prefix`.

**Consequence:** long-term, parser capability should increasingly come from model metadata. For this contribution, the C++ parser remains explicit because OVMS does not yet expose this metadata as a generic parser contract. We should not create a second metadata framework inside this PR.

## 4. Updated comparative matrix

### 4.1 Parser

| Question | Google / Transformers | vLLM | SGLang | llama.cpp | Gemmamonster decision |
|---|---|---|---|---|---|
| Canonical opener | `<|tool_call>call:name...` | canonical plus guarded tolerance | canonical wrapped detector | canonical PEG | **ADOPT canonical; tolerate only observed bounded variants** |
| Native strings | `<|"|>` | explicit preservation/parser | explicit parser | PEG rule | **ADOPT explicit delimiter parser** |
| Nested arrays/objects | metadata/native JSON-like grammar | recursive | recursive | recursive PEG | **ADOPT recursive parser** |
| `{}` and `()` call args | canonical is object-like; response parser tolerates format | both accepted | detector primarily object-shaped | grammar path handles native structure | **ADOPT both as parser tolerance** |
| Numbers | response parser treats JSON-like content | partial-value guards | converts via Python int/float | JSON-number grammar | **OWN lexical-lossless JSON-number validation** |
| Request tool registry | application validates tool calls | parser receives tools | detector/frontend has tool set | grammar built from tools | **ADOPT request registry; unknown call is non-executable** |
| Bare `call:` recovery | not canonical | accumulated recovery support | not primary detector path | not canonical | **OWN line/phase-boundary + registry guard** |
| Malformed call | application must validate | recovery evolves with regressions | permissive detector behavior | grammar prevents many malformed outputs | **OWN fail-closed execution, bounded recovery** |

Parser verdict: the clean staging parser direction is retained. It is intentionally stricter than SGLang's bare-value conversion and more precision-preserving than float-based normalization.

### 4.2 Generation policy

| API policy | vLLM current Gemma4 | SGLang current Gemma4 | llama.cpp Gemma4 | Gemmamonster target |
|---|---|---|---|---|
| no tools | no active tool parser grammar | no active tool constraint | no tool grammar | no tool grammar |
| `tool_choice=none` | no forced tool | disabled | tools disabled | no tool grammar; `response_format` remains usable |
| `auto` | native model output; parser-driven | frontend may construct constraints | lazy trigger on `<|tool_call>` | **lazy native `TriggeredTags` on `<|tool_call>`** |
| `required` | explicitly avoids generic structured JSON for Gemma4 | may fall back to generic JSON schema | native grammar with minimum one call | **hard native structural grammar, at least one call** |
| named | does not claim native hard enforcement | hard frontend path, fallback risk | native grammar constrained to selected tool | **hard native structural grammar, selected tool only** |
| parallel false | API-level semantics exist | policy reaches grammar frontend | native repeat max=1 | **`stop_after_first=true`** |
| parallel true | repeated calls parsable | repeated calls supported | unbounded native repeat | **repeat native tags** |
| grammar validation failure | Gemma adapter avoids conflicting generic grammar | backend-dependent | construction-time grammar contract | **hard choices fail closed; auto may fall back** |
| active tools + response format | implementation-specific | generic structured-output composition risk | response-format branch and tool branch are separate | **OWN explicit rejection instead of silent precedence** |

Critical correction to the old dossier: **vLLM is no longer our hard-generation model.** Its current `Gemma4EngineToolParser` sets `supports_required_and_named = False` and deliberately skips generic structured JSON for hard choices because that mechanism conflicts with native Gemma syntax and has caused content leakage/speculative-decoding failure. That is strong negative evidence for using generic JSON-schema output as the whole hard grammar.

llama.cpp is the better current semantic source for native generation policy: lazy auto trigger, hard minimum-one, and parallel repetition bounds. OpenVINO GenAI `StructuredOutputConfig` is the mechanism used to express those semantics in OVMS.

### 4.3 Special-token approach

| Concern | Transformers | vLLM | SGLang | llama.cpp | Gemmamonster decision |
|---|---|---|---|---|---|
| Parser input | raw decode with structural tokens | token IDs + preserved delimiters | text detector buffer | preserved tokens + PEG | **parser sees structural tokens** |
| User-visible output | structural regions translated/stripped | semantic events/deltas | parsed calls/content | parsed message | **client must not receive structural tokens** |
| Phase entry | response-template anchors + prefix | tokenizer-derived token terminals | textual markers | preserved markers/grammar | **dynamic tokenizer ID resolution, no hard-coded IDs** |
| Prompt prefill | parser gets decoded prompt prefix | adjusts initial parser state from prompt | separate reasoning handling | rendered prompt influences grammar | **rendered prompt must inform parser/generator state** |
| reasoning -> tool adjacency | declarative regions | explicit FSM transition | known fragile area | grammar boundary | **reconcile decode phase before inspecting next token** |

The pending `Gemma4SpecialTokenHandoffTest` expresses the key OVMS regression: with the production default `skip_special_tokens=true`, an adjacent `<channel|><|tool_call>` must not lose the tool opener while the streamer changes decode mode between phases.

Target ordering in `OVMSTextStreamer`:

1. reconcile decode mode for the phase established by the **previous** flushed text;
2. flush any pending cache needed for that transition;
3. re-read parser phase because the flush may itself complete reasoning;
4. then inspect the **current token** for a token-ID phase opener;
5. synthesize/flush the resolved structural start tag and switch phase before subsequent tokens.

This is a generic streaming correctness rule, not a Gemma-specific token-ID table.

### 4.4 Template capability

| Capability | Current Google template | Current OVMS main | Gemmamonster decision |
|---|---|---|---|
| Assistant `tool_calls[].function.arguments` | requires mapping/object when replayed into template | `requiresObjectArguments` probe/adapter exists | **KEEP; load-bearing** |
| Tool definition `response` field | canonical tool schema does not want arbitrary server extension | analyzer can remove it | **KEEP existing capability path** |
| role:`tool` string JSON -> object | current template accepts strings and also iterates sequence-like content parts | no generic conversion | **DO NOT convert unconditionally** |
| runtime Jinja vs Minja | both must render same protocol semantics | #4103 split creates prepared runtime path plus tokenizer path | **apply prompt-state reconciliation after both paths converge** |
| parser capability metadata | model now carries `response_template` | not yet a generic OVMS parser input | **FOLLOW-UP, not this PR** |

Important trap: the current Google template has a content-part path using `part.get(...)`. A Jinja mapping can also look sequence-like. Therefore blindly converting every role:`tool` JSON string into a mapping can route it into the wrong template branch and fail with string/key iteration errors. Any such conversion must be explicitly capability-gated. The canonical current template does not justify a global conversion.

## 5. Prompt-state generation model

Hard tool generation has three materially different starting states.

### State A: new model turn, thought not pre-opened

Valid hard behavior is either:

```text
<|tool_call>...
```

or, where reasoning is allowed:

```text
<|channel>thought
...
<channel|><|tool_call>...
```

A hard grammar may therefore be a union of `tools-only` and `thought-then-tools`.

### State B: prompt already ends inside an open thought channel

This occurs after a tool response under the current template with thinking enabled. Requiring another thought opener is wrong because the model is already inside it.

Correct behavior is:

```text
...continue thought from prompt...
<channel|><|tool_call>...
```

The old Gemmamonster implementation solved this after rendering by adapting the hard grammar to a tool trigger with `at_least_one=true`. That lets ordinary sampling finish the already-open thought, but the request still cannot complete without entering an allowed tool tag.

**Decision:** preserve that semantic fix, refit it to post-#4103 `ChatTemplateProcessor`, and run it after runtime-Jinja and tokenizer/Minja paths converge on `req.promptText`.

### State C: template has already emitted a closed empty thought block

This can occur when thinking is disabled on larger Gemma variants. Generation begins after a valid closed reasoning block, so ordinary hard tool grammar remains correct and no prompt-state rewrite is needed.

## 6. Adopt / reject / own ledger

| Decision | Classification | Source | Why |
|---|---|---|---|
| Recursive native argument parser | ADOPT/REFIT | vLLM, SGLang, llama.cpp, Google metadata | independent implementations agree on nested native structure |
| Lossless numeric lexemes | OWN | Google native wire + JSON API correctness | SGLang float conversion is insufficient for exact API arguments |
| Dynamic special-token IDs | ADOPT | vLLM/Transformers + existing OVMS infrastructure | tokenizer revisions must not require hard-coded numeric IDs |
| Bare-call recovery only at logical boundary and known tool | OWN | vLLM failure evidence + Google canonical strictness | recovers observed model leak without executing prose examples |
| Auto = lazy `<|tool_call>` trigger | ADOPT/REFIT | llama.cpp + OpenVINO structural tags | preserves ordinary text/reasoning until tool syntax actually begins |
| Required/named = native hard grammar | ADOPT/REFIT | llama.cpp; vLLM negative evidence | generic JSON hard output conflicts with Gemma native syntax |
| Hard validation failure = fail closed | OWN | OpenAI `required`/named semantics | silently becoming `auto`/unguided violates caller contract |
| `parallel_tool_calls` controls grammar repeatability | ADOPT | llama.cpp + OpenAI semantics | policy must constrain generation, not merely post-process output |
| Active tools + `response_format` reject | OWN | conflict analysis; llama branches these modes | prevents silent policy replacement |
| Prompt-state grammar adaptation after rendering | OWN/REFIT | Google current template + Transformers prefix-awareness | grammar must match actual generation point |
| Unconditional tool-response JSON object conversion | REJECT | current Google template | can enter wrong content-part branch |
| Copy vLLM ParserEngine into OVMS | REJECT | architecture | semantics useful; framework transplant is unnecessary |
| SGLang generic JSON fallback for Gemma hard choices | REJECT | SGLang current detector lacks native structural tags | wrong wire grammar for native Gemma calls |
| Implement full `response_template` metadata engine in this PR | DEFER | Transformers/model metadata | correct long-term direction, excessive scope for current upstream contribution |

## 7. Implementation sequence for post-#4103 clean refit

The following order is intentional. Each behavioral change must have a failing/contract test before production code where the current environment permits it.

1. **Special-token handoff**
   - Existing contract: `Gemma4SpecialTokenHandoffTest`.
   - Fix the generic streamer ordering described in section 4.3.
   - Do not add Gemma numeric token IDs.

2. **Generation/API policy**
   - Add HTTP contract for `parallel_tool_calls` -> `OpenAIRequest`.
   - Add Gemma builder contracts for `none`, `auto`, `required`, named, parallel true/false, invalid tool schema/name, hard validation failure and response-format collision.
   - Add `Gemma4GenerationConfigBuilder` using native structural tags.
   - `auto`: lazy trigger.
   - hard choices: at least one allowed native tool call and fail closed.

3. **Rendered-prompt state reconciliation**
   - Add post-#4103 tests covering prepared runtime Jinja and tokenizer/Minja convergence.
   - Refit hard grammar after prompt render when the prompt ends in an already-open thought channel.

4. **Template capability hardening**
   - Preserve object-argument replay adaptation.
   - Do not add unconditional role-tool JSON conversion.
   - If a generic tool-response conversion capability is retained for non-Google templates, detection must explicitly exclude templates that iterate content parts with `part.get(...)`.

5. **Acceptance and history hygiene**
   - Import upstream/current array and parser regression cases.
   - Run build/unit/HTTP/live acceptance where the target Windows environment is available.
   - Rebuild/reword the final clean contribution history so every production commit carries the provenance format below.

## 8. Commit provenance contract

Every subsequent behavioral commit in this refit must use this body shape:

```text
<type>(gemma4): <short semantic change>

Provenance:
- <canonical doc / runner source / commit / PR>
- <second source when relevant>

Driven by:
- Observation: <the exact token, prompt, request or failure state that exposes the bug>
- Contract: <the canonical protocol or API behavior that should hold>

Fixes:
- <failure mode>
- <regression test or acceptance probe that detects it>

Decision:
- OWN/ADOPT/REFIT: <what was chosen>
- Rejected alternatives: <what was deliberately not copied and why>
```

Test-only commits should use the same `Provenance / Driven by / Fixes` sections and explicitly state the expected RED condition when the production fix is not yet present.

## 9. Current clean-staging status

Before this refreshed dossier, clean staging contains:

- `8488307d` — post-#4103 parser protocol contracts;
- `bed7a1e5` — recursive/lossless native argument parser;
- `e001de93` — request-registry and logical-boundary bare recovery;
- `251f4b58` — RED contract for special-token reasoning -> tool handoff.

These commits predate the explicit provenance-message requirement introduced during this refit session. Before promotion to the final contribution branch, their messages must either be reconstructed with equivalent provenance bodies or be covered by an immutable provenance ledger. Preferred outcome: reconstruct the final clean history so reviewers can see provenance directly in each behavioral commit.

## 10. Review questions to resolve by observation, not library trivia

No user decision is blocking implementation yet. If a semantic fork appears, it should be presented as an observable experiment. The useful questions are of the form:

- after this exact rendered prompt suffix, what first tokens does the model actually emit?
- when `required` is active, does the model finish a thought and then call a tool, or try to emit prose after the close?
- when `parallel_tool_calls=false`, does the model attempt a second native call and how does GenAI terminate the structural grammar?
- does the live template receive prior assistant arguments as string or mapping at the point where it fails?
- on a failing stream, which raw token ID/text boundary disappears before the parser sees it?

Those observations identify the broken layer much more reliably than asking whether a particular helper class is theoretically supposed to support the case.

## 11. Final architectural verdict

Keep the OVMS-native design. The correct synthesis is:

- **Google/model metadata** defines the protocol and prompt state;
- **Transformers** demonstrates declarative response parsing and prefix-aware state;
- **vLLM** supplies mature parser FSM and token-boundary evidence;
- **llama.cpp** supplies the strongest native generation-policy semantics;
- **SGLang** supplies two-phase constraint evidence and a useful warning about generic fallbacks;
- **OpenVINO GenAI** supplies the structural-tag execution mechanism;
- **Gemmamonster** owns the safety joins: request registry, fail-closed hard policy, prompt-state reconciliation, lexical precision, and cross-chunk boundary discipline.

The goal is not to make OVMS behave like another runner. The goal is to make the same Gemma 4 protocol survive OVMS streaming, OpenAI request semantics, current Google templates, speculative/structured generation and real multi-turn agent loops without requiring the client to know which internal subsystem happened to be confused that day.
