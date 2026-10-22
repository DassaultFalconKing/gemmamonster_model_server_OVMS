# 11 — Ledger моделей и кодерных агентов по этапам A0–A8

**Дата:** 2026-10-22 · **Статус:** операционный план / распределение работ, **не** свидетельство выполнения этапов.  
**Основа:** [архитектура v2](09-ARCHITECTURE-PLAN-V2.md), [implementation roadmap](06-IMPLEMENTATION-ROADMAP.md), [модельные baseline](07-MODEL-AND-DRAFTER-BASELINES.md), [cache layout](10-CACHE-MEMORY-LAYOUT-V2.mermaid).  
**Reality check:** [OTD/QWM01 checkpoint](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/4215aa39da160eb742ecd7f0fa2ace5c90d64efa/docs/qwenmonster/CHECKPOINT-OTD-PACK-QWM01-20261022.md), [whitepaper](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/4215aa39da160eb742ecd7f0fa2ace5c90d64efa/docs/qwenmonster/WHITEPAPER-QWENMONSTER-OTD-PACK-ARCHITECTURE-20261022.md).  
**Isolation:** документационный branch от `main` SHA `171b114e5d76140cd73e9679f1498eb8f3919ab6`. Accepted C6, QWM01 pack integration branch, runtime, публичные dependency locks и GPU plugin не меняются. Operator compute pause сохраняется.

> **Два разных понятия «модель»:** (1) **coding model**, которой поручается инженерная работа; (2) **inference target**, на котором проверяется результат. Не смешивать стоимость агентного труда с VRAM/UMA бюджетом target model. Ниже есть отдельный ledger для обеих групп.

## 1. Независимая model-routing лестница (актуальная политика)

**Обязательный supersession:** [12 — повторное ревью](12-COORDINATOR-REVIEW-20261022.md) и [13 — executable multi-provider prompt](13-HETEROGENEOUS-COORDINATOR-PROMPT-20261022.md) заменяют все прежние рекомендации «Haiku/Sonnet/Opus по умолчанию». Теперь **любой** connected model/provider должен быть обнаружен через real capability registry. Нельзя наследовать модель и контекст главного агента в child-сессию. Нужен отдельный provider-bound session ID, отдельный worktree и независимый reviewer.

| Уровень | Исполнитель из обнаруженного реестра | Вид работы | Эскалация |
|---|---|---|---|
| **L0, инвентаризация** | Дешёвый, реально доступный проверяющий (OpenAI / Anthropic / Google / OpenCode Zen; локальный только если разрешён runtime) | Source grep, manifests, простые fixtures, документы | Нет проверяемых исходников / противоречие |
| **L1, инженер** | Подходящий coding worker любого доступного провайдера, **не унаследованный от координатора** | Ограниченный C++, unit tests, offline replay, harness | Сложная cross-component ownership проблема или два безрезультатных доказанных исправления |
| **L2, архитектурный** | Самый сильный reasoning+coding worker из реально доступных; Claude Opus, Codex/GPT, Gemini и др. на равных при подтверждённых способностях | GPU concurrency, cancellation, slot leases, A5, A7 | До выдачи задачи — явное обоснование риска/невозможности L1; для A5/A7 уровень L2 оправдан сразу |
| **L3, независимый критик** | **Другой model family/provider** в новой сессии и read-only worktree; fallback same-family отмечать явно | Adversarial review, тесты и контрактный аудит | Не пишут код в авторском worktree и не наследуют историю author/coordinator |

Стоимость, лимиты и реальные модельные ID **узнаются из интерфейса провайдера в момент назначения**, не фиксируются как вечные цены Cursor. Отсутствующая интеграция = `UNAVAILABLE`; нельзя симулировать delegate той же главной моделью.

**Условие эскалации:** запиши `failed_gate`, `source_file:line`, проверенные гипотезы или почему нельзя проверить, риск и ожидаемый выход от более сильной модели. Траты оправдывает задача, не имя модели.

## 2. Coding-model ledger: этапы A0–A8

