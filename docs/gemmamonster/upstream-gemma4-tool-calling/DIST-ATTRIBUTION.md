# Tested distribution attribution

> Внутренний prep-документ. УДАЛИТЬ папку `docs/gemmamonster/upstream-gemma4-tool-calling/`
> из diff перед отправкой upstream PR.

## Дистрибутив

```text
PATH: C:\git\gemma4-upstream-refit-clean-20260915\dist\windows\ovms
```

## К какой ветке/коммиту относится

Workspace `C:\git\gemma4-upstream-refit-clean-20260915`:

```text
REMOTE(origin): https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS.git
REMOTE(upstream): https://github.com/openvinotoolkit/model_server.git
BRANCH: staging/gemma4-upstream-refit-clean-20260915
HEAD:   43bc254e8996f17b929afef79f310d0b0b0cc139
        docs(acceptance): corrective Gemma4 live acceptance on 2026.5 freeze binary
```

Это accepted 2026.5 RC — тот же `RC_SOURCE`, от которого сделан transplant
на ветку `upstream/gemma4-tool-calling` (коммит `7c072087f`).

## Доказательства сборки из этого источника

```text
BUILD LOG:   win_build_freeze_20260915-224711.log ... win_build_freeze_20260915-232545.log
PREBUILD TEST LOG: win_prebuild_tests_20260915-230710.log
  (пример: //src/test/llm/gemma4_generation:gemma4_f10_guard_test PASSED)
PACKAGE LOG: win_package_20260916-001031.log
  PACKAGE_EXIT=0 2026-09-16T00:11:12
  ovms.zip 148,956,499 bytes
```

```text
ovms.exe SHA256: 3DFC2D11E614BD03924E6730AD8053DB00A6E5564F41E11F966A0929B44F65FE
```

Совпадает с accepted `BINARY_SHA256` из promotion provenance
(`3DFC2D11E614BD03924E6730AD8053DB00A6E5564F41E11F966A0929B44F65FE`).
Перепроверено прямым хешированием `dist/windows/ovms/ovms.exe` 2026-09-16.

## Как ветка `upstream/gemma4-tool-calling` строится от него

Проверено побайтово (git blobs, не mtime):

```text
git diff 43bc254e8996f17b929afef79f310d0b0b0cc139 HEAD --stat -- src/
  → 1 файл, 1 удалённая строка:
    src/llm/io_processing/gemma4/gemma4_tool_parser.cpp (удалён blank line at EOF,
    hygiene для git diff --check; семантически null — пустая строка вне деклараций)

Всё остальное в `src/` побайтово равно источнику дистрибутива.

git diff 204d3bf3ba6f8e2aeb489c5eeb7ab46c79fde482 HEAD --stat -- ':!src' ':!docs'
  → пусто: всё остальное == текущий upstream/main,
    кроме prep-папки docs/gemmamonster/upstream-gemma4-tool-calling/
    (удалить перед PR)
```

То есть:

```text
upstream/gemma4-tool-calling
  = upstream/main 204d3bf (всё, кроме src/)
  + src/ из 43bc254 (источник тестированного дистрибутива)
  + prep-docs (удалить перед PR)
```

Юнит-тесты, гонявшиеся в workspace-источнике на этом же `src/`
(`win_prebuild_tests_*.log`, promotion 64/64 на дереве с тем же `src/`),
относятся ровно к тому коду, что лежит в нашей ветке.
Финальный gate всё равно прогоняется на HEAD новой ветки
(`HANDOFF.md`, раздел 5) — эквивалентность выше лишь обосновывает,
почему ожидается GREEN, а не заменяет прогон.
