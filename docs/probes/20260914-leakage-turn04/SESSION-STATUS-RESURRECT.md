# SESSION STATUS — reboot resurrection point (2026-09-14 ~20:10 UTC+? local)

Machine reboots now. Everything below is on disk and (after this commit) in
remote `docs/rc2-acceptance-20260914`. Resume: read this file, take GPU baseline
numbers from the user, relaunch ONE instance, continue with XGrammar-A acceptance.

## What dies with the reboot

- Live instance: candidate `17064400` ovms.exe PID 16656 (REST 18091 / gRPC 18092,
  TRACE, standard VLM_CB Heretic graph) — served plain/agentic fine, ~15 requests.
- This agent session (re-enters fresh; all context is in this file + linked docs).

## Git state (all pushed after this commit)

- Evidence branch `docs/rc2-acceptance-20260914` @ remote (this file included).
- Product branch `fix/gemma4-whitespace-loop-20260914` = `17064400` pushed, reviewable.
- `src/` untouched everywhere by this session. No product commits by this session.

## Key SHAs (do not re-derive)

- RC2 product `908d6695`, binary `11d74fd9`; known-good `9a162626`, binary `E7D8024F`
- WS-fix product `17064400`, binary `AF921BB2` (ovms.exe), rebuilt genai `cac5bb7e`
- Runtime DLLs identical everywhere: OV `def53dd3`, tok `ef29a1d5`, tbb `60e4501c`
- GenAI base `7ea25468`; XGrammar stock `v0.1.31=aa44ded2`; A `dbc7f19`; B `9aa840b6`
- Model: Heretic dir (re-exported 09-12, unchanged since); graph VLM_CB GPU 256.

## Settled verdicts (evidence in docs/probes/20260914-leakage-turn04/)

1. `<call:...>` leakage on clean RC2: NOT_REPRODUCED (FINAL-VERDICT.md).
2. turn-04 LENGTH+empty: whitespace-stutter loop after `<|tool_call>call:echo{`
   (server full-decode proof), xgrammar JSON-whitespace hole, silent parser drop
   at LENGTH (WHITESPACE-LOOP-FINDING.md). NOT grammar-thrash, NOT schema failure.
3. 374-vs-371: ChatTemplateAdapter JSON→object conversion, no anomaly (CODE-DELTA-AUDIT.md).
4. Code audit 9a162626→908d6695: src/llm ZERO diff, deps identical (CODE-DELTA-AUDIT.md).
5. Candidate functional: PASS (short 6/6, sweeps 32/32+32/32, agentic A/B/C grounded).
6. Candidate stability: FAIL/BLOCKER — repeatable GPU CL_OUT_OF_RESOURCES deaths on
   grammar path (after ~70 mixed reqs; fresh instances died on 1st grammar inference
   in poisoned-pool state). Plain no-tools always fine. RC2 never logged a GPU error.
7. Killer A/B + 60× homogeneous soak: single grammar req fine, RSS flat → death needs
   heterogeneous accumulation and/or crash-poisoned pool (BISECTION-PLAN.md).
8. Agreed: keep WS fix (loop gone, max_whitespace_cnt needed); target = minimal
   XGrammar (v0.1.31 first, dbc7f19 second); B rejected unless A also fails.

## Evidence map

- Repo: docs/probes/20260914-leakage-turn04/ (FINAL-VERDICT, DEEP-DIVE-REPORT,
  CLASSIFICATION, CODE-DELTA-AUDIT, WHITESPACE-LOOP-FINDING, WS-FIX-ACCEPTANCE,
  BISECTION-PLAN, RENDERER-NOTES, AGENT-HANDOFF, wsfix-acceptance/ with all runs).
- Disk only: C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914\
  and ...\wsfix-acceptance-20260914\ (run-hetero-accept.ps1 HERE — copy into repo
  before/after A-build acceptance; currently syntax-clean, NOT yet run).
- Binaries: RC2 C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914\ovms\ ;
  candidate C:\gemmamonster-artifacts\candidates\2026.4\17064400-…\ovms\ (manifest.json).
- Build script for row 3: unified-checkout scripts/gemmamonster/build-whitespace-genai.ps1
  (pin $xgrammarSha to v0.1.31/A; xgrammar-subproject-install.patch may need hand-adapt
  on old CMake; rebuild ovms.exe too — JSONSchema ABI grew).

## Post-reboot checklist

1. Get from user: FreePhysicalMemory, dxdiag shared/display memory + driver version.
   Expect: Free ~25+/33 GB; compare shared-pool vs pre-reboot choked state.
2. Launch ONE instance of the binary under acceptance (A-build when ready; until
   then nothing to launch — do NOT soak the old candidate further without need).
   Standard config: VLM_CB Heretic graph, REST 18091, TRACE initially.
   (Detached launch that survives tool timeouts:
   `Invoke-CimMethod Win32_Process Create` with
   `cmd.exe /d /c "cd /d <runtime> && call setupvars.bat && ovms.exe --config_path <cfg> --rest_port 18091 --port 18092 --log_level TRACE >> <log> 2>&1"`,
   cwd=runtime. Verify: tasklist exactly 1 ovms.exe + /v3/models shows gemma4.)
3. Smoke: echo auto (expect tool_calls, ~21 tok). Then run-hetero-accept.ps1
   (params: -RestBase http://127.0.0.1:18091 -OutDir <fresh dir>).
4. PASS bar for row 3: ~130 mixed served, no CL_OUT_OF_RESOURCES, soft anomalies counted.
5. If row 3 green → pin v0.1.31, reject B, dependency repair done. If red → suspect
   GenAI structured-output lifetime (grammar objects / compiled-schema cache /
   logits-mask buffers under heterogeneous load), profile allocation boundary.
