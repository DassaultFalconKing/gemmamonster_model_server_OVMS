# CIB2 local build and edit map

## Source locks and isolation

- OVMS: `C:/git/cib2-packv2-ovms-20261024`, branch `dev/cib2-packv2-source-20261024`, initial HEAD `693bbcc02ab3d21cfb3c214b27f90b04c0665bf9`.
- OpenVINO: `C:/git/cib2-packv2-ov-20261024`, branch `dev/cib2-packv2-ov2026.4-integration-20261024`, initial HEAD `d39aa73b8bd788c9b286fc1bcff6298b86827ecc`.
- Both fetched from the specified GitHub forks. OpenVINO is a depth-one clone; fetch donor source separately. Existing dirty trees and deployed binaries are outside these outputs.

## Native edit map

All paths below are relative to OpenVINO unless specified.

| Gate | Files | Work |
| --- | --- | --- |
| N1 runtime | `src/plugins/intel_gpu/src/graph/impls/ocl_v2/moe/moe_otd_runtime.{hpp,cpp}` | Bind actual nine tensor views and per-layer PackLayerSpec to checked reads |
| N1 provider | same directory, `expert_weight_providers.{hpp,cpp}` | Packed demand load, physical placement, residency priorities, rollback |
| N1 graph | same directory, `moe_3gemm_swiglu_opt.{hpp,cpp}` | Scoped layer identity and build/read wiring, retain 2026.4 kernels |
| N1 codec | same directory, `moe_otd_pack.{hpp,cpp}`, `moe_otd_placement_v2.hpp`, `moe_otd_residency_v2.hpp` | Existing staged codec and binary sidecar contracts |
| N2 | same directory, `moe_otd_slot_lease_v2.hpp`, `lru_cache.{hpp,cpp}`, provider and graph above | Slot ownership before replacement, actual producer and terminal consumer event lifetime; synchronous drain fallback |
| N3/N4 | same directory, `moe_otd_uma_prefetch_v2.hpp`, provider/runtime above | Windows overlapping RAM/WDDM probes, global reservations, gated bounded dispatcher |
| Trace | same directory, `moe_otd_trace.{hpp,cpp}` | Complete routing traces and logical/physical accounting |
| Build | `src/plugins/intel_gpu/src/graph/impls/ocl_v2/CMakeLists.txt`, `src/plugins/intel_gpu/src/graph/CMakeLists.txt` | Backend source discovery and dependencies |
| Tests | `src/plugins/intel_gpu/tests/unit/CMakeLists.txt`, `test_cases/moe_offload_lru_cache_test.cpp` | Native registration and safety regression coverage |
| Host | `src/plugins/intel_gpu/tools/moe_otd_control_v2/test_control.cpp` | MSVC C++17 /W4 /WX control harness |
| Pack verification | `src/plugins/intel_gpu/tools/moe_otd_pack/{verify_pack.py,test_verify_pack.py}` | Independent payload negatives |

## OVMS edit and build map

- `src/cli_parser.cpp`, `src/config.cpp`, `src/server.cpp`: CLI, no-listener build-only lifecycle, require-mode generation binding and zero-eligible reporting.
- `scripts/cib2/{trace_profile.py,pack_layout.py,packv2_pipeline.py,verify_pack_v1.py}`: measured trace to placement/residency, independent verification and immutable generation sealing.
- `tests/cib2/test_*.py`: host regressions; observed 198 tests OK on this checkout.
- `versions.mk`, `third_party/openvino/openvino_windows.BUILD`, `third_party/genai/genai_windows.BUILD`: exact 2026.4 SDK and GenAI provenance; no donor DLLs.
- `docs/windows_developer_guide.md`, `windows_build.bat`, `windows_setupvars.bat`, `.bazelrc`: pinned Windows procedure, Python templates and ovms_test.
- Existing machine recipe references (read only): `C:/gm/otd-research/build-tools/ov-gpu-plugin.cmd` and `ovms-bazel.cmd`. Adapt paths into isolated outputs; do not execute their historical paths unchanged.
- Installed MSVC entry: `C:/BuildTools/VC/Auxiliary/Build/vcvars64.bat`. Repository default assumes a different VS install, so capture the explicit override.

## Evidence and execution ledger

- Host log: `C:/git/cib2-packv2-host-tests-20261024.log`; 198 tests, OK, command exit 0 on repeated clean invocation.
- Native build root: `C:/git/cib2-packv2-build-20261024`; production and RC3B are excluded.
- BUILD_GREEN, GPU_PARITY, lease/UMA safety, predictive prefetch and production acceptance remain separate gates. GPU evidence not yet collected.

### Execution checkpoint

- OpenVINO N1 provider/runtime/LRU source port and graph factory wiring implemented; all three changed runtime/provider/Swiglu object files compiled successfully on MSVC 14.44.35207.
- The native control CMake project now builds and runs the actual codec/publication tests without linking the GPU runtime: 24/24 pack tests, 3 LRU scenarios and control harness PASS. Independent Python verifier: 14/14 PASS.
- Fixed priority-based simultaneous acquisition self-eviction: the required set is excluded from victim selection. This does not close GPU reader lifetime safety.
- Full plugin and `ov_gpu_unit_tests` build is active. OVMS/ovms_test build and all live GPU/model/agent/performance gates are NOT_RUN.
- CMake initially required xbyak/gflags submodule initialization and disabling HETERO for this unit-only configuration (its functional test target refers to disabled shared functional tests).
- The nested oneDNN ExternalProject starts its own Ninja. Set `CMAKE_BUILD_PARALLEL_LEVEL=2` as well as the outer parallel limit. A nested build was interrupted during process diagnosis and successfully resumed; do not classify the interruption as a source compiler defect.
- Exact 2026.4 rc1 SDK archive is present locally; a matching rebuilt-core/GenAI tuple still requires verification. The existing SDK plugin is not a replacement for the target plugin build.
