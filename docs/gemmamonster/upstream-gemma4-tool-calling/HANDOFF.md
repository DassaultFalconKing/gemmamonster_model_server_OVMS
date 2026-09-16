# Upstream Gemma4 tool-calling PR — preparation handoff

> Внутренний документ подготовки. НЕ входит в upstream PR body.
> Перед отправкой в `openvinotoolkit/model_server` эту папку
> `docs/gemmamonster/upstream-gemma4-tool-calling/` УДАЛИТЬ из diff.
> Upstream PR должен содержать только `src/` delta + focused tests/docs.

## 1. Resolved refs (2026-09-16, re-resolved via fetch)

```text
UPSTREAM_BASE (openvinotoolkit/model_server:main):
204d3bf3ba6f8e2aeb489c5eeb7ab46c79fde482
  fix documentation menu (#4571)

FORK_MAIN (origin/main):
8f970d4236738ae800b01786af7ad5ad843a62c8

PR-PROMOTION (origin/pr-promotion-2026-5):
29d8ddad295b6427577985325ed0797913d9272c

Accepted RC (historical, re-resolved, exists):
43bc254e8996f17b929afef79f310d0b0b0cc139
  docs(acceptance): corrective Gemma4 live acceptance on 2026.5 freeze binary

Promotion candidate (historical, exists):
239f70d95e5c4eb54fd911dbe438825bd7b47848

Accepted build source (exists):
b722aa440b5555041f24e6d6f7aea8bda100bdf7

MERGE-BASE accepted RC vs current upstream:
a5136cb285482aaef5410a053b5ecd04ff9324ec
  Move ovms python binding to separate library (#4103)
```

PR branch (в форке, от актуального upstream main, НЕ от Gemmamonster main):
```text
PR_BRANCH: upstream/gemma4-tool-calling
BASE: 204d3bf3ba6f8e2aeb489c5eeb7ab46c79fde482
```

Источники истины прочитаны:
- `PR-READY-DESCRIPTION.md` (артефакты `C:/git/artifacts/gemma4-promotion-20260916/`)
- `FINAL-REPORT.md`, `tested-head.txt` (=239f70d...), `test-summary.json` (64/64 PASS на старом promotion HEAD — НЕ валидно для нового HEAD)
- `docs/gemmamonster/promotion-20260916/REPORT.md`, `PR-CANDIDATE.md`, `COMMITS.md` (через `git show 239f70d...`)

## 2. Semantic delta (фактический, против текущего upstream)

```text
git diff --name-only 204d3bf...43bc254 -- src/ third_party/ versions.mk WORKSPACE MODULE.bazel
```

`third_party/`, `versions.mk`, `WORKSPACE`, `MODULE.bazel` — NO DIFF.
Только `src/` (27 файлов). `a5136cb..204d3bf --stat` — только `README/docs/demos`,
`src/llm/` upstream после `a5136cb` не трогал. Upstream НЕ реализовал наш delta
(stop-condition №1 не сработал).

Production (17):
```text
src/llm/apis/openai_api_handler.cpp
src/llm/apis/openai_request.hpp
src/llm/apis/openai_responses.cpp
src/llm/BUILD
src/llm/io_processing/base_generation_config_builder.hpp
src/llm/io_processing/gemma4/gemma4_reasoning_parser.cpp
src/llm/io_processing/gemma4/gemma4_reasoning_parser.hpp
src/llm/io_processing/gemma4/gemma4_tool_parser.cpp
src/llm/io_processing/gemma4/gemma4_tool_parser.hpp
src/llm/io_processing/gemma4/rendered_prompt_state.cpp (new)
src/llm/io_processing/gemma4/rendered_prompt_state.hpp (new)
src/llm/io_processing/generation_config_builder.hpp
src/llm/io_processing/output_parser.cpp
src/llm/io_processing/output_parser.hpp
src/llm/io_processing/output_parsing_config.hpp
src/llm/ovms_text_streamer.cpp
src/llm/servable.cpp
```

