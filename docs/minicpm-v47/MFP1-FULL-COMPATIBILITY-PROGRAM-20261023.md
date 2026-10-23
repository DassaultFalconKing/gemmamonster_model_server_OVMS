# MFP-1 implementation program: full MiniCPM-V 4.7 / 35B-A3B agentic and VLM compatibility

Date: 2026-10-23. Status: **DESIGN / IMPLEMENTATION ROADMAP, ZERO CODE ACCEPTED**.

**Normative project contract:** [`OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md`](../qwenmonster/OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md), A0–A9, including A3.1 anti-hallucination parser-retainer and the channel-ownership exceptions.

**Runtime precondition:** [Arc 140V evaluation](ARC140V-EVALUATION-20261023.md). Parser/policy work can run without model weights; claims about GPU or full multimodal serving need separate observed evidence.

## 0. What is being ported (and what is NOT)

Target: `OpenVINO/MiniCPM-V-4.7-35B-A3B-int4-ov` (multimodal **MiniCPM-V v4.7**, MoE), source `openbmb/MiniCPM-V-4.7-35B-A3B`.

- This **is not** `MiniCPM5-1B/2B` (text model). Existing OVMS `src/llm/io_processing/minicpm5` parses **attribute-form** `<function name="x"><param name="y">...`. It cannot be selected for v4.7 merely because the names share MiniCPM.
- v4.7 is a distinct multimodal model with an officially rendered Qwen-like envelope: `<tool_call>` / `<function=NAME>` / `<parameter=NAME>` / `</parameter>` / `</function>` / `</tool_call>`, tool results using `<tool_response>`. This **suggests** the existing `qwen3coder` retainer, but text similarity does not prove byte/token, schema, role-history and streaming equivalence.
- 1B and 35B-A3B are both v4.7 but with different text backbones/quantization. Keep 35B-A3B as primary target; do not assume matching tokenizer revisions, model config, VLM behavior or tool quality from a 1B smoke test.
- Existing `Qwen3CoderGenerationConfigBuilder` currently belongs to the `qwen3coder` selector; `MiniCPM5` currently has no dedicated generation builder and differs in tool wire. **Do not route v4.7 through minicpm5 or rewrite qwen3coder as a side effect.**
- The v4.7 `enable_thinking` default and complete prompt suffix must be pinned to **the model revision actually downloaded**. Upstream template revisions have changed; external examples disagree on defaults. The renderer/tokenizer is the authority.
- The OpenVINO IR does not magically include the original HF vLLM/llama.cpp tool parser, a constrained generation policy, OpenAI streaming API wrapper, or specialized multimodal event parser. These are independent integration tasks.

### Authoritative peer and upstream sources

1. Canonical original template: https://huggingface.co/openbmb/MiniCPM-V-4.7-35B-A3B/blob/main/chat_template.jinja (pin git revision and file SHA256).
2. Published INT4 IR + processor/generation files: https://huggingface.co/OpenVINO/MiniCPM-V-4.7-35B-A3B-int4-ov (pin revision and local SHA256).
3. Merged export Optimum Intel PR #2033: https://github.com/huggingface/optimum-intel/pull/2033 (VLM export; no proof for 2026.4 SDK).
4. Merged GenAI VLM PR #4591: https://github.com/openvinotoolkit/openvino.genai/pull/4591 (image/video VLM support; upstream may be newer than our pinned SDK).
5. Existing in-tree code `src/llm/io_processing/qwen3coder/{qwen3coder_tool_parser.cpp,generation_config_builder.hpp,tool_schema_profile.cpp}`, `src/llm/io_processing/{output_parser.cpp,generation_config_builder.hpp,parser_config_validation.cpp}`, `src/llm/io_processing/minicpm5/*` for negative controls; exact code ref `eb76a74f7aa39573d452d95443e189b1f5f4d9e8`.
6. Peer behavior: pinned source commits for vLLM/SGLang/llama.cpp/Transformers MiniCPM-V 4.7, with native tool-call parser, reasoning and generation suffix only where actually implemented. **No unpinned copy-paste from latest.**

## 1. A0: provenance and parallel work boundaries

