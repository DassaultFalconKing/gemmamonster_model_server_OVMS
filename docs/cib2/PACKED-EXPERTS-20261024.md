# Packed experts (OTD Pack) — что это, откуда, схема, зачем

Date: **2026-10-24**.  
Status: **описание контракта + текущий native smoke**.  
`runtime_acceptance=NO`. Path A (`usm_device`) по умолчанию; Path B OFF.  
Draft PRs: OVMS [#29](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/29), OpenVINO [#10](https://github.com/DassaultFalconKing/openvino/pull/10).

Связанные документы: [ATLAS-PACKV2-NATIVE-20261024.md](ATLAS-PACKV2-NATIVE-20261024.md), [LOCAL-BUILD-FILE-MAP-20261024.md](LOCAL-BUILD-FILE-MAP-20261024.md), [LAYER-EXPERT-PACK-IMPLEMENTATION-20261024.md](LAYER-EXPERT-PACK-IMPLEMENTATION-20261024.md).

---

## 1. Что такое packed experts

В MoE (Mixture-of-Experts) каждый токен активирует только **top-K** экспертов из большого пула (часто сотни на слой). Веса экспертов — квантованные тензоры (у нас INT4 + scales + zero-points) для трёх проекций **gate / up / down** (GEMM3 + SwiGLU).

**Packed experts** — это **надисковое представление** этих routed-весов:

- один **immutable** файл на **один** скомпилированный MoE-слой;
- внутри — **все** эксперты слоя как одинаковые записи фиксированного шага;
- каждая запись уже в **device layout** (без runtime transpose scales/ZP);
- при miss в GPU-резидентном LRU — **одно позиционное чтение** записи эксперта с NVMe, а не разрозненный разбор исходного `openvino_language_model.bin`.

Формат payload на диске: **OTDPACK1** (`magic = "OTDPACK1"`, version 1).  
Имя файла: `otd-<16hex layer_key>.pack`, где `layer_key` — content-hash спеки слоя (источник весов, офсеты/размеры девяти тензоров, конфиг/layout), чтобы чужая/устаревшая модель **не** подхватывала чужой pack.

Это **не**:

- не «весь бинарник модели в одном файле»;
- не dense-layer offload и не Path B (`usm_host`);
- не доказательство tool-calling / production acceptance;
- не live-trace PGP-профиль (placement из профиля — отдельный offline шаг).

---

## 2. Откуда берутся

```text
Модель на диске (IR + BIN)
        │
        ▼
OVMS загружает servable (GenAI / continuous batching) на GPU
        │  plugin_config: OFFLOAD_RATIO ∈ [1..99], WEIGHTS_PATH=…/openvino_language_model.bin
        ▼
OpenVINO Intel GPU: скомпилированный узел MOECompressed (GEMM3_SWIGLU)
        │  PackLayerSpec из config + 9 routed tensor layouts + офсеты в BIN
        ▼
Режим pack build (env/CLI): GPU_MOE_OTD_PACK_MODE=build, GPU_MOE_OTD_PACK_DIR=<dir>
        │
        ▼
moe_otd::build_layer_pack / build_pack  →  otd-<key>.pack  (atomic temp → publish)
```

**Источник байт:** тот же `WEIGHTS_PATH` / mmap reader, что и для обычного OTD miss из BIN. Pack **переупаковывает** уже известные срезы экспертов в канонический per-expert record; он не «придумывает» веса.

**Кто пишет pack:** только **native GPU plugin** (канонический writer). OVMS лишь:

1. поднимает модель в **build-only** режиме (`--build_moe_experts_pack`, без listeners);
2. передаёт каталог `--moe_experts_pack_dir`;
3. после AVAILABLE считает число native packs (`checkCib2PackBuild`) и выходит.

**Offline Python** (`scripts/cib2/verify_pack_v1.py`, `packv2_pipeline.py`) **не** пишет payload экспертов: проверяет геометрию/хеши и (V2) seals immutable generation envelope вокруг уже построенных OTDPACK1.

### Текущий smoke (локально, не в git)

| Поле | Значение |
| --- | --- |
| Модель | `Qwen3.6-35B-A3B-int4-ov` (`qwen3_5_moe`) |
| Путь | `C:\Users\testc\qwen36-35b-a3b-baseline\models\Qwen3.6-35B-A3B-int4-ov` |
| Eligible слоёв / packs | **40** |
| Экспертов на слой | **256** |
| Размер одного pack | ~418 390 016 B (~399 MiB) |
| Сумма | ~**15.6 GiB** |
| Каталог | `C:\git\cib2-packv2-build-20261024\pack-build-smoke\` |
| Build hint | `OFFLOAD_RATIO=20` (размер резидентного LRU при serve; на состав pack не влияет как «сколько экспертов положить» — в pack кладутся **все** эксперты слоя) |

---

## 3. Схема упаковки (OTDPACK1)

### 3.1 Девять тензоров в записи эксперта

Порядок срезов в record (serialized offset order):

1. `gate_w` — вес gate  
2. `up_w` — вес up  
3. `down_w` — вес down  
4. `gate_s` / `up_s` / `down_s` — scales (обычно FP16)  
5. `gate_z` / `up_z` / `down_z` — zero-points  

Внутри записи тензоры выровнены на **64 B**; вся запись — на **4 KiB** (`pack_alignment`).  
Так miss = один `pread`-подобный read длины `record_stride`, без доп. transpose на горячем пути.

### 3.2 Структура файла

```text
[0 .. header)
  PackHeader: magic OTDPACK1, version, layer_key, num_expert,
              record_stride, records_offset, placement_offset, checksums_offset,
              tensor_bytes[9], tensor_offset_in_record[9], header_checksum

[placement_offset)
  u32 placement[num_expert]   — permutation: logical expert_id → physical slot index
                                (identity по умолчанию; co-access re-pack может переставить)

[checksums_offset)
  u64 checksum[num_expert]    — FNV-1a по payload логического expert_id (не physical index)

[records_offset)
  record[physical_i] × num_expert   — каждый record_stride байт, 4 KiB-aligned
```

**Важно:** checksums индексируются **логическим** `expert_id`. Placement меняет только физический порядок на диске (локальность чтения), не семантику ID.

### 3.3 Content key и publish

- `PackLayerSpec.key()` смешивает размер/сэмпл-хеш исходного BIN, офсеты/размеры девяти тензоров, `num_expert`, layout_params.  
- Файл пишется во временное имя, затем **атомарно** публикуется как `otd-<key>.pack`.  
- При serve режимы: `off` | `use` (fallback на BIN) | `require` (нет валидного pack → fail) | `build`.

### 3.4 Pack V2 envelope (поверх OTDPACK1)

V2 **не** меняет ABI записи эксперта. `packv2_pipeline.py` добавляет:

- offline **plans** (placement + residency sidecars);
- **seal** immutable `generation-<sha>/` + `manifest.v2.json` + `active.v2.json`;
- повторный **verify** generation.

Поле `runtime_acceptance` в манифестах остаётся **`NO`**, пока нет отдельного operator gate.

Независимый verifier: `scripts/cib2/verify_pack_v1.py` (и зеркало в OpenVINO `tools/moe_otd_pack/`). Smoke: 40/40 OK → `pack-build-smoke-verify.json` (build-root).

---

## 4. Зачем это нужно

| Проблема без pack | Что даёт pack |
| --- | --- |
| Эксперты размазаны по гигабайтному BIN; miss = много seeks + layout transform | Один sequential/positional read готовой записи |
| Холодные эксперты не влезают в GPU/UMA (32 GiB LPDDR на Arc 140V) | На диске **все** эксперты слоя; в GPU — только hot LRU (`OFFLOAD_RATIO`) |
| Сложно гарантировать целостность при частичной загрузке | Per-expert FNV + header checksum до publish в слот |
| Сложно версионировать «поколение» весов | `layer_key` + (опционально) V2 generation seal |
| Co-activated эксперты далеко друг от друга в BIN | Placement permutation без смены reader ABI |

**Зачем OVMS CLI build-only:** один раз на eligible модели материализовать packs на той же compiled graph / том же plugin, которым потом будут serve — без HTTP, без путаницы с production listeners.

**Чего pack сам по себе не делает:** не ускоряет decode магически; не заменяет измеренные r0/r20/r40/r75; не включает prefetch/Path B. Он — **контракт хранения и miss-path** для Path A OTD.

---

## 5. Где код (git relative)

### OpenVINO (Draft #10)

| Роль | Путь |
| --- | --- |
| Codec / header / build / verify | `src/plugins/intel_gpu/src/graph/impls/ocl_v2/moe/moe_otd_pack.{hpp,cpp}` |
| Spec + build wiring | `…/moe_otd_runtime.{hpp,cpp}` |
| Demand load / modes | `…/expert_weight_providers.{hpp,cpp}` |
| LRU | `…/lru_cache.{hpp,cpp}` |
| Host tests / UMA probe | `src/plugins/intel_gpu/tools/moe_otd_control_v2/` |
| Offline pack tests | `src/plugins/intel_gpu/tools/moe_otd_pack/` |

### OVMS (Draft #29)

| Роль | Путь |
| --- | --- |
| CLI flags | `src/cli_parser.cpp`, `src/config.cpp` |
| Build count / exit | `src/server.cpp` (`checkCib2PackBuild`) |
| Offline layout / seal / verify | `scripts/cib2/pack_layout.py`, `packv2_pipeline.py`, `verify_pack_v1.py` |
| Trace → profile | `scripts/cib2/trace_profile.py` |

### Локальный build-root (не git)

`C:\git\cib2-packv2-build-20261024\` — `ovms-runtime\`, `launch-pack-build-smoke.py`, `pack-build-smoke\`, receipts JSON.

---

## 6. Минимальный операторский цикл

1. **Build packs** (уже сделано на Qwen3.6 smoke):  
   `ovms.exe --build_moe_experts_pack --moe_experts_pack_dir <DIR> … --plugin_config {"OFFLOAD_RATIO":20,"WEIGHTS_PATH":"…/openvino_language_model.bin"}`
2. **Verify** offline: `verify_pack_v1` / `verify-all-packs.py`.
3. **Seal** (опционально, V2): `packv2_pipeline.py plans|seal|verify` — `runtime_acceptance` остаётся NO.
4. **Serve** (ещё не acceptance): тот же tuple, **без** `--build_moe_experts_pack`, с `--moe_experts_pack_dir` на sealed/verified packs; затем ячейки `OFFLOAD_RATIO` 0 / 20 / 40 / 75.

До шага 4 нельзя утверждать GPU model acceptance. До явного operator OK — не flip `runtime_acceptance`.
