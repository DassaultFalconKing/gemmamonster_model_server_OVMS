# Worklog Session

SESSION_ID: 2026-09-13-stress-crash-root-cause
AGENT: opencode (Muse Spark root-cause session)
DATE: 2026-09-13
TASK: ROOT-CAUSE the 0xC0000005 crash in ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference. No fix before crash evidence. No src/llm/** touches.
BRANCH: integration/gemmamonster-rc2-semantic-refit-20260912
START_HEAD: d29972f65f4855f795ed529517fad30c4282401e
END_HEAD: TBD

## Input authorities

- Task prompt: ROOT-CAUSE SESSION (7 steps, evidence before fix).
- agent-worklog/sessions/2026-09-12-b-parity-build-session.md (build PASS, negative CLI closed via env var, crash open).
- Maintainer gate: tests/windows/gemmamonster_rc2_ovms_test_gate.ps1 (a3957461/7fcb024f).
- Constraints: negative-CLI failures CLOSED, package forbidden until GREEN, no new Windows exclusions without upstream proof.

## Hypotheses (all UNPROVEN at start)

- H1: test-harness callback lifetime race (signal.set_value before response fully consumed).
- H2: production lifetime race on model unload during async inference (guards).
- H3: upstream idle-servable-management delta (07e8aac8d) changed lifetime/locking.
- H4: environmental/flaky (resource exhaustion, thread timing).

## Actions

- Verified START_HEAD=d29972f65f4855f795ed529517fad30c4282401e; worktree has only build-stamp `M src/version.hpp`.
- §1 reproduction: isolated `ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference` 5/5 PASS (~360ms each) — crash needs full-suite context. Full suite crashed 3/3 (build session, maintainer gate, this session under procdump).
- §2 dump: no admin (msi\sheoldred, non-elevated; HKLM WER denied), no cdb/windbg. Downloaded Sysinternals procdump.exe (1.37MB) + installed WinDbg via winget (GUI-only WinDbgX, headless hangs — killed). Parsed 735MB full dump (`dumps/ovms_test.exe_260913_012227.dmp`) with hand-written dbghelp/Minidump PowerShell parser (PS blocks `[ulong]`, used `[uint64]`; corrected MINIDUMP_EXCEPTION_STREAM offsets empirically).
- Crash test confirmed in-dump-run: `ConfigChangeStressTestAsync.ChangeToEmptyConfigAsyncInference` (4th full-suite crash overall).

## Tests and gates

| Run / gate | Result | Evidence |
|---|---|---|
| isolated crash-test runs 1..5 | 5/5 PASS, exit 0 | crashrep_run1..5.log, ~355-372ms each |
| full suite under procdump | CRASH 0xC0000005, dump captured | ovms_test.exe_260913_012227.dmp, 735091706 B |
| crash dump | PARSED (raw below) | no stacks in thread descriptors (Rva=0 for all 35 threads); stacks recovered via Memory64 ranges |
| callback ordering instrumentation | NOT_RUN | |
| A/B/C/D matrix | NOT_RUN | |

## Findings (dump — raw evidence, not conclusions)

- Exception record (3 dumps, identical shape): code=0xC0000005, NumberParameters=2, info0=8 (EXECUTE violation). Targets: 0xA0 (tid 16016), 0xC8 (tid 21952), 0xA0 (tid 10004). Exception context each time: RIP=target, RBP=0/wild, RAX=1, RCX=RDX=0, RBX=heap, RSI=own stack, RDI=wild. Verdict fragment: worker thread executes a null-ish small-int code pointer (smashed return slot or torn function pointer).
- Victims are always stress WORKER threads mid request-cycle (log: Processing request / retired churn / C-API trace), never the OV callback thread (tid 1760/1924 seen alive inside openvino.dll callback dispatch at capture).
- Crash coincides with unload: `Waiting to unload model: dummy v1. Blocked by: N inferences`, `Model with requested version is retired` churn; dump-3 tail adds `setEnd: dummy-1 (UNLOADING)->END` + `Updating default version` at the crash tick.
- Faulting stack (dump-1, via Memory64): +0x48=0xA0, +0x68=ntdll+0x26B31, +0x98=ovms_test.exe+0x2BBAB0, +0x1B8=+0x2C105B, +0x1C8=msvcp140+0x1626F, +0x1E0=+0x1F7BF20, +0xA0..+0x160=in-progress C-API TRACE log text. No PDBs anywhere (Debug directory EMPTY) so no names.
- H1 status: callback code CONFIRMS the suspicious shape — `signal.set_value(42)` BEFORE `response=response` + `ResponseDelete`, worker deletes request right after `get()` on a stack-local struct reused each iteration (stress_test_utils.hpp:1812-1818, 1853-1873). Cross-thread struct reuse is real; whether it yields RIP=0xA0 on a worker is UNPROVEN — needs §3 markers.
- No src/llm involvement anywhere in this chain (C-API + config + test harness only).

## §4 hypothesis test — H1 REJECTED

- TEMP change (signal moved last, NOT committed, then REVERTED): full suite crashed with byte-identical signature (AV-execute 0xA0, worker tid 10004, RAX=1/RCX=RDX=0). Per task table (both crash => reject): the callback-signal position is IRRELEVANT to this crash. H1 (test-harness callback lifetime race) REJECTED as crash cause.
- Marker ordering (signal-first run): 47 ENTER / 47 BEFORE_SIGNAL / 47 AFTER_SIGNAL / 47 BEFORE_RESP_DELETE / 47 AFTER_RESP_DELETE, 0 re-ENTERs, 0 incomplete lifecycles — no callback died mid-flight; crash hit a worker with no active callback. H1-direct independently disproven.
- Leading open direction: H2 production lifetime race around model unload vs in-flight async requests. Audit note: `OVMS_InferenceAsync` (capi.cpp:1108-1164) holds `ModelInstanceUnloadGuard` only as a sync-scope local (dies at return after queueing); completion runs later. Guard coverage of the completion/unload window is the concrete audit target. H4 (pure environmental) weakened: 4/4 full-suite crashes vs 0/5 isolated + 0/3 family runs = needs process-wide suite state, but deterministic enough to be a real race, not cosmic rays.
- NOT done (handed off): §5 B/C/D matrix isolates, §6 upstream delta incl. 07e8aac8d lifetime/locking audit, §7 fix + 20-run gate. No fix claimed, no exclusion-list change, no package.

## Dump-1 raw detail (kept for the record; dumps 2-3 share the shape)

- Exception record: code=0xC0000005, ExceptionAddress=0xA0, ThreadId=16016, NumberParameters=2, info0=8 (EXECUTE violation), info1=0xA0. Exception context: RIP=0xA0, RSP=0x959E1FECE0, RBP=0, RAX=1, RCX=0, RDX=0, RBX=0x230AEDDBF80(heap), RSI=own-stack, RDI=0x9500000000(wild).
- Last pre-crash lines: `[1924] inference_executor.hpp:173 Entry of ov::InferRequest callback call` then `Exception: C0000005 / Unhandled`, plus concurrent `Waiting to unload model: dummy v1. Blocked by: 8 inferences in progress` and `Model with requested version is retired` churn.
- tid 1924 (OV callback thread) at capture: RIP=openvino.dll+0x43F6B9 (inside OV callback dispatch), alive. tid 3372 (worker): RIP=ovms_test.exe+0x2B5E35.
- No src/llm involvement anywhere in this chain (C-API + config + test harness only).

## Files touched (all UNCOMMITTED, in worktree)

- src/test/stress_test_utils.hpp — RACE_* instrumentation markers ONLY (§3; TEMP §4 change applied, tested, REVERTED). No production change, no src/llm.
- src/version.hpp — build stamp (pre-existing mechanics).
- agent-worklog/sessions/2026-09-13-stress-crash-root-cause.md — this file.
- NOT committed: everything above (per task: no commit until RED/GREEN proven; none proven).

## Tests and gates

| Run / gate | Result | Evidence |
|---|---|---|
| isolated crash-test runs 1..5 | 5/5 PASS, exit 0 | crashrep_run1..5.log, ~355-372ms each |
| ConfigChange* family runs 1..3 | 3/3 PASS (5/5 tests incl. AsyncEmpty) | ccfam_run1..3.log; crash needs wider suite context |
| full suite baseline (pre-instrument) | CRASH 0xC0000005 | ovms_test.exe_260913_012227.dmp, 735091706 B |
| full suite (markers, signal-first) | CRASH 0xC0000005 | ovms_test.exe_260913_013706.dmp, 735116146 B; 47/47 callbacks complete, no re-ENTER, 0 incomplete |
| §4 TEMP signal-at-end, full suite x1 | CRASH 0xC0000005, same signature | ovms_test.exe_260913_014025.dmp, 735091264 B; H1 REJECTED |
| crash dump | PARSED (raw in Findings) | hand dbghelp parser; no PDBs (Debug dir EMPTY); stacks via Memory64 |
| A/B/C/D matrix | PARTIAL | A crashes (full suite 4/4); isolated-single + family clean; B/C/D not run |
| upstream delta (§6) | NOT_DONE | handed off |

## Negative evidence

- No PDBs produced by the B-parity build (Debug directory EMPTY) — stacks are module+offset only; WinDbgX headless unusable (hangs, killed); no admin for WER LocalDumps; no cdb. Analysis done with hand dbghelp parser + procdump.
- Crash does NOT reproduce isolated (0/5) or family-only (0/3) — full-suite process state required.
- No callback died mid-flight in any instrumented run (47/47 complete) — the fault is not an interrupted callback.
- Sync-path sibling (SingleModel.ChangeToEmptyConfigInference) passes in family runs — async+unload combination is implicated, sync path not exonerated (not run under full-suite pressure alone).

## Decisions made

- H1 REJECTED by §4 experiment (signal-at-end still crashes, identical signature). TEMP change reverted, not committed.
- No exclusion-list change (task §7: new crash must not hide next to CVS-176244 without upstream proof).
- No package (tests not green — unchanged from build session).
- RACE markers left dirty-but-uncommitted: binary on disk matches them; next session can proceed immediately to 20-run program or revert in seconds.

## Unresolved

- Exact faulting instruction/function (needs PDB or targeted disasm of ovms_test.exe+0x2BBAB0/+0x2C105B/+0x1F7BF20/+0x2B5472).
- H2 mechanism proof (guard audit of completion/unload window + deterministic repro).
- §5 B/C/D isolates, §6 upstream delta (07e8aac8d), §7 fix + 20-run gate.

## Handoff / next safe actions

1. H2 guard audit: `OVMS_InferenceAsync` (capi.cpp:1108-1164) — ModelInstanceUnloadGuard is sync-scope; verify what pins the instance across async completion vs `startFromFile(empty)` unload. Suspect list from task §2 stacks still unchecked against symbols.
2. If H2 confirmed: earliest ownership violation fix (production), deterministic regression test, sync+async check, then full ovms_test.
3. 20-run gate per task §4/§7 before any fix claim; full GREEN (incl. gate ps1 + full ovms_test.exe) before package.
4. Revert RACE markers before any candidate build (they are timing perturbers, however small); rebuild pristine via official bat.

## Final repository state

HEAD: d29972f65f4855f795ed529517fad30c4282401e (no source commits in this session)
STATUS: `M src/test/stress_test_utils.hpp` (RACE markers only), `M src/version.hpp` (build stamp), `?? agent-worklog/sessions/2026-09-13-stress-crash-root-cause.md`
COMMITS_CREATED: none (worklog commit follows)
DUMPS RETAINED: C:\Users\testc\AppData\Local\Temp\opencode\dumps\ovms_test.exe_260913_01{2227,3706,4025}.dmp (~735MB each)
