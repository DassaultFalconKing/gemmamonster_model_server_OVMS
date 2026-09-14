# Gemma4 tool-calling regression notebook

Дата начала: 2026-09-14  
Статус: **живой forensic notebook**  
Область: Gemma4 / agentic multi-turn / tool-calling / reasoning / structured generation / streaming

Этот файл не является acceptance verdict сам по себе. Его задача — сохранять историю расследования классов регрессий, чтобы следующий цикл начинался с подтверждённых границ, а не с повторного изобретения уже отвергнутых гипотез.

## 0. Якоря расследования

Текущий product source:

```text
908d669563f57535ab4eb747989e9ab33dfd5267
```

Документационная ветка на момент создания notebook:

```text
docs/rc2-acceptance-20260914
0fc4951ac77dbed81fb61c44db37d942b51b7d26
```

RC2 binary SHA256:

```text
11d74fd958d1cd2570682fa13562c1bfcf0973dabbf79a0378a8d0cdc886a4fb
```

Поведенческий known-good, от которого отсчитывался refit:

```text
9a1626260614f68a6282b6799842d5152f0dcdff
```

Основная gating-модель текущего расследования: heretic-26B, GPU, `VLM_CB`.

Связанные документы:

- `../README.md` — исходный RC2 acceptance;
- `README.md` — refinement verdict и E4B vs heretic forensic map;
- `MULTITURN.md` — проверка 2-го/3-го последовательного tool call на heretic.

## 1. Правила записи evidence

Каждый вывод в этом notebook должен принадлежать одному из четырёх классов:

- **OBSERVED** — непосредственно получено из запроса, ответа, raw trace, лога, token stream или diff;
- **INFERRED** — наиболее вероятное объяснение observed evidence, но не доказанный механизм;
- **OPEN** — гипотеза или вопрос, который ещё нужно разделить экспериментом;
- **SUPERSEDED** — промежуточный вывод, который позже был опровергнут более сильным evidence.

Запрещено молча переписывать историю. Если новая проверка меняет вывод, старый вывод остаётся в timeline и помечается `SUPERSEDED` с причиной.

## 2. Что именно мы считаем protocol refit

GEMMAMONSTER содержит Gemma4-specific protocol layer поверх OVMS:

- Gemma4 tool parser;
- Gemma4 reasoning parser;
- Gemma4-specific generation configuration;
- structured generation через `TriggeredTags`;
- registry-aware tool-name handling;
- recovery для ограниченного bare-call dialect;
- reasoning → tool phase handoff;
- streaming holdback / parser boundary ownership.

Canonical tool-call dialect:

```text
<|tool_call>call:<tool_name>...<tool_call|>
```

Canonical reasoning markers:

```text
<|channel>thought
...
<channel|>
```

Рабочая отправная точка этого расследования: **нет evidence, что refit исчез или был глобально сломан в RC2**.

Наоборот, clean short probes и heretic multi-turn показывают, что canonical path жив.

## 3. Исторический failure mode: `<call:...>`

### OBSERVED

В ранних Gemma4 agentic-тестах literal формы вида:

```text
<call:exa_web_search_exa(...)>
<call:bash(...)>
```

наблюдались многократно, а не как единичный эпизод.

Это важная историческая поправка. Нельзя классифицировать `<call:...>` только как случайную single-session contamination.

### OBSERVED

Текущий Gemma4 parser canonical `<call:...>` не считает tool call. Он знает canonical `<|tool_call>...<tool_call|>` и ограниченный recovery для bare `call:`. Поэтому если модель уже выдала `<call:...>`, эта форма может пройти как обычный content.

### INFERRED

`<call:...>` выглядит как **soft protocol drift / fallback dialect**: семантический intent вызвать инструмент сохраняется, но модель теряет точную сериализацию native Gemma4 protocol и выбирает приблизительную текстовую форму.

Это отличается от утверждения «parser сломан». Parser может корректно отвергать неканонический dialect, а источник drift находиться раньше.

## 4. Почему сначала подозревали parser/generator regression

Первичный симптом выглядел просто:

```text
tool intent есть
    -> вместо OpenAI tool_calls[] появляется literal <call:...>
```

Естественная первая гипотеза была: сломался Gemma4 parser, generator или phase routing.

