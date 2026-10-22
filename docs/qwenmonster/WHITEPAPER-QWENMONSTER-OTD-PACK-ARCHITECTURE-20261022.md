# QwenMonster × MoE Expert Packs
## Архитектура протокольного и дискового контура OVMS, реализация и экспериментальная проверка

**Technical whitepaper · 22 октября 2026 · revision 1.0 (research snapshot)**  
**Reference code:** `DassaultFalconKing/gemmamonster_model_server_OVMS` @ `85c37fcfb87a5d49d80a362930a5d261baf0ce0e`  
**Measured GPU plugin:** `DassaultFalconKing/openvino` @ `479219245f6f10b670367ad35af16513d72d2091`  
**Acceptance:** **NOT ACCEPTED**; результаты ниже ограничены конкретными проверками, а не заявлением о production-ready системе.

## Abstract

QwenMonster — развитие форка OpenVINO Model Server (OVMS) на базе C6 для корректной агентной работы моделей Qwen3.6/Ornith. В новой интеграционной линии к протокольному контуру добавлен **MoE Offload-to-Disk (OTD) Expert Pack**: отдельный build-проход преобразует дисковое представление каждого routed expert в готовую для GPU укладку, а runtime держит ограниченное число экспертных весов в резидентных слотах. При cache miss весь эксперт читается из pack **одной позиционной операцией вместо нескольких чтений отдельных тензоров и без hot-path transpose**.

В отличие от замены инференс-движка, эта реализация сохраняет архитектуру OVMS/GenAI и исходную маршрутизацию MoE. Она не изменяет веса и семантику модели; изменяется способ их размещения, чтения и попадания в GPU-резидентный кеш. В верхнем контуре QwenMonster сохраняет нативный Qwen XML tool format, строгую проверку аргументов и явное разделение constrained generation, parsing и HTTP/SSE publication.

В измеренном коротком сценарии packed на `OFFLOAD_RATIO=75` повышает среднюю скорость декодирования примерно на **10.5%** (5.33 → 5.89 tok/s); при `OFFLOAD_RATIO=40` прирост около **2.4%** (7.05 → 7.22 tok/s). Это **не** означает пропорционального уменьшения передаваемых байтов или подтверждения прироста с MTP/длинным контекстом. Четыре серии обычной генерации прошли; полные protocol/MTP/пакетные тестовые gates остаются открыты.

## 1. Мотивация и границы решения

Для MoE-модели на ограниченной памяти Intel Arc 140V / Core Ultra 258V часть routed experts не может постоянно находиться в резидентных GPU-слотах. Router выбирает подмножество экспертов на каждом токене. При промахе прежний OTD путь делает выборку девяти логических тензоров (gate/up/down weights, scales, zero-points) из исходного весового файла и преобразует layout scale/ZP на критическом пути. Точное количество физических чтений зависит от наличия тензоров; в зафиксированных измерениях unpacked — **9 reads на miss**.

Цели интеграции:

1. Снизить число операций чтения при промахе, сохранив примерно тот же полезный объём весов.
2. Убрать scale/ZP transpose из критического пути генерации.
3. Сохранить существующий LRU/cache slot allocator и маршрутизацию без пересчёта модели.
4. Сделать pack reuse воспроизводимым по идентификатору исходного представления.
5. Сделать диагностику hit/miss/evict/read latency доступной в release runtime.
6. Не вносить изменения в Qwen tool policy, parser, KV cache или MTP при реализации packs.

**Вне реализованного scope:** layer prefetch, Strata-подобный dynamic hot/cold layer manager, U4 KV offload, speculative-aware expert prefetch, новая стратегия routing, подтверждённое ускорение MTP. Это исследовательские направления, а не готовые функции данной ветки.

## 2. Система состоит из двух независимых, но сопряжённых контуров