Tests (10):
```text
src/test/http_openai_handler_test.cpp (mod)
src/test/llm/gemma4_generation/BUILD (new dir)
src/test/llm/gemma4_generation/gemma4_chunk_invariance_test.cpp
src/test/llm/gemma4_generation/gemma4_f10_guard_test.cpp
src/test/llm/gemma4_generation/gemma4_f7_contract_test.cpp
src/test/llm/gemma4_generation/gemma4_generation_policy_test.cpp
src/test/llm/gemma4_generation/gemma4_phantom_tool_call_test.cpp
src/test/llm/gemma4_generation/gemma4_rendered_prompt_state_test.cpp
src/test/llm/output_parsers/gemma4_special_token_handoff_test.cpp
src/test/llm/output_parsers/gemma4_upstream_refit_contract_test.cpp
```
`output_parsers/*_test.cpp` собираются через `glob` в `src/BUILD:test_llm_output_parser_tests`.
`gemma4_generation/*` — отдельные `cc_test` (`//src/test/llm/gemma4_generation:*` — путь условный,
в RC BUILD это `cc_test`, точный label проверить по `src/test/llm/gemma4_generation/BUILD`).

Ядро delta — отсутствующий upstream `Gemma4GenerationConfigBuilder`
(`src/llm/io_processing/generation_config_builder.hpp`):
- `none` → no tool constraint
- `auto` → lazy `TriggeredTags("<|tool_call>")`, `at_least_one=false`
- `required` → `TagsWithSeparator(at_least_one=true)` + optional `thought` (`<|channel>thought`)
- `named` → один tag выбранной функции, fail-closed unknown
- `parallel_tool_calls` → `stop_after_first`
- hard choice без tools → `InvalidArgument`, `response_format` + active tools → `InvalidArgument`
- `requiresValidStructuredOutput()` для hard policy (база + override)

Плюс: `parallel_tool_calls` plumbing (Chat + Responses), safe tool-name validation
(`[A-Za-z0-9_.-]`, reserve none/auto/required), object-root schema enforcement,
native Gemma4 tool/reasoning parser hardening, rendered-prompt reconciliation,
streaming handoff.

## 3. Dependency audit (предварительный)

```text
versions.mk 204d3bf == 43bc254:
OV_SOURCE_BRANCH=4977f92a234f07b963ad2baf028eab837d1b5869
OV_TOKENIZERS_BRANCH=b40486a0aac26255806ea9895ec9aa8b3cef6b9c
OV_GENAI_BRANCH=fe818c0467feb17b87c5adfb3f7e28dd70b76e99
```

```text
REQUIRED_ON_CURRENT_UPSTREAM: prelim NO
IF YES: —
IF NO (prelim): пины идентичны; исторического
  JSONSchema(...,max_whitespace_cnt) companion-патча в diff нет.
  Требуется финальное подтверждение наличия
  TriggeredTags/TagsWithSeparator/Union/Concat/Tag/AnyText/JSONSchema
  в GenAI fe818c04.
```

XGrammar revision отдельно не менялся в RC vs upstream.

## 4. Что НЕ переносить (исключено)

`acceptance/`, `docs/gemmamonster/` (кроме ЭТОЙ prep-папки, которую удалить перед PR),
evidence, bench dumps, Windows packaging, release tooling, provenance verifier,
NovaClaw/OpenCode runtime, GPU `CL_OUT_OF_RESOURCES`, quarantine, speculative/MTP,
unrelated perf/Windows repairs. В transplant выше — только `src/` из списка.

## 5. Test gate — ПРОЙДЕН на HEAD ветки 2026-09-16

```text
HEAD: f07ae95517361f39eb7774b5d611f3a282b1c980 (upstream/gemma4-tool-calling)
CMD:  bazel test --config=win_mp_on_py_off --nocache_test_results --test_output=all
      (env: windows_setupvars-эквивалент, MSVC C:\BuildTools 14.44.35207,
       BAZEL_SH=MSYS; см. run_gate.cmd в задаче)
LOG:  C:\git\artifacts\gemma4-upstream-pr-20260916\semantic-suite.log
BEP:  .../test-events.json, EXIT: .../exit-code.txt = 0
```

