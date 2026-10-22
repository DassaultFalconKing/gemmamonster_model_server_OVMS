# QWENMONSTER — генеральная рабочая программа R0–R6

**ACTIVE · ACCEPTED: NO · 2026-10-22**

Первоисточник: пользовательская программа «QWENMONSTER — C6 Protocol & Agentic Reliability Program» от 2026-10-21. Эта редакция сохраняет её нормативные R0–R6, первоначальные требования и gates, объединяет измеренные QWM-01/Ornith/Gemma/XGrammar результаты и даёт единую очередь W1–W7. Навигация: [PLAN-MAP.md](PLAN-MAP.md).

**Неприкосновенные границы:** исходный C6 c6-head-mainline-20261020@ba6ec792c3121850fea167fa7d7e190b25fcdc76 и принятый public-source-lock.json не изменять. XGrammar #802@b288dca18ee25d2f35197fb3971334ca049c8554 — отдельный кандидат, НЕ часть lock. Публичные документы не должны содержать локальную карту компьютера, пути, токены и raw логи: только placeholders <WORKTREE>, <MODEL_DIR>, <CANDIDATE_RUNTIME>, <PRIVATE_EVIDENCE>.

**Зафиксированное исключение 2026-10-22:** по явному решению оператора кандидатная GenAI DLL заменила staged runtime и копию рядом с серверным исполняемым файлом. Установленный SHA-256 `442452056e06c3a7e05d71ca082e9f30fd0034c8f6dcf5b2e56f04f140599e4d`. Предыдущий SHA-256 `7892465a3bca67e103e26b198f47fb1d5c0a98fc2cc7cb4616ba0e8d5ad054da` сохранён в частном hub. Tokenizers не заменялись. `public-source-lock.json` не менялся. Агентам нельзя откатывать или подменять эти DLL без нового явного решения.

## 0. Цели, scope и правила

**Цели:** правильный native tool calling Qwen3.6 и Ornith; надёжная цепочка reasoning → tool → tool result → continuation; tool_choice none/auto/required/named; SSE, multi-call, malformed XML и bounded recovery; история рассуждений; OpenCode/совместимые harnesses; параллельные сессии; ноль регрессий Gemma4/C6. Измерять автономное делегирование, а не искусственно вынуждать модель создавать агентов.

**Вне исходного scope:** оптимизация весов, KV-cache, MTP, speculative decoding, изменения архитектуры GenAI и fine-tuning. MoE/OTD/expert-cache — отдельный performance-трек, не блокер протокольного acceptance.

Правила: исходный C6 read-only; branch/worktree isolated; RED → root cause → минимальный фикс → GREEN и Gemma controls; один механизм на коммит; fail-closed режим явно сообщает ошибку, не падает в auto; SOURCE/BUILD/UNIT/MATCHER/HTTP/LIVE/AGENTIC/ACCEPTED различать; каждая правка описывается шестью полями из AGENTS.md.

## 1. Фактический срез

Последний checkpoint **всегда** верх STATE.md и проверенные evidence. Следующая таблица не является новым прогоном.

| Gate | Подтверждено отчетами | Осталось |
|---|---|---|
| C6 и исходники | source cohort locked, C6 frozen | самостоятельный live C6 comparison |
| Qwen parser | 69/69 Qwen, 9/9 generation-policy, 29/29 generic; 14 случаев / 2340 chunk partitions; live LENGTH измерен | cancel и handoff |
| HTTP intake | 2/2 unit (12 внутренних случаев); 11/11 related tools; 17/17 реальных HTTP400 | Hermes контроль, полная policy matrix |
| Gemma | 79/79 Gemma после bounded repairs; combined 148/148 parser controls | live negative control; escaped-quote fixture corrected, это НЕ третий production fix |
| OVMS | полные цели ovms_test и ovms построены; кандидатная GenAI DLL собрана и установлена, SHA-256 выше | public lock не менялся; ACCEPTED нет |
| Ornith live | установленная кандидатная DLL: unary и SSE `max_tokens=16` → `length`, следующий запрос `OK`, один required `city=Paris` | это не проба маски `</parameter1>`; cancel NOT_PROVEN |
| Continuation | 20/20 controlled two-turn (10 unary + 10 SSE); отдельный error → valid named → receipt → continuation с shell exit0 | НЕ 20 длинных автономных loops; первый wrapper у 20/20 завершился exit1 после сохранения semantic traces |
| XGrammar #802 | isolated native29/29, GenAI31/31, Qwen3-8B whitespace baseline 422/425 → candidate 0/425 | undeclared-required пустой XML всё ещё принимается; грамматику без отдельного контракта не менять |
| R1 schema-matrix runner | native matrix 24 PASS, 4 known OPEN, 0 unexpected; 18/18 offline runner tests | это НЕ R1 Jinja/history; 50/100 ходов OPEN |
| XGrammar #650 / required-key | порт `5b0b708`, native matcher 71/71 на Qwen3-8B tokenizer; `lock_excluded_prefixes` есть в установленной DLL | живая маска `</parameter1>` на Ornith не измерялась; undeclared-required OPEN |
| Stability | после live доступная RAM падала до 514 MiB и частично восстанавливалась | не доказана утечка; stress/concurrency unsafe до измерений |
| Promotion | **ACCEPTED NO** | end-to-end gates не закрыты |

