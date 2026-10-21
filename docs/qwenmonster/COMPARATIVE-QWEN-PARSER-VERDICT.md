# QWENMONSTER — Comparative parser and generation verdict (R0–R3)

Status: **SOURCE-VERIFIED / CODE-CANDIDATE / RUNTIME-UNVERIFIED**  
Date: 2026-10-21  
Current source base: C6 `ba6ec792c3121850fea167fa7d7e190b25fcdc76`.  
Implementation branch: `feature/qwenmonster-comparative-refit-20261021`.  
Methodology: adapted from `docs/gemmamonster/COMPARATIVE-GEMMA4-PARSER-VERDICT.md` at `5d995cfafdb2ec90578678aa15714dedebc843b8` (historical commit).

## 1. Authority and provenance

1. Model-specific official template/tokenizer: canonical native wire and history semantics. MUST be pinned per model revision; not all post-3.6 models have identical protocols.
2. vLLM pinned code: `vllm-project/vllm` @ `c2861f7f120d508dcb1be046d9fc659c93062508`:
   - `vllm/parser/qwen3.py` (unified FSM, XML args converter, optional malformed transitions, reasoning->tool);
   - `vllm/parser/engine/{parser_engine.py,adapters.py}` (streaming ownership);
   - `vllm/tool_parsers/qwen3_engine_tool_parser.py` (Qwen adapter);
   - `vllm/tool_parsers/structural_tag_registry.py` (`qwen_3_coder` structural tags / tool-choice contract);
   - `tests/tool_parsers/test_qwen3coder_tool_parser.py` (mixed types, streaming, nested schemas).
3. llama.cpp pinned code: `ggml-org/llama.cpp` @ `339f3242c761f16c27e5ffcde1d35dcc31933a55`:
   - `common/parsers/qwen3-coder.cpp` (PEG native XML, schema-value variants, required/optional, parallel, lazy grammar);
   - `common/chat.cpp` (template-based parser selection);
   - `models/templates/Qwen3-Coder.jinja` (secondary template reference).
4. OpenVINO GenAI C++ API: `openvinotoolkit/openvino.genai` @ `6a35b97bbab88120930a87d81c2ecccd12fc0ba9`: `src/cpp/include/openvino/genai/generation_config.hpp` exposes `QwenXMLParametersFormat`, `TriggeredTags`, `TagsWithSeparator`, with `qwen_xml_parameter` serialization.
5. OVMS Qwen C6: `src/llm/io_processing/qwen3coder/qwen3coder_tool_parser.{hpp,cpp}` and `src/llm/io_processing/output_parser.cpp`.

Source commits pin **this research comparison**; they are not proof that corresponding binaries were run.

## 2. Comparative matrix (explicit decision)

| Contract | vLLM | llama.cpp | Original C6 / refit | Decision |
|---|---|---|---|---|
| Canonical wire | tagged XML, Qwen FSM | XML PEG | native XML C++ | KEEP; official template controls semantics |
| Reasoning→tool | transition on TOOL_START, implicit reasoning end | `</think>` or tool opener | generic OVMS output ownership; Qwen boundary not exhaustive | REFINE with split/re-entry tests |
| Bare `<function=` | recovery transition | literal known-name prefix in non-thinking case | permissive bare opener | TOLERANCE ONLY; registry gate |
| Unknown tool | adapter request awareness | grammar generates only allowed names | impl tolerated any; refit gates registered names at emission | REFINE, no executable unknown calls |
| Schema values | incremental arg converter, full-string XML value path; test differentials | typed per-property PEG/schema, required/optional permutation | RapidJSON and `ParameterType` shallow map | KEEP typing; REFINE invalid typed fallback; no vLLM string-only transplant |
| Nested arrays / objects | differential tests | native typed grammar | RapidJSON nested JSON | KEEP + expand fixture corpus |
| Mixed union types | parser and tests, schema-aware paths | JSON alternatives vs raw-string PEG | shallow enum `ParameterType` cannot represent `anyOf` | UNKNOWN: separate parser/validator implementation |
| XML end marker | FSM buffered partials | PEG delimiter + grammar | exact `</parameter>` search; recovery bounded | KEEP strict, add drift/fragment fixtures |
| Streaming identity | state-local tool calls and events | native AST mapping | M1 queued deltas + reset | KEEP after LIVE verification |
| Multiple envelopes in one chunk | incremental parser engine | PEG AST | M1 queue | REFINE and differential chunk invariance |
| `auto` generation | structural tags and parser selection | lazy grammar trigger | M1 no Qwen-specific builder | New Qwen-native opt-in lazy builder |
| `required/named` | structured constraint | non-lazy PEG | original generic builder, no Qwen XML | New fail-closed XML policy |
| Zero-argument schema | tests; grammar implementation dependent | no required arguments PEG | parser accepts `{}` | Grammar bug gate required before acceptance |
| Tool history | serializer/template contract | Qwen template and continuation | OVMS request/template layer | separate canonical replay oracle required |
| Architecture | Python ParserEngine | C++ PEG/AST | C++ BaseOutputParser, GenAI policy | KEEP OVMS abstractions; no wholesale port |

Decision labels: **KEEP, REFINE, PORT SEMANTICS, TOLERANCE ONLY, DROP, UNKNOWN**.

## 3. Observations directly affecting implementation

### vLLM (PORT SEMANTICS)

`vllm/parser/qwen3.py` maps `REASONING + TOOL_START` to explicit `REASONING_END + TOOL_CALL_START`, tolerates a bare function prefix from content, and recognizes malformed/duplicate markers as separate transitions. Its XML conversion loop handles partial parameter tags; its current converter can treat values as strings, so its coercion behavior must **not** automatically override OVMS typed RapidJSON results.

