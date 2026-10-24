# ТЗ / программа: Pack V2 offline pipeline (seal drop-in + соседние звенья)

| Поле | Значение |
|------|----------|
| ID | `TZ-SEAL-FAST-20261024` |
| Статус | **planning only** — реализация later, сейчас не втискиваем |
| Владелец | CIB2 Pack V2 / offline harness |
| Фокус v1 | незаметная замена `seal`/`verify` внутри `packv2_pipeline.py` |
| Расширение | рекомендации по mapper / packer / всему, что в цепочке |
| Язык | Python 3.12+ в том же tree; **не** Rust/C++ rewrite |
| Манифест | байт-совместимый `cib2.pack_generation.v2` |

---

## 0. Решение оператора (зафиксировано)

| Тема | Решение |
|------|---------|
| Post-seal verify | Default **`fast`**; полный — **только по флагу** (`--post-seal-verify=full` / `verify --mode=full`). Всё в MANUAL. |
| Hardlink | Режимы с флагом: `require-readonly` (default) / `chmod-readonly` / `allow-shared`. |
| Legacy seal | **Нет `--legacy-seal`.** Новый seal **заменяет** старый незаметно для агента / вызывающего кода / оператора. Те же subcommands и позиционные/обязательные аргументы. Новые флаги — только opt-in ускорения/политики с безопасными default. |
| Сейчас | Только планирование. В текущий running seal / ветку **не вмерживать**. |

---

## 1. Проблема seal (кратко)

Baseline ~15.6 GiB / 40 packs ≈ **час**: multi-pass `inspect` + `sha256` + copy+`fsync` + снова то же в `verify_generation`. Язык не bottleneck.

---

## 2. Цель программы

1. **Drop-in seal:** `packv2_pipeline.py seal --plans-dir … --native-packs … --output-root …` без новых обязательных аргументов → быстрее, тот же артефакт, тот же JSON-статус на stdout (совместимый контракт).
2. Опциональные флаги для power users / MANUAL (verify mode, materialize, fsync, hardlink-policy, workers, progress, log) — defaults не ломают скрипты агентов.
3. `verify` без флагов остаётся **`full`** (старое поведение для явного аудита); post-seal внутри `seal` по умолчанию делает **`fast`**, а не второй полный час.
4. **Прогрессбары + многопоточность + логирование + метрики** — must в реализации seal/verify (см. §6.4–6.7).
5. Зафиксировать карту всей offline-цепочки и **рекомендации** по mapper / packer / verify (не обязательно кодить в том же PR).

---

## 3. Не-цели сейчас

- Реализация в этом спринте / подмена running seal.
- Смена OTDPACK1 ABI, Path B, `runtime_acceptance=YES`.
- Rewrite на Rust/C++.
- Ломающее изменение обязательного CLI.
- Обязательный рефактор pack-build C++ в том же изменении, что seal (только рекомендации).

---

## 4. Drop-in контракт (незаметная замена)

### 4.1 Что агент/код/оператор уже вызывают

```text
python packv2_pipeline.py seal --plans-dir DIR --native-packs DIR --output-root DIR
python packv2_pipeline.py verify --generation-dir DIR
python packv2_pipeline.py plans --bundle … --output-dir … --strategy …
```

После замены:

- Те же команды **обязаны** работать.
- Exit codes: `0` ok, `2` reject — как сейчас.
- stdout JSON от `seal`: как сейчас после успешного пути (сегодня seal в `main` печатает результат `verify_generation`). Сохранить ключи `status`, `generation`, `pack_count`, `runtime_acceptance`, …; доп. поля только additive.
- Каталог `generation-<sha>/` + `manifest.v2.json` + `active.v2.json` — тот же schema/set ключей.
- Идемпотентный повторный seal на тот же digest — ok.

### 4.2 Что можно добавить (opt-in)

```text
--post-seal-verify fast|full|none     # default fast (внутри seal)
--materialize copy|hardlink           # default copy
--hardlink-policy require-readonly|chmod-readonly|allow-shared
--fsync dir|each|none                 # default dir
--workers N                           # default min(8, cpu_count); 1 = serial
--progress auto|tty|jsonl|off         # default auto
--log-file PATH                       # optional; JSONL events
--metrics-file PATH                   # optional; final metrics JSON (else receipts/)
```

```text
packv2_pipeline.py verify --generation-dir DIR [--mode full|fast]
  [--workers N] [--progress auto|tty|jsonl|off] [--log-file PATH] [--metrics-file PATH]
```

