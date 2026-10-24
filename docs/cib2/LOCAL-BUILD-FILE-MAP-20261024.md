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

### N2 review fix and N3 probe checkpoint

- OpenVINO published source checkpoint: `c5fc6792a5fd4f84ab2f8eb5480d8ba6aa4b3b97`.
- Shared provider execution serialization now drains oneDNN and OCL before releasing the execution lock and before scratch destruction. Resident r0 bypasses it. Different arena rebinding fails closed; arena memory owners are retained.
- Independent read-only review found that poison alone was insufficient on failed-drain unwind: local scratch could be released while completion remained unverified. Fixed by independently attempting both drains and failing the process without resource teardown if either fails.
- Ruling: native failed-drain fallback exits with code 86 after diagnostic `OTD_FATAL_UNVERIFIED_GPU_COMPLETION`. This prevents local teardown without context-level lifetime proof; its cost is loss of all concurrent requests on that GPU failure. Context/request-owner quarantine and graceful recovery remain unimplemented. No production acceptance is claimed.
- Final host regression checkpoint: 5/5 CTest targets, including 24 native pack tests, 3 LRU scenarios, 400 serialized sections across 4 threads, cancellation/poison/unwind/r0 checks, and 4 child-process drain fault-injection cases. Modified provider/runtime/Swiglu graph compiled again using the real generated MSVC commands and separate object/PDB outputs.
- N3 source probe: `moe_otd_windows_uma.hpp`; tool `probe_windows_uma.cpp`, CMake target `otd_windows_uma_probe`. Actual GlobalMemoryStatusEx and exact-LUID DXGI budget probes compiled /std:c++17 /W4 /WX and ran. The sample reported 33,866,633,216 physical bytes and overlapping WDDM budget 28,658,664,529 bytes. Two Intel LUID observations are not additive memory pools. Cross-layer accounting remains NOT_DONE.
- New build-only scripts outside the repositories: `C:/git/cib2-packv2-build-20261024/{gpu-build.cmd,check-current-port.cmd,native-controls.cmd,ovms-build.cmd}`. Logs and receipts are in that same directory. No production service or model was started.
- SDK archive SHA256 freshly verified: `b74ee43a10bf4615b805b1bacb78f330faec9616309a86126493973ee278e1dc`; dependency staging lives at `sdk-2026.4`, separate from the original SDK. OVMS preliminary compilation uses 2026.4 SDK headers/import libraries and Python 3.12.10, with explicit isolated Bazel repository overlays. Final rebuilt core/plugin installation, matching tuple relink and loaded module attribution remain OPEN.
- Both full builds were launched. A successful three-object compilation or standalone native host suite does not establish full plugin/OVMS build, model eligibility or GPU runtime acceptance. N4 remains OFF and planning-only until N2/N3 live gates are established.

### Resume checkpoint 2026-10-24 afternoon

- **Canonical trees:** `C:/git/` only (not `C:/gm/`). OVMS = PR **#29** tip `c7fe5aa` / `dev/cib2-packv2-source-20261024`. OpenVINO = PR **#10** tip `c5fc679` / `dev/cib2-packv2-ov2026.4-integration-20261024`. Build root `C:/git/cib2-packv2-build-20261024` (no git). Branch `dev/cib2-native-prototype-01-20261024` does **not** exist. Do not merge draft #9/#10/#29 (`runtime_acceptance=NO`).
- Gaps: `cib2-packv2-openvino-20261024` is −4 commits vs #10 tip; `cib2-packv2-ov2026.4-20261024` has broken `.invalid` HEAD — ignore both for work.
- OpenVINO local dirty on tip: `moe_3gemm_gpu_test.cpp` (grouped-prefill diagnostic) + untracked `moe_otd_native_pack_gpu_test.cpp` (unit GLOB).
- GPU plugin + `ov_gpu_unit_tests` linked. Plugin smoke PASS (`plugin-smoke-loaded.json`): Arc 140V, core/GPU `2026.4.1-5-c5fc6792…`, attributed native DLLs. NOT model eligibility.
- Native GPU cohort `native-cohort-121`: **121/121 PASSED** (includes 4× `moe_otd_native_gpu.*`, pack/publish, LRU, 3gemm smoke + grouped_prefill). Receipts under build root.
- Host reconfirm: `check-current-port` → providers/runtime/swiglu obj compile 0; `native-controls` CTest 5/5 PASS.
- OVMS Bazel first failed on `checkCib2PackBuild` (incomplete types + invented APIs). Local uncommitted fix in `src/server.cpp`: includes + `getState() == ModelVersionState::AVAILABLE` + `getNamesOfAvailableMediapipePipelines()`.
- **OVMS BUILD_GREEN (compile/link):** `ovms-build.cmd` EXIT 0 — `Build completed successfully, 236 total actions`; `bazel-bin/src/ovms.exe` + `ovms_test.exe` linked. Still NOT model eligibility / GPU acceptance / pack seal; keep draft #9/#10/#29 unmerged (`runtime_acceptance=NO`).
- **Native tuple attribution (OVMS process): PASS.** Staged runtime `C:/git/cib2-packv2-build-20261024/ovms-runtime` loads rebuilt `openvino.dll` + `openvino_intel_gpu_plugin.dll` (SHA256 match OV `bin/intel64/Release` / install; stock SDK GPU retained as `.sdk-reference-disabled`). Receipts: `ovms-native-tuple-attribution.json`, `ovms-pack-build-smoke-attributed.json`, `ovms-runtime-plugin-smoke-attributed.json`. Backend string `2026.4.1-5-c5fc6792a5f-dev/cib2-packv2-ov2026.4-integration-20261024`; device Arc 140V.
- **Pack-build-only smoke: BLOCKED.** `--build_moe_experts_pack` reaches LLM/VLM init then fails: `Device with "CPU" name is not registered` — GPU-only CMake (`ENABLE_INTEL_CPU=OFF`); stock RC1 CPU plugin DLL does not register with native core. Need matching `openvino_intel_cpu_plugin` (reconfigure/build with `ENABLE_INTEL_CPU=ON`, stage into `ovms-runtime`) before pack-build smoke can proceed. Do not start r20/r40/r75 until that smoke passes. Prefetch / Path B / UMA global accounting = NOT_RUN. N2 host fail-stop ≠ GPU event leases.