- Start from freeze SHA `eb76a74f...` in independent worktree; this branch is **docs/test evidence track**. Separate code PR/branch from this docs baseline only after recording HEAD and exact runtime dependencies.
- Produce `SOURCE-LOCK.json`: OVMS Git SHA, original/HF IR revisions and file hashes, tokenizer config/template and rendered prompt hash, exact GenAI/OpenVINO/XGrammar/minja/transformers source tags or commits, binary SHA256/size, loaded DLL map, GPU driver, compiler and active `LM_CB` vs `VLM_CB`.
- Create/update `STATE.md` before edits. Progress transitions: `SOURCE VERIFIED → RED REPRODUCED → STATIC PATCH → BUILD GREEN → UNIT GREEN → API GREEN → RUNTIME GREEN → AGENTIC GREEN → ACCEPTED`. Every stage needs an evidence pointer and explicit NOT_RUN where appropriate.
- Do not merge/proactively edit Gemma4, Qwen3Coder, Ornith, RC3B, the canonical template, Qwen3Coder schema utilities or CIB2 memory/offload. Keep user-facing endpoint localhost only for eval.

## 2. A1: canonical native protocol dossier (MCPV47-01 P0)

Use the precise checkpoint tokenizer + official Jinja, rendered via the exact HF tokenizer/processor when available, to generate both rendered bytes **and token IDs** for these cases:

| Case | Contract evidence |
| --- | --- |
| `plain no-tool` | role prefix, final assistant suffix and native stop tokens |
| `think ON` | actual beginning, closing of `<think>`/`</think>`, tool transition position |
| `think OFF` | whether template already writes a closed think span; **no fake extra closer** |
| `tool 1 / tool N` | full envelope, between-call separator, ID semantics and expected end-of-turn |
| `tool result` | exact `tool` replay: template may insert user role and `<tool_response>`; do not manufacture a distinct top-level `tool` wire if official template does not |
| `zero args` | empty function and empty-schema tool, no inferred required params |
| `nested / strings` | quoting, numeric spelling, newlines and empty string, repeated parameter keys |
| `partial assistant` | suffix with add_generation_prompt, prefilled tool/thought and incomplete marker boundaries |
| `image / multi-image / video` | content role, image patches/frame placeholders, thinking controls and tool history coexist |

Known structural example, subject to exact canonical revision:

```text
<tool_call>
<function=search>
<parameter=query>
term
</parameter>
</function>
</tool_call>
```

Do **not** assume MiniCPM's `<think>` handling is exactly Qwen3.6. In particular, document whether tool-call open can appear while `think` is still open. No generic Gemma handoff or Qwen reasoning-close heuristic without canonical evidence.

Record special-token *IDs* for tags/stop, and whether rendered strings are tokenizer special tokens or ordinary text. Identify differences from qwen3coder per token/transition; make a `PROTOCOL-DOSSIER.md` with `KEEP / REFINE / PORT SEMANTICS / NEW / REJECT / UNKNOWN`.

## 3. A2: peer implementations and adoption rule (MCPV47-02 P0)

Independent reviewer studies official model Jinja, HF Transformers `MiniCPMV4_7Processor`, upstream GenAI `VLMPipeline`, vLLM and llama.cpp server formats, SGLang only if a v4.7 implementation is found. Pin exact commits/PRs and reproduce at least one known upstream failure as adversarial test.

Only adapt proven native semantics. A peer vLLM/sampling implementation is not authority to rewrite canonical prompt. Explicitly determine whether v4.7 tools are actually usable from the OpenVINO IR tokenizer and whether bare `qwen3coder` mode reproduces byte-identical transcripts before adding a new class.

## 4. A4 before patches: RED corpus and test architecture (MCPV47-03 P0)

Place new tests under `src/test/llm/output_parsers/` and, for request/render logic, the appropriate existing chat-history/template/API test location. Keep new fixtures in `docs/minicpm-v47/fixtures` or repo's test fixture path; no model weights committed.

**Mandatory classes of fixtures**

- `T01–T06`: no tools, 1 call, adjacent 2–4 calls, repeat same name, empty tool schema, return to assistant after tool result.
- `T07–T11`: literal `C:\tmp\foo`; escapes `\t` and `\\`; Unicode and embedded quote/equals/comma; nested numeric `1.10`, `1e3`, `9007199254740993`; nested mixed object/array; empty string vs null.
- `T12–T18`: unknown tool, fabricated/missing required argument, invalid typed value, duplicate key, malformed/partial closing tag, tool-looking XML in plain content, unreasonable depth/length; none may become executable.
- `T19–T25`: thoughts with tool-looking drafts, legal reasoning→tool boundary, think ON/OFF, prefilled think, stream chunk split at every byte/token boundary, unary/SSE equivalence, repeated two-turn reset.
- `T26–T30`: stop vs length vs cancellation vs exception, trailing garbage, multi-choice ID/index identity, multiple requests concurrent, parallel=false contract.
- `T31–T34`: image/text and tool calls same conversation; tool reply followed by another image; multi-image and video history; parser must not swallow multimodal placeholders or mix reasoning with visible content.

