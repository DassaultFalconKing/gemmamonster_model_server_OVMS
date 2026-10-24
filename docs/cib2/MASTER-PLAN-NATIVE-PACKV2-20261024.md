# GEMMAMONSTER CIB2: new OVMS 2026.4 / profile-guided Pack V2 / UMA
2026-10-24. Status: SOURCE WRITTEN; HOST_BUILD NOT_RUN; GPU NOT_RUN. No production acceptance.

## Lineage

OVMS source dev: dev/cib2-packv2-source-20261024 based on the PGP-05 audit
commit 208cd759 (which includes Wave-01 PR #27 and originates from RC3B
eb76a74f). RC3B is a frozen regression witness, not the new dev HEAD.
MiniCPM's failed test was the chronology that triggered this program, but
its 1caffd79 branch has its own fork from eb76a74f, not an ancestral
dependency of CIB2. Import P1 source 608c9c5 plus auditor 13ba318 after
independent tests.

OpenVINO GPU source DONOR: dev/cib2-packv2-native-20261024, based on
2026.5-derived PR #7 74003278. This is NOT the target runtime.
Target OpenVINO dev: dev/cib2-packv2-ov2026.4-integration-20261024,
created from releases/2026/4 60ba6ff015f8b511e1407678062878c5ca466d08.
Cursor must transplant compatible SOURCE, never 2026.5 DLLs.
The exact compatible GenAI/SDK/driver tuple must be established on Windows.

## Architecture

Original OpenVINO XML+BIN remains immutable.
GPU compile -> exact eligible MOECompressed + nine routed tensor views,
weights_path, top_k, quantization and native scoped PackLayerSpec.
First serve with plain OTD -> real complete expert-routing trace.
Native trace -> scripts/cib2/trace_profile.py -> validated per-layer PGP-02
profiles (incomplete/unmapped traces fail).
scripts/cib2/pack_layout.py -> deterministic logical-to-physical expert
placement, with identity/frequency/coaccess candidates.
scripts/cib2/packv2_pipeline.py -> native per-layer .placement and
.residency binary policies plus JSON plan. No weights modified yet.

OVMS build-only mode (HTTP/gRPC NEVER LISTEN) -> native GPU build_pack ->
per-layer Pack V1 files of nine tensor slices and 4KiB expert records,
ordered per the profile-derived physical permutation.
Independent full-payload verifier -> Pack V2 generation envelope with
full-file SHA256, immutable generation-<sha>, manifest and atomic active
pointer. Native leaf record ABI remains OTDPACK1 intentionally;
full V2 sharding/variable record ABI is not implemented or assumed.
Serving mode -> require valid packs -> exact logical expert -> placement
-> one verified record read on miss -> GPU resident state.

## GPU residency is distinct from SSD packing

The same physical expert may reside in one GPU slot no matter which
disk pack generation stores it. A hot file name does NOT pin GPU memory.
Current native candidate has soft expert priorities: cold=0, warm=1,
hot=2. Victim selection prefers lowest priority, then oldest LRU.
If all experts are hot, a genuine demand miss still makes progress;
hot protection is SOFT and the hardware resident capacity is respected.
Missing profile -> original exact LRU. Profiles come from miss-count
times observed read cost, not raw frequency alone. This is a candidate,
not a proven optimal admission policy.

Next required controller: phase-aware per-layer hotness plus cross-layer
working-set/rate/latency, controlled hot arming/warming, dedicated
GPU queue reader/lease generation and cancellation; demand outranks
prefetch; no wrong expert/lifetime, no failed slot published.
The current source does NOT prefetch or proactively fill future GPU slots.
The existing ExpertSlotLease is a vector of indices, NOT a lifetime-safe
GPU event/lease object. Implement real reader lifetime before enabling
background arming or prefetch.

## UMA instead of fictitious independent GPU/CPU tiers

Core Ultra 258V + Arc 140V share 32 GiB LPDDR. WDDM budget and
system-available are overlapping constraints, never additive.
One admission ledger: OS+driver safety; nonexpert/attention/router/vision;
KV U4+prefix; optional drafter; activations/workspaces; unique expert arena;
staging/prefetch. Current first prototype sticks to Path A usm_device:
verified CPU staging -> ordered GPU copy -> safe publish. Path B usm_host
is a separate opt-in experiment with reader-drain + post-write visibility
and startup/GEMV regressions, not enabled in the first prototype.
No direct NVMe-to-GPU zero-copy promise.

## Code slices in first source commit

OVMS: trace_profile.py; packv2_pipeline.py; verify_pack_v1.py imported
from independent OpenVINO PR #6; test_packv2_pipeline.py; surgical
build-only/require CLI port; existing Wave-01 PGP02/PGP05 untouched.

OpenVINO source donor: moe_otd_placement_v2.hpp and
moe_otd_residency_v2.hpp (native handoff); pack builder accepts placement;
expert provider reads profile-driven placement and residency priority
only when explicitly configured; LRUCache adds priority-aware
victim choice with original LRU as exact disabled-mode behavior;
new synthetic native unit tests.

## Status / hard gates

Source is written in cloud, NOT compiled or tested on Intel Arc.
P0: exact source-build binary and loaded module attribution OPEN.
P1: compiled eligibility and nine exact tensor views OPEN.
P2: oversized lease and actual GPU reader ownership OPEN.
P3: compatible 2026.4 source port / Pack V1 kernel parity OPEN.
P4: build-only no-listeners CLI and no-zero-pack false positives OPEN.
P5: full generation source binding, independent manifest verification on
serve and fail-closed corrupt/foreign pack refusal OPEN.
P6: profile policy memory admission + proactive hot arm/prefetch OPEN.
P7: same-cohort speed and resident-memory comparisons OPEN.
P8: unary/SSE + MFP-1 tool correctness and multi-turn agentic OPEN.

Do not promote a STATIC profile as a real trace. Do not report GPU
PASS from host tests, and do not benchmark V2 superiority against the
2026.5 donor without same-machine, same-binary, same-checkpoint controls.

## Operator execution

1. Integrate #26 and #28 locally with exact unit runs, create new
   CIB2 dev branch; never change RC3B or production deployment.
2. Validate Windows toolchain/2026.4 GenAI/GPU API; transplant native
   source donor onto exact compatible releases/2026/4 line.
3. Build GPU native tests and plugin and ovms/ovms_test on dev.
4. Prove P0/P1/P2/P3/P5 safety. No actual packed serve before gates.
5. Serial single-GPU plain offload r20 profiling, complete native trace
   and overhead/complete-end controls.
6. Generate profile + physical placement + residency plans (NOT synthetic).
7. Run no-listener OVMS pack build with --moe_experts_placement_dir.
8. Verify each expert payload and seal immutable V2 generation.
9. OVMS --moe_experts_pack_dir=<generation> --moe_experts_residency_dir
   =<plans> require serve. Check native cold-miss reads actually occur.
10. Run exact same-cohort OFFLOAD_RATIO 0,20,40,75 and applicable
    historical 10,30,50 controls. Test tool JSON literal integrity,
    SSE/unary, agentic loops, C1/C2/C4, TTFT/decode/TPOT,
    resident/eviction/read counters, WDDM+system UMA headroom.
11. Ship two draft integration PRs and sanitized evidence; never
    silently merge #8 (Path B).

The historical Qwen3.6 INT4 2026.4 offload baseline and older 2026.5
packed-vs-unpacked results are useful controls, not interchangeable
cohort measurements.
