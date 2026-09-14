# Второй (и третий) тулколл на heretic-26B — да, делает (2026-09-14)

Вопрос ревьювера: single roundtrip у heretic PASS, а второй tool call подряд?
Ответ: **да**. Тот же RC2-бинарник, heretic-26B, GPU/VLM_CB, `:18091`,
`temperature=0`, всё `tool_choice=auto` (естественное поведение, без форсинга).

## Chain A: один tool, три терна — чисто

```text
A1 user "weather in Berlin?"  -> get_weather(Berlin)  finish=tool_calls  18 tok
A2 + result + "And Munich?"   -> get_weather(Munich)  finish=tool_calls  17 tok
A3 + result + "And Hamburg?"  -> get_weather(Hamburg) finish=tool_calls  16 tok
```

Каждый вызов — правильный `tool_call_id`, имя, аргументы. Content везде `''`
(утечки `<eos>` нет и тут). `MULTITURN_2_CALLS: PASS`, `MULTITURN_3PLUS: PASS`.

## Chain B: кросс-тул question → echo → echo — да, с артефактом бюджета

```text
B1  "ask with question tool"              -> question(...)       tool_calls  142 tok
B2  + {"answer":"A"} + "echo my answer"   -> ПУСТО, finish=length, 256/256 tok
B2b то же самое, max_tokens=1024          -> echo({"text":"A"})  tool_calls   14 tok
B3b + echoed + "echo DONE"                -> echo({"text":"DONE"}) tool_calls 17 tok
```

B2 сгенерировал 256 токенов в никуда: ни content, ни `tool_calls`, ни
`reasoning_content` в ответе. Тот же запрос с бюджетом 1024 — корректный вызов
за 14 токенов. Вывод: B2 — **усечение бюджетом внутри (вероятно) незакрытого
thought-канала**, а не отсутствие способности. Двусмысленный tool result
(`{"answer":"A"}` против опций London/Paris/Berlin/Rome) отправляет модель в
долгое раздумье.

## Пища ревьюверу (открытые вопросы, не утверждения)

1. **Невидимое мышление как класс дефекта наблюдаемости.** 256 токенов работы,
   ноль байт в ответе, `finish=length` — снаружи неотличимо от «модель сожгла
   бюджет вхолостую». Thought-канал в этом API не возвращается вообще. Стоит ли
   тестировать turn2 только с запасом `max_tokens`, и считать ли `length`+пусто
   отдельным failure-классом probe (`TRUNCATED_IN_THOUGHT`)?
2. **Сколько думать — нормально?** 256 токенов раздумий ради тривиального echo —
   много. Это свойство heretic-весов, промпта, или парсер держит канал открытым
   дольше нужного? Без видимости reasoning не разделить.
3. **E4B vs heretic по второму коллу.** На E4B мультитерн мёртв на первом же
   продолжении (см. acceptance), на heretic живут цепочки 3+. Граница
   capability проходит где-то между 4B и 26B — круг кандидатов на минимальный
   gating-модельный ряд открыт.
4. **Эвристика для fix-цикла:** turn2 с неоднозначными tool results гонять с
   `max_tokens ≥ 1024`, иначе ложные `length`-FAILы.

Evidence: `evidence/heretic-multiturn/` (14 файлов: запросы/ответы A1–A3,
B1, B2, B2b, B3b), скрипты `scripts/heretic-multiturn.py`,
`scripts/heretic-multiturn2.py`. Живой heretic-инстанс на момент записи —
`:18091`.
