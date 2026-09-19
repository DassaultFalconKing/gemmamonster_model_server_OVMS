# Live verification report — C5fixed history-normalization (2026-09-19)

Server: `C:\llm\ovms-C5fixed\ovms.exe` (PID 2156), model `gemma4`
(`C:/llm/models/runtime/gemma4-26-heretic-google-current`), `:18091` + `:9000`.
Binary identity: exe `56AD64A0` (unchanged) + `ovms_mediapipe_runtime_shared.dll`
`DD3B5D28` (rebuilt from `8c6f8b00`, fix strings verified inside).
Launch note: dist embed python lacks stdlib — server runs with
`PYTHONHOME=C:\opt\Python312` (env-only, zero file mutation).

## Mid-thought tool call status (as requested)

Shipped fix `5fa8b4c4` (toolStartTerminatesReasoning, Gemma4 opt-in, REASONING->TOOL
handoff, earliest-boundary priority, incomplete-opener holdback) is PROVEN live on
this server (it carries both fixes of HEAD `8c6f8b00`):
- thinking + tool_calls together: reasoning 98ch + `calculator` call, `finish=tool_calls`
- agent loop T1 (calc) -> replay -> T2 (weather) -> replay -> T3 summary: all GREEN,
  final text factually correct, no leaks/duplicates/fabrication
- Newer mid-thought line (`a9ae04188`/`e50ab9856` + WIP): NOT built/run by this track;
  foreign branch + worktree restored byte-exact after an accidental rebase
  (forensics: stash object `dade88e8`; remotes never touched).

## History-normalization gate (this session)

- Exact 2x2 second-turn replay (reasoning_content + call + result present):
  SS/OS/SO/OO = 4x HTTP200 `stop`. Pre-fix baseline was 2x400 (both STRING-args cells).
- Public contract: generated calls still return `arguments` as STRING
  (`calculator{"expression":"17 * 23"}`).
- Negative args (`{bad json`, `[1,2]`, `42`, `true`): all HTTP400 INVALID_ARGUMENT
  with exact parse position; no deep Mediapipe/template crash.
- MEDIAPIPE_TEMPLATE_ERRORS=0 post-fix.

## Repro for live check

```powershell
# 2x2 (needs reasoning_content + tool_calls[id c0] + tool result in history, max_tokens 64):
# SS: arguments '{"x":1}' (string), content '{"value":2}' (string) -> expect 200
# SO: arguments string, content OBJECT -> expect 200
# OS/OO: arguments OBJECT -> expect 200
# Negative: arguments "{bad json" -> expect 400 with parse position
# Agent loop: calc 17*23 -> feed result 391 -> ask weather Boston -> feed sunny,21C -> summarize
```

VERDICT=C5FIXED_HISTORY_PASS (build + live). Handoff:
`docs/gemmamonster/upstream-fix-20260917/handoffs/C5fixed-history-normalization.md`.