Точные источники: верх [STATE.md](STATE.md), [XGRAMMAR-650-NOTE.md](XGRAMMAR-650-NOTE.md), [W3-LENGTH-CANCEL.md](W3-LENGTH-CANCEL.md), [R1-RUNNER-HARDENING.md](R1-RUNNER-HARDENING.md), [EXTERNAL-GATES-20261021.md](EXTERNAL-GATES-20261021.md), [FOLLOWUP-20261021.md](FOLLOWUP-20261021.md), [OVMS-TEST-HTTP-RESULTS.md](OVMS-TEST-HTTP-RESULTS.md), [XGRAMMAR-802-COHORT-PROPOSAL.md](XGRAMMAR-802-COHORT-PROPOSAL.md), [BOUNDED-REPAIRS.md](../gemma4-repairs/BOUNDED-REPAIRS.md).

### Где стоит очередь

Читать вместе с самым верхним checkpoint STATE.md. Нижние исторические абзацы этого файла не отменяют срез.

1. Маска Qwen3-8B tokenizer на расхождении `</parameter` — сделано, 71/71.
2. Живой прогон установленной кандидатной DLL — сделано: hash совпал, unary/SSE `length`, follow-up `OK`, один required city. Сервер остановлен. Это не acceptance и не проба `</parameter1>`.
3. **Текущий пункт:** cancel и возврат ресурсов на этой же DLL. Обрыв после первого SSE-chunk и рабочий набор примерно на 1.5 МиБ выше базового замера — NOT_PROVEN. Повтор такого раннего обрыва не засчитывается. `stop()` в disconnect callback уже есть; правку продукта из отсутствия строки лога не выдумывать.
4. Undeclared-required пустой XML — зафиксированный остаток. Без отдельного контракта грамматику не менять.
5. Public lock и ACCEPTED не двигать. Нужно отдельное решение после разобранных измерений.

## R0 — Frozen baseline и upstream archaeology (P0)

**Исходная программа:** C6 SHA/tree; GenAI/OpenVINO/XGrammar/Tokenizers/Minja/Bazel/MSVC/DLL; Gemma и Qwen VLM_CB/LM_CB profiles; unary/SSE и agentic traces. Исследования official Qwen, vLLM, llama.cpp, SGLang, XGrammar, Gemmamonster G0–G8/C5/C5fixed/C6 по схеме source → implementation → semantic contract → issue → C6 behavior → proposed change. Темы: lazy vs hard grammar, triggered XML, multi-call, schema, bounded recovery, streamer ownership.

**Сейчас:** source/protocol baseline и dossier существуют; независимый исходный C6 live binary comparison ещё не измерен. **Gate R0:** reproducible source/runtime tuple и неприкосновенность accepted C6.

## R1 — Канонический Jinja, reasoning и длинная история (P0)

Профили: Qwen3.6 official Jinja, Ornith separately исправленный unconditional think, Qwen3.8 / Flash/Next later independent official templates. Проверки: last_query_index, preserve_thinking true/false, enable_thinking true/false, reasoning_effort если поддерживается, empty reasoning_content, assistant.tool_calls JSON arguments string, tool result replay, system/developer roles, open generation suffix; 50–100 ходов serialized history. Сверять и видимый текст, и **token IDs** на одинаковом контексте Qwen3.6 vs Ornith. Deliverables: template contract tests, prompt fixtures, equivalence report и список kwargs.

