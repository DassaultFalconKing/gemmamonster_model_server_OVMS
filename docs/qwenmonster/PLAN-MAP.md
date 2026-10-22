# QWENMONSTER — карта планов

**Точка входа:** [MASTER-PLAN.md](MASTER-PLAN.md). **ACCEPTED: NO.** Версия 2026-10-22. Генеральный R0–R6 получен из пользовательской программы, а не из производных source-only отчётов. Текущий пункт очереди — раздел «Где стоит очередь» в MASTER-PLAN и верх STATE.md.

## 1. Иерархия и приоритет

| Документ | Вопрос | Статус |
|---|---|---|
| [MASTER-PLAN.md](MASTER-PLAN.md) | Какие цели R0–R6 и активные W1–W7? | Единственный актуальный рабочий план |
| [AGENTS.md](../../AGENTS.md) | Как осуществлять изменения, RED/GREEN, шесть полей и privacy? | Обязательная инженерная политика |
| [ACCEPTANCE.md](ACCEPTANCE.md) | Какой gate необходимо пройти для PASS? | Нормативные acceptance критерии |
| [STATE.md](STATE.md) | Какой фактический HEAD, результат и NEXT_ACTION? | **Читать самый верхний checkpoint** |
| [NEXT-STEPS-20261021.md](NEXT-STEPS-20261021.md) | Что прямо сейчас мерить на runtime? | Тактика и ресурсные ограничения |
| [PLAN-POST-SMOKE-20261021.md](PLAN-POST-SMOKE-20261021.md) | Что планировали до HTTP400/agentic evidence? | Архив / superseded |
| [OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md](OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md) | Как переносить подход на *любое* модельное семейство? | A0–A9 общий протокол, **не** QWM R0–R6 |

Порядок разрешения противоречий: первоначальная пользовательская цель и acceptance gates → AGENTS.md → свежие raw evidence и STATE.md → W1–W7 → старые narrative snapshots. PASS всегда привязан к конкретному binary/model/runtime tuple.

## 2. R0–R6 карта документов

| Track | Основные документы | Текущий gate |
|---|---|---|
| **R0** frozen baseline/upstream | [C6-BASELINE.md](C6-BASELINE.md), [UPSTREAM-ARCHAEOLOGY.md](UPSTREAM-ARCHAEOLOGY.md), [COMPARATIVE-QWEN-PARSER-VERDICT.md](COMPARATIVE-QWEN-PARSER-VERDICT.md), [PUBLIC-COHORT-INTEGRATION.md](PUBLIC-COHORT-INTEGRATION.md), [public-source-lock.json](public-source-lock.json) | Source freeze подтверждён, отдельный C6 live сравнить |
| **R1** templates/history | [GENERATION-POLICY-DESIGN.md](GENERATION-POLICY-DESIGN.md), [ACCEPTANCE.md](ACCEPTANCE.md), fixtures/ | Canonical Jinja + 50/100-turn tokens OPEN; 28-row R1 runner относится к XML schema, не Jinja |
| **R2** XML streaming/parser | [STREAMING-LIFECYCLE-DECISION.md](STREAMING-LIFECYCLE-DECISION.md), [W3-LENGTH-CANCEL.md](W3-LENGTH-CANCEL.md), [SCHEMA-VALIDATION-PROFILE.md](SCHEMA-VALIDATION-PROFILE.md), [PROTOCOL-MATRIX.md](PROTOCOL-MATRIX.md), [PARALLEL-INDEPENDENT-CODING.md](PARALLEL-INDEPENDENT-CODING.md) | Qwen69/69 и 2340 partitions; live LENGTH измерен; CANCEL OPEN |
| **R3** tool generation | [GENERATION-POLICY-DESIGN.md](GENERATION-POLICY-DESIGN.md), [XGRAMMAR-650-NOTE.md](XGRAMMAR-650-NOTE.md), [XGRAMMAR-802-COHORT-PROPOSAL.md](XGRAMMAR-802-COHORT-PROPOSAL.md), [WHITESPACE-DEFECT-TAXONOMY.md](WHITESPACE-DEFECT-TAXONOMY.md) | Policy9/9; #650 tokenizer mask измерен; кандидатная DLL установлена, lock не менялся; undeclared-required и 100/100 OPEN |
| **R4** reasoning/tool phase | [ACCEPTANCE.md](ACCEPTANCE.md), [OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md](OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md) | Full phase matrix OPEN |
| **R5** multi-turn/agents | [FOLLOWUP-20261021.md](FOLLOWUP-20261021.md), [EXTERNAL-GATES-20261021.md](EXTERNAL-GATES-20261021.md), [NEXT-STEPS-20261021.md](NEXT-STEPS-20261021.md) | HTTP400 17/17 + controlled two-turn20/20; autonomous20,100 calls,2/4 agents,1/2/4 requests OPEN |
| **R6** Qwen3.8/Next | [OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md](OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md) | Deferred separate model capability profiles |

