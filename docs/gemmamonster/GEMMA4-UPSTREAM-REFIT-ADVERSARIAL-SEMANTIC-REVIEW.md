# GEMMA4 UPSTREAM REFIT — ADVERSARIAL SEMANTIC REVIEW

Дата: 2026-09-15. Роль: независимый adversarial reviewer / architecture analyst.

```text
REVIEW_HEAD: 18de2c26cf80317113167712f40cd39b7e3b5987
UPSTREAM_MAIN: e338fb74b53dc8ac1c48707903b85e3901adcbdc
REFIT_BASE: a5136cb285482aaef5410a053b5ecd04ff9324ec
HARDENED_EVIDENCE_HEAD: 5d995cfafdb2ec90578678aa15714dedebc843b8
OVERALL: NOT MERGEABLE
```

**Основной вывод:** malformed arguments могут оставить публичный call с `id/name`, пустыми arguments и занятым index. Production unary сохраняет его; тестовый helper удаляет. Кроме того, hard grammar не учитывает rendered open thought, а существующий detector не распознаёт canonical Gemma opener с переводом строки. Исправление только plumbing/parallel не закрывает эти дефекты.

## 1. Snapshot, authority и границы доказательств

Review выполнен в отдельном checkout [gemma4-adversarial-review-20260915](C:/git/gemma4-adversarial-review-20260915). Сделан local shared clone, origin перенастроен на указанный GitHub repository, добавлен upstream; затем выполнены `fetch --all --prune`, `switch staging/gemma4-upstream-refit-clean-20260915`, `reset --hard origin/staging/gemma4-upstream-refit-clean-20260915`, status, оба rev-parse и log -35. Reset относился только к новому review checkout. Другой агент и его build directory не изменялись. Production source, тесты репозитория и staging remote не изменялись; push не выполнялся.

Все команды и exit codes: [snapshot.json](snapshot.json). Review checkout чист. `upstream/main` содержит один дополнительный docs commit `e338fb74b` после refit base — `Minor links fix (#4566)`.

**Remote drift:** финальный read-only `ls-remote` уже показывает `81f9a133458601569ebcdfb606bbe9f29e039e30`. Это более новый, **не рассмотренный этим документом** snapshot. Выводы ниже относятся строго к REVIEW_HEAD. Перед реализацией следующий агент должен пересопоставить findings с новым HEAD и пропустить уже исправленные пункты; нельзя приписывать текущему remote старый RED по parallel.

Прочитаны обязательные authority documents на REVIEW_HEAD:

- [COMPARATIVE-GEMMA4-PARSER-VERDICT.md](C:/git/gemma4-adversarial-review-20260915/docs/gemmamonster/COMPARATIVE-GEMMA4-PARSER-VERDICT.md).
- [GEMMA4-UPSTREAM-REFIT-PLAN.md](C:/git/gemma4-adversarial-review-20260915/docs/gemmamonster/GEMMA4-UPSTREAM-REFIT-PLAN.md).
- [LOCAL-AGENT-HANDOFF-20260915.md](C:/git/gemma4-adversarial-review-20260915/docs/gemmamonster/LOCAL-AGENT-HANDOFF-20260915.md).

Handoff содержит исторические инструкции реализации, включая push. Здесь применена явная пользовательская граница: review без production changes и push. Старый hardening branch — только evidence. Рассмотрены его история, adapter и prompt-state tests; старый `PyJinjaTemplateProcessor` не предлагается к переносу.

### Evidence labels и выполненные проверки

| Метка | Что означает |
|---|---|
| SOURCE | Прямой вывод из неизменённого кода REVIEW_HEAD; ссылки ниже привязаны к checkout этого SHA. |
| SOURCE-SLICE | Исполнены извлечённые C++ тела методов с inert tokenizer/logging scaffold; это сильнее ручной трассировки, но не production runtime. |
| TEMPLATE | Скачанный Google template исполнен Python Jinja2 3.1.6; это не проверка OVMS runtime loader или Minja. |
| PROPOSED RED | Точный обязательный тест, который ещё должен быть запущен в штатном target. |

| Проверка | Результат |
|---|---|
| Snapshot/status/source hashes | PASS; [snapshot.json](snapshot.json), [source_probe_manifest.json](source_probe_manifest.json). |
| Изолированный C++ source-slice build и execution | PASS как запуск эксперимента; нарушенные semantic contracts перечислены ниже. MSVC C++17, RapidJSON из существующего dependency tree; никаких OVMS/GenAI DLL не загружалось. |
| Canonical template, 5 нормальных render cases | PASS как render; exact prompts сохранены. |
| Object tool-content, string assistant-arguments | Ожидаемые ошибки Jinja воспроизведены. |
| `git diff --check a5136cb..HEAD -- src` | PASS. |
| `git diff --check a5136cb..HEAD` | FAIL, exit 2: Markdown hard-break trailing spaces в двух docs. Это hygiene, не semantic blocker. |
| Полные Bazel tests/build, реальный streamer/tokenizer, GenAI matcher, live model, SSE | NOT RUN в review. PASS из старых docs не переносится на этот snapshot. |

Повтор экспериментов: `rtk proxy python C:/git/artifacts/gemma4-adversarial-review-20260915-18de2c26c/source_probe.py` и аналогично `template_probe.py`. Первый компилирует **только отдельный source-slice executable**, не OVMS. Генератор probe, весь translation unit, hashes, build log и [raw output](source_probe_output.txt) сохранены. Подмена ограничена зависимостями/constructors для text-level маршрута; тела Gemma argument parser, router методов, stringutils, aggregation и HTTP parseTools взяты из snapshot. Token-ID resolution и production callback не проверялись. Direct-parser byte-feed без generic prebuffer в raw log — диагностический контроль, не поддерживаемый production маршрут. Основные выводы используют `route=1`.

## 2. CRITICAL FINDINGS

### F1 — Публичный tool call создаётся до validation arguments [P0]

Источник: [gemma4_tool_parser.cpp:349](C:/git/gemma4-adversarial-review-20260915/src/llm/io_processing/gemma4/gemma4_tool_parser.cpp:349), далее 362–385 и 429–439.

`parseInToolCallState()` проверяет name/registry, создаёт `ToolCall{generateRandomId(), name, ""}` и увеличивает `toolCallIndex`. `parseChunk()` немедленно возвращает header delta. Arguments разбираются только при следующем продвижении FSM. Ошибка `12foo`/`01` сбрасывает validity/arguments, но обратной операции над уже опубликованным delta нет.

Production [parsedOutputFromDeltas():453](C:/git/gemma4-adversarial-review-20260915/src/llm/apis/openai_api_handler.cpp:453) безусловно сохраняет элемент по index. [Streaming serializer:493](C:/git/gemma4-adversarial-review-20260915/src/llm/apis/openai_completions.cpp:493) запоминает факт любого tool delta; при STOP это влияет и на `finish_reason="tool_calls"`. Отмена через финальный статус не отзовёт уже отправленный SSE header.

SOURCE-SLICE, router, byte chunks + один STOP:

| Input | Raw ToolCallDelta | Production aggregation |
|---|---|---|
| `<|tool_call>call:question{x:12foo}<tool_call|>` | header index 0, id/name, args empty | один phantom call |
| `<|tool_call>call:question{x:01}<tool_call|>` | то же | один phantom call |
| `<|tool_call>call:question{questions:[{x:1}<tool_call|>` | то же | один phantom call |
| `<|tool_call>call:not_in_request{x:1}<tool_call|>` | **нет** tool delta при непустом registry | calls empty; отдельная проблема content leakage, F8 |
| malformed `question{x:01}` + valid `question{x:1}` в двух envelopes | malformed header index 0; valid header/args index **1** | два calls, первый phantom |