| Stage / зависимость | Основной исполнитель | Помощник / независимый review | Когда допускается L2 | Конкретный deliverable и закрывающий gate |
|---|---|---|---|---|
| **A0/P0 Model/IR capability** · первым | **L1 выбранного провайдера** | L0 инвентаризация; L2 при blocker | Неясный `MOECompressed` lowering, shader/kernel eligibility, несовместимые IR/drafter artifacts | Model-specific SHA/IR/quant/tokenizer/DLL capability ledger; отсутствие доказательства = `UNVERIFIED`, не `PASS` |
| **A1/P1 Baseline/protocol** · после A0 и разрешения compute | **L1 выбранного провайдера** | Haiku fixtures; независимый L3 по найденному protocol RED | Qwen/Gemma parser-output disagreement, reasoning/tool lifecycle crossing, GPU fatal | Gemma C6 comparison; Qwen3.6/Ornith plain tool tests, C1/C2/C4 и U4 KV там, где умещаются; green только по trace |
| **A2/P2 OTD observability** · параллельно A1 без тяжёлой GPU нагрузки | **L1 выбранного провайдера** | Haiku reports; L2 на concurrency seams | Process-shutdown, ownership, timestamps, run/slot attribution, trace truncation | Read/transform/copy/hits/evictions, trace+summary reconciliation; marked `NOT_EXPOSED` для метрик, которых нет |
| **A3/P3 Router trace + replay** · A0+A2 | **L1 выбранного провайдера**, L2 независимый design review | Haiku synthetic event generation; L3 replay audit | Draft/verify/commit lifecycle, cross-slot event correlation, lease semantics | Schema v1, deterministic native LRU parity, C1/C2/C4 synthetic replay, реальные трассы после compute release |
| **A4/P4 Packed layout** · **реализация уже есть** | **L1 hardening** | L3 независимый integrity review; L2 при race/corruption | Missing/foreign/corrupt payload, concurrent builders, safe publication, require/fallback boundary | Не переписывать packer; добавить negative packs tests + payload integrity contract, проверить `ovms_test *oeExpertsPack*` и GPU filters |
| **A5/P5 Cache + bounded I/O scheduler** · только после A2+A3 | **L2 High Thinking** | L1 isolated implementation/fixtures; независимый L3 review | L2 назначен сразу: concurrency, demand priority, cancellation и GPU slot lifetime архитектурно высокорисковые | Feature-flagged prototype; no demand starvation, cache-miss dedup, bounded prefetch, no p95/p99 regression, clean native LRU fallback |
| **A6/P6 CPU expert lane** · независим после A0 | **L1 выбранного провайдера** | Haiku ISA matrix; L2 на kernel/NUMA parity | SIMD layout, divergent numeric kernels, cross-socket ownership | Separate microbenchmark + numerical parity; **не** интегрировать CPU lane в OVMS до реального улучшения |
| **A7/P7 Integrated reliability** · A1+A4+A5, при разрешённом compute | **L2 High Thinking** | L1 runner, L3 adversarial regression review | L2 назначен сразу: multi-repo/ABI, shutdown/cancel, GPU races, rollback | Pinned candidate, 30–60-min soak, fault injection, C1/C2/C4, original C6 unchanged; fail on protocol/slot/model regression |
| **A8/P8 Qwen3.8 feasibility** · после A0, не блокирует A5 | **L1 выбранного провайдера** | Haiku manifests; L2 при IR/kernel design | Layer-dependent quant dispatch, model metadata/drafter compatibility ambiguity | Mixed-quant/checkpoint/kernel/KV budget matrix; no invented 32-GiB fit or token/s claim |

**Ориентировочный выбор L2 по умолчанию:** только **A5 и A7**; в A0/A1/A2/A3/A4/A6/A8 L2 включается **по указанному blocker**, а не по номеру этапа. Отдельные высокорисковые A4 негативные тесты reviewer может посмотреть независимо без L2 как автора.

### Реальная готовность до начала нового агентного плана

- Native GPU MoE OTD, LRU, trace, per-layer packs **не начинать с нуля**.
- QWM01 integration: 40 pack files; r75 и r40 packed/unpacked live short-bench; 43 standalone GPU unit PASS; parser 69/69, generation policy 9/9; post-repair 148/148 Qwen/Gemma parser controls; 20/20 controlled continuations, 17/17 HTTP400 negatives.
- **Не закрыто**: `ovms_test --gtest_filter=*oeExpertsPack*`, GPU `moe_otd_*`/`moe_offload_*`, MTP K3+packs, полнота `[OTD_PERF]` при завершении, payload checksum gate on require, cancel/resource, full agentic/multi-slot.
- A4 = текущая работа **integrity/negative gates**, не повторное построение .pack. A2/A3 имеют рабочую основу, а не пустой репозиторий.
- Не обновлять `ACCEPTED`, public lock, C6, XGrammar или model/runtime identity на основе новых тестов без явного решения оператора.

