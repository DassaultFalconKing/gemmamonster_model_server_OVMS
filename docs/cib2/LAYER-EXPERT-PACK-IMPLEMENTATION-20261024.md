# CIB2: layer/expert map → native packed OTD → semantic-refit 2026.4 acceptance

Date: **2026-10-24**. Status: **INTEGRATED IMPLEMENTATION PLAN / NOT ACCEPTED**.
Document-only branch, forked from current executed CIB2 wave `feature/cib2-offload-family-map-20261024` @ `ab7412c85a035ba958e28c81e25f9d1efa9fe9a7`.
Never modify the frozen semantic source, known-good binaries, running services or published tags.

## Executive decision

**Implement routed-expert packing first on exact OpenVINO 2026.4 RC1, using the new CIB2 maps strictly as source/offset evidence. Keep dense layer offload, shared-USM Path B, adaptive expert policy, speculative prefetch and CPU SIMD experts separate, later, feature-gated projects.**

The new static mapper is **not a packer**, and naming three routed Const nodes per transformer block is **not** proof of N runnable, individually addressable experts. The old packed expert backend is **implemented and measured** in a GPU 2026.5-derived cohort but **not** in our 2026.4 semantic refit. Do not transfer 2026.5 plugin binaries or conflate source/compile/serving success.

## 1. Source and evidence inventory