Every failure has a captured raw model output or deterministic synthetic transcript and expected authoritative output. **Preserve baseline RED before fixing.** If original model cannot yet run, label fixture `SYNTHETIC`, not `LIVE`. Unknown or unsupported schema keywords must cause hard-mode rejection, never false PASS.

## 5. A3.1: native anti-hallucination parser-retainer (MCPV47-04 P0)

Decision tree:

1. Run `qwen3coder` parser with canonical MiniCPM-v4.7 fixtures **without edits**, and compare exact outputs/deltas.
2. If *all* native grammar, special-token, reasoning and stop rules match, reuse the Qwen3Coder implementation via an explicit **family adapter/selector with tests**, not by pretending the model is a Qwen3.6.
3. If they do not match, implement `MiniCPMV47ToolParser` extending `BaseOutputParser`. It may reuse proven lower-level XML parsing helpers but **must own** variant-native FSM, delimiter status, title/arguments serialization, stream retention and `STOP/LENGTH`.
4. Separate `MiniCPMV47ReasoningParser` only if Qwen3 logic cannot satisfy the exact native thinking boundaries; avoid a second global output pipeline.

**Retainer invariants:**

- Correct `reasoning / content / tool` ownership and no public tool call from thought draft.
- Do not publish name/ID/index/argument deltas before eligibility and completeness are established. Validate against registered tool catalog and supported schema profile **prior** to executable publication; no progressive publication that needs retraction.
- Preserve raw literal strings (encode once) and exact JSON numeric lexemes without DOM-double roundtrip; nested fields too. No silent fallback from invalid typed values to strings. Boolean and JSON type normalization only as explicitly allowed by canonical wire.
- No tool-name invention, default-arg completion, schema coercion or “repair” of an unfinished call. A missing outer transport delimiter may be tolerated on STOP **only** if full inner semantic payload is proved complete and the tolerance has canonical evidence; LENGTH/cancel never close incomplete values.
- Stateless across requests and choices; bounded buffering, depth, number of calls and payload size, resource exhaustion produces explicit error.
- Multiple tool calls keep separate stable generated IDs/order/index; unary JSON and reconstructed streaming match exactly.
- Tool results returned to model exactly as template requires; once the next assistant message opens, previous thoughts must not replay as if the model generated them anew.

No edits to existing Gemma4/Qwen3Coder family implementation unless a separately demonstrated shared bug and its own independently gated PR justify it. Model-specific wrapper preferred.

## 6. A5: tool-generation policy (MCPV47-05 P0)

Add `src/llm/io_processing/minicpmv47/generation_config_builder.hpp` (naming may match existing layout) and register a dedicated `minicpmv47` selector in `GenerationConfigBuilder`. Implement the OpenAI request semantics using **available 2026.4 RC1 GenAI/XGrammar structural tags**, not APIs from untested 2026.5.

| Mode | Required behavior | Explicit failure |
| --- | --- | --- |
| `none` | no tool grammar, no executable tool publication; non-tool response_format preserved | tool candidate must remain non-executable |
| `auto` | base native generation unforced; optional lazy trigger at legal tool transition only, disabled if benchmark fails | never force a call or start tool inside thought |
| `required` | ≥1 valid registered call before completion, hard constrained from applicable generation prefix | grammar build/validation error; never quietly degrade to auto |
| named `{"type":"function","function":{"name":"..."}}` | only named registered function with matching schema | unknown name/incompatible schema = explicit API error |
| `parallel_tool_calls=false` | at most one call including streaming | second call rejected/prevented; no hidden second action |
| `parallel_tool_calls=true` | independent calls with stable IDs/index; only if native protocol supports | explicit capability error if not implementable |

Policy must handle **both** rendered thinking-prefix states:

