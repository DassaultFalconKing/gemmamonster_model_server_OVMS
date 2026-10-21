# QWM-01 implementation and XGrammar #802 companion candidate

Current measured status: see QWM01-BUILD-REPORT.md. Focused parser/policy/generic
units pass; three baseline Gemma failures remain. HTTP full-target dependency
analysis is blocked by absent configured BoringSSL, so HTTP tests are NOT RUN.
Separate #802 native build/checks and candidate GenAI controls pass; no new
runtime cohort is deployed. LIVE NOT RUN, ACCEPTED NO.

The original source-only implementation handoff below is retained for history;
its unexecuted unit/native labels are superseded only by the exact measured
scopes in QWM01-BUILD-REPORT.md.
Implementation worktree: `feature/qwenmonster-qwm01-request-schema-20261021`, branched from `8aba34ad4e422d470d91afdf88aa3dd9696cb143`.
Original known-good C6 and published `public-source-lock.json` unchanged.

## QWM-01: six-field change contract

1. **Cause / evidence:** `OpenAIApiHandler::parseTools()` applied safe-name,
   duplicate-name, hard-choice and root-object gates to Gemma only. Qwen
   unsupported Draft4 schemas could pass HTTP and have their completed calls
   silently discarded later by `Qwen3CoderToolParser::hasValidArguments`.
   SOURCE-VERIFIED; RED test authored but **not executed**.
2. **Files:** `src/llm/apis/openai_api_handler.cpp`;
   `src/llm/io_processing/qwen3coder/tool_schema_profile.{hpp,cpp}`;
   `src/llm/io_processing/qwen3coder/qwen3coder_tool_parser.cpp`;
   `src/llm/BUILD`; `src/test/http_openai_handler_test.cpp`.
3. **Implementation:** Share the *existing exact restricted Draft 4*
   schema/meta-schema validation code via
   `isSupportedQwenXmlToolSchema(schemaText)` (HTTP preflight) and
   `validateQwenXmlToolArguments(schemaText,argsText)` (runtime).
   In `parseTools()`, `qwenXmlPolicy` joins Gemma on safe names,
   duplicate schema conflict, unambiguous object root and named/required
   tool existence. Nonempty selected tools require explicit `parameters`.
   Invalid Qwen schema produces `absl::InvalidArgumentError`; no silent
   downgrade to `none` when hard choice is unsatisfiable.
   **This is not** the measured compiled-schema-cache optimization QWM-02.
4. **Expected:** Unsupported requests fail before generation (HTTP 400 when
   status mapping is verified). Explicit `{"type":"object","properties":{},
   "required":[]}` remains valid at HTTP/parser level; real guided
   zero-argument generation **still requires** XGrammar #802 remediation.
   Hermes and Gemma logic remain semantically unchanged.
5. **Tests:** New `HttpOpenAIHandlerParsingTest.QwenXmlRequestSchemaProfileIntake`
   (12 parameterized-in-loop positive/negative scenarios) and
   `QwenXmlSchemaProfileIsNotAppliedToHermesByAccident`.
   After build: run `//src:ovms_test` with the two GTest filters, then
   Qwen parser 69-case profile, generation policy 9, generic 29,
   full Gemma control. Compare the three preexisting Gemma failures by name.
   RED/GREEN are **NOT EXECUTED** from this GitHub-only source session.
6. **Source/provenance:** Direct source inspection of the pinned
   `OpenAIApiHandler::parseTools` and Qwen runtime `hasValidArguments`;
   fail-closed intake/shared validator boundary is independent design.
   The restricted Draft 4 meta profile was **moved**, not redefined.

### Commits and source controls

- Test commit: `f64894101af80357dd9d8ac44282d367f20fb8e7`.
- Shared profile and HTTP handler: `df01cfecdfd87b6471bdb6f28ffda986c4ec6015`.
- Preserve RapidJSON error diagnostic include: `e0c6966c9f03eec8236548e8bcf5fd164141395b`.
- Build/lint unit outcomes: **NOT RUN**. Do not retroactively label either
  newly authored tests RED or GREEN until an actual execution exists.
- Verify HTTP error mapping, C++ compile/link, and whether the existing
  `//src:ovms_test` target can be built at the current Windows Bazel profile.

Run on the local pinned build machine:

```powershell
bazel test //src:ovms_test --test_arg="--gtest_filter=HttpOpenAIHandlerParsingTest.QwenXml*" --test_output=errors
bazel test //src:qwenmonster_output_parser_test //src:qwenmonster_generation_policy_test //src:output_parser_core_test //src:gemma4_output_parser_test --test_output=errors
```

Check linker inputs for the new Bazel
`//src/llm:io_processing_qwen3coder_tool_schema_profile` target.

## XGrammar #802: companion candidate (separate repository, NOT in lock)

1. **Cause:** Native Qwen XML grammar for genuinely no-argument object
   could consist of unbounded whitespace, observed with synthetic matcher.
2. **Files:** `DassaultFalconKing/xgrammar` branch
   `fix/qwenmonster-xml-empty-object-20261021`,
   `cpp/json_schema_converter.cc` and
   `tests/python/test_json_schema_converter.py`.
3. **Design:** Match [upstream PR #803](https://github.com/mlc-ai/xgrammar/pull/803)
   with branch-specific relocation into this fork's
   `XMLToolCallingConverter::GenerateObject()`. When a *root unbraced*
   XML object cannot contain properties, return `Empty()`. Keep open
   objects, plain JSON and nested braced JSON unchanged.
4. **Expected:** No whitespace-only loop for
   `{"type":"object","properties":{},"required":[]}`. End tag can take
   over immediately. **No claim of live Qwen success.**
5. **Tests:** `test_qwen_xml_no_argument_object_terminates_without_whitespace`
   with closed schemas and `maxProperties:0`,
   `test_qwen_xml_open_object_still_allows_parameter`,
   `test_qwen_xml_nested_empty_object_keeps_json_braces`,
   `test_plain_json_empty_object_braces_unchanged`.
   Compile with pinned library, run tests and native matcher on *actual*
   tokenizer. All are **NOT RUN**.
6. **Source:** [XGrammar #802](https://github.com/mlc-ai/xgrammar/issues/802)
   and [upstream PR #803](https://github.com/mlc-ai/xgrammar/pull/803).
   Alternative [PR #837](https://github.com/mlc-ai/xgrammar/pull/837)
   was studied; do **not** merge both fixes.

Commits in separate fork:
- Test `d9a8f7afa13385e30598cc0d0fbb199624bdf17d`
- Converter `3303659ec09c62c1d024a7d4eed1b0bc18b30cc3`

The current accepted XGrammar source remains `c77d5e0d62411d17d4cf55d280463eb5b3bec7ba`.
Once unit/mask tests pass, propose a **new** lock SHA explicitly.
The independent XGrammar #650 end-marker drift remains OPEN.

## Handoff and promotion

First rerun tests on the actual locked Windows cohort and fix any compile
failures with separate atomic commits. Then compile the separate XGrammar
fork and compare its native masks, compiler output and Gemma controls.
Do not promote anything until SERVER BUILD, MATCHER, API, LIVE, and
agentic acceptance are measured.