Сравнение реального known-good `9a162626...` с RC2 `908d669...` не показало содержательной регрессии в core Gemma4 parser/generator path, которая сама по себе объяснила бы новый dialect.

Это не доказывает отсутствие runtime/state-dependent дефекта, но делает простую source-regression гипотезу слабой.

## 5. Проверенная гипотеза: schema/guidance fallback

В runtime существует путь, где failure JSON-schema validation может снять structured-output configuration и продолжить inference.

Потенциальный механизм был таким:

```text
complex tool schema
    -> structured-output validation failure
    -> guidance снят
    -> tools остаются в prompt
    -> модель импровизирует tool-call syntax
    -> <call:...> уходит в content
```

### OBSERVED

На cold-restart diagnostic с real Exa schema, minimal Exa schema, `auto`, `required` и named choice не было найдено сообщения:

```text
Tool guided generation will not be applied due to JSON schema validation failure
```

Canonical `tool_calls[]` при этом работали.

### CURRENT STATUS

`REAL_SCHEMA_GUIDANCE_FAILURE`: **NOT OBSERVED** в clean RC2 probes.

Это не универсальное доказательство невозможности fallback, но текущий leakage этим механизмом не объяснён.

## 6. Cold-restart leakage campaign

Был выполнен cold restart того же RC2 binary с тем же heretic model family и Gemma4 parsers.

Проверены:

- simple echo / auto;
- real Exa / auto;
- minimal Exa / auto;
- real Exa / required;
- real Exa / named;
- prompt, искусственно содержащий один literal `<call:...>` example.

### OBSERVED

Во всех clean short probes:

```text
tool_calls[]     present
finish_reason    tool_calls
content          empty
literal <call:   absent
```

Single-example contamination не заставила модель перейти на `<call:...>`.

### CURRENT STATUS

Исходный leakage имеет статус:

```text
NOT_REPRODUCED_IN_CLEAN_STATE
```

Не `DISPROVED`.

Не были воспроизведены исходный внешний agent harness, длинная накопленная history и тот же retry pressure.

## 7. Multi-turn: что на самом деле умеет heretic

Первый промежуточный diagnostic report создал впечатление, что после трёх canonical calls четвёртый turn детерминированно сжигает как 256, так и 1024 completion tokens и остаётся пустым.

### SUPERSEDED

Утверждение:

```text
"turn-04 fails at both max_tokens=256 and max_tokens=1024"
```

**опровергнуто более свежим evidence**.

### OBSERVED

`MULTITURN.md` фиксирует:

```text
Chain A:
weather Berlin  -> tool call
weather Munich  -> tool call
weather Hamburg -> tool call
```

Все три последовательных tool calls canonical и успешны.

Cross-tool chain:

```text
B1 question(...)                              -> tool_calls
B2 + {"answer":"A"}, max_tokens=256           -> empty, finish=length, 256/256
B2b same history, max_tokens=1024             -> echo({"text":"A"}), tool_calls, 14 tok
B3b + result                                  -> echo({"text":"DONE"}), tool_calls, 17 tok
```

Следовательно, heretic не имеет простого hard boundary «после трёх tool turns всегда смерть».

### CURRENT INTERPRETATION

Найден другой класс ошибки: **budget-sensitive invisible continuation**.

При неоднозначном tool result и маленьком completion budget модель может потратить весь бюджет так, что клиент не получает ни content, ни `tool_calls`, ни `reasoning_content`, и видит только:

```text
finish_reason=length
```

При большем budget тот же semantic continuation способен завершиться правильным tool call.

## 8. Связь старого `<call:...>` и нового hard failure

### OPEN HYPOTHESIS

Более жёсткий protocol refit мог не создать новый класс проблемы, а изменить её внешний вид.

До hardening:

```text
tool intent
    -> protocol lock ослаб
    -> модель имеет soft escape hatch
    -> <call:foo(...)> / malformed text
    -> агент иногда продолжает жить
```

После hardening:

```text
tool intent
    -> canonical constraints удерживаются лучше
    -> soft dialect drift подавляется
    -> pathological reasoning / constrained continuation дольше остаётся внутри допустимого state space
    -> budget exhaustion / empty length turn
```