```text
//src/test/llm/gemma4_generation:gemma4_generation_policy_test       PASSED (27)
//src/test/llm/gemma4_generation:gemma4_phantom_tool_call_test       PASSED (12)
//src/test/llm/gemma4_generation:gemma4_chunk_invariance_test        PASSED (4)
//src/test/llm/gemma4_generation:gemma4_rendered_prompt_state_test   PASSED (11)
//src/test/llm/gemma4_generation:gemma4_f7_contract_test             PASSED (5)
//src/test/llm/gemma4_generation:gemma4_f10_guard_test               PASSED (5)
Executed 6 out of 6 tests: 6 tests pass. OK-cases: 64, FAILED: 0.
Build completed successfully, 1091 total actions.
```

Окружные грабли по пути (не код, закрыты): диск C: был 0 байт → чистка;
`which(bash)` находил WSL вместо MSYS → `BAZEL_SH` + MSYS первым в PATH;
`BAZEL_VS/VC` не заданы в голом шелле → MSVC `C:\BuildTools` (14.44.35207);
`setupvars.ps1` — только runtime, для сборки нужен build-env
(см. `windows_setupvars.bat`, MSVC-путь у нас не дефолтный).

Contracts: none/auto/required/named, invalid named, hard без tools,
nested objects/arrays/strings/numbers/booleans/null, reasoning→tool,
split start/end markers, finalization, malformed + bounded recovery,
registry validation, same-name repeated, parallel, parallel=false,
unary/stream equivalence, tool-result continuation.

## 6. PR architecture (reviewer-facing)

```text
OpenAI chat request (tools/tool_choice/parallel_tool_calls)
  → Gemma4GenerationConfigBuilder (none/auto/required/named)
  → OpenVINO GenAI structured output
  → Gemma4 native tool protocol
  → Gemma4 tool/reasoning parser → typed OVMS deltas
  → OpenAI response (Chat + Responses)
```

Это missing tool-calling path, не parser-fix.

## 7. PR text (draft, 1–2 экрана, удалить prep-папку перед отправкой)

Title: `Add robust Gemma4 tool calling support`

Body draft — Problem (incomplete agentic tool use across policy/protocol/reasoning/streaming),
Changes (builder, parser hardening, lazy/hard guided generation, streaming, template compat),
Design (Google Gemma — authority; OVMS — native impl с выделенным `Gemma4GenerationConfigBuilder`;
vLLM/SGLang/llama.cpp/Transformers — comparative only), Validation (contracts + exact tests на final HEAD),
Compatibility (no peer deps, non-Gemma preserved, GPU/MTP/perf out of scope).

## 8. Статус (обновлено: transplant закоммичен, dist атрибутирован)

- [x] refs resolved
- [x] delta определён
- [x] branch от upstream/main создана
- [x] transplant 27 файлов закоммичен (`7c07208`; semantic split — следующий шаг)
- [x] dist атрибутирован (`DIST-ATTRIBUTION.md`: staging/gemma4-upstream-refit-clean-20260915 @ 43bc254,
      ovms.exe SHA256 == accepted BINARY_SHA256; `src/` ветки == источнику dist
      минус 1 hygiene-строка EOF в `gemma4_tool_parser.cpp`, коммит `4536180`)
- [ ] test gate на новом HEAD → ПРОЙДЕН (6/6 targets, 64/64 cases, exit 0)
- [x] `git diff --check`: остаётся FAIL ТОЛЬКО по `src/llm/BUILD` —
      файл целиком CRLF уже в upstream blob (714/714 строк), наши добавленные
      строки наследуют кодировку файла. Все остальные файлы PASS
      (EOF blank line в `gemma4_tool_parser.cpp` удалён). Перед PR решить:
      оставить как есть (pre-existing условие upstream) или нормализовать —
      нормализация = rewrite 714 строк, противоречит minimal delta.
- [ ] semantic commit series
- [ ] upstream docs (focused, вне этой папки)
- [ ] удалить эту папку из PR diff

```text
UPSTREAM_PR_NEAR_READY (gate GREEN; остались: semantic split коммитов,
+ output_parsers/http_openai_handler прогон, upstream focused docs,
удаление prep-папки из PR diff)
```