Без флагов поведение «как привыкли по CLI shape»; быстрее за счёт алгоритма + разумного default `--workers`; прогресс на TTY не ломает JSON stdout (см. §6.4).

### 4.3 Что нельзя

- Переименовать subcommand / обязательные флаги.
- Требовать `--legacy-seal` или второй бинарь.
- Класть лишние файлы внутрь `generation-*` так, что strict inventory verify падает (receipt → рядом, в `output-root/receipts/`).

---

## 5. Карта задействованных звеньев (что ещё есть)

Поток от модели до sealed generation и serve:

```text
[model IR on disk]
    → family_map.py              # MAP-02 static inventory (mapper)
    → (optional) storage_geometry / static_nine_slice / source_lock
    → trace (live) → trace_profile.py   # COMPLETE moe_otd_trace → profiles
    → pack_layout.py             # PGP-02 logical→physical placement (mapper/layout)
    → packv2_pipeline.py plans   # plans.v2 + otd-*.placement / *.residency
         OR make-identity-plans-from-packs.py  # identity plans from already-built packs
    → OVMS --build_moe_experts_pack + GPU pack codec   # паковальщик (native)
    → verify_pack_v1.py / verify-all-packs.py          # offline pack verify
    → packv2_pipeline.py seal    # ★ этот ТЗ (drop-in fast)
    → packv2_pipeline.py verify  # full|fast
    → OVMS serve + launch-pack-serve-*.py / smoke / metrics
```

### 5.1 Перечень компонентов

| # | Звено | Где | Роль |
|---|--------|-----|------|
| 1 | **Mapper (family)** | `scripts/cib2/family_map.py` | Статический inventory модели/слоёв/тензоров; не hotness |
| 2 | Storage geometry | `storage_geometry.py` | Геометрия хранения / offline sizing helpers |
| 3 | Static nine-slice | `static_nine_slice.py` | Офлайн разметка nine-slice ролей |
| 4 | Source lock | `source_lock.py` | Фиксация source provenance |
| 5 | Trace → profile | `trace_profile.py` | Live COMPLETE trace → PGP-02 profiles |
| 6 | **Mapper (layout)** | `pack_layout.py` | Логический→физический placement permutation |
| 7 | Plans | `packv2_pipeline.py plans` | Bundle → `plans.v2` + sidecars |
| 8 | Identity plans | build-root `make-identity-plans-from-packs.py` | Plans из уже собранных packs (smoke Path A) |
| 9 | **Паковальщик** | OVMS CLI `--build_moe_experts_pack` + OV GPU `moe_otd_pack` | Пишет OTDPACK1 на диск |
| 10 | Pack verify | `verify_pack_v1.py`, build `verify-all-packs.py`, OV `tools/moe_otd_pack` | Payload integrity |
| 11 | **Seal** | `packv2_pipeline.py seal` | Immutable generation envelope |
| 12 | Verify generation | `packv2_pipeline.py verify` | Envelope + digests |
| 13 | Attribution / stage | build-root stage + `*-attributed.json` | Правильные DLL для pack-build/serve |
| 14 | Serve / smoke | `launch-pack-serve-*.py`, smoke, metrics | Live GPU (после seal) |
| 15 | Preflight / inventory | `preflight_rc3b.py`, `run_family_inventory.py`, `benchmark_screen.py` | Вспомогательные гейты |
| 16 | Native runtime | OV `expert_weight_provider*`, residency/placement V2, execution guard | Consume packs at serve (не offline seal) |

---

## 6. Seal — функциональные требования (кратко)

Детали алгоритма — § ниже; суть:

1. **Single-pass** на pack: structural + sha256 + materialize в одном чтении (copy path).
2. Default materialize=`copy`, fsync=`dir`, post-seal-verify=`fast`.
3. Hardlink только с `--materialize=hardlink` + policy flag.
4. `verify --mode=full` = сегодняшний полный аудит.
5. Цели perf: copy ≤8 мин; hardlink ≤30 с на 15.6 GiB/40 (must) — с workers.
6. **Progress + workers + structured log + metrics** (§6.4–6.7) — must.
7. Receipt/metrics рядом с generation root, не внутри identity dir.

### 6.1 Алгоритм seal (target)

```
queue packs (stable order for logs; manifest still sorted by pack_layer_key)
workers (N) each:
  stream once → inspect/structural as needed + sha256 + materialize
  emit progress event
barrier → build manifest → generation_sha256
write manifest; post-seal verify (fast default; may use workers for full)
rename .generation-* → generation-<digest>
write active.v2.json + metrics receipt
```

