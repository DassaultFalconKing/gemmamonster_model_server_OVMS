# UMA-00 SYSTEM — Windows 11 / Core Ultra 258V / Arc 140V

**Gate:** `UMA-00` host topology + budget inventory  
**Collected:** 2026-10-22 (local machine)  
**Method:** host-only probes; no inference; no large GPU buffer allocation; drivers/BIOS unchanged  
**Raw evidence:** `C:\gm\orchestration\uma-00-windows-20261022\evidence\`  
**Probe binary:** `C:\gm\orchestration\uma-00-windows-20261022\probe\uma_caps_probe.cpp` → `uma_caps_probe.exe`  
**Linux:** `LINUX_DEFERRED_NO_MACHINE` (not a Windows failure)

## 1. Host identity

| Field | Value |
|---|---|
| OS | Microsoft Windows 11 Home `10.0.26300` (Build 26300) |
| Machine | Micro-Star International Co., Ltd. / `Claw 8 AI+ A2VM` |
| CPU | Intel(R) Core(TM) Ultra 7 258V (8 cores) |
| Physical RAM | `33866633216` bytes (~31.54 GiB); dxdiag reports `32768MB RAM` |
| Visible RAM (OS) | `TotalVisibleMemorySize=33072884` KiB |

## 2. GPU / driver / WDDM

| Field | Value |
|---|---|
| Adapter name (WMI/dxdiag) | `Intel(R) Arc(TM) 140V GPU (16GB)` |
| PCI | `VEN_8086&DEV_64A0&SUBSYS_146C1462&REV_04` |
| Driver | `32.0.101.9150` (dxdiag Display; second string `32.0.101.8509` also present) |
| Driver model | **WDDM 3.2** |
| D3D feature levels | `12_2 … 9_1` (dxdiag) |
| WMI `AdapterRAM` | `4293918720` (~4 GiB) — **not** authoritative for UMA shared budget |

OpenCL device LUID matches DXGI adapter 0: `00000000:00011DD9`.

## 3. D3D12 architecture (adapter 0, Arc 140V)

From `ID3D12Device::CheckFeatureSupport(D3D12_FEATURE_ARCHITECTURE1)`:

| Flag | Value |
|---|---|
| **UMA** | **true** |
| **CacheCoherentUMA** | **false** |
| TileBasedRenderer | false |
| IsolatedMMU | true |

`UMA=true` does **not** imply zero-copy or coherent shared pointers. `CacheCoherentUMA=false` requires explicit GPU/CPU ordering (fences / blocking copies) for host-written bytes to become GPU-visible.

## 4. DXGI memory (adapter 0)

| Metric | Bytes | GiB (1024³) |
|---|---:|---:|
| `DXGI_ADAPTER_DESC1.DedicatedVideoMemory` | 134217728 | 0.125 |
| `DedicatedSystemMemory` | 0 | 0 |
| `SharedSystemMemory` | **29463970897** | **27.4405** |
| `LOCAL.Budget` | **28658664529** | **26.6905** |
| `LOCAL.CurrentUsage` (idle probe) | 0 | 0 |
| `LOCAL.AvailableForReservation` | 14463549992 | 13.47 |
| `LOCAL.CurrentReservation` | 0 | 0 |
| `NON_LOCAL.*` | all 0 | — |

On this UMA adapter, DXGI reports usable GPU memory almost entirely as **LOCAL budget over shared system memory**, with only 128 MiB “dedicated video”.

## 5. OpenCL / Intel USM (Arc 140V GPU device)

Platform: `Intel(R) OpenCL Graphics (integrated)` / OpenCL 3.0 NEO  
Device: `Intel(R) Arc(TM) 140V GPU (16GB)`  
`CL_DEVICE_LUID_KHR` = `00000000:00011DD9` (**matches DXGI adapter 0**)

| Property | Value |
|---|---|
| `CL_DEVICE_HOST_UNIFIED_MEMORY` | **true** |
| `cl_intel_unified_shared_memory` | **present** |
| `CL_DEVICE_SVM_CAPABILITIES` | `0x1` = **COARSE_GRAIN_BUFFER only** (no fine-grain buffer/system, no SVM atomics) |
| `CL_DEVICE_HOST_MEM_CAPABILITIES_INTEL` | `0x3` = ACCESS \| ATOMIC_ACCESS |
| `CL_DEVICE_DEVICE_MEM_CAPABILITIES_INTEL` | `0x3` |
| `CL_DEVICE_SINGLE_DEVICE_SHARED_MEM_CAPABILITIES_INTEL` | `0x3` |
| `CL_DEVICE_CROSS_DEVICE_SHARED_MEM_CAPABILITIES_INTEL` | `0x3` |
| `CL_DEVICE_SHARED_SYSTEM_MEM_CAPABILITIES_INTEL` | **`0x0` (unsupported)** |

Interpretation: explicit Intel USM host/device/shared allocations are available; **arbitrary `malloc` system pointers are not** usable as GPU shared-system USM on this device. Coarse-grain SVM only.

CPU OpenCL device (Ultra 7 258V) reports richer USM/SVM (including shared-system `0xf`); that is **not** the GPU consumer path for MoE weights.

## 6. Origin of the ~27.5 GB “GPU memory” figure

**Verdict: WDDM shared-GPU-memory reporting / pinning budget — not a physical VRAM carve-out and not an OpenVINO setting.**

Exact chain on this machine:

1. Registry (display class `0000` Arc adapter):  
   `GpuSystemMemoryPinninglimit = 87`  
   `HardwareInformation.qwMemorySize = 30064771072` (= **exactly 28 GiB**)
2. Arithmetic identity (evidence `pinning-limit-math.json`):  
   `floor(TotalPhysicalMemory * 87 / 100) = 29463970897 = DXGI SharedSystemMemory` (**Δ = 0 bytes**).
3. dxdiag: `Shared Memory: 28099 MB`, `Dedicated Memory: 128 MB`, `Display Memory: 28227 MB`.  
   Treating dxdiag “MB” as MiB: `28227/1024 ≈ 27.57 GiB` → the user-facing **~27.5 GB** figure.
4. DXGI `LOCAL.Budget ≈ 26.69 GiB` is the dynamic WDDM residency budget inside the same physical LPDDR pool (idle probe).
5. Adapter marketing string `(16GB)` ≠ measured shared budget; do not treat it as a reserved partition.
6. No OpenVINO / OVMS config key was found that sets 27.5 GiB. No BIOS/DVMT change was made or required to explain the number.

**Do not** treat ~27.5 GiB as pre-allocated exclusive GPU DRAM. It is an OS/driver **accounting ceiling** over unified system memory, competing with the OS and CPU runtime.

## 7. Source locks used for this inventory

| Artifact | Ref |
|---|---|
| ADR / handoff branch tip (docs parent) | OVMS `docs/adr-uma-arc140v-shared-memory-20261022` @ `8e03f6ae285b381a2abfb46c6c11d46be5079b27` |
| OVMS integration lock (ADR) | `integration/qwm01-otd-pack-20261022` @ `746dc833dc3bcccf64fabdb469feda9260582bae` |
| OpenVINO GPU cohort lock | `479219245f6f10b670367ad35af16513d72d2091` (`C:\gm\otd-research\openvino-cohort`) |
| Wave-01 integration candidate (integrity path) | `74003278a9c8925fcda7bc32ceb27320e59bbb1d` (`C:\gm\otd-research\wt-integration`) — inspection only |
| Golden C6 | `ba6ec792c3121850fea167fa7d7e190b25fcdc76` — READ ONLY; untouched |

## 8. UMA-00 status

`UMA-00 PASS` for host capability capture on this machine.  
GPU compute / acceptance: **not asserted** (`GPU_NOT_RUN`).