Ответы A1–A4: **да**, raw streaming callback может увидеть malformed id/name; **да**, unary сохраняет phantom; **да**, index расходуется до validation; **да**, следующий valid получает 1. Реальный callback здесь доказан маршрутом `OVMSTextStreamer::flush_chunk()` → `m_callback(delta, isLast)` в [ovms_text_streamer.cpp:270](C:/git/gemma4-adversarial-review-20260915/src/llm/ovms_text_streamer.cpp:270); source-slice фиксирует сами deltas, не выдаёт себя за SSE capture.

### F2 — Rendered prompt, grammar и parser начинают из разных состояний [P0]

1. [Builder:78](C:/git/gemma4-adversarial-review-20260915/src/llm/io_processing/generation_config_builder.hpp:78) всегда создаёт `tools | thought-opener + thought-body + thought-close + tools` для required/named.
2. [ChatTemplateProcessor:89–122](C:/git/gemma4-adversarial-review-20260915/src/llm/io_processing/input_processors/chat_template_processor.cpp:89) после обоих render paths проверяет только непустой prompt. Reconciliation отсутствует.
3. [GenAiServable:236](C:/git/gemma4-adversarial-review-20260915/src/llm/servable.cpp:236) вызывает parser detector, но [detector:358](C:/git/gemma4-adversarial-review-20260915/src/llm/io_processing/output_parser.cpp:358) сначала делает `rtrim(renderedPrompt)`, затем сравнивает с `startTags`, где Gemma имеет **`<|channel>thought\n`**. После rtrim строка не может заканчиваться этим tag. SOURCE-SLICE: `needSpecialTokensForCurrentDecode(false)==false`; `private body.` становится **ContentDelta**.

TEMPLATE: после assistant call и role:tool с thinking=true prompt действительно заканчивается `<tool_response|><|channel>thought\n`. При новом turn с thinking=false template заканчивается закрытым empty thought. Результаты: [template_probe_output.json](template_probe_output.json).

Следствия: grammar может требовать второй opener либо немедленный tool внутри открытого thought; отдельно parser может отдать thought continuation как visible content. Исправить только grammar недостаточно. Detector — унаследованный дефект base, а не новая строка refit; он всё равно блокирует заявленный multi-turn contract.

### F3 — HTTP стирает explicit hard choice, когда tools отсутствует/null [P0]

[parseTools():295](C:/git/gemma4-adversarial-review-20260915/src/llm/apis/openai_api_handler.cpp:295) устанавливает `toolChoice="none"`, если `tools` отсутствует или null. Builder уже не видит required/named.

SOURCE-SLICE actual `parseTools()`:

```text
{"tool_choice":"required"}              -> OK, choice=none, registry=0
{"tool_choice":"required","tools":null} -> OK, choice=none, registry=0
{"tool_choice":"required","tools":[]}   -> OK, choice=required, registry=0
```

Последний вариант затем правильно отвергает builder; первые два обходят его hard guard. Это не grammar validation failure. Existing `RequiredWithoutToolsIsRejected` вручную создаёт `OpenAIRequest`; HTTP downgrade остаётся невидимым. Требуется сохранить explicit intent и вернуть InvalidArgument на самом раннем request boundary. То же проверить для named и обоих endpoints.

### F4 — Результат зависит от количества parseChunk-вызовов, а не только от текста [P0]

[Gemma parseChunk:420](C:/git/gemma4-adversarial-review-20260915/src/llm/io_processing/gemma4/gemma4_tool_parser.cpp:420) делает один `parseNewContent()` за вызов; `nullopt` не различает «нужны bytes» и «state продвинулся без delta». Вся строка одним chunk переводит Content → ToolCallStarted без выдачи события; единственный STOP выдаёт только header и завершается ранним return. Arguments и следующие calls остаются недренированными.

SOURCE-SLICE: canonical two calls по символам → a и b с arguments; тот же текст одним chunk + STOP → только пустой header a. Malformed+valid одним chunk также теряет valid. Это **text parser contract FAIL**, реальная частота таких chunks в tokenizer streamer пока NOT RUN.

Отдельно [Gemma reasoning parser:31](C:/git/gemma4-adversarial-review-20260915/src/llm/io_processing/gemma4/gemma4_reasoning_parser.cpp:31) выбрасывает весь chunk при наличии любого marker. `"<|channel>thought\nsecret<channel|>answer"` одним chunk + STOP в router source-slice даёт `ReasoningDelta("answer")`: secret теряется, answer неправильно классифицируется. По символам результат другой. Этот inherited дефект должен иметь собственный RED, без обвинения новой boundary flag.

## 3. IMPORTANT FINDINGS

### F5 — Parallel policy на REVIEW_HEAD ещё RED [P1, уже работа другого агента]

HTTP не читает `parallel_tool_calls`; `OpenAIRequest` не имеет поля; builder не присваивает `stop_after_first`. HEAD `18de2c26c` добавляет RED tests, не GREEN. SFINAE helper `parallelPolicy(..., long)` возвращает true при отсутствии поля: default/true tests могут быть зелёными без plumbing. False и invalid-type cases правильно должны падать. Полная штатная suite в review не запускалась. Новейший remote может уже закрывать этот пункт — сначала проверить, не дублировать работу.

### F6 — HTTP и builder принимают names, которые output parser отвергает [P1]

[HTTP:233–290](C:/git/gemma4-adversarial-review-20260915/src/llm/apis/openai_api_handler.cpp:233) проверяет string type, но не alphabet. [buildToolTag:45](C:/git/gemma4-adversarial-review-20260915/src/llm/io_processing/generation_config_builder.hpp:45) конкатенирует name как literal begin. Parser использует `saneToolName()` и registry. SOURCE-SLICE: все восемь пользовательских adversarial names проходят parseTools и попадают в registry. Дальнейшее поведение — compiler reject либо generation/parser mismatch; оба хуже раннего InvalidArgument.

Также `toolChoice` — одна строка для policy и function name. Named tool с именем `none`, `auto` или `required` коллидирует с policy keywords. Это отдельный request representation contract: valid tool name не должен интерпретироваться как policy. Нужен discriminant либо явная, документированная ранняя ошибка до silent reinterpretation.

### F7 — Валидный JSON Schema может описывать body, который Gemma parser не принимает [P1]

Builder допускает, например, parameters `{"type":"string"}` или `{"type":"array"}`. Такой schema может быть валиден для JSONSchema engine, но Gemma header parser ищет `{` или `(` и ожидает object arguments. Запретить non-object tool argument schemas; неоднозначный union с non-object тоже не объявлять supported. `$ref`/compositions требуют разрешения реального root contract, а не примитивной проверки единственного поля `type`.

Tool definition без `parameters` остаётся в template tools, но не попадает в `toolNameSchemaMap`. Определить единую политику: стандартный empty object schema для разрешённого no-args tool либо ранняя ошибка. Silent omission даёт разные tool sets в prompt/generator/parser. Duplicate names сейчас перезаписывают map, сохраняя неоднозначный исходный tools array: тоже InvalidArgument.

### F8 — Unknown tool не исполняется, но его envelope может утечь в content [P1]

Registry constructor заменяет generic text opener набором известных prefix+name+brace. Unknown canonical call не включает tool phase. DefaultContentParser не удаляет `<|tool_call>`/`<tool_call|>`. SOURCE-SLICE routed text выдаёт unknown input в ContentDelta целиком или частями. При production skip-special часть markers может исчезнуть, но text `call:not_in_request...` останется; точный token path — PROPOSED RED. `RejectsUnknownRegisteredTool` проверяет только calls.empty().