Запрет по умолчанию: 3–4 независимых full-file прохода + `fsync` на каждый файл.

### 6.2 Hardlink policies

| `--hardlink-policy` | Поведение |
|---------------------|-----------|
| `require-readonly` | writable source → fail |
| `chmod-readonly` | снять write, затем link |
| `allow-shared` | ok + warning + receipt |

### 6.3 Verify modes

| Mode | Когда |
|------|--------|
| `fast` | default **после** seal |
| `full` | default явного `verify`; release gate |
| `none` | только dev; не в release scripts |

### 6.4 Прогрессбары (must)

Оператор и агент сейчас **не видят**, на каком pack застрял seal (baseline: час молчания). Это дефект UX/ops.

| `--progress` | Поведение |
|--------------|-----------|
| `auto` (default) | Если stderr isatty → `tty`; иначе `jsonl` на stderr (агенты/CI) |
| `tty` | Однострочный/многострочный бар: `seal 12/40 packs \| 4.2/15.6 GiB \| 180 MB/s \| ETA 1m20s \| workers=8` |
| `jsonl` | По одной JSON-строке на событие в stderr (не смешивать с финальным JSON **stdout**) |
| `off` | Тихо; только финальный stdout JSON + files |

**Правила:**

- **Stdout** = только финальный machine JSON (как сейчас) — агенты парсят одну строку/один объект.
- **Stderr** = progress + human logs.
- Обновление не чаще ~10 Hz; обязательно событие на **каждый завершённый pack** и каждые ~64 MiB внутри крупного pack (если stream позволяет).
- ETA = по `bytes_done/bytes_total` (предсказуемо), не по wall/pack count alone (packs почти равны, но byte-ETA точнее при stragglers).
- При `workers>1` бар показывает aggregate + optionally `in_flight` count; не флудить побайтно с каждого worker без throttle.
- Windows: не ломать cp1251/UTF-8 консоль; ASCII fallback (`#`/`-`) если Unicode box drawing глючит.
- `verify` — тот же механизм (`verify 8/40 …`).

**JSONL event schema (минимум):**

```json
{"ts":"...Z","event":"pack_done","op":"seal","pack":"otd-….pack","i":12,"n":40,
 "bytes_done":4509715660,"bytes_total":16735400640,"rate_bps":188743680,
 "eta_s":64,"workers":8,"phase":"materialize"}
```

Фазы: `materialize` | `post_seal_verify` | `verify`.

### 6.5 Многопоточность (must)

Baseline seal = **1 поток**. Packs независимы → параллелить **по файлам**, не резать один pack на куски (проще корректность SHA/inspect).

| Параметр | Default | Смысл |
|----------|---------|--------|
| `--workers N` | `min(8, os.cpu_count() or 4)` | Число worker’ов для pack jobs |
| `N=1` | — | Полностью serial (отладка / диск еле живой) |

**Модель:**

- Thread pool **или** process pool: рекомендация **threads** для I/O+hashlib (GIL отпускается в OpenSSL `hashlib`); если на практике SHA упирается в GIL — `ProcessPoolExecutor` как fallback за тем же флагом (деталь реализации).
- Один pack = одна задача: open → single-pass → close → результат `(entry, error)`.
- Запись в shared temp dir: **уникальные имена файлов** (уже `otd-<key>.pack`) → без lock на write path; lock только на shared counters/progress.
- Manifest / rename / `active.v2.json` — **только main thread** после barrier.
- Ошибка в любом worker → cancel outstanding (best-effort), cleanup temp, exit 2, в log `event=error` с pack id.
- Hardlink mode: тоже параллелится (link+hash source); chmod-readonly policy — сначала serial policy pass, потом parallel link.
- Post-seal `full` verify и CLI `verify --mode=full` — **те же workers**.
- Не параллелить через разные volumes без отдельного ТЗ; same-volume NTFS ok.
- Disk saturation: если `rate` падает при N=8 vs N=4, MANUAL советует снизить `--workers` (SSD/antivirus). Целевой default 8 — empirically ok на NVMe; не hardcode «чем больше тем лучше».

**Инварианты параллельности:**

- Итог `generation_sha256` / набор digests **бит-идентичен** serial при тех же inputs (порядок в manifest по `pack_layer_key`, не по finish time).
- Никаких partial packs в финальном `generation-*`.

### 6.6 Логирование (must)

| Канал | Содержание |
|-------|------------|
| stderr (human) | Краткий start line: op, n packs, bytes_total, workers, materialize, verify mode |
| stderr JSONL / `--log-file` | События: `start`, `pack_start`, `pack_done`, `pack_error`, `phase`, `done`, `reject` |
| stdout | Финальный результат (без progress spam) |

