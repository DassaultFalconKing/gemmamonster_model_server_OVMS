# GEMMAMONSTER RC2 acceptance — 2026-09-14

Artifact under test, без пересборки, без правок исходников и тестов.
Продукт не чинился в этой сессии: FAIL — это результат теста.

## 1. Тестируемый артефакт

```text
RC2_BINARY:        C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914\ovms\ovms.exe
RC2_BINARY_SHA256: 11d74fd958d1cd2570682fa13562c1bfcf0973dabbf79a0378a8d0cdc886a4fb
RC2_BINARY_SIZE:   22964224
RC2_BINARY_MTIME:  2026-09-13T23:14:13.6350072Z

SOURCE_REPO:       https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS.git
SOURCE_BRANCH:     docs/rc2-908d6695-handoff-20260914
SOURCE_HEAD:       a2eaeb783dfd66f80c50070bf7050dd184b01364
RC2_PRODUCT_COMMIT: 908d669563f57535ab4eb747989e9ab33dfd5267
GIT_STATUS:        clean

OVMS_VERSION:      2026.4.0.908d66956
OPENVINO_VERSION:  2026.4.0-22955-227c33757d1-releases/2026/4
GENAI_VERSION:     2026.4.0.0-3407-7ea2546852a
```

SHA256 проверен хешем именно запущенного `ovms.exe`; копия
`extracted\ovms\ovms.exe` совпадает. Других OVMS-процессов не было,
`ovms` в PATH отсутствует. Машинное описание — `artifact.json`.

## 2. Live-конфигурация

```text
PID:                6136 (ovms.exe; launcher cmd 23904)
EXECUTABLE:         = RC2_BINARY
COMMAND_LINE:       ovms.exe --config_path <evidence>/live-sanity/config.json --rest_port 18091 --port 18092
REST_PORT:          18091 (gRPC 18092)
MODEL:              gemma4
MODEL_PATH:         C:/llm/models/OpenVINO/gemma-4-E4B-it-int4-ov
PROFILE:            VLM-CPU legacy (device CPU, pipeline_type VLM, паритет с собственным smoke RC2)
CHAT_TEMPLATE_MODE: model-default (без оверлея)
```

Граф/конфиг: `evidence/live-sanity/gemma4-graph.pbtxt`, `evidence/live-sanity/config.json`.
Мета процесса: `evidence/live-sanity/server-meta.json`.

## 3. Статическое покрытие в RC2-источнике (честная инвентаризация)

Запрошенные пути в RC2-источнике **отсутствуют**:

- `tests/llm_module/spec/gemma4_tool_parser/` — NOT_FOUND
- `gemma4_tool_parser_acceptance.py`, `gemma4_parallel_runner.py`, `expected_results.md` — NOT_FOUND
- `src/python/ovmsclient/lib/compat/openai/test_gemma4_{preprocess,streaming}.py` — NOT_FOUND
  (в RC2 вообще нет `src/python/ovmsclient`)
- `ovms/gemma4-diagnostic-pack/*`, `ACCEPTANCE.md`, `tokenizer_markers.py` — NOT_FOUND в RC2

Реально существующие C++ contract sources (8 файлов, не запускались как
RC2-evidence — в пакете нет тест-бинарников, сборка запрещена):

- `src/test/llm/gemma4_fast/gemma4_parser_contract_test.cpp` (20 TEST_F)
- `src/test/llm/gemma4_fast/gemma4_recovery_contract_test.cpp` (5 TEST_F)
- `src/test/llm/gemma4_fast/gemma4_reasoning_semantic_refit_test.cpp` (6 TEST_F)
- `src/test/llm/output_parsers/gemma4_output_parser_test.cpp` (43 TEST_F)
- `src/test/llm/generation_config/gemma4_generation_contract_test.cpp` (17 TEST)
- `src/test/llm/generation_config/gemma4_prompt_state_generation_contract_test.cpp` (3 TEST)
- `src/test/llm/gemma4_overlay/gemma4_chat_template_overlay_contract_test.cpp` (7 TEST)
- `src/test/llm/gemma4_overlay/gemma4_google_jinja_contract_test.cpp` (2 TEST)

Предсобранные `*_test.exe` есть только в чужой сборке
`gemmamonster-2026.4-build/bazel-bin` — их запуск в зачёт RC2 запрещён
принципом, не выполнялся.

Итог статики:

```text
PARSER acceptance (запрошенные файлы): NOT_FOUND
PREPROCESS pytest: NOT_FOUND (0/0/0)
STREAMING pytest:  NOT_FOUND (0/0/0)
GENERATION/TEMPLATE/REASONING contracts: FOUND-as-source, NOT_EXECUTED (test gap)
```

## 4. Startup sanity