## 3. Очерёдность и зависимости

R0 → R1 official template/token IDs → R4 reasoning handoff → R5 real autonomous loops. Параллельно R2 parser + R3 policy/grammar; R3 требует отдельной проверки #802 candidate installed DLL и фикса #650. Стресс R5 зависит от W1 resource accounting. R6 возможен после принятия Qwen3.6.

**Текущая очередь MASTER W1–W7:** W3 cancel/resource измерен и остаётся NOT_PROVEN: private bytes не вернулись, система получила память только после выхода процесса; disconnect падает на `generation_stream.hpp:136`. W4: исходный порт и маска tokenizer сделаны, живая проба `</parameter1>` не запускалась. W5: кандидатная DLL установлена явным решением, lock не менялся. W2 native matrix 24 PASS / 4 OPEN; Jinja history открыта. W6 и W7 позже.

## 4. Документальный timeline: почему старые NOT RUN не главные

| Evidence | Область/момент |
|---|---|
| [C6-BASELINE.md](C6-BASELINE.md) / [ISSUES-AND-RISKS.md](ISSUES-AND-RISKS.md) | Early source-only risks; не текущее build status |
| [QWM01-BUILD-REPORT.md](QWM01-BUILD-REPORT.md) | First focused build, historical HTTP blocker |
| [OVMS-TEST-HTTP-RESULTS.md](OVMS-TEST-HTTP-RESULTS.md) / [BOUNDED-REPAIRS.md](../gemma4-repairs/BOUNDED-REPAIRS.md) | Full build, Qwen/Gemma 148/148 |
| [STATUS-20261021.md](STATUS-20261021.md) | Ornith unary/SSE/single-tool smoke |
| [FOLLOWUP-20261021.md](FOLLOWUP-20261021.md) | 17 HTTP negatives, 20 controlled 2-turn semantic receipts; old shell exit1 |
| [EXTERNAL-GATES-20261021.md](EXTERNAL-GATES-20261021.md) | Actual negative→positive→receipt replay, shell exit0; low RAM headroom |
| [R1-RUNNER-HARDENING.md](R1-RUNNER-HARDENING.md) | 18/18 offline runner tests, 28-row native NOT RUN |
| [PLAN-POST-SMOKE-20261021.md](PLAN-POST-SMOKE-20261021.md) | Old proposed A–H pre-continuation, superseded by MASTER W1–W7 |

## 5. Контракт для агентов

Перед правкой читать AGENTS.md, MASTER-PLAN.md, верх STATE.md, ACCEPTANCE.md. Сверить HEAD/worktree/source-lock; выбрать W-card, R-gate и owning boundary; предоставить шесть полей, выполнить RED→GREEN и минимальный commit. Raw machine paths/credentials/logs остаются private. Новые milestones фиксировать в STATE/evidence, не плодить новый конкурирующий «генеральный» план. Никаких изменений C6, staged runtime или lock без отдельного решения.
