# Agent handoff: leakage live-progon + turn-04 deep-dive (2026-09-14)

Product: `908d669563f57535ab4eb747989e9ab33dfd5267`, binary
`C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914\ovms\ovms.exe`
SHA256 `11d74fd958d1cd2570682fa13562c1bfcf0973dabbf79a0378a8d0cdc886a4fb`.
Model: Heretic 26B QB GPU VLM_CB (`C:/llm/models/OpenVINO/Wondernutts/...-heretic-int4-ov`).
No source/parser/generator changes, nothing else committed, binary unsubstituted.
`*.log` files in this dir are force-added (`*.log` is repo-ignored) — they are the
TRACE evidence, do not delete.

## Verdicts (read these two files first)

- `FINAL-VERDICT.md` — leakage progon: **E. NOT_REPRODUCED**. Clean RC2 never emits
  `<call:...>` (echo/Exa auto+required+named/contaminated probes all canonical).
- `deep-dive/DEEP-DIVE-REPORT.md` — turn-04 empty-length failure: signature
  `LENGTH_WITH_EMPTY_OUTPUT`, mechanism **UNDETERMINED (stateful/transient)**,
  explicitly NOT GRAMMAR_THRASH (no raw-token evidence). Bonus finding: unguided
  model natively emits bare `call:echo{...}` text (variants A/B) — it is the
  special-stripped form of the canonical frame, not `<call:...>`.

## Layout

- `before-restart.*` / `after-restart.*` — PID/exe/cmdline/SHA/models/parsers/modules.
- `server-fresh/` — standard graph+config+launch cmds, full TRACE/DEBUG stdout.
- `test-4-echo-auto/ test-5-real-exa-auto/ test-6-minimal-exa-auto/
  test-7a-real-exa-required/ test-7b-real-exa-named/ test-8-contaminated-exa-auto/`
  — each: `request.json`, `tools.json` (where applicable), `response.raw.json`,
  `summary.json`, `server-window.log`, `server-guided-lines.txt`.
- `sweep-long-context/` — 32-step echo sweep, stopped at iter 4 (B+E), plus
  `turn-04-retry-256/`, `turn-04-budget-1024/`, `turn-04-stream-probe/`,
  `CLASSIFICATION.md`, `sweep-summary.json`, `sweep-table.txt`.
- `deep-dive/` — TRACE side-by-side (`turn-03-trace/`, `turn-04-trace/` with
  `parsechunks-parsed.txt`: phase + token IDs per chunk), `repro-warm/`,
  `repro-full/` (failure NOT reproduced), `variants-ABCD/`,
  `noreason-graph/` (`reasoning_parser:"none"` config-only variant, worked identically),
  `noreason-turn-04/`, `decode.py` (needs `pip install tokenizers`).
- `run-*.ps1`, `parse-chunks.ps1`, `mk-req5.ps1`, `wrap5.ps1` — exact repro drivers
  (pwsh; REST 18091; temperature 0).

## Open questions for next agents

1. turn-04 failure needs its original instance state (prefix-cache/executor); faithful
   history replay does not re-trigger it. Repro may require long mixed-load soak.
2. Step 9 of the leakage progon (real external orchestrator) was NOT_RUN — no harness
   in this env. Do not present raw-OVMS cleanliness as harness cleanliness.
3. Sweep checkpoints 8/16/24/32 never reached (stopped at first reproducible point).
4. Do NOT add `<call:...>` recovery to the parser on the basis of this probe —
   that dialect remains NOT_REPRODUCED on clean RC2.

## Operational notes

- Keep exactly ONE ovms.exe at a time on this host (two 26B VLM_CB loads risk OOM).
  Detached launch: `Invoke-CimMethod Win32_Process Create` (survives tool timeouts);
  verify with `tasklist /FI "IMAGENAME eq ovms.exe"` + `/v3/models`.
- Live instance at handoff: standard TRACE config, REST 18091 / gRPC 18092.