## 3. Inference-target ledger: какие модели участвуют на каждом этапе

**E = обязательный эталон/контроль**, **T = первичный target**, **V = независимая cross-check модель**, **F = feasibility**, **D = диагностический fallback**, `—` = не запускать по умолчанию. Символ означает **планируемую роль**, не выполненный runtime test.

| Этап | Gemma4 26B-A4B C6 | Qwen3.6-35B-A3B | AEON Ornith 35B | Qwen3.8 Flash-Next | Legacy Qwen3-30B |
|---|---|---|---|---|---|
| **A0** capabilities | E: граф/protocol identity | **T: native OTD + MTP IR** | **V: separate checkpoint/DFlash** | F: IR/quant/MTP inventory | D: known MoE gate |
| **A1** protocol baseline | **E: C6 tool/slots** | **T: agent loops/OTD** | **V: agent loops/OTD** | — | D if target unsupported |
| **A2** OTD metrics | E regression only if eligible | **T: r40/r75, packed/unpacked** | **V: independently measured** | F only | D kernel sanity |
| **A3** trace/replay | E protocol invariants | **T: plain/verify/draft traces** | **V: distinct expert distribution** | F MTP patterns only | D synthetic/legacy |
| **A4** pack integrity | E no regression | **T: malformed/foreign/corrupt packs** | **V: cross-check pack keys** | — | D minimal fixture |
| **A5** cache prototype | E unaffected tool protocol | **T: main workload** | **V: avoid overfit** | F if eligible | D differential |
| **A6** CPU experts | E if numeric reference exists | T after parity | V after parity | F conditional | D microkernel fixture |
| **A7** integration | **E: canonical C6** | **T: production-style** | **V: independent checkpoint** | F, never production gate | D only |
| **A8** feasibility | Reference memory comparator | Reference model | Separate workload | **F: lead target** | — |

**Checkpoint invariants:** exact model SHA, quantization and OpenVINO IR, tokenizer and template hash, matching GenAI/GPU DLL hashes, device/kernel path, actual successful OTD graph eligibility, and supported drafter all go into evidence. Qwen3.6 and Ornith are **not interchangeable**. Qwen3.8 Flash-Next is an architectural reference, not a prerequisite for pack hardening.

### Speculative-mode ledger

| Model | Plain | Native MTP | DFlash | Gate |
|---|---|---|---|---|
| Gemma4 C6 | Baseline | Conditional | Conditional | C6 known-good protocol first; identify exact compatible drafter before testing |
| Qwen3.6 | Baseline | Short K1/K2/K3 smoke reported on separate pre-pack executable; **packs+K3 NOT RUN** | Published candidate; runtime not accepted | Exact IR/tokenizer/slot identity, long-context TTFT/decode, acceptance rate, NVMe bytes/committed |
| AEON Ornith | Baseline | Never assume base-Qwen MTP works automatically | AEON DFlash export available; previously missing target hidden-state metadata on startup | Checkpoint-specific draft compatibility and startup before speed claims |
| Qwen3.8 Flash-Next | Feasibility baseline | Native model-dependent candidate | Not assumed | Actual exporter/model heads/mixed-quant GPU kernel support |
| Qwen3-30B | Diagnostic | Not a product gate | Not a product gate | Legacy OTD differential only |

### Physical 32-GiB UMA ledger — no invented MiB

**Not a third independent RAM tier**: Arc 140V GPU-readable slots, OS page cache, warm host pages, staging buffers, draft weights and KV U4 all occupy one 32-GiB LPDDR pool. NVMe is only cold backing storage, not free memory.

For **each model × quant profile × stage × plain/MTP/DFlash × context × C1/C2/C4** record physical unique bytes:

