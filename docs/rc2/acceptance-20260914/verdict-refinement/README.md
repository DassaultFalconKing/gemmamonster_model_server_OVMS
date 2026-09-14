# Verdict refinement — гипотезы расследованы (2026-09-14, вечер)

Продолжение acceptance из `../README.md` (вердикт `RC2_NOT_ACCEPTED_PROTOCOL`
для конфигурации E4B). Тот же RC2-бинарник (`11d74fd9…`), продукт не менялся,
ничего не пересобиралось. Вопрос был один: **смерть turn2 — баг продукта или
вес модели?** Ответ: **вес модели (H1 подтверждена), механика продукта
реабилитирована**.

Дополнение тем же вечером: [`MULTITURN.md`](MULTITURN.md) — второй и третий
тулколлы heretic делает (цепочки 3/3 same-tool и question→echo→echo), плюс
артефакт усечения бюджетом внутри мышления (B2 `length`+пусто при 256 токенах,
корректный вызов при 1024).

## Решающий эксперимент

Та же forensic probe (`roundtrip_probe.py`, ветка
`diagnostics/gemma4-roundtrip-forensics`, HEAD `e657d40`, 9/9 тестов OK на
Windows-чекауте), те же истории (exact / clean-null / clean-empty ×
unary+stream), тот же RC2 `ovms.exe` — но против **heretic-26B** (GPU,
`VLM_CB`, geometry из wondernutts-smoke, READY за ~28 c):

```text
[run 1/1] PASS [none]
OVERALL: PASS
```

- turn1: `tool_calls=[question]`, `content=''`, `FAIL=[]` — **утечки `<eos>` нет**;
- turn2 все 6 вариантов: живое продолжение
  (`The answer is **Paris**…`), `FAIL=[]`.

Evidence: `evidence/heretic/` (`REPORT.md`, `summary.json`, `run-001/`).

## Что это доказывает и что уточняет

1. **H1 CONFIRMED.** Смерть turn2 на E4B — EOS-аргмакс маленькой модели после
   well-formed `<tool_response|>` (промпт доказан TRACE-рендером:
   id совпадают, блок `response:question{…}` канонический, конец сразу после
   `<tool_response|>`). Механика roundtrip в RC2 работает.
2. **Утечка `<eos>` — двойная атрибуция.** Триггерится терминальной эмиссией
   E4B (heretic её не даёт), но чинится на стороне продукта: terminal flush
   `Gemma4ToolParser` (`AfterToolCall → Content`, `parseChunk`, строки ~928–938)
   стирает только `{TURN_END_TAG ("<turn|>"), TOOL_RESPONSE_START_TAG}`,
   `"<eos>"` в erase-списке нет, `stringsToErase` в конфигах Gemma4 не задан.
   Минимальный безопасный фикс — добавить `"<eos>"` (и аудит `"<end_of_turn>"`).
   Reasoning parser ни при чём ни там, ни там: в turn2 он не активируется
   (1 токен EOS, start-тегов нет, `finishReason` он игнорирует), в turn1
   thought-канала нет вообще.
3. **H2 ослаблена до ~10%, H3 ~0%.** Форма `tool_response`-блоков побайтово
   одинакова в шаблонах E4B и heretic — heretic на ней продолжается.
   Prefix-cache-коллизия убита E6a (пересекающийся префикс — жив).
4. **Честный остаток: конфоунд executor (~5%), неустранимый средствами RC2.**
   Heretic шёл через `VLM_CB`, E4B — через legacy `VLM`. Проверка E4B+CB
   невозможна: E4B падает на CB и на GPU с той же SDPA-ошибкой, что и на CPU:
   `No ScaledDotProductAttention operation observed … SDPAToPagedAttention`,
   `LOADING_PRECONDITION_FAILED` (лог: `evidence/server-e4b-cb/`). Контрдовод:
   весь `io_processing` общий и executor-agnostic; deterministic EOS-vs-23-токена
   из шедулера не выходит; E3 доказывает продолжение на legacy.
5. **Дифференциальная карта E4B** (все на живом RC2, evidence `evidence/hypotheses/`):
   plain 2-turn без tools — жив; assistant+tool_calls без tool-сообщения — жив;
   любое `role: tool` в истории — смерть (1 токен, пусто) при любых `tools` /
   `tool_choice` / температуре / длине результата. Яд — именно `tool`-сообщение
   в рендере, а не грамматика и не история.

## Следствия для acceptance и цикла агента

- Буква вердикта для **E4B-конфигурации** сохраняется
  (`RC2_NOT_ACCEPTED_PROTOCOL`), но атрибуция меняется: model capability.
- E4B исключить из roundtrip-gating; gating-гейт — **heretic PASS** (уже есть).
- Фикс утечки `<eos>` — делать независимо (реален, механизм показан).
- Цикл `AGENT_ROUNDTRIP_FIX_PROMPT.md` дополнить: heretic-PASS обязателен,
  E4B-roundtrip не gating; executor-swap E4B↔CB невозможен (SDPA).

## Карта evidence

- `evidence/heretic/` — PASS-прогон probe (REPORT, summary, run-001, snapshots).
- `evidence/hypotheses/` — E1–E8 запросы/ответы дифференциальной карты.
- `evidence/server-trace/` — TRACE-лог с дампами истории и рендером промпта turn2.
- `evidence/server-heretic/` — конфиг/лог живого heretic-инстанса.
- `evidence/server-e4b-cb/` — конфиг + SDPA-фейл E4B на CB/GPU.
- `scripts/` — раннеры (hypotheses, trace-capture, стартеры серверов, показы).

Живой инстанс на момент записи: heretic-26B / RC2 / `:18091` (VLM_CB, GPU).
Ключевые forensic-артефакты TRACE-прогона:

```text
turn2 prompt (дословно, глазами модели):
<|turn>user
Ask me one simple test question using the question tool.<turn|>
<|turn>model
<|tool_call>call:question{questions:[...]}<tool_call|><|tool_response>response:question{value:<|"|>{"answer": "A"}<|"|>}<tool_response|>
```