~~~mermaid
flowchart TB
    A["Agent / OpenCode / API client"] --> B["OVMS REST / OpenAI-compatible request"]
    B --> C["Qwen3Coder GenerationConfigBuilder"]
    C --> D["OpenVINO GenAI / XGrammar constrained or native generation"]
    D --> E["OpenVINO GPU plugin: MoE routing and OTD expert provider"]
    E --> F{"Expert resident in LRU slot?"}
    F -->|Yes| G["Reuse resident expert"]
    F -->|No: packed| H["Read one aligned expert record from .pack"]
    F -->|No: unpacked| I["Read source weight tensors + transpose scale/ZP"]
    H --> G
    I --> G
    G --> J["MoE GPU computation + next tokens"]
    J --> K["Qwen XML parser + schema validation"]
    K --> L["OVMS response/SSE + finish reason"]
    L --> A
    M["Dedicated --build_moe_experts_pack run"] --> N["Content-keyed, per-layer .pack files"]
    N --> H
~~~

**Protocol plane** управляет интерпретацией запроса, выбором `tool_choice`, ограничением генерации, сборкой XML tool calls, проверкой схемы и публикацией OpenAI-compatible событий. **Weight/data plane** принимает expert IDs от исходного GPU MoE router, обслуживает резидентные slots и загружает веса из диска по cache miss. Связь между контурами проходит через GPU-инференс, но pack feature **не является** исправлением XML/parser bugs.

### 2.1 QwenMonster protocol plane

- `Qwen3CoderGenerationConfigBuilder` формирует структурные теги нативного Qwen XML с `QwenXMLParametersFormat`, а не Hermes-style JSON внутри XML.
- `none`: builder не устанавливает tool grammar; запрет executable tool calls должен также обеспечиваться API/parser policy.
- `auto`: по умолчанию unconstrained, добровольное решение модели использовать инструмент. Экспериментальный guided auto включает lazy `TriggeredTags` после native `<tool_call>`.
- `required` / named: hard `TagsWithSeparator` + `at_least_one=true`, при named только выбранный зарегистрированный tool.
- `parallel_tool_calls=false` задаёт `stop_after_first=true` для constrained tag builder; unguided post-parser enforcement остаётся отдельным тестовым gate.
- `Qwen3CoderToolParser` инкрементально получает XML, удерживает незавершённые маркеры/значения и публикует только валидированные вызовы. Типизированные аргументы и schema проходят проверки. Отдельный XML grammar mask предотвращает нежелательные токены **только когда соответствующий runtime действительно установлен**.
- `finish_reason=length` из actual backend должен доходить до клиента, несмотря на внутренний streamer `end()`, используемый для завершения parser state. Cancel/reclamation остаётся не доказанным.

### 2.2 Expert pack data plane

- Резидентные routed experts обслуживаются в `ResidentExpertWeightProvider` либо `OffloadExpertWeightProvider`; текущая OTD ветка сохраняет expert-ID → resident-slot mapping через LRU.
- При `try_acquire_simultaneous` уникальные expert IDs вычисляются до загрузки. Если их число превышает capacity, функция отказывает **до воздействия на кеш**, исключая ненужные eviction/load из неудачной групповой попытки.
- Cache hit: slot переиспользуется без чтения весов.
- Cache miss: LRU выделяет свободный либо вытесненный slot; packed path использует `fill_weights_from_pack`, unpacked — `fill_weights_memory`.
- Слоты, маршрутизация, модельная математика и KV defaults не меняются. Это оптимизация layout/read path, а не переписывание MoE kernels.

## 3. Пакетный формат и его корректность

**Один pack на MoE-слой**, содержащий все routed experts этого слоя. При зафиксированном benchmark получилось 40 файлов по 434,118,656 байт каждый (всего 17,364,746,240 байт ≈ 16.17 GiB).

