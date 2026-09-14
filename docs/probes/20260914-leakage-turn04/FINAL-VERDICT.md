# GEMMAMONSTER RC2 leakage live-progon — FINAL VERDICT

Date: 2026-09-14. Product commit: 908d669563f57535ab4eb747989e9ab33dfd5267. No source/parser/generator changes, no recovery added, nothing committed, binary not substituted.

## Binary / process identity

- Binary: C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914\ovms\ovms.exe
- SHA256: 11d74fd958d1cd2570682fa13562c1bfcf0973dabbf79a0378a8d0cdc886a4fb (identical before/after restart)
- Before: PID 14440, cmdline `ovms.exe --config_path ...\rc2-roundtrip-forensics\server-heretic\config.json --rest_port 18091 --port 18092`
- After (fresh): PID 11220, cmdline `ovms.exe --config_path "...\gemmamonster-leakage-20260914\server-fresh\config.json" --rest_port 18091 --port 18092 --log_level DEBUG`
- Model: gemma4 -> C:/llm/models/OpenVINO/Wondernutts/gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov (GPU, VLM_CB, max_num_seqs 256)
- tool_parser=gemma4, reasoning_parser=gemma4 (auto-detected, both runs); session-state store disabled
- Old PID gone, ports 18091/18092 verified free (no LISTENING) before relaunch

## Result table (short-context probes)

| Test                  | Structured validation | tool_calls | finish_reason | literal `<call:` | verdict |
| --------------------- | --------------------- | ---------- | ------------- | ---------------- | ------- |
| simple echo auto      | no failure msgs       | 1 echo     | tool_calls    | no               | PASS canonical |
| real Exa auto         | no failure msgs       | 1 exa      | tool_calls    | no               | PASS canonical |
| minimal Exa auto      | no failure msgs       | 1 exa      | tool_calls    | no               | PASS canonical |
| real Exa required     | no failure msgs       | 1 exa      | tool_calls    | no               | PASS canonical |
| real Exa named        | no failure msgs       | 1 exa      | tool_calls    | no               | PASS canonical |
| contaminated Exa auto | no failure msgs       | 1 exa      | tool_calls    | no               | PASS canonical, no imitation |
| clean agent harness   | NOT_RUN (no orchestrator present in this env) | — | — | — | N/A |

Secondary hypothesis (StructuredOutputConfig validation failure on real Exa schema): NO EVIDENCE. The string `Tool guided generation will not be applied due to JSON schema validation failure` and any xgrammar/structured-output/guided-generation messages are ABSENT from the entire fresh DEBUG log; real-schema auto works canonically.

## Long-context sweep (extra directive, same server, not stopped)

- 3 canonical echo tool turns, then iter=4 (prompt 437 tok): finish=length, 256/1024 completion tokens burned, content="", tool_calls=[], zero SSE deltas; deterministic repro at 256 and 1024 budgets.
- Class: B. GRAMMAR_THRASH (+ E. EMPTY_POST_TOOL_TURN consequence). No A/C/D. Checkpoints 8/16/24/32 not reached (stopped at first reproducible point per protocol).
- Neighbor diff turn-03 -> turn-04: exactly one routine canonical tool exchange appended; no instruction/schema/contamination change.
- Zero `<call:` / bare `call:` in all 12 campaign exchanges.

## Verdict

E. NOT_REPRODUCED — чистая Gemma4 на свежем RC2 сама `<call:...>` не генерирует: ни с простым tool, ни с реальной Exa schema (auto/required/named), ни после текстовой контаминации. Отдельная native находка (не leakage): постинструментальное продолжение срывается в B+E на 4-м turn (437 tok prompt) — генерация сжигает весь бюджет без видимого вывода.

First deviation layer (sweep B+E): model generation layer post-tool-result (observable at OVMS response: length+empty; parser OutputParser init nominal; no guidance/validation diagnostics).

## Evidence root

C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914\
before-restart.{txt,json}, after-restart.{txt,json}, *-models.json, *-modules.txt, *-parser-lines.txt, server-fresh/{config.json,gemma4-graph.pbtxt,launch-cmd.txt,server.stdout.log}, test-4/5/6/7a/7b/8-{...}/{request.json,tools.json,response.raw.json,summary.json,server-window.log,server-guided-lines.txt}, sweep-long-context/{sweep-summary.json,sweep-table.txt,CLASSIFICATION.md,first-deviation.json,turn-NN/...}.