**Важная омонимия:** свежий 28-row R1 *native runner* проверяет XGrammar schema-boundary; его 18/18 offline unit — это НЕ R1 template gate. **Gate R1:** reference Jinja/token IDs подтверждены, искусственный reasoning не внедряется в длинную историю.

## R2 — XML parser, SSE lifecycle, bounded recovery (P0)

Native Qwen3-Coder FSM: queue validated name/id then arguments, stable per-request indexes; single/N calls per chunk, arbitrarily split markers, typed/nested args, duplicate/malformed tags, unknown names, zero-args; restore only completed call at STOP, never fabricate open args for LENGTH/CANCEL/ERROR. Maintain 2340+ partition and reset invariants.

**Сейчас:** parser and policy units pass; output publication hardened, schema fail-closed; real HTTP rejects and controlled continuation pass. Live backend LENGTH и следующий здоровый запрос измерены на установленной кандидатной DLL. **Открыто:** cancel и возврат ресурсов, phase boundaries. Static review установил, что внешняя API сериализация использует фактический GenerationOutput.finish_reason, а STOP в streamer.end() может быть только parser cleanup. Не переписывать API finish mapping без RED. **Gate R2:** детерминированный stream со всеми finish modes и без потерь/ложных executable calls.

## R3 — GenerationConfigBuilder / tool policy / XML grammar (P0)

| mode | Контракт | Live status |
|---|---|---|
| none | запрет публикации executable tools | smoke PASS |
| auto | сначала unconstrained reference; lazy TriggeredTags experimental, без принуждения модели | guided auto default OFF, A/B OPEN |
| required | ≥1 валидный вызов из registry и schema; невозможность = ошибка | один city smoke; 100/100 OPEN |
| named | только выбранный зарегистрированный инструмент | named after-error positive; 100/100 OPEN |
| parallel=false | не больше одного вызова, включая unguided post-parser policy | OPEN вне guided ограничений |
| parallel=true | несколько корректно индексированных вызовов | parser unit есть, real model matrix OPEN |

R3 Native generator в qwen3coder/generation_config_builder.hpp использует qwen_xml_parameter / structural tags. Проверить hard и lazy grammar против реальных token masks, top-level zero-args и typed/nested args, stop_after_first, trigger prefixes, открытый think. #802: candidate only. #650: end marker drift, отдельный mask fix. Undeclared required property gap: отдельный fail-closed profile/grammar contract, без blanket reject допустимых JSON Schemas.

**Gate R3:** фактический loaded DLL+Qwen3.6 tokenizer, 100/100 required и named, подтверждённый non-forcing auto, отсутствие неверного fallback, Gemma/Hermes controls.

## R4 — Reasoning → content/tool phase ownership (P1, R5 blocker)

Требуются переходы UNKNOWN→REASONING→CONTENT, UNKNOWN→REASONING→TOOL, UNKNOWN→TOOL, CONTENT→TOOL, TOOL→TOOL, TOOL→CONTENT. Для каждого: full, 1-character, random chunks, split tokens, combined closer/opener, open think, thinking disabled, early finish. Rendered prompt state выводить **из текущего suffix**, не из старых think markers истории. Сначала использовать существующий generic OutputParser owner, не вводить независимый параллельный parser pipeline.

**Gate R4:** фазы не теряются и не меняются местами, reasoning не протекает в content/tool.

## R5 — Multi-turn / autonomous subagents / concurrency (P1)

Сопоставимый harness Gemma4 ↔ Qwen3.6 ↔ Ornith, одинаковые schemas/sampling. Задания: несколько файлов, три модуля, 2 исследовательских субагента, 4 независимых субагента, aggregation, retry после tool error, длинная tool history. Разделять tool available → model decided → emitted native → parsed → API delivered → harness executed → subagent completed → model continued. Thinking ON/OFF, preserve ON/OFF; native auto vs lazy auto A/B.

Гейт **из исходной программы без снижения**: 100% deterministic protocol, 100/100 required, 100/100 named, ноль malformed executable args/lost calls/cross-request contamination, ≥20 **полных** самостоятельных tool-result loops, отдельно измеренные autonomous delegation/multi-agent rates, Gemma regressions=0, GPU fatal/quarantine=0. Context 8K/32K/64K/128K (262K только если память позволяет); 1/2/4 параллельных requests с реальными occupied contexts, KV/TTFT/TG/latency и executor health. Наличие 4 сессий не равно 4 одновременно исполняемым KV-нагрузкам.