Transfer: explicit Qwen phase-transition fixture, bounded partial-delimiter retention, incremental emitter invariants. Do **not** import Python ParserEngine/adapter stack or replace OVMS output ownership.

### llama.cpp (PORT SEMANTICS)

`common/parsers/qwen3-coder.cpp` selects native XML PEG; builds per-tool grammar from declared JSON schema (including required/optional parameter lists), schema-aware values, `parallel_tool_calls`, and `tool_choice=required` minimum count. `auto` uses lazy grammar and trigger words; it also protects against broad `<function` matches by constructing complete allowed function prefixes.

Transfer: grammar constraints and collision-resistant trigger selection. Do **not** port PEG/GBNF backend into GenAI or claim parser format identification by superficial Jinja substring is safe.

### OVMS (KEEP / REFINE)

M1 added ordered delta queue and STOP recovery limited to a completed `</function>`. This refit additionally rejects unknown tool execution and invalid typed argument coercion at the XML parser. Its current type map is shallow; the refit now checks presence of required fields but does not fully validate `anyOf`, `oneOf`, null unions, enums, value-type matches across unions, or `additionalProperties`. Full JSON Schema validation remains an acceptance gate. Do not mark them solved by shallow type checks.

### New Qwen builder (CANDIDATE, NOT GREEN)

`src/llm/io_processing/qwen3coder/generation_config_builder.hpp` uses native GenAI `QwenXMLParametersFormat(schema)` as the value grammar within XML `Tag`. Hard `required/named` uses `TagsWithSeparator`; `auto` uses opt-in `TriggeredTags` with `<tool_call>`, never forced. **Constrained generation with an already-open `<think>` is an unresolved prompt-tail issue**. The hard grammar is not yet proven compatible with thinking-enabled models.

## 4. Concrete upstream failure evidence

- llama.cpp #26530 (2026-08-03): on long tool-rich prompts, `auto` may never emit XML trigger even when grammar is correct; `required` can still work. Separate model decision from parser loss.
- llama.cpp #26987 (2026-08-12): bare XML trigger deviation defeats lazy grammar; bounded recovery only.
- llama.cpp #29319 (2026-09-23): false positive detection from template similarity can select wrong protocol; capability fixtures over model-name heuristics.
- XGrammar #650 / PR #651: `</parameter` can drift to `</parameter1>`. As checked 2026-10-21 both issue and PR remain open/unmerged. Parser tolerance cannot fix grammar runaway. Gemma's `JSONSchema(..., 2)` does not address this prefix-exclusion defect.
- XGrammar #802: genuinely parameter-less XML tool schemas can produce a whitespace-only looping grammar. Issue #802 and both fix proposals PR #803 / #837 are open/unmerged as checked 2026-10-21. This is **not** the Gemma `empty-args` anomaly from C5.
- SGLang #27336: `required` XML end-marker drift observed for Qwen3.6; independent confirmation of grammar risk.

## 5. Version/gate caveats

- OpenVINO GenAI **documented upstream header** supports `QwenXMLParametersFormat`; the exact C6 build-machine header/binary/XGrammar pin has not yet been identified. **Do not merge until versioned compile & structural-tag validation succeed**.
- M1 test and code patches are committed but not built/benchmarked on live OVMS. The new policy is therefore experimental.
- Gemma C5 `JSONSchema(..., 2)` and local GenAI/XGrammar whitespace patches are evidence for the **JSON grammar path**, not the Qwen `qwen_xml_parameter` path. The upstream GenAI API snapshot used for this dossier offers a one-parameter `JSONSchema` constructor; pin the local patched GenAI fork/build before relying on the two-parameter overload.
- Historical C5 verdict `24847c96805b28e4625fd85dbf98bece20ed2d3e`: whitespace **CONFIRMED FIXED**, unexpected empty args **NOT REPRODUCED** (267 later filled canonical calls). The latter does not cover parameterless tools.
- For every discrepancy: `native output → vLLM semantic output → llama.cpp semantic output → OVMS events → OpenAI API`. Compare normalized tools `name + typed JSON + call order` and compare reasoning text separately. IDs may differ but must be unique/stable per call.
- Never reclassify a model's *decision not to delegate* as a parser defect unless the native output contained a valid executable call that OVMS lost.

## 6. Rejected architectural ports

- vLLM's ParserEngine class hierarchy: DROP as implementation dependency, PORT SEMANTICS only.
- llama.cpp's PEG grammar objects/runtime: DROP as dependency, PORT rules through GenAI.
- vLLM converter's string-for-every-value behavior: DROP as unconditional coercion policy.
- Unbounded bare-XML recovery, fabricated argument values, default required tools in `auto`: DROP.
- Global Gemma-specific OutputParser changes in a Qwen fix: DROP unless separately demonstrated unavoidable and regression-checked.

## 7. Promotion verdict

**KEEP OVMS-native boundaries; REFINE Qwen XML parser and add a distinct Qwen native generation builder.** C6 and Gemma4 stay pinned. Promotion blocked pending compiler, XGrammar compatibility, canonical template, reasoning, streaming and full agent-harness evidence.

## 8. Required defect provenance separation

The extended matrix in `WHITESPACE-DEFECT-TAXONOMY.md` distinguishes (a) **known-good Gemma JSON whitespace**, (b) **historical non-reproduced unexpected empty arguments**, (c) **XML excluded end-marker prefix drift**, and (d) **XML grammar looping for legitimately empty parameter lists**. These have different triggers, layers and remedies. A fix or successful test in one row cannot promote the others. 
