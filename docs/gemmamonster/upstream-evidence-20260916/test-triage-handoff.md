# Handoff: test-triage — GREEN gate + 16 падений ovms_test (чинивший, читай всё)

Дата: 2026-09-16. Ветка под разбором: `origin/upstream/gemma4-tool-calling` @ `d582668e6`
(тот же `src/` что `43bc254`, минус 1 blank line EOF в `gemma4_tool_parser.cpp`).
Окружение: Windows, MSVC `C:\BuildTools` 14.44.35207, MSYS bash первым в PATH,
`BAZEL_SH=C:/opt/msys64/usr/bin/bash.exe`, Python 3.12.10, `--output_user_root=C:/o`.

## 1. Что прошло (не трогать, это база)

```text
bazel test --config=win_mp_on_py_off --nocache_test_results --test_output=all
  //src/test/llm/gemma4_generation:gemma4_generation_policy_test       27 OK
  //src/test/llm/gemma4_generation:gemma4_phantom_tool_call_test       12 OK
  //src/test/llm/gemma4_generation:gemma4_chunk_invariance_test         4 OK
  //src/test/llm/gemma4_generation:gemma4_rendered_prompt_state_test   11 OK
  //src/test/llm/gemma4_generation:gemma4_f7_contract_test              5 OK
  //src/test/llm/gemma4_generation:gemma4_f10_guard_test                5 OK
Executed 6 out of 6 tests: 6 tests pass. Exit 0. OK-cases: 64.
Лог: C:\git\artifacts\gemma4-upstream-pr-20260916\semantic-suite.log
```

## 2. Что упало (чинить это)

```text
bazel test --config=win_mp_on_py_on  (py_on ОБЯЗАТЕЛЕН: при py_off в upstream
  коде src/llm/servable.hpp:239 unguarded PyJinjaTemplateProcessor* при
  guarded include — pre-existing поломка, НЕ наша, файл вне нашего diff)
  --test_env=PYTHONPATH=<ws>\bazel-out\x64_windows-opt\bin\src\python\binding;C:/opt/openvino/python
    (обязательно: в .bazelrc буквально %workspace%, не раскрывается)
  --test_filter=Gemma4OutputParserTest.*:Gemma4UpstreamRefitContractTest.*:Gemma4SpecialTokenHandoffTest.*:HttpOpenAIHandlerParsingTest.*
  //src:ovms_test
Итог: 229 ran, 213 PASSED, 16 FAILED. Лог:
  C:\o\owi5bgwi\execroot\ovms\bazel-out\x64_windows-opt\testlogs\src\ovms_test\test.log
BEP: C:\git\artifacts\gemma4-upstream-pr-20260916\test-events-ovmstest-pyone3.json
```

Junction для токенайзера (нужен `Gemma4SpecialTokenHandoffTest`, иначе упадёт поиском модели):
`src\test\llm_testing\OpenVINO\gemma-4-E4B-it-int4-ov` -> `C:\llm\models\OpenVINO\gemma-4-E4B-it-int4-ov`
(git его не видит — `llm_testing` в игноре; после работы можно удалить).

Полный список падений (сигнатуры из test.log):
- `HttpOpenAIHandlerParsingTest.OutputParserInitializationDependsOnParserNames` — C++ exception: opt-125m tokenizer not loaded (МОДЕЛИ НЕТ локально → ENVIRONMENTAL, не чинить).
- `HttpOpenAIHandlerParsingTest.ParseRequestWithTools_Provided3_ChoiceNotInProvidedList` — unknown named `get_weather4`: наш код даёт `INVALID_ARGUMENT`, тест ждёт `OK`. INTENDED (fail-closed — требование контракта §4.7) → обновить expectation теста с justification, код не трогать.
- `Gemma4UpstreamRefitContractTest.PreservesValidNumberLexemesLosslessly` — НАШ собственный контракт: ждёт `{"x":123456789012345678901234567890.12345678901234567890e-42}`, парсер вернул `{"x":1.2345678901234566e-13}` (double-нормализация). РЕАЛЬНЫЙ БАГ, чинить (lossless §4.3).
- `Gemma4OutputParserTest.ParseTwoToolCallsAtOnce` — два `call:` в одном `<|tool_call>`, ждёт 2, парсер вернул 0. Вероятно РЕАЛЬНАЯ регрессия (parallel!): generation policy различает вызовы по тегам, но парсер обязан принимать N вызовов в блоке. Чинить, см. просьбу 1.
- `Gemma4OutputParserTest.ParseToolCallOutputWithThreeToolCalls` — та же семья, проверить вместе с предыдущим.
- `Gemma4OutputParserTest.ParseToolCallWithArgumentMissingEquals` — ждёт значение, проверить.
- `Gemma4OutputParserTest.ParseToolCallWithStringArgumentsContainingEscapedQuotes` — проверить экранирование в новой рекурсивной грамматике.
- Стриминговые early-emit (8 шт): `ParseToolCallWithArrayOfObjectsArgumentsStreaming`, `ParseToolCallWithMultipleUtfCharsStreaming`, `ParseToolCallArgumentValueWithUnclosedQuoteAndBraceMidStream`, `HolisticStreaming`, `StreamingWithBiggerChunks`, `StreamingWithWhitespacesBetweenToolCalls`, `StreamingWithToolCallWithEmptyParams`, `StreamingWithToolResponseTokenAtTheEndOfGeneration`, `StreamingWithMissingEndTagBeforeStop` — паттерн: upstream ждёт `tool_calls` delta на фрагменте (`{array`, `{arg1:`, `{}`), наш парсер возвращает nullopt (fail-closed до валидного конверта). Возможно INTENDED hardening («не превращать malformed prose в executable call»), но каждый кейс рассудить отдельно, см. просьбы 1–2.