**Текущее:** 20/20 controlled **двухходовых**, не автономных длинных loops. RAM pressure пока не классифицировано как leak. Gate R5 остаётся OPEN.

## R6 — Post-3.6 family profiles и upstream (P2)

Qwen3.8, Flash/Next и Ornith регистрировать по capability profile и отдельному official template; не считать все Qwen одинаковой XML/reasoning моделью. Отдельные upstream PR по parser streaming, recovery, generation policy, reasoning handoff, template/history. Формат Problem → Reproducer → Root cause → Fix → Negative control → Live evidence. Без raw user paths/weights.

**Gate R6:** самостоятельная protocol/runtime acceptance для каждой модели после Qwen3.6.

## Текущая реализация: W1–W7

**Порядок:** W1 + W2, затем W3/W4 независимо, W5 isolated candidate, после ресурсо-безопасного baseline W6, W7 только по измерениям. Каждая карточка содержит требуемые **причина; файлы; алгоритм; эффект; тест; источник**.

### W1 · Harness/resource accounting и корректный exit (P0, R0/R5)
1. Причина: прошлый wrapper exit1 при семантических 20/20; RAM headroom проседал.
2. Файлы: scripts/qwenmonster/acceptance/ (новый runner), docs/qwenmonster/evidence/ (только sanitized), STATE.md.
3. Алгоритм: exact subprocess exit+run ID, timeout/cleanup only owned process, hashes loaded DLL/model, before/after/idle RSS/private bytes и snapshot resource.
4. Эффект: доверенные execution receipts и оценка RAM без фиктивного диагноза leak.
5. Тест: deliberate exit1/timeout/missing receipt, positive after-error, memory trace.
6. Источник: FOLLOWUP-20261021.md и EXTERNAL-GATES-20261021.md; independent tooling.

### W2 · R1 canonical templates и 28-row native XGrammar matrix (P0)
1. Причина: template/history ещё OPEN; native R1 schema rows не выполнены.
2. Файлы: scripts/qwenmonster/r1_gate.py, r1_runner.py, tests, fixtures/, Jinja template tests.
3. Алгоритм: сохранить exact row set/timeout/sealed source из текущего hardening, выполнить baseline-vs-candidate native; **отдельно** Jinja rendered suffix/token IDs, last_query_index и 50/100-turn history.
4. Эффект: различать grammar-converter defect и template/history defect.
5. Тест: 28 native schema rows real build/run + Qwen3.6/Ornith 50/100 turn token-level A/B.
6. Источник: R1 original program и R1-RUNNER-HARDENING.md.

**Статус 2026-10-22:** native matrix 24 PASS, 4 known OPEN, 0 unexpected. Jinja/history 50/100 ходов по-прежнему OPEN. Эта карточка не текущий пункт.

### W3 · Real LENGTH/CANCEL/disconnect semantics (P0, R2/R4)
1. Причина: старые direct parser тесты не равны backend cancellation.
2. Файлы: streamer/API owning C++ только при конкретном RED; focused tests и evidence.
3. Алгоритм: record backend→parser cleanup→API finish, mid-parameter max_tokens, disconnect, after-cancel healthy request; никаких догадок о finish reason.
4. Эффект: завершение без malformed executable call и без незавершённых SSE.
5. Тест: real LENGTH, STOP, CANCEL, retry, Qwen/Gemma/generic.
6. Источник: STREAMING-LIFECYCLE-DECISION.md и EXTERNAL-GATES-20261021.md.

**Статус 2026-10-22:** unit `CbChatStreamingPreservesBackendLengthFinishReason` PASS. Live unary/SSE `length` и follow-up `OK` PASS на установленной кандидатной DLL. Generation-handle cancel и возврат памяти NOT_PROVEN. Новую правку продукта не начинать, пока измерение не даст конкретный RED.

