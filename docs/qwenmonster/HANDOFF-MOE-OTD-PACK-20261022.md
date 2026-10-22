# Agent handoff: MoE offload-to-disk packs, linked to the drafter track, 2026-10-22

**ACCEPTED: NO.** The unpacked `OFFLOAD_RATIO=75` row and the `OFFLOAD_RATIO=40` packed/unpacked pair are now measured with the same binaries and token budget as the recorded packed row. MTP K3 with packs and the open test gates are still NOT RUN. The drafter pause in [HANDOFF-DRAFTERS-20261022.md](HANDOFF-DRAFTERS-20261022.md) still applies to that track.

## Why the tracks are linked

Every drafter measurement in the drafter handoff runs with `OFFLOAD_RATIO=40`, i.e. through GPU MoE offload-to-disk (OTD). Routed-expert misses are read from the original weights file, one positional read per tensor, with scale/zero-point transposition on the hot path. Drafter results (MTP K1/K2/K3, AEON DFlash K4/K6) therefore include OTD miss cost, and speculative verify batches change which experts are touched per committed token. The research plan for this is on branch `docs/moe-nvme-experts-research-20261021`, folder `docs/research/routed-experts-nvme-20261021` (06 roadmap, 07 model/drafter baselines, 08 speculative expert cache). That branch is documentation only and has no common history with this code line, so it is referenced, not merged.

## Source boundary

| Component | Branch / commit | Content | Published |
|---|---|---|---|
| OVMS | `research/ovms-otd-pack-mode-2026` @ `1d9b497ea`, merged here in `44d76afec` | `--build_moe_experts_pack`, `--moe_experts_pack_dir` | Fork, and this integration branch |
| OpenVINO GPU plugin, portability line | `research/ov-gpu-otd-observability-2026` from `29c068c9`: `da568aa7` P2, `c1047efd` P3, `f054eecc` fixes, `534db6bb` P4, `956d5eca` stderr reporting | OTD counters and router trace, offline cache simulator, LRU slot reuse fix, oversized lease rejection, per-layer packs, release-build stderr for the opt-in perf summary and pack status | `DassaultFalconKing/openvino` |
| OpenVINO GPU plugin, measured DLL | `research/ov-gpu-otd-cohort-b5bfb148` from `b5bfb148`: `4ff78eac` P2, `86bab01e` P3, `7d905ba9` fixes, `52f57df1` P4, `47921924` stderr reporting | Same feature set built on the C6 plugin base. This is the DLL that served the bench below. `956d5eca` is the same stderr change cherry-picked afterwards and was not the measured binary | `DassaultFalconKing/openvino` |

The drafter executable in the drafter handoff predates this work. GenAI DLL SHA-256 is unchanged: `442452056e06c3a7e05d71ca082e9f30fd0034c8f6dcf5b2e56f04f140599e4d`. Measured OVMS executable SHA-256: `1175bd25d6faf90e41c6591e23507cf6117895351462ff3b5648c8a6df08a760`. Measured GPU plugin SHA-256: `1093b69f6314898238ffec06fb46631759526e89c90e3e3fd2fd29c122e8058e`. These binaries are not the staged runtime, the dependency lock or C6.

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
| Plugin DLL | Built from the cohort line above and used for the packed bench |
| OVMS `//src:ovms` | Link PASS on this integration branch. `ovms_test --gtest_filter=*oeExpertsPack*` NOT RUN |
| Weight-provider overflow test | NOT RUN (needs the full GPU unit-test build) |
| Pack build at `OFFLOAD_RATIO=40` | 40 pack files, 434118656 bytes each. A second build-mode run exited and again reported 40 pack files; its stderr lines said the packs were reused |
| Packed serve at `OFFLOAD_RATIO=75` with those packs | PASS. `require` accepted the packs (the pack key does not include the ratio) and the graph reached AVAILABLE. Available RAM at process start was 9824 MiB, below the 15463 MiB drafter floor, so this is not a drafter-cell row |
| Packed bench, temperature 0, max_tokens 384, one warmup plus 3 repeats | All four generations: 55 prompt tokens, 384 completion tokens, `finish_reason=length`. Warmup TTFT 13.85 s, decode 5.68 tok/s. Repeats TTFT 4.43 / 4.18 / 4.20 s, decode 5.75 / 5.94 / 5.97 tok/s |
| Unpacked serve at `OFFLOAD_RATIO=75`, same budget | PASS. Available RAM at process start 17667 MiB. Warmup TTFT 17.02 s, decode 5.08 tok/s. Repeats TTFT 5.23 / 5.23 / 5.23 s, decode 5.32 / 5.31 / 5.35 tok/s. All four generations 55/384, `finish_reason=length`. Packed is faster at ratio 75: repeat TTFT about 0.9 s lower, decode about 10% higher |
| Packed serve and bench at `OFFLOAD_RATIO=40` | PASS. Available RAM at process start 16765 MiB, above the 15463 MiB floor. Warmup TTFT 3.40 s, decode 6.96 tok/s. Repeats TTFT 1.32 / 1.09 / 1.06 s, decode 6.95 / 7.33 / 7.39 tok/s. All four generations 55/384, `finish_reason=length`. The first bench attempt for this row died client-side without writing its result; the server kept the completed warmup and a cancelled partial generation, so the full-process trace counters include them. The recorded counters below are taken from the trace window of the four measured generations only |
| Unpacked serve and bench at `OFFLOAD_RATIO=40`, same budget | PASS. Available RAM at process start 17835 MiB. Warmup TTFT 19.41 s, decode 5.85 tok/s. Repeats TTFT 1.98 / 1.45 / 1.26 s, decode 6.95 / 7.13 / 7.08 tok/s. All four generations 55/384, `finish_reason=length` |
| OTD trace counters (offline `summary`, per measured bench window) | Packed r75: hits 426946, misses 77576, disk bytes 131549036544, reads 77576 (1 per miss), transform 0 ms, per-load p50/p95/p99 1188.8/1841.7/2132.9 µs, evictions 75016. Unpacked r75: hits 426921, misses 77572, disk bytes 131542253568, reads 698148 (about 9 per miss), transform 11656 ms, per-load p50/p95/p99 806.4/3400.6/4077.6 µs, evictions 75012. Packed r40: hits 494685, misses 9871, disk bytes 16738689024, reads 9871, transform 0 ms, per-load p50/p95/p99 651.0/1928.0/5965.6 µs, evictions 9871. Unpacked r40: hits 489410, misses 15091, disk bytes 25590472704, reads 135819 (about 9 per miss), transform 2408 ms, per-load p50/p95/p99 2059.8/4174.8/6042.6 µs, evictions 9411. Ratio 40 keeps 153 of 256 expert slots resident versus 64 at ratio 75, which is why misses drop by roughly 8x |
| Process-exit `[OTD_PERF]` stderr summary | **NOT CAPTURED in any row.** The termination path does not run the atexit summary; three of four traces also end mid-record. All counters above come from the offline `otd_sim.py summary` on the trace files (copies without a truncated final line where needed) |
| MTP K3 with packs | **NOT RUN** |

## Stopped here

Do not launch the next model from this commit. The packed/unpacked comparison at ratio 75 and the ratio-40 pair are measured; the remaining open items are MTP K3 with packs, `ovms_test --gtest_filter=*oeExpertsPack*`, and the GPU unit tests `moe_otd_*` / `moe_offload_*`. The process-exit `[OTD_PERF]` summary needs a graceful shutdown path that actually runs atexit before it can be recorded. No promotion until those gates pass.
