# Corrective Gemma4 Live Acceptance (2026.5 freeze binary)

Retest of scouting profiles `00 / 20 / 21` on the EXACT packaged Gemmamonster 2026.5
binary (`dist/windows/ovms/ovms.exe`, SHA `3DFC…44F65FE`), plus the full semantic /
tool / streaming / multi-turn gate and a live agentic dogfood loop on the winner.

- `environment.txt` — branch/HEAD, GPU, model, endpoint, MTP status.
- `binary-provenance.txt` — SHA, versions, loaded-DLL paths, `MIXED_OLD_RUNTIME: NO`.
- `commands.txt` — every server/test command.
- `results.csv` — per-run measurements (measured runs only; warmups excluded).
- `results-summary.json` — mean/min/max/stddev per profile×workload.
- `runs-<profile>.json` — full per-profile rows incl. WS/GPU snapshots.
- `requests/` `responses/` `streams/` — raw evidence (sanitized, model-generated text only).
- `logs/` — server logs per profile. `-attempt1-died0432.log` preserves the
  unattributed morning server death. `dogfood-transcript.txt` is the agent loop log.
- `semantic-verdicts.txt` — per-gate PASS/FAIL.
- `launch-*.bat` — exact server launchers (foreground-safe, `>>` log append).
- `bench-2026.5.ps1`, `control-short.ps1`, `prefix-test.ps1`, `semantic-gate.ps1`, `dogfood.ps1` — harnesses.

## Result (see FINAL verdict message for the full table)

- Profiles measured fresh on 2026.5; scouting 2026.4 numbers NOT reused.
- `20 ~= 21` on medium/long; short converges to ~26.5 after control → **winner: 20** (simpler).
- Repeated-prefix: turn1 TTFT 26.0s → turn2 2.8s → turn3 1.7s (prefix cache works).
- Semantic gate 14/14 PASS (phantom probe: text-only, `tool_calls: []`, no executable call).
- Dogfood: 4 turns / 3 tool calls / 0 errors, grounded summary.
- MTP: `SKIPPED_NO_ASSISTANT_IR`.
- Max measured throughput 27.46 tok/s (short); no `>30 tok/s` claim made.

## Integrity notes (read before citing numbers)

1. `results.csv` initially contained a FOREIGN batch (02:48–02:49Z: re-run of profile 00
   incl. 3 failed long rows, `tok_s=0`) — purged; kept rows verified as this session's.
2. Morning window 04:36–05:09 local shows unattributed parallel server activity
   (`ovms-22-*.log`, `ovms-20u4b4096seq4-longonly.log`, second AVAILABLE appended into
   profile logs) — foreign files preserved untouched, not cited.
3. Profile-20 attempt-1 death (04:32:17 local, silent, no dump/OS event) is unattributed;
   afternoon session (10:56Z+) ran 60+ requests with zero failures on PID 16804.
4. Streaming TTFT ≈ wall on this runtime (chunks burst after full generation);
   `tpot_ms` column is therefore an artifact — use `tok_s` = output/wall.
