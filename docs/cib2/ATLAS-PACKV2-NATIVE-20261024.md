# CIB2 Pack V2 / MOE OTD — ATLAS (2026-10-24)

Evidence from local trees + `docs/cib2/LOCAL-BUILD-FILE-MAP-20261024.md`. Paths exact. No PR merges; `runtime_acceptance=NO` unchanged.

---

## Резюме работы

| Tree | Local | Branch | HEAD | Remote / PR |
| --- | --- | --- | --- | --- |
| OVMS | `C:\git\cib2-packv2-ovms-20261024` | `dev/cib2-packv2-source-20261024` | `13fabc185f90febdb0025f78acf82240ea286ab7` (= origin) | https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS — **Draft PR #29** |
| OpenVINO | `C:\git\cib2-packv2-ov-20261024` | `dev/cib2-packv2-ov2026.4-integration-20261024` | `b7105471c42fb8f33d607891651e67872697d15e` (= origin) | https://github.com/DassaultFalconKing/openvino — **Draft PR #10** |
| Build/staging | `C:\git\cib2-packv2-build-20261024` | — | **NO git** | private |

**Что сделано (гейты / смоки):**

1. **N1** — port Pack demand/provider/runtime/Swiglu wiring + codec/placement/residency; host pack tests 24/24; Python verifier 14/14.
2. **N2** — `SynchronousExecutionGate` + fail-stop drain (`OTD_FATAL_UNVERIFIED_GPU_COMPLETION`, exit 86); host CTest 5/5 (control/LRU/guard/fail-stop/pack).
3. **N3 probe** — `moe_otd_windows_uma.hpp` + `otd_windows_uma_probe` (GlobalMemoryStatusEx + exact-LUID DXGI); **не** global accounting.
4. **BUILD_GREEN** — GPU plugin + `ov_gpu_unit_tests`; OVMS Bazel link (`ovms.exe` / `ovms_test.exe`); Path A CMake.
5. **Attribution** — staged `ovms-runtime` loads matching native `openvino.dll` + GPU + CPU plugins (SHA match `bin\intel64\Release`).
6. **CPU stage** — `ENABLE_INTEL_CPU=ON` rebuild; stock CPU demoted to `.sdk-reference-disabled`.
7. **Pack-build** — attributed `--build_moe_experts_pack` → **40** OTDPACK1 layers under `pack-build-smoke\` (~**15.59 GiB**). Layer pack-build = OVMS CLI `--build_moe_experts_pack` + GPU plugin pack codec.
8. **NOT done / OFF** — V2 seal/verify generation; r20/r40/r75 serve matrix; Path B; prefetch/N4; production/`runtime_acceptance`.

**Filesystem check (ATLAS write time):**

- OVMS HEAD `13fabc185`; dirty: `M docs/cib2/LOCAL-BUILD-FILE-MAP-20261024.md`; untracked `?? bazel-cib2-packv2-ovms-20261024/` (**не коммитить**).
- OpenVINO: clean at `b7105471`.
- Build-root: всё private; **40** packs present under `pack-build-smoke\`.
- **verify-all-packs:** terminal `790874` / shell PID **22352** still **running** (`python312\python.exe verify-all-packs.py`); **`pack-build-smoke-verify.json` отсутствует**. Identity plans / seal / generation dirs тоже **отсутствуют**.

---

## Модули OpenVINO

База (git relative под `src/plugins/intel_gpu/`):

| Capability | Role (one-liner) | Git relative |
| --- | --- | --- |
| Expert weight providers | Packed demand load, placement, residency, rollback | `…/ocl_v2/moe/expert_weight_provider.hpp`, `expert_weight_providers.{hpp,cpp}` |
| LRU cache | Slot residency / eviction (self-eviction excluded for required set) | `…/moe/lru_cache.{hpp,cpp}` |
| Pack codec | OTDPACK1 read/write + publish contracts | `…/moe/moe_otd_pack.{hpp,cpp}` |
| Placement / residency sidecars | Binary sidecar contracts V2 | `moe_otd_placement_v2.hpp`, `moe_otd_residency_v2.hpp` |
| Runtime | Nine-tensor views + PackLayerSpec checked reads | `moe_otd_runtime.{hpp,cpp}` |
| Execution guard | Serialize shared OTD exec; dual drain; fail-stop 86 | `moe_otd_execution_guard.hpp` |
| Slot lease (header) | Generation-tagged GPU reader leases (live wiring incomplete) | `moe_otd_slot_lease_v2.hpp` |
| UMA prefetch (header) | Overlapping CPU/WDDM admission + bounded predict | `moe_otd_uma_prefetch_v2.hpp` |
| Windows UMA probe | Exact-LUID DXGI + GlobalMemoryStatusEx | `moe_otd_windows_uma.hpp` |
| Swiglu wiring | Scoped layer identity; 2026.4 kernels retained | `moe_3gemm_swiglu_opt.{hpp,cpp}` |
| Trace | Routing / logical↔physical accounting | `moe_otd_trace.{hpp,cpp}` |
| Host controls | MSVC `/W4 /WX` harness without full GPU runtime | `tools/moe_otd_control_v2/*` + README |
| Independent pack verify | Offline payload negatives | `tools/moe_otd_pack/{verify_pack.py,test_verify_pack.py}` |
| GPU unit tests | Native pack/LRU/3gemm/grouped-prefill cohort | `tests/unit/test_cases/moe_*.cpp` esp. `moe_otd_native_pack_gpu_test.cpp`, `moe_3gemm_gpu_test.cpp` |

**Host CMake targets** (`tools/moe_otd_control_v2`): `otd_control_test`, `otd_lru_test`, `otd_execution_guard_test`, `otd_windows_uma_probe`, `otd_pack_tests` (+ CTest: controls/lru/execution_guard/drain_fail_stop/pack).

**Recent OV commit tip:** `b7105471` — native Pack V2 GPU unit coverage + grouped-prefill diagnostics.

---

## Модули OVMS + Python обвязка

### C++ / CLI (перепаковщик слоёв = native pack-build path)

| Module | Role | Git relative |
| --- | --- | --- |
| CLI | `--build_moe_experts_pack`, `--moe_experts_pack_dir`, placement/residency dirs | `src/cli_parser.cpp` |
| Config | Build-only lifecycle constraints | `src/config.cpp` |
| `checkCib2PackBuild` | After AVAILABLE, count native packs; Windows API fix in tip | `src/server.cpp` (`13fabc185`) |
| Versions / Bazel Windows | Pin 2026.4 SDK + GenAI; no donor DLLs | `versions.mk`, `third_party/openvino/openvino_windows.BUILD`, `third_party/genai/genai_windows.BUILD` |

### `scripts/cib2/*` (offline harness)

| Script | Role |
| --- | --- |
| `pack_layout.py` | Offline logical→physical expert layout optimizer (PGP-02) |
| `packv2_pipeline.py` | `plans` / `seal` / `verify` — immutable Pack V2 generation envelope (`OTDPACK1` payload) |
| `verify_pack_v1.py` | Bounded offline OTDPACK1 verifier |
| `trace_profile.py` | COMPLETE `moe_otd_trace` → PGP-02 profiles |
| `storage_geometry.py` | Read-only Windows storage/UMA probe (PGP-00) |
| `source_lock.py` | Static component identity collector |
| `static_nine_slice.py` | Static co-occurrence of nine expert storage names |
| `family_map.py` / `run_family_inventory.py` | Static family/layer inventory |
| `benchmark_screen.py` | Offline A0/A1/B0/B1 receipt screen (PGP-05) |
| `preflight_rc3b.py` | RC3B provenance preflight (no inference) |
| `otd_sim/` | Deterministic offline MOE_OTD_TRACE replay |

### Host tests

`tests/cib2/test_*.py` (16 modules); historical ledger: 198 / 174 OK depending on wave — **not** GPU/`runtime_acceptance`.

---

## Build-root tooling (вне git)

`C:\git\cib2-packv2-build-20261024\` — staging only.

| Tool | Role |
| --- | --- |
| `gpu-build.cmd` / `cpu-plugin-build.cmd` | Path A OpenVINO CMake (+ CPU ON) |
| `ovms-build.cmd` | Isolated Bazel OVMS |
| `native-controls.cmd` / `check-current-port.cmd` | Host CTest / port-check objs |
| `stage-native-core.py` / `stage-cpu-plugin.py` | Overlay native core/CPU(+GPU) into `ovms-runtime` / SDK staging |
| `run-attributed.py` | Run process + capture loaded module paths/SHA |
| `launch-pack-build-smoke.py` | Attributed Qwen3.6 `--build_moe_experts_pack` |
| `verify-all-packs.py` | Offline `verify_pack_v1` over all 40 packs → `pack-build-smoke-verify.json` (**in flight**) |
| `make-identity-plans-from-packs.py` | Identity `plans.v2.json` from packs → `pack-build-smoke-plans\` (**not run yet**) |
| `ovms-runtime\` | Staged `ovms.exe` + native tuple DLLs |
| `openvino\` | Ninja build tree |
| `sdk-2026.4\`, `python312\`, `bazel-repos\` | Isolated deps |
| `model-textonly-qwen\` | Small smoke model (not the 40-pack Qwen3.6 source) |
| `pack-build-smoke\` | **40** native packs |
| `cache-pack-build-smoke\` | OVMS/OpenVINO cl_cache for pack-build |

---

## Таблица путей

| Local | Git relative | Repo | In next commit? |
| --- | --- | --- | --- |
| `C:\git\cib2-packv2-ovms-20261024\docs\cib2\LOCAL-BUILD-FILE-MAP-20261024.md` | `docs/cib2/LOCAL-BUILD-FILE-MAP-20261024.md` | OVMS | **YES** (dirty tracked; CPU+pack-build ledger) |
| `C:\git\cib2-packv2-ovms-20261024\docs\cib2\ATLAS-PACKV2-NATIVE-20261024.md` | `docs/cib2/ATLAS-PACKV2-NATIVE-20261024.md` | OVMS | **YES** (this atlas) |
| `C:\git\cib2-packv2-ovms-20261024\src\server.cpp` | `src/server.cpp` | OVMS | Already in `13fabc185` |
| `C:\git\cib2-packv2-ovms-20261024\src\cli_parser.cpp` | `src/cli_parser.cpp` | OVMS | already on branch |
| `C:\git\cib2-packv2-ovms-20261024\src\config.cpp` | `src/config.cpp` | OVMS | already on branch |
| `C:\git\cib2-packv2-ovms-20261024\scripts\cib2\*.py` | `scripts/cib2/…` | OVMS | already on branch |
| `C:\git\cib2-packv2-ovms-20261024\tests\cib2\…` | `tests/cib2/…` | OVMS | already on branch |
| `C:\git\cib2-packv2-ovms-20261024\bazel-cib2-packv2-ovms-20261024\` | — | — | **NO** (untracked bazel symlink/cache) |
| `C:\git\cib2-packv2-ov-20261024\src\plugins\intel_gpu\src\graph\impls\ocl_v2\moe\*` | same under repo | OpenVINO | already on tip `b7105471` |
| `C:\git\cib2-packv2-ov-20261024\src\plugins\intel_gpu\tools\moe_otd_control_v2\*` | same | OpenVINO | already on branch |
| `C:\git\cib2-packv2-ov-20261024\src\plugins\intel_gpu\tools\moe_otd_pack\*` | same | OpenVINO | already on branch |
| `C:\git\cib2-packv2-ov-20261024\src\plugins\intel_gpu\tests\unit\test_cases\moe_otd_native_pack_gpu_test.cpp` | same | OpenVINO | in `b7105471` |
| `C:\git\cib2-packv2-build-20261024\*.cmd` / `*.py` (stage/launch/verify/identity) | not in git / build-only | — | **NO** (private) |
| `C:\git\cib2-packv2-build-20261024\ovms-runtime\*` | build-only | — | **NO** |
| `C:\git\cib2-packv2-build-20261024\pack-build-smoke\otd-*.pack` | build-only | — | **NO** (binaries) |
| `C:\git\cib2-packv2-build-20261024\*attributed.json` / `*-pass.json` / logs | build-only | — | **NO** (optional sanitized excerpt → OVMS `docs/cib2/evidence/` later) |
| Future `pack-build-smoke-verify.json` | build-only (until copied to evidence) | — | **pending** (verify-all-packs still running; file absent) |
| Future `pack-build-smoke-plans\` | build-only | — | **absent** (pending `make-identity-plans-from-packs.py`) |
| Future `generation-<sha>\` + `active.v2.json` | build-only | — | **absent** (pending `packv2_pipeline.py seal`) |

---

## Состояние гейтов / `runtime_acceptance=NO`

| Gate | Status |
| --- | --- |
| N1 port / host codec | PASS (host + compiled objects) |
| N2 host fail-stop / guard | PASS (host); **≠** live GPU event leases |
| N3 UMA probe | PASS (sample); global reservation **NOT_DONE** |
| N4 prefetch / Path B | **OFF** |
| GPU plugin BUILD_GREEN | PASS |
| Native GPU cohort `native-cohort-121` | **121/121** (receipt `native-cohort-121.json`) |
| Plugin smoke loaded | PASS (`plugin-smoke-loaded.json`, Arc 140V) |
| OVMS BUILD_GREEN | PASS (`ovms-build.cmd`) |
| Native tuple attribution | PASS (`ovms-native-tuple-attribution.json`) |
| CPU plugin stage | PASS (`ovms-cpu-plugin-staged.json`) |
| Pack-build-only smoke | PASS — 40 packs (`ovms-pack-build-smoke-pass.json`) |
| Offline verify_all packs | **RUNNING** (`pack-build-smoke-verify.json` **absent**) |
| Identity plans / V2 seal / verify generation | **NOT PRESENT** |
| Serve matrix OFFLOAD_RATIO 20/40/75 | **NOT_RUN** |
| `runtime_acceptance` | **NO** |
| Path A | default |
| Path B | **OFF** |
| Draft PRs #29 / #10 | stay Draft; do not merge |

Backend string (attribution): `2026.4.1-5-c5fc6792a5f-dev/cib2-packv2-ov2026.4-integration-20261024`  
Loaded native SHA256 (pack-build smoke):  
`openvino.dll`=`64d68698…`, CPU=`a34fa6f6…`, GPU=`e7fc7a93…`.

---

## Pack outputs (explicit)

Dir: `C:\git\cib2-packv2-build-20261024\pack-build-smoke\` — **40** files × **418390016** bytes (~15.59 GiB):

```
otd-05c76027abf73de3.pack
otd-0c1369b772589800.pack
otd-0e3e30c4c76c8532.pack
otd-111505589154952f.pack
otd-19696590089508e1.pack
otd-1a8237c5b7660532.pack
otd-1e2cdc90958f9b39.pack
otd-1ebc440032d13215.pack
otd-2890242efbc74536.pack
otd-2d6186166670e89c.pack
otd-2fc437f09a6982d0.pack
otd-3c6515e7d18a5b92.pack
otd-42ab280c5b726786.pack
otd-44f6bdbd3132bd00.pack
otd-45b4c4233c94b839.pack
otd-56a44d77b22dceeb.pack
otd-65107c1d60274e3c.pack
otd-6654d072ace4caf1.pack
otd-6c08f41cde78bf8b.pack
otd-7d413133434f6302.pack
otd-80b145c8371fae3c.pack
otd-848aec60605d5f5e.pack
otd-8ee283fb2988b663.pack
otd-90ab0489b4703f0d.pack
otd-a22e7383071ad001.pack
otd-a76cb2aa131d5be1.pack
otd-b143a40d0ac4b901.pack
otd-b31197e0ec7f57f6.pack
otd-b6d2787e5819ecc6.pack
otd-ba62605d70ffc596.pack
otd-bc4fd618be1ac063.pack
otd-d07af34f4a2be1bd.pack
otd-d8400f65afa4b354.pack
otd-e1fef85bebc1f989.pack
otd-f02fd5fe788323c9.pack
otd-f45837da90f287fb.pack
otd-f66a8bae4232aa32.pack
otd-f73115e10b4de02d.pack
otd-f91dd5ceb1f3d09a.pack
otd-ff79e322f4fabf40.pack
```

Sample hash (one file): `otd-05c76027abf73de3.pack` SHA256=`91F3E9099D55657BB6556962A328CCB314D384D28E53C6CAA8811E2F371C2067`.

**Model source for build:** `C:\Users\testc\qwen36-35b-a3b-baseline\models\Qwen3.6-35B-A3B-int4-ov`  
**Log:** `C:\git\cib2-packv2-build-20261024\pack-build-smoke-ovms.log` — line: `CIB2 build produced or reused 40 native expert layer packs`.

### Receipts JSON (build-root)

| Receipt | Path |
| --- | --- |
| Pack-build PASS summary | `…\ovms-pack-build-smoke-pass.json` |
| Pack-build attributed modules | `…\ovms-pack-build-smoke-attributed.json` |
| CPU stage | `…\ovms-cpu-plugin-staged.json` |
| Tuple attribution | `…\ovms-native-tuple-attribution.json` |
| Runtime plugin smoke | `…\ovms-runtime-plugin-smoke-attributed.json` |
| Plugin smoke loaded | `…\plugin-smoke-loaded.json` |
| Native cohort 121 | `…\native-cohort-121.json` (+ `.xml`) |
| UMA probe | `…\uma-probe.jsonl` |

### Seal / verify generation paths (**once present**)

| Step | Expected path | Status now |
| --- | --- | --- |
| Offline pack verify | `C:\git\cib2-packv2-build-20261024\pack-build-smoke-verify.json` | **pending** (verify-all-packs running; file absent) |
| Identity plans | `C:\git\cib2-packv2-build-20261024\pack-build-smoke-plans\plans.v2.json` + `otd-*.placement` / `otd-*.residency` | **absent** |
| Seal | `packv2_pipeline.py seal --plans-dir …\pack-build-smoke-plans --native-packs …\pack-build-smoke --output-root <OUT>` → `<OUT>\generation-<sha>\manifest.v2.json` + copied packs; `<OUT>\active.v2.json` | **not run** |
| Verify generation | `packv2_pipeline.py verify --generation-dir <OUT>\generation-<sha>` | **not run** |

Note: seal requires `native_packs` **outside** generation root (pipeline enforces).

---

## Рекомендуемые следующие коммиты

### 1) OVMS (docs ledger) — this commit candidate

- **Files:** `docs/cib2/LOCAL-BUILD-FILE-MAP-20261024.md` + `docs/cib2/ATLAS-PACKV2-NATIVE-20261024.md`.
- **Exclude:** `bazel-cib2-packv2-ovms-20261024/`, binaries, packs, build-root scripts.
- Optional later: sanitized evidence under `docs/cib2/evidence/20261024/` (hashes/receipts excerpts only — not 15 GiB packs).
- Keep PR **#29 Draft**; do not flip `runtime_acceptance`.

### 2) OpenVINO

- Working tree **clean** at `b7105471` — **no commit needed** until new source changes.
- Optional docs-only note in PR #10 body pointing at pack-build evidence living under build-root (still Draft).

### 3) Stay private under build-root (never git unless explicitly promoted)

- All `*.cmd` / stage/launch/verify/identity scripts  
- `ovms-runtime\`, `openvino\` build, `sdk-2026.4\`, `python312\`, caches  
- `pack-build-smoke\*.pack`, logs, attributed JSON  
- Future plans/seal trees

### 4) Operator sequence before claiming V2 bind (documented only)

1. Wait for `verify-all-packs.py` → `pack-build-smoke-verify.json` (`ok_count==40`).  
2. `make-identity-plans-from-packs.py` → `pack-build-smoke-plans\`.  
3. `packv2_pipeline.py seal` then `verify` (identity ≠ live-trace PGP).  
4. Only then consider attributed **serve** cells OFFLOAD_RATIO 20/40/75 **without** `--build_moe_experts_pack` (per LOCAL-BUILD-FILE-MAP “Next”).  
5. Prefetch / Path B / UMA global accounting remain **OFF**.

---

## “New OVMS” atlas tip

Treat **OVMS tip `13fabc185` + Draft #29** as the “new OVMS” identity for Pack V2 CLI/`checkCib2PackBuild`; pair with OpenVINO tip **`b7105471` / Draft #10** for GPU MOE OTD. Build/runtime proof lives only under `C:\git\cib2-packv2-build-20261024` until evidence is deliberately copied into `docs/cib2/evidence/`.
