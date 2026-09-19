# Verbose report — C5fixed working state (2026-09-19)

Commit: `8c6f8b00912e8baa24fb1566a843b031584f1eaa`
(`fix/gemma4-agentic-transition-recovery-c5-20260918`)
Binary: exe `56AD64A0` + `ovms_mediapipe_runtime_shared.dll` `DD3B5D28`
(fix strings verified inside; exe untouched — handler lives in the shared lib).
Server: `C:\llm\ovms-C5fixed\ovms.exe`, model `gemma4`
(`gemma4-26-heretic-google-current`), `:18091`, live and serving.

## What the commit contains (both fixes)

1. `5fa8b4c4e` — mid-thought transition: `toolStartTerminatesReasoning` (Gemma4
   opt-in), REASONING→TOOL handoff on earliest structural boundary, incomplete-opener
   holdback. Thought → tool call works without mandatory `<channel|>`.
2. `8c6f8b00` — `normalizeToolCallArgumentsForTemplate()` in
   `src/llm/apis/openai_api_handler.cpp` (+57, single file): replayed STRING args →
   OBJECT on the template-bound `ChatHistory` copy only (Gemma4-gated); malformed
   input → clear `INVALID_ARGUMENT` before graph execution. Public contract unchanged
   (responses still return arguments as STRING — verified live).

## Proven live on this binary

- Exact 2×2 second-turn replay: 4× HTTP200 `stop` (pre-fix: 2× 400 mapping error).
- Public contract: `calculator{"expression":"17 * 23"}` as string.
- Agent loop T1→T2→T3 (calc, weather-after-replay, summary): GREEN, no leaks/dupes.
- Negatives (`{bad json`, `[1,2]`, `42`, `true`): all HTTP400 with exact parse position.
- Dogfood session 03: 81 steps / 69 tools, G2 pack complete and sane, zero spam/length
  failures, zero raw channel-marker leaks.
- MEDIAPIPE_TEMPLATE_ERRORS=0 post-fix.

## Context sizes — honest ledger (NOT 64K)

Proven healthy: 5232-token gate (tool_calls), ~16K prefix probes (text, `stop`),
~32K sustained live (current dogfood session, cache ~2.1GB of 4.2GB pool).
32K bench previously ran at ~19 tok/s but underOOM-scarred host (marked DEGRADED).
**64K single-request context is NOT proven by any artifact on record.**
Claiming 64K requires a dedicated probe (single 64K prompt + completion + usage
capture); until then the proven ceiling is 32K.

## Host load — the server breathes, the machine sweats

- RAM Available ~3.9 GB (dogfood + build residue), commit 43/127 GB — OK but tight.
- OVMS working set paged down to ~0.8 GB against 21.4 GB committed — the OS is
  paging the server; responses still flow, latency under pressure not measured.
- Disk hit 235 MB free twice (npm cache 7.4 GB cleared; orphan Bazel bases ~40 GB
  cleared). Currently ~6 GB free. Pagefile cannot grow into a full disk — this is
  the actual stability risk, not the model.
- Recommendation: freeze non-essential processes during long-context runs, keep
  ≥10 GB disk headroom, re-prove any >32K claim on a clean host.

Verdict: commit `8c6f8b00` is the working state for agentic tool use up to 32K.
64K and pressure-latency remain open probes, not established facts.