| Поле / элемент | Реализация и роль |
|---|---|
| Magic/version | `OTDPACK1`, format v1 |
| Header | key, expert count, record stride, offsets, tensor sizes/placement offsets, checksum |
| Expert record | Девять групп тензоров gate/up/down × weights/scales/ZP, отсутствующие тензоры имеют нулевой размер |
| Alignment | Тензоры выравниваются на 64 байта; запись эксперта — на 4096 байт |
| Placement table | Отображает expert ID → позицию записи; есть механизм перестановки, но runtime adaptive reclustering не заявлен |
| Checksums | FNV-1a-подобные per-record checksums для проверки целостности при `verify_pack` |
| Content key | Учитывает версию, исходные размеры и offsets, выборочные байты исходных весов и layout params |
| Atomic build | Временный файл → проверка/публикация rename; валидный существующий файл можно переиспользовать |

**Важное ограничение целостности, обнаруженное при чтении исходников:** `PackLayerSpec` использует **sampled non-cryptographic hash** исходного файла, а не полный SHA-256 весов. `build_pack` проверяет повторно используемый файл через `verify_pack`. Однако `OffloadExpertWeightProvider::configure_pack` в serving/require path вызывает `PackLayout::open`, проверяющий header/key/структуру, **но не вызывает полный `verify_pack` для payload records**. Следовательно, предположение «любой bit-flip в теле файла обязательно выявляется на startup» кодом **не подтверждено**. Это не основание считать packs неисправными, но важное требование к негативным тестам и дальнейшему hardening.

Pack layout хранит уже подготовленный device-oriented формат. Это **не новый формат квантования** и не утверждение о «сжатии в девять раз». Выигрыш заключается в числе syscall/read operations, удалении hot-path трансформаций и последующей локальности.

## 4. Сборка и использование: два жизненных цикла

### 4.1 Build mode (одноразовый prepare)

~~~bash
ovms --config_path <CONFIG> \
  --build_moe_experts_pack \
  --moe_experts_pack_dir <PACK_DIR>
~~~

- OVMS проверяет аргументы, создаёт pack directory и выставляет `OV_GPU_MOE_OTD_PACK_MODE=build` + `OV_GPU_MOE_OTD_PACK_DIR`.
- Компилирует необходимые servables; idle-unload groups на этом пути отключены. REST/gRPC слушатели **не стартуют**.
- GPU plugin формирует `PackLayerSpec` для каждого offloaded MoE layer, генерирует pack либо подтверждает reuse; после проверки наличия packs OVMS выходит.
- При ошибке компиляции servable или полном отсутствии pack files build должен завершаться ошибкой.
- Это **не** «вызвать `--pull`» и не изменение весов исходной модели.

### 4.2 Serving mode (fail-closed for absent/foreign packs)

~~~bash
ovms --config_path <CONFIG> \
  --rest_port 8000 \
  --moe_experts_pack_dir <PACK_DIR>
~~~

- Выставляет plugin mode `require` вместо `build`.
- При компиляции слоя GPU plugin открывает ожидаемый по spec файл и строит таблицу record offsets.
- Если требуемый pack отсутствует либо ключ/формат/header отклонён, servable не должен загрузиться с silent fallback на unpacked. **Полная payload checksum verification в require mode пока не доказана.**
- Если флаги отсутствуют, прежний OTD путь остаётся доступным (контрольная база unpacked).
- Значение `OFFLOAD_RATIO` контролирует resident-capacity, но **не входит в pack content key**, поэтому один набор паков может работать при разных ratio, как зафиксировано на r40/r75.

### 4.3 Формула стоимости

Для одного MoE-layer cache miss и сравнимого expert payload:

- `T_unpacked ≈ T_seek/read(1..N tensors) + T_layout_transform + T_GPU_copy + T_cache`
- `T_packed ≈ T_single_aligned_read + T_GPU_copy + T_cache`

Это качественная модель стоимости, **не подогнанная линейная формула**: OS page cache, конкурентные запросы, I/O depth, наличие тензоров и GPU scheduling меняют реальную латентность. Упаковка не сокращает число miss автоматически: на него влияют memory budget, routing locality, cache policy и speculative verify pattern.