| Field | What must be counted | Verification |
|---|---|---|
| `os_runtime_bytes` | OS, OVMS/OpenVINO, other processes, safety reserve | OS native counters; preserve operator compiler |
| `pinned_nonexpert_bytes` | embeddings/attention/router/dense/shared/head | actual IR resident sizes |
| `expert_hot_unique_bytes` | GPU-readable resident expert slots only | slots × actual per-layer layout, metadata |
| `warm_page_cache_unique_bytes` | OS page-cache pages; **not** a free separate memory pool | working set/file cache telemetry, de-duplicate mappings |
| `staging_unique_bytes` | USM staging/transform/copy workspaces | allocations/peak |
| `kv_u4_target_unique_bytes` | target KV/prefix per C1/C2/C4 and sharing | actual U4, prefix accounting separately |
| `draft_weights_and_kv_unique_bytes` | drafter memory, including its own KV | 0 only when draft actually disabled; otherwise measured |
| `activation_workspace_unique_bytes` | runtime activation/kernel workspace | peak under representative workload |
| `safety_margin_bytes` | required headroom for OS and concurrency | explicitly configured budget |
| `physical_free_after_reserve_bytes` | **32 GiB minus unique resident allocations/reserve** | negative means deny admission, never swap |

Use `null + evidence_status=NOT_MEASURED`, **not 0**, for unavailable counters. OS page cache may overlap file-backed mappings; reconcile before summing. Model weights/pack files on NVMe are not added to `B_UMA` unless they occupy physical pages. A Qwen3.8 model that fails the memory gate is correctly marked `NOT_ELIGIBLE_ON_258V`, not silently run with swapped memory.

## 4. Unit of work: one evidence row and a strict model escalation note

Every coding-agent stage logs:

~~~json
{
  "stage": "A4",
  "task_id": "PACK-REQUIRE-PAYLOAD-CRC",
  "coding_model": "OBSERVED_EXACT_MODEL_ID",
  "model_tier": "L1",
  "escalated_from": "claude-haiku-5-5",
  "escalation_reason": "A checksum check may require a new trusted read boundary; implementation ownership is not mechanical.",
  "target_model": "Qwen3.6-35B-A3B",
  "source_head_sha": "EXACT_SHA",
  "gpu_plugin_sha": "EXACT_SHA",
  "runtime_hashes": "PRIVATE_RECEIPT_REFERENCE",
  "execution_scope": "unit_tests_only_compute_paused",
  "tests": ["missing_pack", "wrong_key", "header_corruption", "payload_bitflip"],
  "test_result": "NOT_RUN",
  "evidence_path": "PRIVATE_OR_PUBLIC_SAFE_PLACEHOLDER",
  "accepted": false
}
~~~

For any model escalation, keep **precise reason, expected benefit, allowed files, test gate and stop condition**. Expensive models must not spawn peers recursively without operator permission. When compute pause is lifted, user controls scheduling of exclusive GPU jobs.

## 5. Release/stop ledger

| Milestone | Completed when | Decision |
|---|---|---|
| **M0 static** | A0 compatibility matrix, all exact refs and unknowns explicit | No inference required |
| **M1 pack correctness** | A2 existing counters reconciled, A4 pack negative/integrity unit gates green; no unreviewed GPU mutation | Candidate baseline, **not product accepted** |
| **M2 cache policy** | A3 real trace+deterministic replay, A5 feature-flagged candidate beats native LRU on meaningful p95/bytes metrics | Only then trial under GPU |
| **M3 integration** | A1+A7 protocol and C1/C2/C4, Gemma4 control, Qwen+Ornith, suitable draft modes, soak, rollback | Separate operator promotion review |

**Stop now if:** C6 or public lock mutated, pack baseline not reproducible, untraced cache changes, missing manifest, wrong expert/router/logit parity, unexpected out-of-memory/swap, stale/resurrected request after cancellation, or agent claims `PASS` without test logs. A2/A3 instrument before A5 prefetch; A6/A8 are optional and must not block M1.

## 6. Resumption note

Read this ledger alongside the [frozen checkpoint](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/4215aa39da160eb742ecd7f0fa2ace5c90d64efa/docs/qwenmonster/CHECKPOINT-OTD-PACK-QWM01-20261022.md). **Next immediate handoff:** L1 + L0 for A0 static gap list and A4 integrity tests; L2 only for a substantive blocked design decision. The existing A4 format is preserved. Until operator authorizes GPU jobs, restrict action to code reviews, docs and offline tests. Nothing in this ledger authorizes a new runtime launch.