```text
GET /v3/models → 200, gemma4 AVAILABLE (~7 c)
POST /v3/chat/completions без tools ("2+2") → 200, content "4", finish_reason "stop"

SERVER_START: PASS
MODEL_LOAD:   PASS
PLAIN_CHAT:   PASS
```

Лог: `Auto-detected tool_parser: gemma4`, `reasoning_parser: gemma4`.
Карантина / executor fault / GPU fatal нет.
Evidence: `evidence/live-sanity/models.response.json`,
`evidence/live-sanity/plain-chat.{request,response}.json`,
`evidence/live-sanity/server.stdout.log` (stderr пуст).

## 5. Tool-calling matrix (существующий harness, не переписан)

Harness: внешний `toolcall_matrix.py` + `run-toolcall-acceptance.ps1`
(интерфейс `--base-url/--model/--mode/--output-dir/--timeout/--max-tokens`
использован как есть). Прогнан `--mode all`, `max-tokens 256`, `timeout 240`:

```text
none              PASS — 0 calls, finish stop
auto_optional     PASS — READY без calls
auto_expected     PASS — echo, finish tool_calls
required          PASS — echo, finish tool_calls
named (echo)      PASS — вызван именно echo
question_auto     PASS — question, finish tool_calls
question_required PASS — question, finish tool_calls
question_named    PASS — question, finish tool_calls
parallel_required PASS — echo + echo_second, 2 calls, ID уникальны
question_stream   PASS — SSE [DONE] + tool_calls delta
question_roundtrip FAIL — turn1 PASS, turn2 пуст
OVERALL: FAIL (10/11)
```

Evidence: `evidence/matrix-all/` (`request.json`, `response.raw.txt`,
`response.sse.txt`, `summary.json`, `matrix-summary.json`).

Семантика unary: HTTP 200, имена из разрешённого множества, arguments —
валидный JSON-объект без повреждения типов, структура OpenAI-совместима,
`finish_reason` соответствует path. `PROMISE_WITHOUT_TOOL_CALL`,
`MALFORMED_ARGUMENTS`, `UNKNOWN_TOOL`, `TEXTUAL_FAKE_TOOL_CALL`,
`EMPTY_TOOL_CALL`, `DUPLICATE_TOOL_CALL` — не наблюдались.

Оговорка: каждый tool-call ответ несёт `"content":"<eos>"`
(unary и stream, включая `auto_expected`, `required`, `named`,
`question_*`; в RC1-evidence было `""`). Тулколл настоящий, но special
token просачивается в пользовательский `content` — протокольный дефект.

`tool_choice`: `none` без calls — PASS; `required` реально форсит —
PASS; `named` вызывает именно разрешённый tool — PASS.

Stream: имя/аргументы `question` реконструируются как в unary, потерь и
дублей фрагментов нет, reasoning в tool-поля не попадает; но `<eos>`
приходит отдельной `content`-дельтой после tool-дельты.

Parallel repeated same tool (вручную, вне harness):
`get_weather(Berlin/Munich/Hamburg)` + `get_timezone(Berlin)` —
**PASS 4/4**: порядок, уникальные ID, без дедупликации и смешивания
аргументов. Evidence: `evidence/manual-probes/parallel-repeated-same-tool.*`.
Stream-вариант parallel отдельным кейсом не гонялся (gap).

## 6. Roundtrip / multi-turn — КРИТИЧЕСКИЙ FAIL

```text
turn1: question tool_call, 200, finish tool_calls — PASS
turn2 (tool result {"answer":"A"}) → 200, finish stop, content "", calls [] — FAIL
```

Симптом: `model stops after tool result / empty assistant response /
generation terminates immediately` (`completion_tokens: 1`).
Изоляция: turn2 повторён с вычищенной историей (`content: null` и
`content: ""` вместо `"<eos>"`) — тот же пустой ответ. Причина не в
отравлении истории, а в продолжении после `role: tool`
(session state / generation / template path).

```text
ROUNDTRIP_SINGLE:  FAIL
MULTITURN_2_CALLS: FAIL
MULTITURN_3PLUS:   FAIL (не достигнуто)
```

Evidence: `evidence/matrix-all/question_roundtrip/turn{1,2}/`,
`evidence/manual-probes/rt-clean-turn2-{clean,empty}-history.*`.

## 7. Stability

100-call run сознательно не гонялся при открытом semantic FAIL.
Обязательный минимум:

```text
20 sequential unary (echo/auto):  20/20 PASS
20 streaming (echo/auto):         20/20 PASS
post-run plain chat ("2+2"→"4"):  PASS
```

Деградации нет — это logical/protocol failure при здоровом runtime.
Evidence: `evidence/stability/unary-20.json`, `stream-20.json`,
`post-plain.json`, `summary.json`.

## 8. Runtime faults