## 5. Observability и воспроизводимость

OTD instrumentation включается явно; без opt-in маршрутизация и кеш должны работать прежним способом.

- `MOE_OTD_TRACE` включает line-oriented trace: регистрация слоя, вызовы acquire, последовательности expert IDs, hits/misses, evictions, bytes, disk reads, read/transform/copy timing. Сам текст prompt в trace не записывается.
- `MOE_OTD_PERF_LOG` активирует process-wide counters. В release plugin исправлен вывод в `stderr`, так как `GPU_DEBUG_INFO` компилировался из release. Текущий summary регистрируется через `std::atexit`.
- Offline replay/summary использует `otd_sim.py`, сравнивает последовательность cache events и позволяет считать метрики даже когда stderr-summary отсутствует.
- Trace quantiles и встроенный `[OTD_PERF]` histogram нельзя смешивать без проверки одинаковых определений: runtime histogram хранит верхние границы степенных microsecond buckets.
- В измеренных четырёх строках summary получен **offline**, потому что process exit не вызвал atexit. Три из четырёх trace files заканчиваются mid-record; такие усечения необходимо документировать, а не скрывать.

## 6. Benchmark: четыре измеренных режима

**Один warmup + 3 повтора, temperature=0, 55 input / 384 generated tokens; каждый запрос заканчивается `length`.** Значения ниже относятся к повторам после прогрева, а не к warmup.

| Parameter | Packed r75 | Unpacked r75 | Packed r40 | Unpacked r40 |
|---|---:|---:|---:|---:|
| TTFT mean (s) | **4.27** | 5.23 | **1.16** | 1.56 |
| Decode mean (tok/s) | **5.89** | 5.33 | **7.22** | 7.05 |
| Hit rate | 84.6% | 84.6% | 98.0% | 97.0% |
| Misses | 77,576 | 77,572 | 9,871 | 15,091 |
| Disk read operations | **77,576** | 698,148 | **9,871** | 135,819 |
| Read bytes (GB, decimal) | 131.55 | 131.54 | 16.74 | 25.59 |
| Transpose/transform total (ms) | **0** | 11,656 | **0** | 2,408 |
| Available RAM at launch (MiB) | 9,824 | 17,667 | 16,765 | 17,835 |

**Интерпретация:**

- At r75 packed и unpacked имеют почти одинаковые misses и bytes. Здесь ускорение логично связано с меньшим количеством дисковых чтений и отсутствием трансформации, а не с объёмом данных.
- At r40 resident slots больше (153/256 вместо 64/256), существенно меньше misses и скорость в целом выше. Величина эффекта packs относительно unpacked сокращается; на packed r40 также меньше misses, чем на unpacked r40, поэтому оценка не представляет идеально изолированный эксперимент.
- Стартовая RAM различалась, особенно на packed r75, который стартовал ниже драfter-floor **15,463 MiB**. Поэтому численные показатели следует считать **пилотными производительными измерениями**, а не доказательством воспроизводимого выигрыша под одинаковым memory pressure.
- У первой попытки packed r40 был сбой клиента; published trace counters обрезаны до окна четырёх валидных генераций. Ни одна строка не доказывает multi-request/concurrency throughput.
- Наличие `finish_reason=length` доказывает достижение output limit, **не качество выводимого текста, JSON, XML или autonomous tool calls**.

## 7. MTP / speculative decoding: что интеграция пока не доказывает

Существующий drafter track использовал `OFFLOAD_RATIO=40` и **неpacked** путь. Подтверждены экспорт/преобразование MTP head и короткие baseline/K1/K2/K3 smoke (27 входных / 64 выходных токена). Это не проверка упаковки вместе с MTP.

Speculative decoding потенциально меняет распределение expert IDs на одну подтверждённую output token: candidate verify batch может одновременно задействовать больше экспертов и увеличить working set/evictions. Pack снижает цену отдельного cache miss, но **не гарантирует повышения cache hit rate** и не решает проблему слишком большого simultaneously-acquired set.