## 3. ПРОСЬБА 1 — проследи историю регрессии по коммитам

Наш delta собран из RC `43bc254`, его история — ~36 implementation-коммитов поверх merge-base `a5136cb28`. Полный список: `docs/gemmamonster/promotion-20260916/COMMITS.md` (читать через `git show 239f70d95e5c4eb54fd911dbe438825bd7b47848:<path>` из `C:\git\model_server-gemma4-clean`). Короткие списки по файлам (`git log --oneline a5136cb..43bc254 -- <file>`), главные подозреваемые:

- `src/llm/io_processing/gemma4/gemma4_tool_parser.cpp`:
  `bed7a1e54 fix(gemma4): harden recursive native argument parsing` (подозрение №1 для number-lexeme и escaped-quotes),
  `e001de937 fix(gemma4): bound registry-aware bare-call recovery`,
  `909e21f07 fix(gemma4): commit validated tool envelopes atomically` (подозрение №1 для early-emit и two-calls),
  `2b1dfb812 fix(gemma4): drain parser progress independent of chunking` (подозрение №1 для streaming chunking),
  `66c661401 fix(gemma4): bound malformed tool candidates`,
  `58fe7b7d8 hygiene(gemma4): restore parser utility declaration include`.
- `src/llm/io_processing/output_parser.cpp`: `2b1dfb812`, `c746a9b97 fix(gemma4): reconcile rendered thought state before generation`, `e001de937`.
- `src/llm/apis/openai_api_handler.cpp`: `079eb6f66 fix(gemma4): enforce object-root tool schemas`, `355ae00c1 fix(gemma4): reserve tool policy names at request boundary`, `3755dc85b fix(openai): reject hard tool choice without usable tools`, `cf6fc0412 fix(gemma4): fail hard structured validation at API boundary` (для ChoiceNotInProvidedList — подтвердить что fail-closed введён здесь и намеренно).
- `src/llm/io_processing/generation_config_builder.hpp`: `5d8327cf6`, `9c0b698e0`, `5af1c0472`, `27b66eda1`, `76c792ca2`, `7be4b7aa4`, `547df8030` (policy, не парсинг — для контроля что генерация не при чём).

Метод: для каждого класса падений найди коммит, после которого upstream-тест начал бы падать (ментальный bisect по diff'ам; при желании — реальный `git bisect` на `//src:ovms_test` с фильтром, кэш тёплый, пересборка инкрементальная ~10–20 мин на шаг). Результат зафиксируй таблицей «тест → коммит → intended/regression».

## 4. ПРОСЬБА 2 — поищи собственные доки по теме

Прежде чем менять поведение или тесты, проверь, было ли ужесточение намеренным и задокументированным:

1. `docs/gemmamonster/promotion-20260916/REPORT.md` — разделы про parser contracts, bounded recovery, fail-closed (читать из форка: `git show 239f70d...:docs/gemmamonster/promotion-20260916/REPORT.md`).
2. `docs/gemmamonster/promotion-20260916/PR-CANDIDATE.md` — что заявлялось про парсер.
3. Comparative parser dossier (vLLM/SGLang refs) — искать в `docs/gemmamonster/` того же дерева (`git ls-tree -r 239f70d -- docs/gemmamonster/`), разделы про early-emit, partial markers, bounded recovery.
4. Generator/parser contracts + acceptance reports (`acceptance/` в worktree `C:\git\gemma4-upstream-refit-clean-20260915`, `C:\git\artifacts\gemma4-promotion-20260916\PR-READY-DESCRIPTION.md`, `FINAL-REPORT.md`) — есть ли записи про multi-call в одном блоке, lossless numbers, ранний emit delta.
5. История 2026.4 (`origin/main` форка, `git log --grep=whitespace -i`, `JSONSchema(..., max_whitespace_cnt)` companion patch) — какой whitespace-контракт предполагался изначально.

Вопросы, на которые доки должны ответить: (а) ранний emit tool_calls на фрагменте — баг upstream, который мы чинили, или поведение, которое мы сломали; (б) lossless numbers — где требовалось и каким путём (tokenizer decode vs string parse); (в) N вызовов в одном теге — валидный parallel или malformed.

## 5. Контекст, чтобы не пойти по ложному следу

- Repair-ветка whitespace bound (`origin/fix/gemma4-whitespace-regression-1609`, GenAI companion `e00eada6`) — НЕЗАВИСИМА (уровень grammar), её source-сборка сейчас компилится (cmake+cl). Не смешивать.
- `servable.hpp:239` при py_off и `%workspace%` в `.bazelrc` — pre-existing грабли upstream, уже обојдены флагами выше, не чинить в рамках PR.
- E4B-модель не грузится в CB (в её IR нет SDPA) — модельное ограничение; live dogfood шёл на 26B-heretic (5/5 HTTP 200, unary/parallel/Responses чистые; отдельный streaming-баг `bug-streaming-named-degenerate.md` уже отдан в repair).
- `upstream/gemma4-tool-calling-split` (`62676e2e4`) — чистая серия для PR; правки парсера вносить в ОБЕ ветки (или в основную + перегенерировать split), тесты — те же фильтры + 6 таргетов gate.