- Think ON: if the template opens reasoning, the grammar must close it **before any permitted tool-call production**, if and only if that is the canonical order. The native grammar may need `Concat(Tag(...),TagsWithSeparator)`; verify against installed headers and test output.
- Think OFF: if template already outputs a closed reasoning span, do **not** generate a second closer. Start native tools from legal fresh suffix.
- `auto` guided strategy should be opt-in. First establish native unguided baseline with capture. `required` and named must be validated against real schema-dependent outputs. If structural tags cannot encode MiniCPM-v4.7's exact syntax, record `GENAI_GRAMMAR_API_GAP` and leave hard modes **unsupported with explicit error**.
- Validate supported JSON Schema: `required` vs optional, enums, string/number/integer/bool/null, nested array/object, escaping, unknown keywords. Note precisely supported subset (Qwen Draft4 parser profile is not an arbitrary full JSON Schema implementation).
- Enforce `stop` and `finish_reason` meaning for tool calls, length and cancellation; don't confuse parser recognizing a call with model policy enforcing a choice.
- Preserve standard `response_format` and reject mutually exclusive constraints in one request.
- Generate *template-specific* prefix/token checks with every policy test; never reuse a Qwen grammar merely because similar text labels were found.

## 7. A3/A6: OpenAI API, streaming lifecycle and history (MCPV47-06 P1)

Verify end-to-end seams:

- `ChatHistory/Jinja` and VLM `MiniCPMV4_7Processor`: user, assistant, tool history, image blocks and follow-up, think defaults, `enable_thinking` flags and exact generation suffix.
- `OutputParser` and `OVMSTextStreamer`: decoding of special tokens, tool/reasoning handoff, buffered incomplete markers, unary vs `stream=true` and SSE, ordered finalization, cancellation cleanup.
- API shape: `message.content`, `reasoning_content`, `tool_calls[].id/type/function.name/function.arguments`; streamed `delta.tool_calls[index]`, correct finish reason for tool calls vs normal completion vs length; never leak native delimiters into visible text.
- `VLM_CB` and session-state behavior: C1 first, then C2/C4; correct tool-result replay within multimodal histories. Do not mark VLM compatibility from successful text-only GenAI; support `image_url`/frames is a distinct endpoint capability.
- Failure modes: if CB/VLM processor or image input path missing under RC1, declare **runtime blocked** even if parser/policy isolated tests pass. Keep model and OpenVINO runtime independent from policy PR.

## 8. Production-quality gates and test commands (MCPV47-07 P0/P1)

Status vocabulary: `PASS / FAIL / BLOCKED / NOT_RUN`; multiple provenance levels:

1. **SOURCE VERIFIED**: exact original template and official model/tokenizer revision pinned, source parser differences logged.
2. **RED REPRODUCED**: mandatory synthetic/model-native cases with baseline evidence.
3. **STATIC PATCH**: bounded family-specific files committed; no shared regression.
4. **BUILD GREEN**: full `ovms.exe` and `ovms_test.exe` from exactly pinned new source, DLL hash map and build command.
5. **UNIT GREEN**: MiniCPMV47 tests plus pinned existing MiniCPM5, Qwen3Coder, Gemma4 and Ornith negative controls; do not re-label historic `81/81` as new tests.
6. **API GREEN**: unary and SSE with `none/auto/required/named/parallel` (unsupported hard-mode explicit error accepted only as capability gap, NOT full policy PASS).
7. **RUNTIME GREEN**: actual full 35B-A3B INT4 on Arc 140V: `VLMPipeline`, text, image, successful OVMS endpoint if available.
8. **AGENTIC GREEN**: multi-turn actual tools, response replay, repeated/cancelled streaming, C1 and eligible C2/C4, thinking on/off; benchmark on same machine.
9. **ACCEPTED**: owner sign-off, no regressions, merged only after review. **Parser GREEN ≠ model inference GREEN ≠ API GREEN ≠ product support**.

Acceptance matrix to save:

`TEMPLATE_TOKEN_IDS, TOOL_RETAINER, REASONING, LOSSLESS_ARGS, SCHEMA_VALIDATION, POLICY_NONE, POLICY_AUTO, POLICY_REQUIRED, POLICY_NAMED, POLICY_PARALLEL_FALSE, POLICY_PARALLEL_TRUE, SSE_UNARY_PARITY, TOOL_RESULT_REPLAY, MINI_CPM5_REGRESSION, QWEN_REGRESSION, GEMMA_REGRESSION, EXPORT_IDENTITY, GPU_COMPILE, VLM_TEXT, VLM_IMAGE, VLM_VIDEO, OVMS_VLM_CB, TOOL_LOOP_C1, TOOL_LOOP_C2, TOOL_LOOP_C4, PERF_PARITY, OWNER_SIGNOFF`.