Для ответственного сравнения нужны: identity модели/drafter/IR/бинарников, одинаковый prompt/token IDs (2048 входных токенов), prefill/TTFT/decode отдельно, speculative accepted/proposed token metrics, OTD hit/miss/bytes/tail latency, memory peak и 2+ повтора. Подтверждённого результата **MTP K3 + packs нет**.

## 8. Protocol acceptance: почему успешный OTD bench не равен «QwenMonster готов»

К моменту checkpoint в QWM01 отдельно измерены:

- Qwen parser `69/69`, generation policy `9/9`, generic parser `29/29`; post-repair Qwen+Gemma `148/148`.
- HTTP request/tool unit controls `2/2` / `11/11` и реальные HTTP400 `17/17`.
- `20/20` controlled two-turn tool-result continuations (10 unary / 10 SSE) с сохранённой semantic evidence, но **без зафиксированного final wrapper exit code** и **не** автономные subagents.
- Живой Ornith smoke с `ping {}`, `city=Paris`, `none`, unary/SSE; matched installed DLL проверен в ограниченных случаях.
- Isolated XGrammar #802 native fix, #650 matcher с реальным Qwen3-8B tokenizer 71/71. В нативной R1 schema-boundary matrix **24 PASS + 4 expected OPEN**, включая undeclared required fields.

Пока **не** закрыты: полный canonical Qwen3.6/Ornith Jinja+token-ID history, reasoning→tool phase matrix, loaded-candidate live `</parameter1>`, полный #802 installed runtime acceptance, guided auto A/B, 100/100 required/named, multi-call и настоящие 1/2/4 agentic sessions, доказанная CANCEL resource reclamation. Изолированные unit PASS не превращаются в полный production acceptance только потому, что GPU дал 384 токена.

## 9. Слабые места, ограничения и безопасная эксплуатация

1. **Integrity granularity.** Pack key основан на sampled FNV-style fingerprint, не на full cryptographic hash. Build/reuse record checksum есть, но serving `require` не вызывает полный `verify_pack` до inference. Обязателен тест payload-bitflip, а также missing/foreign/truncated cases.
2. **Trace closure.** Текущий процесс shutdown не гарантирует вызов `atexit`, поэтому не считать process-exit summary доступным по умолчанию. Требуется предсказуемый flush/close path.
3. **Memory budget.** Дисковый pack не заменяет GPU-resident slot memory и не гарантирует, что 4 параллельных запроса помещаются в память.
4. **Bench fairness.** Не сравнивать исходный drafter executable и новый pack executable без фиксации каждой DLL; не переносить результат между `OFFLOAD_RATIO` режимами без контроля начальной памяти.
5. **Protocol isolation.** Изменение weight loading не исправляет generation policy, XGrammar hard/lazy masks, SSE lifecycle или agent decisions.
6. **No background restart.** По действующему handoff оператор остановил вычислительные прогоны; whitepaper описывает систему и разрешённые будущие gates, но **не разрешает возобновлять benchmark workers**.
7. **Data publication.** Pack-файлы, исходные веса, локальные пути, приватные trace/prompt evidence не публиковать в Git. Публичная документация содержит только source refs, агрегаты и невосстанавливающие личные данные placeholders.

## 10. Acceptance roadmap, не новый scope creep

**P0 — закрепить и воспроизвести текущую реализацию:** на отдельном рабочем checkout, после снятия compute pause, проверить source/DLL hashes, четыре строки с одинаковым RAM floor, затем `ovms_test --gtest_filter=*oeExpertsPack*`, GPU `moe_otd_*` / `moe_offload_*`. Отдельно проверить bad-pack fail-closed и corrupt-record handling; по возможности unit fixture без GPU.

**P1 — совместная работа packs × speculative:** сначала baseline и MTP K3 на идентичных 2048-token input histories, затем K1/K2; честный accounting OTD, latency, acceptance, GPU memory.