### W4 · XGrammar #650 + required-key gap (P0, R3)
1. Причина: #802 не исправляет </parameter1> и required вне declared properties.
2. Файлы: separate XGrammar fork TagDispatch/FSM/converter tests, Qwen shared schema profile при необходимости.
3. Алгоритм: opt-in longest-excluded-prefix из upstream #651, standalone RED/GREEN; отдельно schema required/additionalProperties matrix.
4. Эффект: matcher исключает ошибочное XML закрытие до генерации.
5. Тест: actual token mask at every delimiter prefix, hard/lazy, #802 regression, Gemma JSON controls.
6. Источник: XGrammar #650/#651, XGRAMMAR-650-NOTE.md и XGRAMMAR-802-COHORT-PROPOSAL.md.

**Статус 2026-10-22:** эквивалент #651 на `5b0b708`; upstream #837 не мержить. Маска Qwen3-8B unit tokenizer PASS. Undeclared-required пустой XML остаётся. Живой Ornith этот пункт не закрывает: он не проверял `</parameter1>`.

### W5 · GenAI/XGrammar installed candidate cohort (P0, R3)
1. Причина: native #802 PASS не входит в активный GenAI DLL.
2. Файлы: отдельные кандидатные build configs, runtime manifest и sanitized evidence; не public lock.
3. Алгоритм: pinned b288dca18 candidate → isolated GenAI build → loaded DLL/hash proof → real tokenizer masks, затем отдельный #650-combo A/B.
4. Эффект: настоящая constrained generation на протестированном matcher, не подмена installed C6.
5. Тест: exact build/link/DLL receipts, Q-ZERO/Q-END, GenAI31/31, Gemma and Ornith live A/B.
6. Источник: XGRAMMAR-802-COHORT-PROPOSAL.md; independent isolated packaging.

**Статус 2026-10-22:** изолированная сборка есть и по явному решению оператора установлена (hash в исключении выше). Public lock не обновлялся. Unary/SSE/один city на установленном файле разобраны. Это не cohort acceptance.

### W6 · Agentic acceptance R3/R4/R5 (P0, после W1)
1. Причина: HTTP 17/17 и controlled two-turn20/20 не закрывают автономию.
2. Файлы: scripts/qwenmonster/acceptance/ + fixtures, ACCEPTANCE.md и STATE.md, product C++ только при RED.
3. Алгоритм: 100 required + 100 named, thinking/preserve/guided-auto matrix, 20 full autonomous loops, 2/4 subagents, 1/2/4 sessions после resource safety.
4. Эффект: отделить ошибки модели, парсера, API, harness и ресурсный fault.
5. Тест: R5 multi-agent benchmark, SSE identity, long-history, no state leakage, GPU health.
6. Источник: исходная R5 программа, ACCEPTANCE.md, measured followup.

### W7 · Performance QWM-02, XML retention, MTP (P2)
1. Причина: повторная schema compilation и растущий XML buffer замечены в исходниках, стоимость ещё не измерена.
2. Файлы: tool_schema_profile.*, qwen3coder_tool_parser.*, benchmark tests и отдельный inference track.
3. Алгоритм: before/after 1/10/100/1000 schema calls, 100/1000/10000 completed envelopes; cache per request/compaction только при измеренном эффекте. MTP/OTD отдельно.
4. Эффект: latency и RAM улучшаются, не ухудшая протокол.
5. Тест: 36 schema cases, 2340 partitions, negative Qwen/Gemma, matched A/B.
6. Источник: NEXT-STEPS-20261021.md, earlier QWM-02 research, independent benchmark hypothesis.

## Acceptance и checkpoints

После каждого meaningful gate обновить верх STATE.md с ACTIVE_STAGE/BASE_SHA/CURRENT_HEAD/LAST_GREEN_TESTS/CURRENT_FAILURE/NEXT_ACTION/REVERT_POINT/EVIDENCE_PATH/ACCEPTED, а raw evidence оставить private. **Qwenmonster принимается только после R0–R5 gates:** native/tool correctness, official Qwen3.6/Ornith templates, required/named, SSE, реальные длинные агентные циклы/субагенты, 1/2/4, Gemma regression=0 и GPU healthy. Главный принцип первоначальной программы: **protocol correctness before behavioral tuning**.

Роли документов: MASTER-PLAN.md задаёт «что и зачем»; AGENTS.md — «как писать»; ACCEPTANCE.md — «что значит PASS»; STATE.md — «что реально сделано»; PLAN-MAP.md — «где искать». PLAN-POST-SMOKE-20261021.md теперь исторический snapshot, не конкурентная программа.