**Требования к log-file:**

- Append JSONL, UTF-8.
- Каждый event: `ts` (UTC ISO), `event`, `op`, `run_id` (uuid4 на запуск).
- Ошибки: `error` string + `pack` + необязательный `exc_type`; без секретов/абсолютных путей модели если не нужны (pack paths ok — уже local build).
- `--log-file` по умолчанию **выкл**; для агентов рекомендовать в MANUAL:  
  `--progress jsonl --log-file …\seal.jsonl`.
- Не писать log внутрь `generation-*`.

### 6.7 Метрики (must)

Писать **один** JSON metrics document в конце (success или fail):

- Default path: `output-root/receipts/seal-<run_id>.json` (или `verify-<run_id>.json`).
- Override: `--metrics-file PATH`.
- **Не** входит в generation identity / inventory.

**Обязательные поля:**

```json
{
  "schema": "cib2.packv2_seal_metrics.v1",
  "run_id": "…",
  "op": "seal",
  "status": "OK|REJECTED",
  "wall_s": 0,
  "cpu_s": 0,
  "workers": 8,
  "workers_used_max": 8,
  "materialize": "copy",
  "hardlink_policy": null,
  "fsync_policy": "dir",
  "post_seal_verify": "fast",
  "pack_count": 40,
  "bytes_total": 0,
  "bytes_read": 0,
  "bytes_written": 0,
  "packs_ok": 40,
  "packs_failed": 0,
  "phase_timings_s": {"materialize": 0, "post_seal_verify": 0, "rename": 0},
  "rate_bps_avg": 0,
  "rate_bps_peak": 0,
  "eta_last_s": 0,
  "generation": "generation-…|null",
  "generation_sha256": "…|null",
  "progress_mode": "tty|jsonl|off",
  "host": {"python": "…", "platform": "win32", "cpu_count": 0}
}
```

Агрегаты доступны агенту без парсинга барa. При reject — тот же файл со `status=REJECTED` и `error`.

Рекомендация later для pack-verify / pack-build launchers: **тот же** schema family (`cib2.packv2_*_metrics.v1`) и JSONL events — единообразие для оркестратора.

---

## 7. Рекомендации по соседним звеньям (планирование, не код)

### 7.1 Mapper — `family_map.py` (MAP-02)

**Сейчас:** read-only inventory; тяжёлый XML/BIN accounting; не на критическом пути seal.

**Рекомендации later:**

- Кэшировать inventory по hash дерева модели (`source_lock`), не пересканировать без изменения IR.
- Явно разделить «inventory JSON» и «eligibility for pack-build» (сейчас легко перепутать статусы).
- Для агентов: один канонический output path + schema version в MANUAL.
- Не тащить family_map внутрь seal.

### 7.2 Mapper/layout — `pack_layout.py` + `plans`

**Сейчас:** детерминированный placement; identity fallback; `plans` пишет sidecars.

**Рекомендации later:**

- Path A smoke (identity plans from packs) vs live-trace PGP — **разные** entrypoints в MANUAL, чтобы агент не мешал `runtime_acceptance`.
- `make-identity-plans-from-packs.py` перенести/выравнять в `scripts/cib2/` (сейчас private build-root), тот же CLI shape.
- Не пересчитывать layout при seal; seal только читает plans.
- Стратегии layout: документировать cost model; запретить silent change seed/strategy без смены plan digest.

### 7.3 Паковальщик — OVMS `--build_moe_experts_pack` + GPU codec

**Сейчас:** единственный writer OTDPACK1; ~15.6 GiB; attribution DLL обязателен.

**Рекомендации later:**

- После pack-build сразу `chmod`/read-only на `otd-*.pack`, чтобы hardlink-seal был безопасен без `allow-shared`.
- Писать per-pack sidecar digest во время encode (hash-while-pack), чтобы seal/verify-all не читали payload лишний раз с нуля — **самый большой** выигрыш после самого seal.
- Не держать temp packs на том же volume без cleanup policy (disk skill).
- `checkCib2PackBuild` уже считает packs — добавить optional «all packs read-only» в preflight.
- Параллельный pack-build слоёв — отдельное ТЗ (GPU/process safety); не смешивать с seal drop-in.

### 7.4 Pack verify — `verify_pack_v1` / `verify-all-packs`

**Сейчас:** полный payload scan; на 40 packs долго; дублируется seal’ом.

**Рекомендации later:**