Предпочтительно распознавать canonical envelope независимо от registry и отклонять candidate внутри parser; registry должен решать eligibility, а не возможность увидеть boundary. Bare recovery остаётся только registry-aware.

### F9 — Одно-envelope multi-call и garbage promotion [P1]

[parseInToolCallEndedState():390](C:/git/gemma4-adversarial-review-20260915/src/llm/io_processing/gemma4/gemma4_tool_parser.cpp:390) ищет следующий `call:` через произвольный текст до end marker. SOURCE-SLICE byte-routed варианты `a{x:1}call:b{x:2}` и `a{x:1} garbage call:b{x:2}` дают **два** исполняемых calls. Ни newline, ни новый canonical opener не нужны. Это намного шире объявленного bounded bare recovery.

### F10 — Fail-closed recovery неполна; bounds не являются лимитом [P1]

Незакрытый native string `a{x:<|"|>broken}...<tool_call|><|tool_call>call:b{x:2}<tool_call|>` оставляет scanner в string и поглощает последующий valid call; SOURCE-SLICE оставляет один phantom a. Arbitrary text после незакрытого string нельзя одновременно считать literal string и надёжным new envelope без дополнительного evidence — безопаснее ограничить resource budget и не исполнять двусмысленный хвост.

Порог `streamingPosition>=4096` только удаляет уже consumed prefix, не ограничивает растущий body. Scanner заново обходит body на каждом chunk; большой unterminated string/container может дать квадратичную работу. Recursive value parser не имеет явной глубины. Нужны лимит candidate bytes/depth и тесты предсказуемого отказа, согласованные с request token budget; не менять пользовательские context limits в этом PR.

### F11 — Publication не ждёт закрытия envelope [P1]

SOURCE-SLICE input `<|tool_call>call:question{x:1}` по символам + STOP публикует полноценные arguments без `<tool_call|>`. Существующий parser считает достаточным закрытие object. Нельзя объявить это canonical completed call. При transactional redesign commit point должен учитывать envelope close; исключения для bare recovery и stop-token stripping должны быть явными и проверенными реальным token path.

### F12 — Shared remainder ownership не доказана [P1 regression gate]

`parseToolCallChunk()` ищет первый textual endTag и сохраняет suffix, **одновременно передавая весь buffer** subparser, который тоже его хранит. Для native string с literal `<tool_call|>` generic router и container scanner могут выбрать разные boundaries. Это унаследованная архитектурная опасность, не новая строка refit. Условия duplication/loss надо фиксировать exact chunk tests, не объявлять все parser families сломанными. Простого F1 patch недостаточно для доказательства этого invariance.

## 4. FALSE-GREEN TESTS

| TEST/HELPER | WHAT IT HIDES | REPLACEMENT/ADDITIONAL ASSERTION |
|---|---|---|
| `parseWithStreamer`, lines 106–124 | Удаляет empty-arguments calls; сжимает vector и стирает наблюдаемую дыру index 0. Комментарий «mirrors exactly production» неверен. | Capture raw `vector<Delta>`, call production `parsedOutputFromDeltas`, сравнить без фильтрации; отдельно assert отсутствие **любого** malformed ToolCallDelta. |
| `RejectsInvalidNumberLikeBareScalars` | `toolCalls.empty()` после helper sanitization проходит при header leak. | Raw header count=0; production unary count=0; SSE ни разу не содержит malformed id/name. |
| `MalformedCallIsBoundedAndLaterValidCallSurvives` | Удаляет первый phantom и оставляет красивый valid call, не проверяя public index=1. | valid raw header index=0, один id, args соответствуют valid; malformed bytes не участвуют в этом id. |
| `PreservesValidNumberLexemesLosslessly` + helper | DOM parse/write превращает precise lexeme в double. Это может дать **ложнокрасный** exact-byte test и ложнозелёный тест, сравнивающий только numeric value. | Compare arguments bytes до DOM. SOURCE-SLICE: helper roundtrip превращает исходный lexeme в `1.2345678901234566e-13`; сам parser сохраняет оригинал. Не ослаблять assertion. |
| `Gemma4UpstreamRefitContractTest::parse`, line 82 | Всегда `userWantsSpecialTokens=true`; обход default decode path. | Все core cases при false; true оставить второй осью. |
| `Gemma4SpecialTokenHandoffTest` | False выбран правильно, но helper всё ещё sanitizes; один счастливый tokenization и reasoning text. | Raw deltas, no leaked markers, exact reasoning/content, suffix with UTF-8 и malformed/repeated calls. |
| `RequiredToolChoiceInstallsNativeStructuredGrammar` | Только has_value: не доказывает язык, завершение и отсутствие prose-only derivation. | Matcher accepts/rejects таблица из §6, EOS legality, at least one call. |
| `NamedChoiceRestrictsGrammarToSelectedTool` | Substring search serialized AST не доказывает реальную языковую restriction. | Accepted chosen; rejected unchosen, prefix-collision name, EOF before call. |
| `RequiredWithoutToolsIsRejected` | Минуется HTTP normalize-to-none. | HTTP omitted/null/[] + required/named на Chat и Responses. |
| `parallelPolicy(..., long)` | Missing field даёт true, true/default часть suite не доказывает наличие plumbing. | После GREEN убрать fallback; прямой field access и false/type tests. |
| Старый `Gemma4PromptStateGenerationContractTest` | Проверяет вид AST `TriggeredTags`, не принятие continuation body. | Реальный matcher должен принять `continue<channel|><|tool_call>...`; проверить, что prefix free text разрешён до обязательного call. |
| `parseWithStreamer` callback / `streamer.end()` | Ignored isLast/FinishDelta и синтетический STOP не доказывают actual LENGTH/cancellation behavior. | Записывать событие завершения и реальный generation finish reason; invalid/truncated candidate не публиковать. |

Не требуется менять все helpers сразу. Добавить raw capture helper и перевести критические Gemma contracts; отдельно откорректировать общий helper/его misleading комментарий с regression review для остальных consumers.

## 5. TRANSACTIONAL TOOL PUBLICATION

### Design T1 — Полный envelope в буфере, один commit delta — предпочтительный

Candidate содержит private raw name/body, scanner state и validity. До полной syntactic validation, registry check и принятого close envelope публичных index/id нет. На commit выделить следующий index и id, вернуть один `ToolCallDelta{index,id,name,complete_json_arguments}`. `{}` — корректный непустой arguments string. Malformed candidate целиком discard. На следующий valid commit index всё ещё 0.

```text
PROS: нет phantom в SSE/unary; без rollback protocol; один observable commit point.
CONS: header latency до close envelope; нужен bounded candidate buffer.
STREAMING CONSEQUENCES: text/reasoning продолжают стримиться; tool публикуется целиком по завершении каждого envelope.
UNARY CONSEQUENCES: существующая честная aggregation безопасна без санитарной фильтрации.
REGRESSION RISK: клиенты могут ожидать ранний name; проверить callback cancellation и multi-call drain.
```

Это минимальный **semantic** patch: текущая реализация уже буферизует весь arguments body; добавляется ожидание delimiter и перенос index/id allocation. Не требуется field-by-field streaming или новый wire event. Allocation random id раньше commit не является главным дефектом само по себе; главное — не публиковать и не расходовать публичную нумерацию.

### Design T2 — Private candidate, затем header + args как атомарно поставленная пара

После тех же проверок enqueue два существующих delta: header, затем complete args. Очередь обязана drained до FinishDelta; у malformed candidate очередь пуста.

```text
PROS: сохраняет привычный формат двух deltas и existing serializer shape.
CONS: требуется pending-event queue; cancellation между header и args оставит неполную доставку даже валидного call.
STREAMING CONSEQUENCES: нет выигрыша latency до validation; два callback вместо одного.
UNARY CONSEQUENCES: корректна только если queue полностью drained до aggregation/finalize.
REGRESSION RISK: средний; API optional<Delta> легко оставить недренированным при STOP.
```

