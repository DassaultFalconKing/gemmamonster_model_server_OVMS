# Dependency bisection plan: whitespace fix vs GPU OOM (2026-09-14)

## Pinned revisions (resolved, read-only)

- OVMS RC2 product: `908d6695`; WS-fix product: `17064400` (local branch only, see §5)
- GenAI base: `7ea2546852a382cd16bd22dea0cfad2db70ed744` (both)
- XGrammar stock (known-good): `v0.1.31`
- XGrammar A (first `max_whitespace_cnt`): `dbc7f1968ebc744a3d4d89d23bf181fd67630a8d`
  (2025-09-06, PR #414, +241/-41: grammar.cc, grammar_compiler.cc,
  json_schema_converter.{cc,h}, bindings; nothing structural-tag/FSM related)
- XGrammar B (bleeding-edge in failing candidate): `9aa840b6d16abf094f3e8e2ac9c10465b77656c9`
  (~1yr later: structural tags, FSM sparsity, dedup, new formats)
- XGrammar source: `C:\g54r2\openvino_genai_build\_deps\xgrammar-src` (has full history)

## Build matrix (builder: one row at a time, same OVMS GenAI-branch pins otherwise)

| # | OVMS source | GenAI base | XGrammar | whitespace cap | expected role |
|---|---|---|---|---|---|
| 1 | RC2 908d6695 | stock 7ea25468 | v0.1.31 | none | stable control (already have binary 11d74fd9) |
| 2 | WS 17064400 | stock 7ea25468 | v0.1.31 | cap N/A (no API) | source-control: does WS OVMS code alone OOM? |
| 3 | WS 17064400 | rebuilt 7ea25468 | **A dbc7f19** | yes (minimal backport) | TARGET if green |
| 4 | WS 17064400 | rebuilt 7ea25468 | **B 9aa840b** | yes | current failing (have binary AF921BB2) |
| 5 | WS 17064400 | rebuilt 7ea25468 | newer HEAD | yes | only if 3==4 (both fail) |

Key pair: row 3 vs row 4 — same WS source, same GenAI base, same everything
except XGrammar A vs B.
- A lives, B dies → drop the delta, ship minimal backport (no GPU debugging).
- Both die → suspect is new-XGrammar structural implementation in general or
  GenAI's bounded-schema API integration, not the whitespace cap.

## Killer A/B on one rebuilt DLL (ALREADY RUN on AF921BB2, PID 16656)

Same binary, same session, in order:
1. no tools → `stop`, "15" — GenAI generic path EXONERATED.
2. tools + `tool_choice=none` (grammar OFF) → `stop`, normal text — tool
   prompt/template path EXONERATED.
3. same tools + `auto` (grammar ON) → canonical `tool_calls` — single grammar
   request does NOT OOM.
4. 60× identical grammar soak → 60/60 canonical, process RSS flat 15837 MB.

So: no instant grammar OOM; no per-request RSS growth on homogeneous load.
The OOM needs heterogeneous accumulation (70 mixed requests preceded the first
death) and/or a crash-poisoned shared pool. Single-shot killer A/B CONVICTS
nothing by itself — the soak leg is mandatory per matrix row.

## Per-row test protocol (acceptance gate, one instance at a time)

1. Reboot baseline (GPU shared-pool state is a confounder; 3 crash-poisonings seen).
2. Short probes 6/6 canonical; t0 sweep 32/32; t1 sweep 32/32.
3. Killer A/B (1/2/3) + 60× homogeneous grammar soak with RSS sampling.
4. Verdict row GREEN only if all pass AND no CL_OUT_OF_RESOURCES.

## Administrative snag (blocks source review, not evidence review)

- Product branch `fix/gemma4-whitespace-loop-20260914` (= `17064400`) exists ONLY
  locally in `C:\git\gemmamonster-2026.4-unified-20260911` (clean).
  Remote `ls-remote` shows NO such branch and NO `17064400` object.
- Synced remote HAS evidence `4c63f9fbf` (docs/rc2-acceptance-20260914) — reviewed OK.
- To unblock: `git -C C:\git\gemmamonster-2026.4-unified-20260911 push origin fix/gemma4-whitespace-loop-20260914`
  (product-code push; deliberately NOT executed from this session).