- Режимы как у generation verify: `fast` (header/tables/size) vs `full` (payload).
- Seal `fast` **доверяет** недавнему `verify-all-packs full` только если receipt связан (plan_sha / pack list hash) — иначе structural minimum обязателен.
- Не вызывать full inspect трижды (pre-seal + post-copy + verify_generation).

### 7.5 Trace / profile

**Сейчас:** Path A identity ≠ live PGP.

**Рекомендации:** в MANUAL жирно: identity seal не претендует на profile acceptance; отдельный pipeline для trace→profile→plans→pack-build→seal.

### 7.6 Serve launchers (build-root)

После drop-in seal: launchers должны читать `active.v2.json` / `generation-*` без смены путей. Рекомендация: один helper `resolve_active_generation(output_root)` shared.

### 7.7 Диск / cleanup

Связь с `gm-disk-cleanup`: generations и pack-build-smoke — keep while seal/serve; stale `.generation-*` temp — safe nuke; duplicate ov-cache в evidence — не часть seal.

---

## 8. Производительность seal (must)

| Метрика | Цель |
|---------|------|
| copy + post-seal fast, 15.6 GiB/40 | ≤ 8 мин |
| hardlink + post-seal fast | ≤ 30 с |
| Полных чтений payload при seal copy | ≤ ~1.2× |
| `verify --mode=full` | ≤ 1.0× чтения (один проход) |

Receipt: `bytes_read`, `bytes_written`, `materialize`, `wall_s`, `cpu_s`, …

---

## 9. Документация (must при реализации)

Один MANUAL (или раздел ATLAS + `docs/cib2/MANUAL-PACKV2-SEAL.md`):

- Drop-in: старые три команды без сюрпризов.
- Таблица флагов: verify / materialize / hardlink-policy / fsync / **workers / progress / log-file / metrics-file**.
- Прогресс: stdout = JSON результат, stderr = бар/JSONL; примеры для TTY и агента.
- Когда нужен `full` (релиз), когда хватает `fast` (итерации).
- Риски hardlink; как выбрать `--workers` если диск упёрся.
- Карта цепочки §5 (mapper → packer → seal → serve).
- Что **не** делает identity seal.

Help CLI = краткая копия таблицы флагов.

---

## 10. Тесты (при реализации later)

- Существующие `test_packv2_pipeline.py` — PASS на drop-in вызовах без новых kwargs.
- Read-counter / single-pass.
- Hardlink policies T4a/b/c.
- Corrupt mid-file → no published generation.
- Idempotent re-seal.
- JSON stdout keys additive-only.
- Workers: `N=4` vs `N=1` same digests/manifest; error in one pack fails run cleanly.
- Progress: `jsonl` emits `pack_done` with monotonic `bytes_done`; stdout remains single final JSON.
- Metrics file written on OK and REJECTED; schema fields present.

---

## 11. Этапы внедрения (когда скажешь «делай»)

| Этап | Что | Ломает агента? |
|------|-----|----------------|
| P0 | Этот документ + review | нет |
| P1 | Реализовать fast seal **внутри** `seal_generation`; defaults drop-in | нет (быстрее) |
| P2 | Флаги + MANUAL | нет |
| P3 | hardlink policies | нет (opt-in) |
| P4 | Perf evidence на cohort; ATLAS update | нет |
| P5 (отдельно) | hash-while-pack в паковальщике; verify-all modes; identity plans в scripts/cib2 | отдельные PR |

**Сейчас останавливаемся на P0.**

---

## 12. Подход

| Вариант | Вердикт |
|---------|---------|
| A. Algorithm fix, same module, drop-in CLI | **выбран** |
| B. Только CopyFile2 | недостаточно |
| C. Rust/C++ rewrite | out of scope |
| D. `--legacy-seal` dual path | **отклонён** — незаметная замена |

---

## 13. Открытых решений по seal — нет

Все три развилки закрыты (§0). Дальнейшие уточнения — только когда начнётся реализация соседних звеньев (P5).

---

## 14. Ссылки

- `scripts/cib2/packv2_pipeline.py`, `pack_layout.py`, `family_map.py`, `verify_pack_v1.py`, `trace_profile.py`
- Build-root: `make-identity-plans-from-packs.py`, `verify-all-packs.py`, `launch-pack-build-smoke.py`, `launch-pack-serve-*.py`
- Native: OVMS `--build_moe_experts_pack`; OV `moe_otd_pack` / providers
- `docs/cib2/ATLAS-PACKV2-NATIVE-20261024.md`
- Disk: `gm-disk-cleanup` skill