Это **не доказано**, пока не видны raw generated tokens проблемного turn.

Но такая модель хорошо согласуется одновременно с двумя фактами:

1. `<call:...>` многократно встречался в ранних менее жёстких тестах;
2. clean RC2 теперь уверенно держит canonical syntax, но показывает budget-sensitive невидимые continuation failures.

## 9. Важный вывод про refit

### OBSERVED

На текущем RC2:

- canonical short tool calling на heretic работает;
- real Exa schema работает;
- `auto`, `required`, named работают в clean probes;
- same-tool chain 3/3 работает;
- cross-tool chain продолжает работать при достаточном budget;
- `<call:...>` в clean campaign не воспроизведён.

### INFERRED

Protocol refit, вероятнее всего, **сохранился и выполняет свою основную работу**.

Более строгий protocol layer мог сделать старые эпизодические ошибки более дискретными и наблюдаемыми. Вместо смеси malformed text, случайных повторов и неполных вызовов мы чаще получаем чёткие классы:

- canonical success;
- terminal-token leakage;
- empty post-tool turn;
- budget truncation inside invisible reasoning;
- hard structured-generation stall;
- dialect drift.

Для расследования это улучшение, даже если acceptance от этого магически зелёным не становится.

## 10. Не путать разные failure classes

### F1. DIALECT_DRIFT

Пример:

```text
<call:foo(...)>
```

Tool intent видим, native serialization потеряна.

### F2. TERMINAL_TOKEN_LEAK

Пример: `<eos>` попадает в visible content после корректного tool call.

Это отдельный product/parser flush defect. Он уже имеет независимую атрибуцию и не должен смешиваться с `<call:...>`.

### F3. EMPTY_POST_TOOL_EOS

Характерен для E4B: после `role: tool` модель может сразу выбрать EOS.

Current refinement относит это в первую очередь к model capability E4B, а не к общей broken roundtrip mechanics RC2.

### F4. TRUNCATED_IN_THOUGHT / INVISIBLE_BUDGET_EXHAUSTION

Наблюдаемая форма:

```text
completion_tokens == max_tokens
visible deltas == 0
finish_reason == length
```

Тот же history может завершиться корректно при большем budget.

### F5. TRUE_GRAMMAR_THRASH

Пока **не доказан** для текущего B2.

Для этого нужно видеть raw tokens / grammar state и показать повторяющуюся невозможность завершить structured form, а не просто `length`.

### F6. PARSER_OR_STREAMER_LOSS

Raw generation валидна, но observable deltas теряются downstream.

Также требует raw-token/phase evidence.

## 11. Главный следующий forensic вопрос

Для любого нового `empty + length` case сначала отвечать не на вопрос «что чинить?», а на вопрос:

> Какие именно raw tokens модель сгенерировала и на каком слое они перестали быть observable?

Минимальная цепочка evidence:

```text
rendered prompt
    -> effective GenerationConfig
    -> raw generated token IDs
    -> decode(skip_special_tokens=false)
    -> decode(skip_special_tokens=true)
    -> reasoning/tool/content parser phase
    -> Delta / nullopt
    -> SSE/API response
```

Первый слой, где good turn и bad turn расходятся, получает приоритет расследования.

## 12. Differential matrix для empty/length regression

При идентичной history проверить один и тот же failing continuation:

```text
A. tools removed
B. tools present + tool_choice=none
C. tools present + tool_choice=auto
D. tools present + tool_choice=required
```

Интерпретация:

```text
A works, C/D fail
    -> tool/guidance path

B works, C/D fail
    -> structured generation specifically

C fails, D works
    -> lazy auto / TriggeredTags path

C and D fail
    -> common tool grammar / continuation path

A/B/C/D all fail
    -> model/template/reasoning/executor continuation

raw decode normal, API empty
    -> parser/streamer loss
```

Не использовать эту таблицу как verdict без raw evidence.

## 13. Кодовые поверхности первого уровня

Основные файлы для такого класса регрессий:

```text
src/llm/io_processing/generation_config_builder.hpp

src/llm/io_processing/output_parser.cpp
src/llm/io_processing/output_parser.hpp

src/llm/io_processing/gemma4/gemma4_tool_parser.cpp
src/llm/io_processing/gemma4/gemma4_tool_parser.hpp

src/llm/io_processing/gemma4/gemma4_reasoning_parser.cpp
src/llm/io_processing/gemma4/gemma4_reasoning_parser.hpp
```