**P2 — QwenMonster protocol promotion:** закрыть #650/#802 live, required/named, reasoning/tool phases, SSE cancel/resources, autonomous loops, regression against immutable C6. **Только отдельное явное решение** может передвинуть accepted baseline/public lock.

**Future research, not delivered:** экспертная thermal policy (hot/warm/cold), router-aware prefetch, Strata-style cold layer placement, U4 KV policy, DFlash/EAGLE3 feasibility. Эти темы полезны, но не должны затмевать ещё незакрытые базовые gates.

## 11. Source map (review starting points)

| Aspect | Frozen source |
|---|---|
| OVMS CLI/mode/HTTP suppression | [server.cpp](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/src/server.cpp), [cli_parser.cpp](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/src/cli_parser.cpp) |
| Pack build/docs and evidence | [HANDOFF-MOE-OTD-PACK-20261022.md](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/docs/qwenmonster/HANDOFF-MOE-OTD-PACK-20261022.md) |
| Pack format and verifier | [moe_otd_pack.hpp](https://github.com/DassaultFalconKing/openvino/blob/479219245/src/plugins/intel_gpu/src/graph/impls/ocl_v2/moe/moe_otd_pack.hpp), [moe_otd_pack.cpp](https://github.com/DassaultFalconKing/openvino/blob/479219245/src/plugins/intel_gpu/src/graph/impls/ocl_v2/moe/moe_otd_pack.cpp) |
| Provider, cache and streaming | [expert_weight_providers.cpp](https://github.com/DassaultFalconKing/openvino/blob/479219245/src/plugins/intel_gpu/src/graph/impls/ocl_v2/moe/expert_weight_providers.cpp), [lru_cache.cpp](https://github.com/DassaultFalconKing/openvino/blob/479219245/src/plugins/intel_gpu/src/graph/impls/ocl_v2/moe/lru_cache.cpp) |
| OTD trace/counters | [moe_otd_trace.hpp](https://github.com/DassaultFalconKing/openvino/blob/479219245/src/plugins/intel_gpu/src/graph/impls/ocl_v2/moe/moe_otd_trace.hpp), [moe_otd_runtime.cpp](https://github.com/DassaultFalconKing/openvino/blob/479219245/src/plugins/intel_gpu/src/graph/impls/ocl_v2/moe/moe_otd_runtime.cpp) |
| Qwen XML generator | [generation_config_builder.hpp](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/src/llm/io_processing/qwen3coder/generation_config_builder.hpp) |
| Qwen XML parser / schema | [qwen3coder_tool_parser.cpp](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/src/llm/io_processing/qwen3coder/qwen3coder_tool_parser.cpp), [tool_schema_profile.cpp](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/src/llm/io_processing/qwen3coder/tool_schema_profile.cpp) |
| Acceptance, unit/protocol evidence | [MASTER-PLAN.md](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/docs/qwenmonster/MASTER-PLAN.md), [OVMS-TEST-HTTP-RESULTS.md](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/docs/qwenmonster/OVMS-TEST-HTTP-RESULTS.md), [FOLLOWUP-20261021.md](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/docs/qwenmonster/FOLLOWUP-20261021.md) |
| Drafter limitations | [HANDOFF-DRAFTERS-20261022.md](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/85c37fcfb/docs/qwenmonster/HANDOFF-DRAFTERS-20261022.md) |

### Conclusion

Главный технический результат этой версии QwenMonster — **отделение model/agent protocol correctness от memory/I/O optimisation**. В верхнем контуре сохраняется C6/OVMS и нативная Qwen XML semantics; в нижнем GPU-контуре routed experts получают подготовленное 4KiB-aligned представление, что измеримо сокращает число чтений при miss и устраняет преобразование layout во время decode. Экспериментальный результат поддерживает практическую ценность подхода, но не отменяет существенных незакрытых correctness gates. **Оптимизация работает в измеренном режиме; промышленная и агентная приёмка остаются отдельной задачей.**