### Design T3 — Header и args публикуются после parse object, до envelope close

```text
PROS: самый короткий patch F1; устраняет early header для malformed arguments.
CONS: не исправляет valid-object + garbage/second-call/missing-envelope-close; не полная транзакция протокола.
STREAMING CONSEQUENCES: name становится доступен на несколько tokens раньше T1.
UNARY CONSEQUENCES: phantom-arguments исчезают, но malformed envelope может остаться executable.
REGRESSION RISK: низкий объём изменений, высокий остаточный semantic risk.
```

T3 допустим только как промежуточный GREEN для узкого RED, **не merge-ready**. Публикация header до validation с последующим «удалением» в unary не является вариантом решения: SSE retract event в текущем контракте нет.

**Обязательные invariants:** нумерация dense по committed calls; name/id stable; discarded candidate никогда не становится call; args валидный JSON object; STOP/LENGTH/cancel не коммитят недописанный envelope; повторный terminal/drain не дублирует commit. Transactional здесь означает syntactic validity + registry, а не доказательство корректности бизнес-смысла или всех JSONSchema constraints для unguided auto.

## 6. POST-4103 PROMPT STATE

### 6.1 Единая state model

Определения языка, а не обещания конкретного AST:

```text
O = <|channel>thought\n
E = <channel|>
T(S) = <|tool_call>call:<name in S><object body><tool_call|>
R(S,p) = T(S)                 if parallel=false
         T(S)+                if parallel=true
B = thought body up to E, without interpreting markers inside prior tool results

A NEW_TURN:       R(S,p) | O B E R(S,p)
B OPEN_THOUGHT:   B E R(S,p)
C CLOSED_THOUGHT: same ordinary hard grammar as A in the minimal refit
```

Для C direct-tool branch обязательно допустим; adaptation не должна повторно открывать уже закрытый thought. Текущий ordinary grammar также допускает новый thought; stricter thinking-disabled prohibition — отдельное поведение, не скрытая часть этого fix.

Required: S = все допустимые request tools. Named: S = ровно selected tool. После `E` при hard policy нет свободного prose-only пути. Пустой B разрешён. До полного T EOS не принимается как успешное выполнение hard policy; внешняя LENGTH/cancel всё равно возможна и должна остаться честным незавершением, а не обещанием «grammar гарантирует eventual tool при любом token budget».

Auto: обязательного T нет. В OPEN_THOUGHT продолжать B, потребить E, затем обычный lazy auto, который может закончиться текстом без call. Call после закрытия thought использует тот же whitelist/schema/parallel policy. Marker внутри thought не должен становиться executable call; если решено сохранить recovery из reasoning прямо в tool, это отдельная явно маркированная tolerance с тестом, не canonical hard-language branch.

### 6.2 Как определить state по rendered prompt

Использовать фактический prompt после template adapter/render. Не `messages.back().role`, model name или `enable_thinking` в отдельности.

Минимум для current template: сравнивать **одинаково нормализованные** suffix и thought opener (без финального whitespace); closed E в suffix даёт C, new model-turn suffix даёт A. Не делать нынешнее `rtrim(prompt)` vs untrimmed tag.

Для partial assistant prefill нужен state scan текущего model continuation: учитывать последний turn/tool-response boundary, пары channel start/end, literal native strings/quoted regions; OPEN сохраняется и при уже начатом B, а не только пустом opener. Старые thought markers в system/user/tool content не задают state следующей model generation. Token IDs можно использовать как вспомогательные boundaries, разрешая их через tokenizer, но raw marker в tool result тоже может tokenize как special: это не автоматическое доказательство роли. При неоднозначном/незавершённом структурном prefix hard request должен получать явную ошибку, а не угадывать состояние.

Лучше небольшой общий detector, возвращающий state, который потребляют **и grammar adapter, и parser initialization**. Не вводить полноценный declarative response_template engine в этом PR. Результат detector не должен быть исполняемым policy сам по себе: tool choice остаётся источником required/named/auto.

### 6.3 Рекомендуемый seam

`ChatTemplateProcessor::process()` **после** runtime-Jinja/Minja веток и проверки непустого `req.promptText`, **до** возврата, последующего TokenizationProcessor и inference. Именно здесь `InputRequest` уже имеет и actual prompt, и generationConfig. Не переносить старые constructors и Python wiring.

Предпочтение: request-local replacement grammar root по state; сохранить tool tags/schemas, selected subset, repetition bound и mandatory semantics. Не мутировать разделяемый nested shared_ptr из base config: построить новый root, а reused nodes считать immutable. Adaptation idempotent. После изменения вызвать `req.generationConfig.structured_output_config->validate(tokenizer)`; ошибка hard adaptation → InvalidArgument, без optional fallback. Existing early validation в API необходима, но не заменяет validation итогового grammar.

Возможны два bounded implementation paths:

1. Semantic helper, распознающий строго Gemma hard grammar shape и native tag prefix, с построением OPEN_THOUGHT root; на чужом shape не трогать config. Это минимальный перенос в текущие типы. Нужны guards от false match пользовательского response_format и тест неполной/неожиданной формы.
2. Если надёжно восстановить intent из shape невозможно, перенести небольшой typed tool-policy intent в request context, чтобы адаптер перестраивал grammar из policy. Это предпочтительнее дальнейшего наращивания pattern matching AST. Сам по себе generic `generation_state_hint` без потребителя не исправит существующий structured config; большой generic metadata framework не нужен.

Parser initialization в `GenAiServable::prepareInputs()` должен пользоваться тем же detector и видеть OPEN. Он вызывается после process; нельзя независимо повторить нынешнюю ошибочную suffix эвристику.

### 6.4 Старый TriggeredTags workaround не является доказанным GREEN