Document exact command lines in `TEST-COMMANDS.md` after discovering actual Bazel/gtest filters. Never invent target names or record a test as executed without process exit code and output.

## 9. Atomic PR/agent decomposition and dependencies

| Ticket | Scope | Input → output | Hard gate |
| --- | --- | --- | --- |
| **MCPV47-00** provenance / source lock | `docs/minicpm-v47` + source check | pinned IR/Jinja/tokenizer/GenAI and regression corpus | no source ambiguity |
| **MCPV47-01** template corpus | render official Python Jinja with and without thinking, tool history, image/video | fixture files with bytes+token IDs | canonical reference and token-level equality |
| **MCPV47-02** protocol peer dossier | vLLM, llama.cpp, SGLang, official HF, current OVMS | comparative KEEP/PORT/REJECT matrix | source URLs and exact commits |
| **MCPV47-03** RED tests | independent test-only commit | counterexamples for old `minicpm5` and naive Qwen reuse | baseline failure demonstrated |
| **MCPV47-04** parser-retainer | `minicpmv47` family adapter/FSM and targeted glue | valid native tool calls extracted losslessly | STOP/LENGTH, SSE, negative + registration |
| **MCPV47-05** generation policy | family builder + registry; no global fallback | none/auto/required/named/parallel capability matrix | hard modes fail closed; ON/OFF think parity |
| **MCPV47-06** multimodal API glue | processor/history and OpenAI streaming contract | text/image/video and tool result reentry | native framing + no content leakage |
| **MCPV47-07** integration acceptance | Windows exact source binaries, golden regressions, end-to-end tests | evidence.json, logs, matrices | real live tools, owner review |
| **MCPV47-08** performance qualification | matched GPU/SDK C1 vs Qwen3.6/Ornith; C2/C4 if eligible | real TTFT/tok/s/memory table | no baseline degradation; bounded resource |
| **MCPV47-09** optional roadmap | only after green: LES, DSpark/MTP, CIB2 OTD expert eligibility | separate design/replay, **not** part of parser PR | no GPU plugin merge, no false performance claims |

Run **00/01/02/03** in parallel in isolated docs/test worktrees; start **04** after native protocol corpus; **05** after pinned thinking/suffix and grammar API audit; **06** after parser+policy unit gates; **07/08** after actual VLM GPU readiness. No automatic cross-PR merge. Maintain `STATE.md` and commit/push each useful checkpoint.

## 10. Expected behavioral differences, if accepted

- Correct native MiniCPM-V 4.7 tool-calling, including multi-tool and tool-result continuation.
- Zero parser-invented executable calls, missing schema values or JSON double decoding; original nested number spelling retained.
- Explicit working `none / auto / required / named / parallel` semantics **only if supported**; clear errors otherwise.
- Stable reasoning/content separation across think ON/OFF, streaming and multi-turn.
- Text+vision+tool workflows in OVMS only after actual `VLM_CB` API support is proved.
- Measured INT4 GPU inference/performance under pinned 2026.4 or clearly isolated newer runtime.
- Unmodified Gemma/Qwen/Ornith accepted behavior and clean rollback by feature branch.

No speedup, automatic LES, DSpark, native pack/OTD, 256K usable context or C4 memory fit is promised merely because model documents advertise the architecture.

## 11. Required final agent handoff

Under `docs/minicpm-v47` write `STATE.md` after each stage and `FINAL-HANDOFF.md` when stopping. Report: `CURRENT_STAGE`, base and current Git SHA, source/model/template SHA, full binaries and DLL SHA, precise test commands and exit codes, unit+API+live statuses, OS GPU memory and tool-loop evidence, blockers with smallest reproducible log, rollback commit and next responsible agent. Include links to every Draft PR; no production merge without operator approval.

**Acceptance decision:** protocol source/tests can land as gated experimental functionality independently of GPU model support; production-compatible full MiniCPM-V 4.7 requires both the complete MFP-1 acceptance ladder and separate VLM/GPU execution acceptance.
