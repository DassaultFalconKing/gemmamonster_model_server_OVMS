# ORCHESTRATOR EXECUTION ORDER: CIB2 N1–N4 (2026-10-24)

**Status:** RUN LOCALLY. NOT a GPU PASS. This supersedes any handoff that postpones N2–N4 until an undefined later programme.

## Exact source locks

OVMS dev PR #29 `dev/cib2-packv2-source-20261024` at **`b9ef9ce1a01139ae7fca1d13da5eb7514bfd477d`** before this documentation update. Includes Wave-01 PR #27, derived-metric hardening #28, static P1 audit #26, trace profile, CLI build-only, V2 envelopes, native placement/residency policies.

OpenVINO target dev PR #10 `dev/cib2-packv2-ov2026.4-integration-20261024` at **`fbbfaa11d2f944947a5e26d77d5d37bfe3609d75`**, parent **`releases/2026/4` @ `60ba6ff015f8b511e1407678062878c5ca466d08`**. New C++17 slot-lease, UMA and prearm controls with a standalone host test. **No native GPU integration yet.**

OpenVINO 2026.5-derived source DONOR PR #9 `7e9fb22df7c76ed6be4334b8bb22ecb734eff430`; pack integrity donor PR #7 `74003278`; independent verifier PR #6 `986a0d4`. **Source only, never copy a donor DLL.** Path B PR #8 remains OFF. RC3B is read-only regression comparison.

## Execute, not re-plan

**N1 PORT AND BUILD, first critical path**
- On the 2026.4 *target* branch, port the minimum complete Pack V1 GPU writer+reader, tracing, provider, tests and Wave-01 transactional integrity fixes from source donor.
- Integrate profile-driven physical placement, residency sidecars and native PackLayerSpec; retain existing 2026.4 GPU kernels and ABI; record every altered source file and dependency.
- Assemble matching OpenVINO/GenAI/OVMS Windows runtime tuple; isolate outputs. Build GPU unit suite, `ovms.exe` and `ovms_test.exe`. Prove P0 actual loaded DLL hash and P1 compiled 9-slice eligibility.
- A failing compile is a coding task: fix and repeat within the dev tree, not an invitation to declare source ready.

**N2 REAL GPU EVENT OWNERSHIP, parallel source work, prior to async activity**
- Read `moe_otd_slot_lease_v2.hpp` and host tests (PR #10). Wire to the actual `OffloadExpertWeightProvider`, LRU slot selection, `moe_3gemm_swiglu_opt`, oneDNN/OCL queue transitions and terminal consumer events.
- Existing `ExpertSlotLease = vector<size_t>` is only a slot index list, and existing `stream.finish()` barriers are not an asynchronous event lease.
- Invariant: choose a recyclable slot **before** modifying LRU mapping; `begin_write`; verify packed bytes; queue copy; attach producer event; mark ready only when complete; `begin_read` for every consumer, retire with terminal event; no reuse before all consumers complete.
- Handle grouped top-k, multi-request concurrent clones, cancellation, exceptions, GPU reset, and double retirement. No stale resident hit or event lost.
- Preserve conservative synchronous fallback if any event provenance cannot be guaranteed. Do not fake asynchronous safety by attaching the producer event in place of a consumer event.

**N3 GLOBAL UMA ADMISSION, in parallel after resource inventory**
- Read `moe_otd_uma_prefetch_v2.hpp`, add actual OS available RAM/WDDM GPU budget probes and model-wide reservations for dense weights, U4 KV, activations, draft, GPU expert slots, stage/prefetch and driver reserve.
- The 32 GB LPDDR pool is SHARED. Never add free GPU budget to free CPU RAM.
- Reconcile actual committed bytes and pending reservations across all layers and C1/C2/C4 requests. Runtime allocation fails closed under pressure; demand tokens prioritized over speculative allocations.
- No active 2026.4 Path B, no global BIOS/WDDM settings changes.

**N4 PREDICTIVE HOT ARMING, after N2+N3 are proven**
- Use real complete native routing traces, not static XML or synthetic profiles. Derive profile confidence, phase and cost; score candidate future experts in bounded lookahead windows.
- Plan `next-window-probability * critical-stall - exposed-load - eviction-cost`; choose no more than admitted free slots/staging bytes; acquire N2 write tickets and N3 UMA reservation before any asynchronous read or copy.
- Attach real GPU copy event and publish only after completion. Cancel low-confidence prefetch and yield to demand without evicting active GPU readers; hot/warm/cold with LRU only last tie-breaker.
- No false claim that planning header already uploads experts; implement dispatcher and tests.
- Trace overhead, warm-up contamination, accuracy and workload shifts must be measured, with prefetch ON/OFF paired runs.

## Mandatory staged GPU validation

G0: exact target compile + native host/regression pass; this includes cross-repo version/library SHA and loaded module provenance.

G1: correct packed read, corrupted pack negative, no HTTP/gRPC in pack-only mode, scoped compiled eligibility; P2 lease reader safety.

G2: plain offload r0 (non-OTD reference) and r20. Capture native routing trace with completeness end marker. Generate PGP profile, placement, residency, build packs (only eligible, no stale count), verify per-expert payload, seal immutable V2 generation and bind manifest to the native serve request. No silent fallback in `require`.

G3: ON/OFF prefetch and hot/warm/cold policies, actual GPU event lifecycle, UMA pressure at C1; aborted/over-budget arming remains fail-closed.

G4: matched r20/r40/r75 and safe extra r10/r30/r50 (Qwen3.6 historical comparators), C1/C2/C4 and contexts subject to available RAM. Measure TTFT, decode TPS, TPOT p95/p99, logical and physical reads separately, misses/evictions, stalls, copy bandwidth and memory headroom.

G5: tool calling and multi-turn agentic regression using existing Qwen/Gemma/Ornith test harness: empty {}, literal identifiers/VIN/part numbers, nested JSON, unary/SSE, actual tool execution and tool result continuation. Test unpacked, V1 identity, V2 reactive and V2 prefetch separately.

## Start commands

PowerShell 7 and Developer Command Prompt on operator's Windows Core Ultra 258V/Arc140V machine:

```powershell
git -C <OVMS_DIR> fetch origin
git -C <OV_DIR> fetch origin
# Create isolated worktrees; preserve all existing dirty working trees.
py -3 -m unittest discover -s <OVMS_DEV>\tests\cib2 -p "test_*.py" -v
# In native OpenVINO target tools/moe_otd_control_v2 directory:
# cl /nologo /std:c++17 /EHsc /W4 /WX /O2 test_control.cpp /Fe:control_test.exe
# .\control_test.exe
```

For the entire native/plugin/OVMS build, use the repository documented pinned
Windows scripts and actual generator/toolchain environment; do not invent
SDK paths. Build artifacts live in a new isolated directory with SHA256 receipt.

## Deliverables

Two updated dev commits + two draft PRs (#29 OVMS and #10 target OpenVINO); exact file and code diffs; successful host and native tests with a real count; compiled binaries/hashes; model eligibility and failure reasoning; pack generation contents; full trace/PGP provenance; tool-call correctness; benchmark receipts; hardware gate statuses.

`BUILD_GREEN` != `GPU_PARITY` != `PREFETCH_CORRECT` != `PERF_WIN` != `PRODUCTION_ACCEPTED`.

**Priority: produce a real working OVMS 2026.4 with safe Pack V2 before feature polishing. N2 and N3 may be developed in parallel with the N1 port. N4 may be implemented earlier as code, but must remain disabled until native N2/N3 gates pass.**