Старая ветка заменяет hard union на tool-triggered root с `at_least_one=true`, сохраняя `stop_after_first`; её tests проверяют только AST. Current [XGrammar structural-tag docs](https://xgrammar.mlc.ai/docs/latest/structural_tag/structural_tag.html#triggered-tags) явно запрещают leading free text при этом флаге. [Converter v0.2.1](https://github.com/mlc-ai/xgrammar/blob/v0.2.1/cpp/structural_tag.cc#L1926) строит first tag перед dispatch continuation. Следовательно, переносить утверждение dossier «обычная sampling завершит thought» как проверенный факт нельзя.

Версия GenAI, увиденная в local header tree: `2026.4.0-22955-227c33757d1-releases/2026/4`; WORKSPACE указывает на `C:\opt\openvino\runtime`, а не immutable package. Это **обнаруженная build dependency**, не доказанный runtime candidate. Matcher tests нужно выполнить против actual candidate GenAI/XGrammar и записать binary/module hashes. Сравнительная проверка v0.2.1 не заменяет их.

Предпочтительный OPEN root — explicit remaining-thought region с обязательным E, затем R. Первым проверить имеющийся `Tag(begin="", content=AnyText(), end=E)` в Concat с R. Empty begin support и запрет premature structural markers проверить реальным compiler/matcher. `AnyText` в установленном C++ API не имеет поля excludes; не выдумывать его. Если нужен запрет embedded O/tool/turn markers, использовать поддерживаемую structural JSON representation с exclusions после проверки engine либо короткий EBNF/Regex DFA через существующий engine. Это grammar adapter, не новый engine. Переход `B E` должен оставаться обязательным, а просто lazy trigger не является эквивалентным языком.

### 6.5 Exact RED matrix

Fixtures используют tools question/clock с object schemas; `Tq=<|tool_call>call:question{"x":1}<tool_call|>`. JSON body здесь специально обозначает нынешний hybrid mode. В native-body варианте добавить эквивалент `{x:1}`.

| RED test | Rendered state / ожидаемый parser state | ACCEPT | REJECT / дополнительные assertions |
|---|---|---|---|
| Runtime Jinja / tool result / required | suffix O; OPEN / REASONING | `continue` + E + Tq; E + Tq | bare Tq до E; второй O вместо B; `continue` + EOS; E + prose + EOS |
| Minja / тот же history / required | тот же state и generation suffix | тот же язык | те же reject cases; compare final grammar semantics, не только prompt nonempty |
| Normal new turn / required | `<|turn>model\n`; A / UNKNOWN | Tq; O + B + E + Tq | prose-only, O+B+E+EOS, unavailable name |
| Closed empty thought / required | O+E; C / UNKNOWN | direct Tq, original hard grammar retained | no adaptation to OPEN; existing E не требует второго E |
| Open thought / named question | OPEN / REASONING, S={question} | B+E+Tq | B+E+Tclock, EOS before Tq |
| Open thought / auto | OPEN / REASONING, optional tools | B+E+final text+EOS; B+E+Tq | никакого executable delta от marker внутри B; no forced tool solely because OPEN |
| Prior tool result → second tool call | реальный request parse → adapter → render → state → grammar → raw deltas | second call name/args верны; prior reasoning сохранено в tool-use turn | thought body не в content; индекс второго **request** начинается с 0; не продолжать индекс старого response |
| OPEN + parallel=false/true | R max=1 / repeat | один / два canonical calls соответственно | false отвергает второй T после первого; проверять actual matcher termination, не только AST bool |
| Partial assistant thought prefill | O+`already thinking`; OPEN | продолжение B+E+Tq | startsWith/endsWith-only detector не должен объявить A |
| Role:tool value содержит O, но prompt закрыт новым turn | A/C | обычный язык | marker в history не включает OPEN |

В каждом case отдельно проверить `structured_output_config.validate(tokenizer)`, prefix acceptance, EOS acceptance, raw output parser state, finish reason. Test, который подтверждает только `shared_ptr<TriggeredTags>`, недостаточен.

## 7. NATIVE GENERATION GRAMMAR

**Verdict: native envelope + ordinary JSONSchema body — рабочая parser-compatible компромиссная форма для object arguments, но не canonical Gemma wire. Её live model/replay качество в этой сессии не доказано.**

| Вопрос | Вывод |
|---|---|
| Модель способна сгенерировать? | Grammar может задавать JSON object внутри envelope; это не доказательство устойчивой генерации на конкретной модели. Нужны raw token/live tests, включая strings, nested objects и EOS. |
| Parser способен принять? | Да для valid object: `parseKey` принимает JSON quoted keys, `parseJsonString` — JSON strings, recursive parser — objects/arrays/scalars; lexemes сохраняются. Non-object root не поддерживается. |
| Template/replay способен принять? | Да при корректном API JSON object roundtrip: `requiresObjectArguments` адаптирует string arguments в mapping, template сериализует mapping обратно в native notation. Нельзя скармливать ему literal JSON string как mapping. Большие numbers/нестандартные keys требуют отдельного lossless replay test. |
| Canonical protocol? | Нет: [Google prompt-format authority](https://ai.google.dev/gemma/docs/core/prompt-formatting-gemma4) задаёт `<|"|>` для string values. Название «native grammar» сейчас точно лишь для envelope/policy. |
| Хороший upstream design? | Допустим как явно названный hybrid с documented support boundary и acceptance. Нельзя выдавать за завершённый native schema grammar или молча ослаблять schema enforcement. |

[llama.cpp pinned parser](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/common/parsers/gemma4.cpp#L220) строит native strings/recursive values и min/max repetition, но прямо оставляет schema→native conversion незавершённой: per-tool parameters constraints не превращаются в полную native grammar. Его полезная policy не доказывает schema fidelity. [vLLM adapter](https://github.com/vllm-project/vllm/blob/e6960af33b379d502f409e3e2241bbf2b2c2f68d/vllm/tool_parsers/gemma4_engine_tool_parser.py) отказывается от generic whole-output JSON для hard choices; это не прямое опровержение гибридного **body** внутри native envelope. [SGLang detector](https://github.com/sgl-project/sglang/blob/832ec39cc0324cb0e7823dc8385e27a30c356bdd/python/sglang/srt/function_call/gemma4_detector.py) не поддерживает native structural tags; его permissive scalar conversion не образец fail-closed/lossless parser.

Минимальный путь к native body:

1. Сохранить envelope/policy/post-render states. Сменить только body grammar representation.
2. Использовать уже доступный `StructuredOutputConfig::EBNF` либо расширение существующего schema converter на dialect. Не писать xgrammar engine.
3. Если нужен быстрый native syntax-only режим как llama.cpp, **явно** обозначить, что arbitrary JSONSchema constraints им не enforced; перед commit нужна schema validation, и это всё равно не эквивалент hard constrained generation. Не подменять им нынешний контракт незаметно.
4. Для schema-preserving варианта перечислить supported keywords и reject unsupported semantics: object properties/required/additionalProperties, array items/bounds, enum/const, numeric/string restrictions, refs/compositions. Нельзя текстово заменить quotes в JSON grammar: ломаются escaped strings, keys, regex и enum literals.
5. Gate: одна семантическая object fixture должна пройти native generation → raw parser → API arguments → capability adapter → Google replay, сохранив значения/допустимую точность. Unsupported schema → InvalidArgument при hard mode.

Этот roadmap P2; F1/F2/F3/F4 нельзя откладывать ради нового dialect converter.

## 8. MULTI-CALL RECOVERY

В рассмотренных Google template/examples и pinned llama.cpp grammar каждый call имеет собственный envelope. vLLM FSM полезна tolerant transitions, но не предоставляет оснований выполнять `call:b` после произвольного garbage внутри envelope a. Наличие подобного кода в старой OVMS линии — implementation history, не model evidence.

**Verdict:** canonical repeated envelopes оставить; one-envelope multiple `call:` + arbitrary garbage — fail closed. Если после a body до его end marker найден b header, целиком отклонить этот malformed canonical envelope по T1. Уже завершённый отдельный envelope a сохраняется, если следующий envelope malformed. Не «починять» tool traffic превращением substrings в actions.

Оставить tolerant:

- согласованное whitespace вокруг разрешённых lexical границ;
- `()` как уже выбранную ограниченную parser tolerance;
- известный bare `call:name{...}` на настоящем response/reasoning-close/line boundary;
- отдельно доказанный `:<name>` variant, если сохраняется существующая совместимость;
- recovery на следующий полный canonical envelope после **однозначно** завершённого malformed envelope.

Fail closed: unknown/invalid names; invalid numbers; mismatched containers; second call внутри envelope; garbage перед end; ambiguous unclosed strings; truncated canonical envelope на LENGTH. Registry и newline guard bare recovery не разрешают исполнять произвольные примеры в prose — сохранить negative test `Documentation example: ` + следующий chunk `call:question{...}`.

## 9. TOOL NAME VALIDATION

Рекомендуемый Gemmamonster native subset: **ASCII `[A-Za-z0-9_.-]+`**. Это совместимый с существующим output parser policy subset, **не утверждение**, что Google специфицирует именно этот regex или что dot входит в контракт всех других OpenAI servers. `std::isalnum` заменить для contract check на явные ASCII ranges, чтобы locale не определяла wire alphabet.

| Adversarial name | HTTP сейчас | Требуемое поведение |
|---|---|---|
| `foo bar` | accepted | InvalidArgument до изменения tools array / grammar build |
| `foo:bar` | accepted | то же |
| `foo{bar` | accepted | то же |
| `foo<bar` / `foo>bar` | accepted | то же |
| `foo\nbar` — настоящий newline | accepted | то же; literal backslash+n тоже invalid |
| `<|tool_call>` | accepted | то же |
| `call:foo` | accepted | то же; нельзя нормализовать request name в другое имя |

Проверять обе формы tools — nested `function.name` и flat Responses `name` — и обе формы named choice **до filtering**. Использовать length-aware strings: `GetStringLength()`; embedded NUL нельзя усечь до разрешённого prefix. Empty, non-ASCII и duplicate names — явная ошибка. Positive matrix: `foo`, `a.b`, `a-b`, `_x`, `f1`.

Если generic API compatibility не позволяет сразу ужесточить все parser families, применять Gemma name contract в раннем Gemma-aware request validation seam с тем же InvalidArgument; не расширять scope на чужие protocol names без их matrix. Output validation остаётся defence in depth, builder повторно проверяет internal request paths. Ни malformed name, ни impossible body shape не должны превращаться в optional guided-generation fallback.

## 10. GENERIC REGRESSION MATRIX

Whitespace-insensitive diff показывает: большая часть generic OutputParser rewrite — formatting; substantive changes — registry-aware Gemma construction, persistent line-boundary flag, lookupPreambleTags и новый порядок decode reconciliation. Existing remainder extraction/finish limitations не нужно неверно приписывать refit. Но они участвуют в изменяемом пути и должны быть regression gates.

Shared invariants: bytes потребляются один раз; suffix остаётся у одного владельца; partial tags удерживаются без потери при финализации; logical line boundary не возникает от cache.clear(); flush может поменять phase; текущий token проверяется уже для новой phase; special token visibility не зависит от client preference там, где он нужен parser; завершение не дублирует/не теряет deltas.

| PARSER | RISK | MINIMAL TEST |
|---|---|---|
| Qwen3 reasoning + фактический tool parser `hermes3` | mode change после `</think>` и следующий `<tool_call>`; не путать builder alias qwen3 с supported OutputParser tool name | tokenized `</think><tool_call>` без whitespace, false decode; reasoning/text/call exact; split close и coalesced suffix |
| Qwen3Coder | XML parameter delimiters, trailing argument finalization, available-tool types | два native XML functions; split name/parameter end/outer close; all splits vs normal stream; quoted `<tool_call>` в string не новый call |
| GPT-OSS | baseline special decode=true; commentary recipient vs final channel, `<|call|>` remainder | commentary tool → `<|call|>` → final channel в одном и двух chunks; final content один раз, markers не leak |
| Onyx | content parser удерживает prefix; WAITING_FOR_TOOL переключается по `to=user<|message|>` | tool → split `to=user<|message|>` → final; complete+partial marker в одном cache; ни удержанный prefix, ни final не пропадают |
| LFM2 | token-ID entry, special close, pending parse on STOP | `<|tool_call_start|>` call `<|tool_call_end|>` + trailing text; end token delayed; STOP и LENGTH сохраняют прежнюю явную recovery policy |
| Devstral | default special=true, `[TOOL_CALLS]`, `</s>`; формат IDs должен сохраниться | valid call с native ID, close+suffix coalesced; false/true preference дают одинаковые tool semantics |
| MiniCPM5 | default special=true, `<s>`/`<|im_end|>`, XML nested parameters и existing partial recovery | два native calls; stop mid-parameter case из существующей suite; typed args, no duplicate index; не переносить Gemma strict EOF policy на него |

Для всех: response split в каждой byte position на text-parser уровне; tokenized default-decode test отдельно. Не требовать одинаковые **границы** content/reasoning deltas, требовать одинаковые concatenated values, committed calls/order и finish status. Для numeric-lossless fixture сравнивать bytes. Callback returning STOP/CANCEL на phase flush не должен повторно доставлять текущий token.

Дополнительный inherited generic риск: `parseContentChunk()` всегда передаёт NONE, а `DefaultContentParser` может удержать trailing partial erased tag навсегда. Minimal test — plain text, заканчивающийся `<`, перед STOP. Решение о literal flush vs discard должно быть model-specific/contractual; не объявлять такой suffix успешным tool.

## 11. ДОПОЛНИТЕЛЬНАЯ ADVERSARIAL ПРОГРАММА

### 11.1 Parser inputs — сверх обязательных

| Input | Нарушаемая гипотеза / expected observation |
|---|---|
| `<|tool_call>call:question{x:1}` + LENGTH | нет completed envelope → zero public ToolCallDelta; текущий object-close path недостаточен |
| `<|tool_call>call:question{x:1,x:2}<tool_call|>` | SOURCE-SLICE сохраняет duplicate keys; выбрать fail-closed duplicate policy до downstream first/last-key disagreement |
| `<|tool_call>call:a{x:<|"|>broken}<tool_call|><|tool_call>call:b{x:2}<tool_call|>` | unterminated string не должен приводить к unbounded resource use; recovery b не объявлять доказанной |
| `<|tool_call>call:question{x:<|"|><tool_call|><|"|>}<tool_call|>` | end marker внутри string принадлежит value; compare raw splits для router/subparser boundary disagreement |
| `<|tool_call>call:question{x:NaN}<tool_call|>` и `{x:1e99999}` | JSON lexical validity, finite-range и lexeme policy разграничить; никакой float coercion в parser |
| `<|tool_call>call:question{a b:1}<tool_call|>` | native key parser сейчас сканирует до `:` без identifier check; документировать supported keys и roundtrip либо reject |
| 10k вложенных arrays / 1 MiB незакрытого string | depth/bytes limit; error bounded, zero public call; не запускать stress без согласованного budget в shared live server |
| valid call + ` garbage ` + второй `call:` в том же envelope | оба не могут стать независимыми canonical actions; T1 reject envelope |

### 11.2 Generation/API requests — сверх обязательных

1. Required + `tools` omitted/null/[]: все три InvalidArgument, а не нормализация первых двух в none.
2. Named object с function.name=`none`, затем `auto`, `required`: selected function сохраняется как named intent или explicit early rejection; не policy reinterpretation.
3. Parameters root `string`, `array`, либо union object|string: не принимать grammar, чей output несовместим с parser object contract.
4. Duplicate tool names с разными schemas: ранняя ошибка, а не map last-write + два template declarations.
5. No-argument function без parameters: единый `{}` contract на prompt/builder/parser либо ранняя ошибка; не исчезновение из registry.
6. `parallel_tool_calls` string/null/int: reject non-bool по выбранному endpoint contract; false tested через HTTP, не assigned field.
7. Required с `max_tokens=1`, stop string внутри tool header и/или ignore_eos: grammar не даёт права заявлять tool success; truncated raw output → zero committed calls, честный length/stop status.
8. Auto + enable_tool_guided_generation=false + malformed schema/name: syntax/request errors не маскировать как optional compilation fallback. Response_format collision остаётся явной policy, не accidental overwrite.

### 11.3 Multi-turn histories

1. User → assistant reasoning+call → tool string JSON → required follow-up. Сохранить prior tool-turn reasoning; new generated thought не в content; second request starts public index 0.
2. Tool-content string содержит fake O/E/tool markers, затем новый user turn и generation prompt. Детектор смотрит на реальное continuation state, а не историческую последнюю подстроку.
3. Assistant calls a+b, два tool results с переставленным порядком и явными tool_call_id. Имена ответов разрешаются по id, не по позиции; string/content-parts остаются совместимы с Google template. Invalid/missing id требует explicit behavior test.
4. То же history с thinking=false: closed/new suffix либо завершённый tool-response suffix; не OPEN только из наличия предыдущего reasoning.
5. Partial assistant prefill O+body при add_generation_prompt=false: state OPEN, grammar residual без второго O; malformed partial channel prefix не угадывается.

### 11.4 Special-token/chunk sequences

1. `...thought-body` | `<channel|>` | `<|tool_call>` | `call:question` | `{x:1}` | `<tool_call|>`; false decode, old cache содержит unflushed body. Marker должен попасть parser ровно один раз.
2. Text chunk `"<|channel>thought\nsecret<channel|>answer"` vs каждый byte: equal reasoning/content; текущий SOURCE-SLICE FAIL.
3. Один chunk canonical a-envelope + b-envelope, затем единственный STOP: два calls, dense indexes; без дополнительных фиктивных empty chunks для «раскачки» FSM.
4. Native string с emoji/многобайтным символом прямо перед delimiter/phase close; incomplete UTF-8 delay не должен перепутать token slice или потерять current opener.
5. `"Docs: "` | `"call:question{x:1}"` → только content; `"Docs:\n"` | тот же known bare call + close → выбранная bounded recovery. Дополнить chunk перед каждым символом preamble.

## 12. OBSERVABLE DISCRIMINATORS

| Гипотеза | Наблюдение, которое отличает её от остальных |
|---|---|
| Parser bug | Raw decode содержит полный корректный envelope; tool deltas потеряны/duplicated или malformed input даёт публичный header. Воспроизведение text-level без модели. |
| Generator bug | Render state верен; compiled grammar/matcher принимает forbidden prefix либо model output не соответствует установленному grammar. Сохранить actual config + accepted token trace. |
| Template-state bug | История одинакова, rendered suffix OPEN, parser/grammar state A; либо runtime-Jinja и Minja расходятся по suffix. |
| Streamer/special-token bug | Token IDs/full decode содержат opener, но последовательность chunk, переданная parser, его не содержит или содержит дважды. |
| API policy bug | HTTP explicit required/false/name меняется в OpenAIRequest до builder. F3 воспроизводится без generation. |
| Test-helper bug | Raw deltas/production aggregation показывают call, но helper output его удаляет; либо arguments lexeme меняется только после helper DOM roundtrip. |

Обязательные observation points в штатном RED: HTTP raw request → normalized request policy/registry → rendered prompt exact suffix → final grammar → raw token IDs/full decode → parser chunks → raw deltas → unary/SSE response. Не смешивать emitter finish reason с наличием calls.

## 13. FIX PROGRAM

### P0 — Закрыть нарушенные внешние контракты

- [ ] **Transactional commit + честный oracle.** Files: `src/llm/io_processing/gemma4/gemma4_tool_parser.{hpp,cpp}`, `src/test/llm/output_parsers/gemma4_upstream_refit_contract_test.cpp`, raw helper рядом с `output_parser_test_utils.hpp`. Input: recognized candidate. Output: один complete committed ToolCallDelta либо ничего. RED F1/F11 → T1; old helper не должен превращать FAIL в PASS.
- [ ] **HTTP hard-intent preservation.** Files: `src/llm/apis/openai_api_handler.cpp`, `src/test/llm/gemma4_generation/gemma4_generation_policy_test.cpp`. Input: explicit HTTP hard choice. Output: preserved hard policy или InvalidArgument. RED omitted/null/[] и named. Не ослаблять уже исправленный cf6fc0412 validation catch.
- [ ] **Prompt-state agreement.** Files: `src/llm/io_processing/input_processors/chat_template_processor.{hpp,cpp}`, `src/llm/io_processing/output_parser.{hpp,cpp}`, при необходимости bounded shared detector; tests в existing input_processing fixture. Input: final rendered prompt + native policy. Output: согласованные residual grammar/parser state, revalidated config. До GREEN экспериментально опровергнуть/подтвердить старый TriggeredTags workaround.
- [ ] **Chunk invariance/final drain.** Files: Gemma tool/reasoning parsers; generic `output_parser`/`ovms_text_streamer` только по separate RED. Input: произвольная допустимая partition одного output. Output: одинаковый набор committed semantic events и одна финализация. Одного progress step на parseChunk недостаточно; state machine должна продвигаться до NeedMore либо ready event. Если ready events несколько, нужна drainable queue и явный drain перед terminal callback. Не вызывать бесконечные empty-chunk loops по nullopt: nullopt не сообщает progress.

Каждый пункт — самостоятельная reviewable пара RED/GREEN. После изменения queue/remainder protocol запустить generic matrix до дальнейшего рефакторинга. Точный internal API для multi-event drain выбирать по tests: лучше небольшой explicit `hasPending/nextEvent` или result с consumed-count/need-more, чем неявный повторный прогон одного buffer. Сначала проверить возможность узкого Gemma loop; не менять весь parser framework без необходимости.

### P1 — Policy/recovery и regression closure

- [ ] Подхватить готовый parallel GREEN другого агента, проверить actual HTTP/Responses echo + required/named/auto bounds на новом HEAD.
- [ ] Общий Gemma tool-name contract, duplicate/non-object schema/no-parameters policy; сохранить различие named и policy keyword.
- [ ] Отвергать one-envelope garbage/multi-call; registry-independent canonical envelope recognition, registry-dependent commit.
- [ ] Bounded candidate bytes/depth; stable behavior при malformed strings, STOP/LENGTH и resetState reuse.
- [ ] Решить raw suffix ownership с minimal failing case; не исправлять guessed duplication вслепую.
- [ ] Actual runtime-Jinja и Minja object-arguments replay, string/content-part tool results, thought preservation.
- [ ] Generic default-decode/token-boundary matrix; finish/cancellation evidence.

### P2 — Подготовка upstream contribution

- [ ] Уточнить «native envelope / hybrid JSONSchema body» в docs, unsupported cases и точные accepted schemas.
- [ ] Native body converter только отдельным bounded follow-up с сохранением schema semantics.
- [ ] Уменьшить unrelated formatting churn shared parser; не менять public behavior при hygiene.
- [ ] Обновить dossier там, где experiment опровергает old TriggeredTags assumption; сохранить provenance и exact dependency identity.
- [ ] Полная metadata-driven response_template интеграция, session store, MTP, performance и deployment остаются вне scope.

## 14. PROPOSED RED COMMITS

Это предлагаемые commits, **не созданные в review**. Названия tests ниже — спецификация будущих assertions, не утверждение об уже существующих/запущенных тестах.

1. `test(gemma4): expose malformed calls through raw deltas and unary aggregation` — required three malformed inputs, unknown, bad+valid; no header, next index 0; raw default decode and true variant.
2. `test(gemma4): require closed envelopes and chunk-invariant final drain` — valid complete/truncated, canonical two calls одним chunk, repeated STOP, reasoning coalesced suffix; expected events из §2/11.
3. `test(openai): preserve explicit hard tool choice without tool definitions` — Chat/Responses omitted/null/[]; named keywords и missing selected tool.
4. `test(gemma4): pin rendered thought state and residual hard grammar` — Runtime Jinja/Minja таблица §6.5; matcher принимает continuation перед E, запрещает EOS до required call; detector false-positive history cases.
5. `test(gemma4): reject unsafe names and incompatible argument schema roots` — все восемь names, NUL, duplicate, non-object root; InvalidArgument до generation.
6. `test(gemma4): reject garbage multicall recovery and bound malformed candidates` — one-envelope variants zero commits; отдельные envelopes valid; unclosed-string resource bound.
7. `test(llm): preserve phase handoffs remainders and terminal events` — targeted seven-family regression matrix с false decode. Не объединять все implementation changes в один GREEN.

Parallel RED уже присутствует на REVIEW_HEAD (`18de2c26c`): не создавать дубликат. Numeric lossless helper RED имеет отдельное происхождение: production lexeme верен, helper его портит.

## 15. PROPOSED GREEN COMMITS

1. `fix(gemma4): commit validated tool envelopes atomically` — T1, dense indexes, no phantom. Не «чинить» только aggregate filter.
2. `fix(gemma4): drain parser progress and preserve coalesced reasoning text` — по отдельным RED; если затронут generic transport, отдельный commit после matrix.
3. `fix(openai): reject missing tools without erasing hard choice` — ранний explicit intent guard; typed named resolution при необходимости отдельно.
4. `fix(gemma4): reconcile rendered thought state before generation` — actual post-#4103 seam, corrected detector, residual grammar, revalidation, idempotence.
5. `fix(gemma4): validate tool identifiers and argument schema contracts` — HTTP earliest seam + builder/internal parity + output defence.
6. `fix(gemma4): bound recovery to unambiguous native envelopes` — no garbage promotion, resource bounds.
7. `test(llm): align raw parser helpers with production aggregation` — honest helper semantics; не удалять evidence tests.

В каждом behavioral commit сохранить `Provenance / Driven by / Fixes / Decision`; указывать actual RED command/output и выбранную альтернативу. RED/GREEN history не squash до финального review.

## 16. WHAT MUSE CAN FIX / WHAT REQUIRES CODEX

Это распределение по необходимым observations и границам изменений, а не предположение о недокументированных возможностях моделей.

**WHAT MUSE CAN FIX:** bounded plumbing по уже утверждённому контракту; parallel request/Responses echo; таблица invalid name requests; raw-capture assertions; removal of false-green filtering из специально выделенного helper; BUILD wiring, formatting, doc links/checkpoints. Все changes проверять на current remote и не дублировать local-agent работу.

**WHAT REQUIRES CODEX:** transaction commit boundary; parser progress/drain и shared remainder ownership; discrimination grammar-vs-template-vs-streamer; rendered state detector; actual GenAI matcher language tests и live multi-turn evidence; решение native-body/schema scope. Эти задачи требуют сопоставлять несколько слоёв и re-review после каждого GREEN. Если любой агент может воспроизвести эти observations и выполнить gates, роль можно передать ему; label не заменяет evidence.

## 17. WHAT SHOULD REMAIN UNCHANGED

- Post-#4103 Runtime Jinja preparation/loader архитектура и общий render convergence.
- Request capability adaptation `requiresObjectArguments`; no unconditional role:tool JSON-string→object conversion. TEMPLATE experiment дал `'str object' has no attribute 'get'` при такой подмене object в content-part ветке.
- Lossless parser numeric lexemes; не подстраивать production под lossy helper.
- Dynamic tokenizer-resolved start IDs. В Gemma reasoning header есть legacy числовые constants 100/101, но рассматриваемый parseChunk их не использует; не объявлять их активным hard-coded transport defect без call path.
- Explicit rejection response_format + active tool guidance; hard validation failure → InvalidArgument; разрешённый optional auto schema-compilation fallback.
- Existing parser-specific incomplete recovery других семейств, пока отдельный test не обосновал изменение.
- Другие runtime/model settings, 2026.4 release ветки, session store, packaging, MTP, GPU процессы/порты и staging другого агента.

## 18. FINAL MERGE GATE

**На рассмотренном SHA — NOT MERGEABLE.** Для финального кандидата выполнить заново, с literal candidate SHA и immutable evidence; не использовать source-slice как замену integration.

1. **Freeze:** clean disposable checkout exact remote SHA; commit ancestry/diff; actual OpenVINO/GenAI/XGrammar/tokenizer/template identity и hashes. WORKSPACE local_repository делает dependency provenance обязательной.
2. **Штатные tests:** существующий runnable target `//src/test/llm/gemma4_generation:gemma4_generation_policy_test`; parser/input-processing suites входят в `//src:ovms_test`, а `//src:test_llm_output_parser_tests`, `//src:test_llm_input_processing_tests`, `//src:test_llm_input_processing_integration_tests` — **cc_library**, не runnable tests. Не выдавать `bazel test` библиотеки за выполненные tests. Использовать штатный test runner/bootstrap и filters либо отдельный согласованный narrow cc_test. Query целевых cc_test перед запуском.
3. **RED execution:** все перечисленные failure cases должны реально упасть на baseline по semantic assertion, не compilation/bootstrap. После GREEN raw header count=0 для malformed; valid recovery dense index=0; canonical full text partition invariant; no reasoning→content leakage.
4. **Matcher:** final post-render grammar accepted/rejected language из §6.5 на actual dependency. Проверить EOS before call, selected tool restriction, root object, false max-one, auto free text, OPEN continuation. Проверка наличия AST поля не считается PASS.
5. **Transport/API:** default `skip_special_tokens=true`; raw IDs/full decode/chunks/deltas сохранены. Unary использует production aggregation; SSE inspected byte-for-byte для id/name, arguments, call count, finish_reason. LENGTH/cancellation не становятся tool success; compiled hard grammar не гарантирует успешный call при исчерпанном budget.
6. **Replay:** обоими реальными OVMS render paths: first call → tool result → second call → final response; prior thought сохранён внутри tool turn; string/content-parts корректны; canonical current Google template hash recorded. Минимум required/named/auto × unary/streaming, parallel false/true, repeated calls и one forced truncation.
7. **Generic regression:** семь parser families из §10; реальные tokenizers; phase boundary, partial tags, suffix exactly once, finish behavior. Unrelated startup error, пустой test discovery или filtered helper — не PASS.
8. **Live model:** сохранить requests/responses/raw logs и actual model/binary/settings tuple. Hybrid JSONSchema body отдельно проверить strings/native equivalent/replay. NovaClaw/OpenCode style loop — финальный consumer gate после API checks, не вместо них.
9. **Review/status:** clean source diff, actual tests counts и no unexpected skips; source-style/buildifier; docs whitespace policy решена явно. Обновить authority dossier, особенно ошибочную гарантию старой open-thought adaptation.

Все P0 закрыты реальными RED→GREEN; P1 с внешним semantic impact либо закрыт, либо явно выделен из заявляемого supported scope с тестируемым отказом. Только после этого рассматривать promotion/merge отдельным действием. Этот review ничего не публиковал и не продвигал.

## Appendix: reference provenance

External sources скачаны с immutable SHAs из dossier, кроме Google template main, чей resolved revision зафиксирован: `842da3794eaa0b77d5f08bae87a17459d91ff475`, SHA256 `ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4`. [Reference manifest](references/manifest.json) содержит URL, bytes и hash каждого файла.

- [Google template pinned](https://huggingface.co/google/gemma-4-31B-it/blob/842da3794eaa0b77d5f08bae87a17459d91ff475/chat_template.jinja): actual render/replay authority; parts/mapping trap воспроизведён отдельно.
- [vLLM state detector](https://github.com/vllm-project/vllm/blob/e6960af33b379d502f409e3e2241bbf2b2c2f68d/vllm/parser/gemma4.py#L479): token-boundary scan и prompt-seeded reasoning. State semantics полезны, foreign engine transplant не требуется.
- [llama.cpp native policy](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/common/parsers/gemma4.cpp#L269): canonical repeated envelopes, required min и parallel max.
- [SGLang detector](https://github.com/sgl-project/sglang/blob/832ec39cc0324cb0e7823dc8385e27a30c356bdd/python/sglang/srt/function_call/gemma4_detector.py#L441): no native structural-tag capability; recursive parser полезен как сравнение, permissive cast — negative example.

Source-slice / Jinja probes — review artifacts, production files не изменены. Формулировки PASS/FAIL выше относятся к явно названным уровням доказательств.