| Component | Branch/SHA | Implemented | Remaining |
| --- | --- | --- | --- |
| Semantic 2026.4 RC3B-postfix | OVMS `freeze/rc3b-postfix-20261023-eb76a74f` / `eb76a74f7aa39573d452d95443e189b1f5f4d9e8` | Gemma4, Qwen3Coder lossless args, Ornith official tool-result template and MFP-1 | **No** `--build_moe_experts_pack`, `--moe_experts_pack_dir`. Frozen runtime/build identity still requires independent attestations. |
| Current CIB2 family map + replay | OVMS `feature/cib2-offload-family-map-20261024` / `ab7412c85a035ba958e28c81e25f9d1efa9fe9a7` | `family_map.py` (static graph/block/roles and unioned BIN ranges), `run_family_inventory.py`, `otd_sim.py` (strict complete trace replay), `source_lock.py`; **67/67 local host tests** | No compiled MoE eligibility, no source/build association, no native GPU/OVMS tests, no actual pack. |
| Old pack CLI adapter | OVMS `integration/qwm01-otd-pack-20261022` / `1d9b497ea27221c51636af028e597e6c681d42b2` | Build-only server exit, `--build_moe_experts_pack` and `--moe_experts_pack_dir`, env handoff to GPU plugin, `require` fail closed | Re-implement minimal compatible diff on semantic 2026.4, not wholesale cherry-pick. |
| Native expert pack v1 | OpenVINO `research/ov-gpu-otd-cohort-b5bfb148` / `479219245f6f10b670367ad35af16513d72d2091`, underlying `52f57df1` | Per-layer pack, **9 tensor slices**, 4 KiB records, one positional read per expert miss, pre-transposed scales/ZP, `off/use/require/build` | 2026.4 RC1 source-level port, exact compiled weights layout/offsets and live parity. |
| Hardened host pack | OpenVINO Draft PR [#7](https://github.com/DassaultFalconKing/openvino/pull/7) / `74003278a9c8925fcda7bc32ceb27320e59bbb1d` | #1 integrity, #4 same-handle pin, #2 atomic publish, #3 trace and #5 trace evidence; 47/47 Windows host C++ + 33/33 Python; no auto-merge | GPU live / independent 2026.4 binaries / model acceptance open. |
| Offline pack verifier | OpenVINO Draft PR [#6](https://github.com/DassaultFalconKing/openvino/pull/6) | Python read-only v1 verifier, 14 synthetic tests | Independent native C++ pack differential and Windows QA pending. |
| UMA Path B | OpenVINO Draft PR [#8](https://github.com/DassaultFalconKing/openvino/pull/8), scratch HEAD `94e0eea6` | `usm_host` CPU scatter with pre-write reader drain and post-write visibility fence; short Arc model C1/C2/C4 acceptance | Not production; more startup/memory/throughput analysis, event/lease ownership, full 2026.4 port later. |

**Historical numbers, not 2026.4 projections:** at offload ratio 75, packed decode ~5.9 vs unpacked ~5.3 tok/s (old slower 2026.5 GPU plugin); at ratio 40 ~7.3 vs ~7.1. Separate stock 2026.4 Qwen3.6 baseline ~32 tok/s. The huge 2026.5 decode cliff persists even with offload disabled: absolutely no binary mixing or performance inference across cohorts.

## 2. Current family/layer matrix and preconditions

From [FAMILY-MAP](FAMILY-MAP-20261024.md), [GEMMA-QWEN tests](GEMMA-QWEN-TESTS-20261024.md) and the checked-in machine-readable report:

| Actual local export | Static language blocks | Weight BIN GiB | Routed Const nodes | Decision |
| --- | ---: | ---: | ---: | --- |
| MiniCPM-V-4.7-35B-A3B INT4 | 40 | 18.368 | not independently tested in 67/67 Gemma/Qwen round | `qwen3_5_moe_text` candidate; **GPU/processor/memory blocker**, eligibility NOT_RUN. |
| Gemma4 E4B INT4 | 42 | 5.979 | 0 | negative control for expert OTD; dense layer offload is separate. |
| Gemma4 26B-A4B INT4, QAT/overlay variants | 30 | 15.015 | 90 | alternate MoE expert-kind requires compiled path proof; no GEMM3 assumption. Overlay aliases are not independent physical models. |
| Ornith 35B INT4 | 40 | 18.270 | 120 | best available full exported Qwen-family native OTD candidate; verify compiled GEMM3_SWIGLU and weights_path. |
| Qwen3.6 Eagle3 IR | draft only | 0.605 | 0 | never treat as full Qwen3.6 target; no target-OFFLOAD claim. |
| LFM2.5 / GLM 4.7 / Qwen3.8 | absent from scanned root | unknown | unknown | `NOT_AVAILABLE` until actual export; capability must be proven per family. |

The 90/120 are named routed Const *nodes*, generally three tensor groups per layer; **NOT** the number of experts and **NOT** pack record count. `family_map` records offsets, sizes, hashes of XML/config, interval-unioned ranges and conservative tensor roles. BIN weights are statted, not read/hashed; a future packer must validate all weight file ranges against the same exact compiled source/format, per-projection quantization, transposes and nine-slice resident arrangement. Nested XML node IDs can repeat; use graph + subgraph scope + ordinal + source range, never raw `layer_id` alone.

Exact RC1 source `61afcb26271140347709138b13d678e8b1b5925c` enables native disk expert OTD for compiled `MOECompressed` `GEMM3_SWIGLU`, `OFFLOAD_RATIO=1..99`, usable `weights_path`. 0 and 100 **do not** enable this path. Prefusion IR XML **cannot prove or exclude** compiled OTD eligibility by itself.

MiniCPM latest independent live evidence `1caffd79`: two isolated new GenAI constructor attempts ended in `MEMORY_BLOCKED`, second peak process-tree private ~20.65 GiB, system available low ~1.97 GiB, no tokens generated. No inference, tool, vision or pack acceptance. Avoid repeating this unbounded.

## 3. System ownership and target architecture

```text
OVMS 2026.4 semantic refit (OpenAI API, model admission, MFP-1 parsers, tool policy)
  |-- compiled-model eligibility + resource ledger (only configure, don't re-route model)
  |-- pack build-only CLI -> native GPU plugin build mode -> exit without listeners
  |-- serve pack require/use via explicit immutable model-identity-aware settings
  |
OpenVINO GenAI RC1 (target/drafter, CB, KV U4, prefix, plain/MTP/DFlash gated)
  |
OpenVINO Intel GPU 2026.4 RC1 source (separate candidate plugin build)
  |-- Compiled MOECompressed + GEMM3_SWIGLU, weights_path, top_k, exact quant layout
  |-- PackLayerSpec -> per-layer immutable Pack V1 (nine views, 4KiB records)
  |-- verified read -> resident slot -> LRU publish only after checksum/ownership
  |-- passive source-tagged trace -> bounded offline LRU replay
  |
One physical 32 GiB UMA: OS + fixed model + KV + draft + workspaces + *one*
bounded expert resident arena + small staging/OS page cache + safety reserve
  |
NVMe: cold immutable packed experts, not a second GPU memory allocation
```

Separate future research branches:

- Path A: `usm_device` GPU resident buffers; reference/default.
- Path B: `usm_host` CPU-visible GPU-readable resident buffers; default OFF with explicit lifetime + post-write visibility.
- Path C: mapped cold record and OS paging; not accepted, unpredictable faults.
- CPU expert D: independent SIMD worker, especially relevant to P720 NUMA; never assumed beneficial for 258V shared LPDDR.
- Dense/layer offload: architecture-specific execution placement/HETERO feasibility study; **no** automatic SSD paging for fixed attention/convolution/embedding layers and no assumption that the routed Pack V1 knows how to store arbitrary layers.

## 4. Implementation packets: ordering, owners, deliverables and exit gates

### P0 — source/binary lock + same-host baseline (must precede runtime edits)
**Owner:** local acceptance/integration agent; no source patch. Re-run CIB2 preflight, physical SHA256 of working-postfix `ovms.exe`/`ovms_test.exe` and GenAI/OpenVINO/Intel GPU DLLs, loaded module paths + runtime fingerprints, driver, SDK `2026.4.0.0rc1`, available RAM. Bind exact executable to verified source/build receipt; `component-receipt.json` currently proves *file identity only*. Freeze baseline with tool regressions (Gemma, Qwen, Ornith) and plain `OFFLOAD_RATIO=0`. Exit: reproducible tuple and nonempty log-backed PASS; otherwise stop.

### P1 — compiled model eligibility and resident-size source of truth (can run with P0)
**Owner:** family graph auditor. Extend read-only mapper output with a separate **compiled** eligibility report, never promote static XML classification. On target IR for each family record compiled expert-kind (`GEMM3_SWIGLU` or other), `weights_path`, exact pack source offsets/9 tensor layout, group size, routed expert count/top_k, quant types, compiled GPU kernel and resident memory at r0/20/40. Run only one model at a time under watchdog; no live model for missing full Qwen/LFM/GLM exports. Exit: per-model `ELIGIBLE / INELIGIBLE / UNKNOWN / MEMORY_BLOCKED` with on-device evidence; Gemma26 needs its own alternate-kind assessment. No mutation of tool/parser modules.

### P2 — native GPU transactional safety on **2026.4 RC1** (first GPU source patch)
**Owner:** dedicated `DassaultFalconKing/openvino` worktree from exact RC1 GPU source, NOT from 2026.5 feature tree. Baseline RED for oversized simultaneous expert lease mutating earlier slots. Port smallest precheck from `7d905ba9` only if RED reproduces. Include no-false-hit, multi-queue in-flight reader, cancellation, exception, LRU exact-state invariance. Compare r0/r20 compiled correctness against unmodified same-source plugin. Exit: RED→GREEN gtests, safe rollback, no source-derived assertion treated as run receipt.

### P3 — minimal 2026.4 Pack V1 core and safety (separate GPU feature PR)
**Owner:** GPU storage/compiler engineer. Port architecture/semantics, not wholesale source code: `moe_otd_pack.{hpp,cpp}`, `moe_otd_runtime.*` packed backend adapter, `expert_weight_providers.*` mode provider integration, gpu unit tests and BUILD dependencies, into **verified compatible RC1**. Preserve aligned one-record-per-expert format, nine slices, no runtime scale/ZP transpose, canonical quant bytes. Include fail-closed `require` and feature-flagged `off`/`use`/`build`. Required defenses: header+payload checksums before touching a resident slot, source/weight generation and layer-key checks, stable source handle/snapshot, atomic temp+publish, no partial serving, pack-content validation independent from model map. FNV handles accidental corruption only, not adversarial authenticated tampering. No automatic pack v2 or mapped-file zero-copy. Exit: C++ host pack/negative tests + native build and runtime kernel parity on Arc with content-checked old/new weight sources.

### P4 — semantic-refit OVMS pack CLI **on 2026.4** (separate OVMS feature PR)
**Owner:** OVMS engineer. Adapt minimal behavior from old OVMS `1d9b497ea` using current `src/cli_parser.cpp`, `src/config.cpp`, `src/server.cpp`, `src/capi_frontend/server_settings.hpp`, relevant BUILD/tests. New supported options:
- `--build_moe_experts_pack --moe_experts_pack_dir <DIR>` loads configured servables for pack build then exits, **no bound HTTP/gRPC listeners**, reports actual eligible layers/pack count; `zero eligible` is explicit failure, not silent success.
- `--moe_experts_pack_dir <DIR>` in serve mode sets `require`; invalid, stale, foreign, missing, incomplete or unverified pack aborts serving for eligible compiled layers.
- Without either flag => unmodified stock behavior. Config path and CLI model modes validated; env/handoff `OV_GPU_MOE_OTD_PACK_MODE` and `OV_GPU_MOE_OTD_PACK_DIR` must be scoped to the candidate process, not global production config; detect conflicting settings and path ambiguity.
- Build every eligible graph exactly once; invalidate/skip wrong quant/model revisions; preserve C1/C2/C4 and tool policies. Do not depend on 2026.5 server ABI or call APIs absent in RC1.
Exit: CLI parse positive/negative tests, `ovms_test`, dry launch, no-network assertion, genuine 40-layer pack build on eligible model and deterministic corrupted-pack refusal.

### P5 — independent verifier + deterministic storage evidence
**Owner:** separate storage QA agent. Port independent Draft PR #6 verifier to candidate test tree as a read-only checker. Cross-check true native C++ built 216-byte-header Pack V1 files with nonidentity placement and synthetic bitflips, swap/foreign-model metadata, truncation, stale manifest, permissions, parallel writers, cancellation, same-handle reader identity. Confirm no wrong expert can be published to LRU on checksum or lifetime failure. Bind traces to actual code and artifact digests. Physical NVMe bytes remain `NOT_EXPOSED` until OS-level counters are collected.

### P6 — 2026.4 live GPU/OVMS pack acceptance on isolated tuple
**Owner:** local hardware agent, operator-authorized, serial runs and RAM guard.
- First native mock/synthetic GPU tensor parity; then real Ornith (and a full Qwen3.6 if present), `OFFLOAD_RATIO=0` control followed by eligible 20/40/75. Ratio 100 negative; require works only when compiled eligibility exists.
- One-time build of packs from **the same** checkpoint/quant metadata and candidate GPU DLL, then paired packed vs unpacked with identical source+IR+driver+GenAI, warmups >=1, >=3 repeats; TTFT, decode TPS, p50/p95/p99 TPOT, read bytes+reads and compile/load times.
- C1→C2→C4, context 512/2048 then 8K/32K if KV U4 + memory admission permits, prefix and no-draft/plain. Run unary/SSE, tool calls, result replay for Qwen/Ornith/Gemma. MTP/DFlash only when own checkpoint/IR and draft verifier are accepted, and measure **physical bytes per actually committed target token**.
- Gemma4 26B may not reach the same GEMM3 OTD path; produce explicit ineligible result if compiler chooses another expert kind, rather than interpreting r40 as proof. MiniCPM-V4.7 first needs memory/processor and native compiled graph gate; do not loop crash attempts.
Exit: no wrong logits/tool history, no GPU_CONTEXT_FATAL, no OOM or swap storm, measurable end-to-end benefit vs stock or neutral correctness gain with explicit off-by-default policy. Run 30–60 min soak only after shorter suite green.

### P7 — UMA admission with default Path A (`usm_device`) and optional Path B (`usm_host`), opt-in
**Owner:** memory engineer. Read-only system and WDDM allocation ledger first. No extra fictional VRAM, no huge pinned RAM duplicate on 258V. Enforce `fixed + vision + KV U4 + draft + workspace + expert arena + small staging + OS safety` within 32 GiB. After P6, optional scratch `usm_host` Path B (PR #8) with strict pre-write reader drain and post-write visibility. B cold fill was ~21% faster in a short 1.617 MiB record test, but M=1 GEMV ~15.7% slower and model start ~283s vs A ~42s; NOT a universal default. Long term implement per-slot event/lease ownership rather than global stream finish. Gate with identical real 2026.4 A/B.

**P7 A/B extension:** [PGP full Path A/B controller, evidence, four-arm A0/A1/B0/B1 acceptance and per-slot lease requirements](PROFILE-GUIDED-EXPERT-PACKING-20261024.md#11-uma-path-a--optional-path-b-placement-controller-integrated-with-pgp-2026-10-24); [editable graph](PGP-UMA-PATH-AB-20261024.mermaid). The only production control is **A: verified Pack V1 staging → `usm_device` GPU `copy_from` → safe slot publish**. **B remains default OFF** (`OTD_RESIDENT_USM_HOST=1` scratch only), uses pre-write GPU reader draining, CPU scatter into `usm_host`, then post-write visibility fencing before publication; it must not be mistaken for zero-copy from NVMe. Scratch B cold-miss ~21% faster, M=1 GEMV ~15.7% slower and warm startup ~283 s vs A ~42 s; these are **2026.5-scratch evidence, not fast 2026.4 RC1 acceptance**. No automatic per-expert A/B switching or hybrid cache keys until memory/accounting/lease/cancel correctness is proved.

### P8 — routing hotness, optional 2Q and prefetch from real traces
**Owner:** offline simulation plus GPU scheduler researcher. Collect complete per-layer/per-expert trace tied to model and quant, distinguish prefill, verifier demand, draft demand, rejected speculative work, accepted target tokens; no prompt contents. Replay exact current LRU vs CLOCK/2Q/SLRU under C1/C2/C4 and MTP window, mark truncation invalid. Then only if it wins, feature-flag 2Q/admission and bounded prefetch with target demand priority, cancellation and no eviction of live GPU readers. Reject on extra NVMe amplification or p95/p99 regressions. No automatic `CLD-04` based on synthetic 67/67 host suite.

### P9 — dense layer and other-family/offload architecture (distinct research, later)
**Owner:** execution engine architect; no change to packed-expert V1.
- Dense E4B, conv/attention in LFM2.5, vision/MLA, shared experts and non-GEMM3 MoE need their own compiled op ownership and placement graph. Document legal CPU/GPU boundaries, KV continuity, model layer DAG, synchronized tensors and numerical parity.
- Trial HETERO/CPU execution splitting only if supported by exact runtime; do NOT treat CPU↔GPU on one LPDDR as independent memory tiers. Per-token disk-swapping dense layers likely dominated by I/O; begin with static CPU/GPU placement or single-use prefill modules, not a universal dense SSD pager.
- Build a **versioned model component manifest** with identity (`checkpoint/graph/scope/transformer_block/projection/quant/shape/bytes`); maybe share static source-lock with expert PackSpec, but don't conflate on-disk record formats.
- Add fresh GLM/LFM/Qwen3.8 and MiniCPM actual exports into family map only when downloaded and eligible; no inferred support from card/model name.
Exit: executable minimal prototype and independent performance/quality evidence before integration. CPU experts on P720 2x Xeon 6242 AVX-512/VNNI with NUMA affinity are separate benchmarks.

## 5. Dependencies, release gates and abort paths

```text
CURRENT ab7412c (static family map + strict replay, 67/67 host PASS)
       |
       +--> P0 exact executable/module provenance --> baseline protocol suite
       |
       +--> P1 compiled expert eligibility / no unsupported-family assumptions
                 |
              P2 native RC1 transactional lease RED→GREEN
                 |
              P3 RC1 packed core + integrity/publish ---- P5 independent verifier
                 |                                      /
              P4 semantic-refit CLI integration --------
                 |
              P6 Arc C1 / C2 / C4 real model & tool-loop A/B
                 |
                 +--> P7 memory ledger + Path B separate gated
                 +--> P8 real routing trace replay/prefetch (optional)
                 +--> P9 dense/non-GEMM3 model placement (separate R&D)
```

**Promotion levels:** `SOURCE VERIFIED` → `RED REPRODUCED` → `STATIC PATCH` → `BUILD GREEN` → `UNIT GREEN` → `API GREEN` → `RUNTIME GREEN` → `AGENTIC GREEN` → `OWNER ACCEPTED`. No “all GREEN” from host-only 67/67, compilation, old pre-2026.4 binaries or tiny toy-GPU fixtures.

**Hard stops:** wrong/foreign pack accepted; partial/stale LRU hit; unbounded GPU reader race; semantic tool loss/change of JSON number spelling; production DLL mixing; source-build identity missing; swap pressure or driver reset; unsupported model silently reports OTD enabled; ratio 100 assumed full disk; no actual completed tool call in live responses; physical NVMe read bytes invented from logical trace count.

## 6. Agent work tickets to hand off immediately

1. **P0 local integrator:** exact working-postfix model/runtime/module manifest, re-run CIB2 strict preflight and Qwen/Gemma/Ornith regression; artifact digest evidence and blockers.
2. **P1 graph specialist:** use family_map + actual compiled graph for Ornith and Gemma26, prove/deny `MOECompressed/GEMM3_SWIGLU/weights_path`, document nine provider slice offsets/shape vs XML graph scope.
3. **P2 GPU fix specialist:** native RED on oversize lease exact RC1, no modifications until reproduced, small isolated patch and host C++ GPU tests.
4. **P3+P5 pack specialist:** port minimal Pack V1 plus Wave01 safety into separate RC1 OpenVINO PR, native C++/independent Python verifier and negative fixtures.
5. **P4 OVMS integrator:** refit old `1d9b497ea` CLI semantics onto new `eb76a74f` source without copying old parser and config drift; ensure build-only with no listeners and require fail-closed.
6. **P6 hardware QA:** after previous gates, run stock vs candidate 2026.4 on Arc140V, Ornith initially, optionally full Qwen, Gemma only if eligible, with RAM watchdog and exact benchmark receipts.
7. **P7–9** remain future research workers, not allowed to merge changes while P6 is pending.

Agent execution branches from immutable source/tag each; no concurrent writes to production install. Every worker writes `docs/cib2/STATE.md` in its own isolated branch or standalone handoff, report exact base/head/revert SHA, files changed, commands and exit codes, PASS/FAIL/BLOCKED/NOT_RUN per gate; coordinator cherry-picks *only* independently accepted patches in stated dependency order.

## 7. Definition of done

A) Semantic-refit 2026.4 serves an eligible MoE at stock speed when packed mode is OFF.
B) A single native `build` process creates valid immutable per-layer packs from exactly matched quant/checkpoint, deterministic **one positional pack read per cold expert** in serving `require` mode.
C) Corrupt/foreign/truncated packs and multi-process races fail closed, no stale expert/slot use; independent verifier agrees.
D) Same source/IR/SDK GPU kernels pass packed-unpacked logits/router parity, C1/C2/C4 and tool/agentic live loops.
E) Resource and throughput measured against **same** stock 2026.4, no hidden 2026.5 slowdown, source+binary+model hashes pinned.
F) An additional dense/layer offload route is accepted **only separately** after actual source/kernel research; it is not part of the routed Pack V1 completion.