Поиск по живому логу: `ERROR 0, FATAL 0, exception 0,
CL_OUT_OF_RESOURCES 0, GPU_CONTEXT_FATAL 0, quarantine 0, timeout 0,
WARNING 0`; `executor` — только info `All requests: 0/1`;
`tool` — auto-detect gemma4; stderr пуст. Наличие слова `ERROR` не
считалось дефектом без контекста — контекста дефекта нет.

## 9. Итоговая таблица

| Layer | Test | Result | Evidence |
|---|---|---|---|
| artifact | RC2 binary identity | PASS | path + SHA256 |
| startup | server/model load | PASS | `live-sanity/models.response.json`, лог |
| baseline | plain chat | PASS | `live-sanity/plain-chat.response.json` |
| parser | parser regression suite | NOT_EXECUTED (gap) | sources §3 |
| preprocess | OpenAI preprocessing | NOT_FOUND | нет `ovmsclient` в RC2 |
| generation | prompt/generation contracts | NOT_EXECUTED (gap) | sources §3 |
| template | Gemma template contracts | NOT_EXECUTED (gap) | sources §3 |
| unary | auto | PASS* | `matrix-all/auto_expected` |
| unary | required | PASS* | `matrix-all/required` |
| unary | named | PASS* | `matrix-all/named` |
| streaming | streamed tool call | PASS* | `matrix-all/question_stream` |
| parallel | distinct calls | PASS* | `matrix-all/parallel_required` |
| parallel | repeated same tool | PASS* | `manual-probes/parallel-repeated-same-tool.*` |
| roundtrip | tool result continuation | FAIL | `matrix-all/question_roundtrip/turn2` |
| multi-turn | >=2 sequential calls | FAIL | `manual-probes/rt-clean-turn2-*` |
| stability | repeated unary | PASS | `stability/unary-20.json` 20/20 |
| stability | repeated streaming | PASS | `stability/stream-20.json` 20/20 |
| runtime | post-load health | PASS | лог без faults + post-plain |

`*` — tool-семантика PASS, с оговоркой `<eos>` в `content`.

## 10. Verdict

```text
RC2_NOT_ACCEPTED_PROTOCOL
```

Блокеры: пустое продолжение после tool result (roundtrip/multi-turn) и
систематическая утечка `<eos>` в `content` tool-ответов. Runtime здоров,
стартап и stability зелёные. Продукт в этой сессии не менялся.

```text
GEMMAMONSTER RC2 ACCEPTANCE

RC2_BINARY: C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914\ovms\ovms.exe
RC2_SHA256: 11d74fd958d1cd2570682fa13562c1bfcf0973dabbf79a0378a8d0cdc886a4fb

SOURCE_HEAD: a2eaeb783dfd66f80c50070bf7050dd184b01364

UNIT_TESTS:
PARSER: NOT_EXECUTED
PREPROCESS: NOT_FOUND
GENERATION: NOT_EXECUTED
TEMPLATE: NOT_EXECUTED
STREAMING: NOT_FOUND (unit); live stream PASS with <eos> caveat

LIVE:
PLAIN_CHAT: PASS
AUTO: PASS*
REQUIRED: PASS*
NAMED: PASS*
STREAM: PASS*
PARALLEL: PASS*
REPEATED_TOOL: PASS* (4/4)
ROUNDTRIP: FAIL
MULTITURN: FAIL

STABILITY:
UNARY: 20/20 PASS
STREAM: 20/20 PASS
POST_RUN_HEALTH: PASS

RUNTIME_FAULTS: none

FAILED_TESTS: question_roundtrip/turn2; rt-clean-turn2-clean-history; rt-clean-turn2-empty-history; <eos>-in-content

VERDICT: RC2_NOT_ACCEPTED_PROTOCOL
```

FAIL-разбор:

1. **roundtrip turn2 пуст** — факт: `200/stop/""/[]/1 token`;
   ожидалось: финальный ответ или следующий валидный `tool_call`;
   вероятный subsystem: `session state` / `generation config` / `chat template`;
   evidence: `evidence/matrix-all/question_roundtrip/`,
   `evidence/manual-probes/rt-clean-turn2-*`.
2. **`content:"<eos>"` в tool-ответах** — факт: литерал `<eos>` в `content`
   при корректном `tool_calls`; ожидалось `""`/`null`; вероятный
   subsystem: `streamer` / `output parser`; evidence:
   `evidence/matrix-all/{required,named,question_*,auto_expected}/`,
   `evidence/matrix-all/question_stream/response.sse.txt`.

## 11. Воспроизводимость

Скрипты прогона (без изменений продукта): `scripts/run-sanity.py`,
`scripts/manual-probes.py`, `scripts/run-stability.py`; матрица —
внешний `toolcall_matrix.py --mode all` против `http://127.0.0.1:18091/v3`.
Сервер после прогона остановлен. Ветка содержит только документацию и
evidence этой сессии.