Regression tests:

```text
src/test/llm/gemma4_fast/gemma4_parser_contract_test.cpp
src/test/llm/gemma4_fast/gemma4_recovery_contract_test.cpp
src/test/llm/gemma4_fast/gemma4_reasoning_semantic_refit_test.cpp
```

Правило: до определения первого divergent layer не добавлять recovery просто потому, что очередной malformed dialect можно распознать regex-ом.

## 14. Почему `<call:...>` recovery нельзя делать первым фиксом

Если `<call:...>` является сигналом потери protocol lock, автоматическое превращение любой похожей строки в executable `tool_calls[]` может:

- скрыть исходный failure mechanism;
- превратить обычный model prose в действие;
- создать новый false-positive surface;
- замаскировать tool thrashing;
- ухудшить безопасность registry boundary.

Если recovery когда-либо добавляется, он должен быть:

- registry-aware;
- ограничен точной observed shape;
- streaming-safe;
- покрыт negative tests;
- мотивирован evidence после выяснения upstream cause.

## 15. Reusable protocol для следующих регрессий

При новом agentic failure:

1. Pin source SHA, binary SHA, model, executor, parsers и launch profile.
2. Отделить clean short probe от accumulated-history reproduction.
3. Сохранить exact request/response до любых изменений.
4. Проверить canonical unary tool call.
5. Проверить один roundtrip с tool result.
6. Проверить 2–3 последовательных canonical tool calls.
7. При `length` сравнить минимум два completion budgets.
8. Не называть failure `grammar thrash`, пока нет raw-token/grammar evidence.
9. При text leakage сохранить literal malformed dialect полностью.
10. Проверить, зарегистрировано ли имя инструмента и где parser впервые отдаёт content.
11. Сравнить good и bad rendered prompt tail.
12. Найти первый divergent layer, и только после этого менять код.
13. Любой изменившийся вывод пометить `SUPERSEDED`, а не стирать из истории.

## 16. Текущая стартовая позиция

На момент создания notebook:

```text
Gemma4 protocol refit                 apparently intact
canonical short tool calling          PASS on heretic
real Exa clean probes                  PASS
required/named clean probes            PASS
historical <call:...>                  repeatedly observed in early tests
<call:...> on clean current RC2        NOT_REPRODUCED_IN_CLEAN_STATE
single-example contamination           NOT_REPRODUCED
schema-validation fallback             NOT_OBSERVED
same-tool 3-call chain                 PASS
cross-tool continuation                PASS with sufficient budget
256-token ambiguous continuation       empty + finish=length observed
1024-token same continuation           PASS, tool call in 14 tokens
true grammar thrash                    NOT_YET_PROVEN
raw-token location of invisible work   OPEN
```

Главная рабочая гипотеза на старте следующей итерации:

> Refitted RC2 удерживает canonical Gemma4 tool protocol заметно лучше ранних версий. Старый soft failure mode `<call:...>` исторически реален, но в clean RC2 не воспроизводится. Более строгие constraints могли превратить часть прежних мягких protocol drifts в более жёсткие budget-sensitive / invisible continuation failures. Следующий шаг — локализовать невидимые generated tokens по слоям до любого нового parser recovery.

## 17. Журнал изменений

### 2026-09-14 — notebook initialized

- Зафиксирован исторический факт многократного `<call:...>` в ранних тестах.
- Clean-RC2 leakage campaign записан как `NOT_REPRODUCED_IN_CLEAN_STATE`, а не `DISPROVED`.
- Schema-validation fallback оставлен `NOT_OBSERVED`.
- Исправлен устаревший промежуточный вывод о deterministic 1024-token failure: актуальный evidence показывает B2 `256 -> empty/length`, B2b `1024 -> canonical echo tool call`.
- Same-tool 3-call heretic chain зафиксирован как PASS.
- `GRAMMAR_THRASH` по одному `empty + length` запрещено считать доказанным без raw-token evidence.
- Сформулирована reusable процедура для будущих Gemma4 agentic regressions.