This is the minimal path to realize the planned hot/cold layer architecture without manufacturing compatibility, speedups or memory that do not exist.


## Addendum 2026-10-24: profile-guided physical packing and SSD geometry

The core P0–P9 plan above establishes correctness and an exact 2026.4-compatible Pack V1 before *any* profile optimization. The next programme is [PGP-01: Profile-Guided Expert Packing](PROFILE-GUIDED-EXPERT-PACKING-20261024.md), with `PGP-00…PGP-05` independent tickets.

- **Start without V2:** existing Pack V1 `PackLayout::set_placement` and `build_pack(..., placement)` support per-layer expert record permutation with unchanged logical IDs, checksums and reader ABI. Native `fill_weights_from_pack` still reads one payload only; physical reordering alone is not a proven improvement.
- **Trace-driven hotness:** use complete, provenance-pinned real expert access sequences with C1/C2/C4 and verifier/drafter ownership. Static XML Const offsets and synthetic 67/67 host tests are **not** hotness evidence.
- **Three independent knobs:** (1) bounded unique-LPDDR expert residency, (2) per-layer physical record order/co-access locality, (3) bounded grouped reads/prefetch. No fake OS-cache/`usm_host` capacity tier or auto-pinning.
- **Windows:** measure NTFS allocation cluster, physical/logical sectors, aligned I/O extent, OS cache effect and file fragmentation separately. Do not format drives, assume 4KiB hardware sectors, or label `FILE_FLAG_NO_BUFFERING` as GPU direct DMA.
- **V2 only on objective evidence:** versioned manifest/shards and async IO after Pack V1 same-runtime correctness and paired performance. Quant/mixed precision changes are a separate, quality-sensitive model export project.
