# Agent handoff: MoE offload-to-disk packs, linked to the drafter track, 2026-10-22

**ACCEPTED: NO. Operator compute pause from [HANDOFF-DRAFTERS-20261022.md](HANDOFF-DRAFTERS-20261022.md) applies.** Do not build, start models or benchmark from this handoff until the operator releases compute.

## Why the tracks are linked

Every drafter measurement in the drafter handoff runs with `OFFLOAD_RATIO=40`, i.e. through GPU MoE offload-to-disk (OTD). Routed-expert misses are read from the original weights file, one positional read per tensor, with scale/zero-point transposition on the hot path. Drafter results (MTP K1/K2/K3, AEON DFlash K4/K6) therefore include OTD miss cost, and speculative verify batches change which experts are touched per committed token. The research plan for this is on branch `docs/moe-nvme-experts-research-20261021`, folder `docs/research/routed-experts-nvme-20261021` (06 roadmap, 07 model/drafter baselines, 08 speculative expert cache). That branch is documentation only and has no common history with this code line, so it is referenced, not merged.

## Source boundary

| Component | Branch / commit | Content | Published |
|---|---|---|---|
| OVMS | `research/ovms-otd-pack-mode-2026` @ `1d9b497ea`, merged here in `44d76afec` | `--build_moe_experts_pack`, `--moe_experts_pack_dir` | This integration branch only |
| OpenVINO GPU plugin | `research/ov-gpu-otd-observability-2026` from C6 OpenVINO `29c068c9`: `da568aa7` P2, `c1047efd` P3, `f054eecc` fixes, `534db6bb` P4 | OTD counters and router trace, offline cache simulator, LRU slot reuse fix, oversized lease rejection, per-layer packs | **Local only, not published** |

The executable and GenAI DLL hashes in the drafter handoff predate all of this work. None of these commits are part of the measured runtime, the staged runtime, the dependency lock or C6.

## Behaviour

- Build packs once per model, then exit (pull-like): `ovms --config_path <CONFIG> --build_moe_experts_pack --moe_experts_pack_dir <PACK_DIR>`. Same servable arguments as serving; gRPC/REST are not started; idle servable groups are disabled so every graph compiles. Fails if any servable does not load or no pack is produced.
- Serving with `--moe_experts_pack_dir <PACK_DIR>` sets the plugin to `require`: every offloaded MoE layer must open a valid pack or the servable fails to load. There is no silent fallback to the unpacked path.
- OVMS passes the mode through `OV_GPU_MOE_OTD_PACK_MODE` / `OV_GPU_MOE_OTD_PACK_DIR`, read by the GPU plugin on each compile. Without the OVMS flags behaviour is unchanged.
- Pack format: one content-keyed file per MoE layer, expert-major 4 KiB-aligned records already in the resident layout, so a miss is one read. Header, placement table and per-record checksums; corrupt or foreign packs are rejected and rebuilt atomically. Packs are derived data and stay out of Git like weights.
- Routing math, KV defaults, parsers, tool policies and the XGrammar lock are not touched.

## Evidence and actual status

| Item | Status |
|---|---|
| Plugin unit tests (trace, LRU, pack) | 43 PASS in a standalone gtest build |
| C++ LRU and trace vs Python exact-LRU replay | 0 mismatches over 31306 synthetic events |
| Precheck fix on synthetic trace | misses 33223 to 27002; synthetic only |
| Plugin sources with C6 flags | compile PASS; plugin DLL not linked |
| OVMS changed sources | compile PASS against generated headers of the qwm01 build tree; full link and `ovmsconfig_test` run NOT RUN |
| Weight-provider overflow test | NOT RUN (needs the full GPU unit-test build) |
| Real model pack build, serving with packs, GPU timing | **NOT RUN** |

## Resume contract, after operator releases compute

1. Follow the drafter handoff ordering; serialize GPU work and keep the 15463 MiB available-RAM floor. Pack build loads the full model, so it occupies the exclusive runtime slot.
2. Build OpenVINO from the plugin branch and OVMS from this branch in isolated output trees; do not replace the installed DLLs without a new operator decision.
3. Run `ovms_test --gtest_filter=*oeExpertsPack*` and the GPU unit tests `moe_otd_*` / `moe_offload_*`.
4. Build packs for the exact drafter target tuple, then repeat baseline and MTP K3 at `OFFLOAD_RATIO=40` with and without `--moe_experts_pack_dir`, plus `MOE_OTD_TRACE` for the simulator. Report OTD misses, read bytes and read latency next to TTFT/decode as separate columns. Do not mix packed and unpacked rows.
5. Update this handoff, MASTER-PLAN.md and STATE.md; no promotion until its own gates pass.
