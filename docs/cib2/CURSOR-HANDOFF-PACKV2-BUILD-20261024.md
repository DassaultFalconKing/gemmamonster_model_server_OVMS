# Cursor execution handoff: new OVMS 2026.4 + GPU profile-aware Pack V2
Date: 2026-10-24. SOURCE CODE WRITTEN. New Windows/GPU tests NOT_RUN.

## Exact inputs and dependencies

OVMS PR #29, dev/cib2-packv2-source-20261024, most recent published
source HEAD in PR. Parent is PGP-05 auditor PR #28 + Wave-01 PR #27,
and exact P1 Static files from PR #26 are added on top.
RC3B eb76a74f is a REGRESSION WITNESS, not the new base.

OpenVINO GPU source DONOR: PR #9 at 7e9fb22df7c76ed6be4334b8bb22ecb734eff430
on 2026.5-derived Wave-01. It includes binary native placement and soft
hot/warm/cold GPU LRU priority. This DONOR IS NOT A 2026.4 TARGET.

Actual OpenVINO GPU TARGET DEV BRANCH:
dev/cib2-packv2-ov2026.4-integration-20261024,
based on releases/2026/4 @ 60ba6ff015f8b511e1407678062878c5ca466d08.
Port selected SOURCE, not any 2026.5 DLL. Do NOT graft
the entire donor tree over the newer 2026.4 kernel/runtime.

## Task

Finish source-compatible target GPU port; rebuild Intel GPU plugin and
OVMS on Windows; test, profile actual routed experts, derive placements,
build V1 native leaf packs in profile order, independently verify, seal
immutable V2 generation, serve require mode, test tool calls and offload
ratios. This is an EXECUTION TASK, not a planning-only report.

## Source and runtime gates in order

1. Fetch exact remote heads of OVMS PR #29 / OpenVINO PR #9. Use
   isolated worktrees. No edits to working RC3B or deployed model DLLs.
2. Test Python host:
   py -3 -m unittest discover -s tests/cib2 -p "test_*.py" -v
   py -3 -m py_compile scripts/cib2/trace_profile.py scripts/cib2/packv2_pipeline.py
   Do not inherit 174/174 PASS from Wave-01 for new code.
3. Native OpenVINO source-level port onto target 2026.4 branch.
   Preserve 2026.4 GEMM3_SWIGLU kernels. Port Pack V1 reader/build,
   Wave-01 integrity/handle/publish fixes, placement and residency
   binary files, priority-aware eviction, GPU tests and build deps.
   Compile Intel GPU plugin using the repository's verified Windows
   CMake/MSVC recipes; never substitute 2026.5 plugin DLLs.
4. Build OVMS with Python/tool template support and ovms_test with
   repository windows_build.bat / docs/windows_developer_guide.md.
   Capture source+compiler+SDK/GenAI+driver+actual loaded DLL SHA.
5. Native P0/P1/P2/P3/P5: prove compiled eligible MOECompressed kind,
   weights_path, exact nine slices and scoped PackLayerSpec; reproduce
   and fix oversized leases; no evict of live GPU stream reader;
   corrupted/foreign/stale packs fail before GPU slot publication.
6. OVMS --build_moe_experts_pack must bind NO REST/gRPC listeners and
   must not claim success from unrelated leftover pack files. Improve
   zero-eligible/source-count reporting if required by real tests.
7. Plain native OTD GPU run on one eligible full MoE model, r20 first.
   Record actual trace via MOE_OTD_TRACE with complete # end footer,
   profile-off/on overhead, IR/module/build identity. Operator builds
   trace_identity.v1 from the REAL compiled model, not raw XML alone.
8. Run actual PGP pipeline (paths are variables, not literal strings):
   py -3 scripts/cib2/trace_profile.py --trace TRACE --identity IDENTITY --output BUNDLE
   py -3 scripts/cib2/packv2_pipeline.py plans --bundle BUNDLE --output-dir PLANS --strategy frequency
   ovms --config_path CONFIG --build_moe_experts_pack --moe_experts_pack_dir NATIVE_PACKS --moe_experts_placement_dir PLANS --moe_experts_residency_dir PLANS
   py -3 scripts/cib2/packv2_pipeline.py seal --plans-dir PLANS --native-packs NATIVE_PACKS --output-root GENERATIONS
   py -3 scripts/cib2/packv2_pipeline.py verify --generation-dir GENERATION_SHA_DIR
   ovms --config_path CONFIG --moe_experts_pack_dir GENERATION_SHA_DIR --moe_experts_residency_dir PLANS
9. V2 still uses native Pack V1 records: do not claim changed quantization
   or new GPU record ABI. Source-generated manifest/active pointer is
   independently verified OFFLINE, but OVMS does not yet natively bind
   its manifest to the live compiled generation; code+test this gate
   before declaring FULL V2 runtime acceptance.
10. GPU residency: profile hot/warm/cold tiers currently influence
    soft victim choice, with LRU only the tie-breaker and fallback.
    Predictive prefetch/arm of future hot experts, phase-aware
    continuous profile evolution, per-slot GPU event/lease ownership and
    unified cross-layer UMA budget enforcement remain NOT_IMPLEMENTED.
    Do not activate speculative prefetch or Path B usm_host.
    Build the event/lease safety work as a separate gated patch rather
    than pretending soft priority is the complete controller.
11. After basic demand path is safe, compare one matched cohort:
    ordinary unloaded r0 control, unpacked r20/r40/r75, identity-packed,
    profile-V2 frequency/coaccess (where complete real trace exists).
    Include Qwen3.6 historical r10/r30/r50 only as a separate baseline.
    At least one warmup + three repetitions per accepted cell.
    TTFT, decode TPS, accepted target tokens, p95/p99 TPOT, native
    logical reads and misses, startup, OS+WDDM overlapping UMA headroom.
12. Reuse accepted Gemma/Qwen/Ornith lossless protocols: actual harness
    tool calls, empty {}, big numeric/part/VIN string literals, nested
    args, SSE/unary and tool-result replay, 2+ agentic tool turns.
    No plausible tool-call text may count as a real tool execution.
13. Publish build+test receipts, updated exact source SHAs and
    draft GPU integration PR against new target OpenVINO 2026.4 branch.
    Never close P0/P1/P2/P3/P5 from compilation alone and do not
    modify active production services, original exports or drivers.

## Hard verdict policy

Source-only candidate != build-ready or GPU-tested.
Packed data bytes verified != compiled checkpoint trusted.
Co-access order != fewer reads unless grouped requests are measured.
One physical 32GiB LPDDR pool: WDDM and system counters overlap.
Path A usm_device only. Path B remains isolated experimental research.
Native P2 reader lifetime failure, wrong logits/tool literals,
pack corruption accepted, GPU reset or swap storm = STOP.
