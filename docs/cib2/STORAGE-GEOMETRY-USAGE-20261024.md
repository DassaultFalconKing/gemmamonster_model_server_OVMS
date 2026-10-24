# CIB2 storage-geometry / UMA diagnostic usage (2026-10-24)

`scripts/cib2/storage_geometry.py` is a stdlib-only, read-only Windows CLI that
resolves the volume actually hosting an existing path and emits a private JSON
snapshot. It is diagnostic evidence, not runtime acceptance.

## Run

```text
C:/gm/minicpm-v47-eval/venv-pinned/Scripts/python.exe scripts/cib2/storage_geometry.py \
  --path C:/llm/models/ornith-35b-ov \
  --output C:/gm/orchestration/offload-family-20261024/reports/PGP-00-hardware.json
```

`--output` must end in `.json`. The tool refuses to write to the probed source
path or anywhere inside the probed source directory, so model weights and profile
files cannot be overwritten by the snapshot.

stdout is a sanitized summary (statuses/path only). Device serials and full detail
stay in the private JSON file. `runtime_acceptance` is always `NO`.

## What is probed

| Section | Source | Notes |
|---|---|---|
| volume mount root | `GetVolumePathNameW` | honors NTFS mounted folders; no syntactic-drive inference |
| volume filesystem | `GetVolumeInformationW` | filesystem name, label, serial, flags |
| allocation geometry | `GetDiskFreeSpaceW/ExW` | logical sector, sectors/cluster, cluster bytes, logical capacity |
| fsutil sectors | fixed `fsutil fsinfo sectorinfo C:` | access denial stays `NOT_EXPOSED` |
| device mapping | `IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS` | disk numbers and byte extents |
| device identity | `IOCTL_STORAGE_QUERY_PROPERTY(StorageDeviceProperty)` | bus/vendor/product/revision/serial when exposed |
| alignment | `IOCTL_STORAGE_QUERY_PROPERTY(StorageAccessAlignmentProperty)` | device logical/physical sector, separate from fsutil |
| physical memory | `GlobalMemoryStatusEx` | total/available physical bytes |
| system commit | `GetPerformanceInfo` | pages converted to bytes; whole-system counters |
| process commit | `GetProcessMemoryInfo` | this probe process only |
| WDDM video memory | intentionally disabled | `NOT_EXPOSED` until reviewed DXGI bindings exist |

Physical-device mapping deliberately refuses mounted-folder and UNC roots rather than substituting the parent drive letter. Volume metadata can still be queried independently. Partial disk-extent maps beyond the bounded parser limit are rejected, not presented as complete. The `GetVolumeInformationW` buffer lengths are passed as WCHAR counts, not byte counts.

All device handles use access 0. No admin escalation, I/O benchmark, write,
format, resize, service, driver, listener, model load, or BIN read is performed.

## Units and invariants

- Fields ending `_bytes` are byte counts.
- `logical_sector_size_bytes`, `cluster_allocation_unit_bytes`, and
  `device_*_sector_size_bytes` are bytes-per-unit; `sectors_per_cluster` is
  dimensionless.
- Filesystem volume totals are filesystem-logical capacity, not physical NVMe
  traffic and not device bytes moved.
- WDDM budget/usage is a separate ledger and overlaps the single physical memory
  pool. It is never added to system free/available bytes, and no extra VRAM is
  synthesized.
- Every probe record carries `status`, `probe`, and `captured_at_utc`.
  `NOT_EXPOSED` records also carry a `reason` and must not contain byte values.
- Missing privilege, unsupported platform, malformed descriptor, or denied
  command produces `NOT_EXPOSED`; no default 4096 or fabricated zero is inserted.
- No SSD NAND erase-block or flash page geometry is inferred from cluster/sector
  sizes.

## Validation

```text
rtk C:/gm/minicpm-v47-eval/venv-pinned/Scripts/python.exe -c "import py_compile; py_compile.compile(r'scripts/cib2/storage_geometry.py',doraise=True)"
rtk C:/gm/minicpm-v47-eval/venv-pinned/Scripts/python.exe -m unittest discover -s tests/cib2 -p 'test_storage_geometry*.py' -v
```

The original and independent review suites cover unit separation, malformed/denied result handling,
non-Windows behavior, Win32 struct ABI sizes, invariant rejection of fabricated
aggregate memory, and output-path protection.

## Known limitations

- `fsutil fsinfo sectorinfo` commonly requires elevation and remains
  `NOT_EXPOSED` here; the device alignment IOCTL is the separate physical-sector
  source.
- WDDM/DXGI remains `NOT_EXPOSED`; generated COM vtable/ABI code was removed from
  the live path rather than risk an unsafe call.
- Non-drive-letter roots (UNC/mounted volumes) are not mapped to a physical disk;
  the device mapping joins `NOT_EXPOSED` instead of guessing.
- Multi-extent `IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS` can produce `ERROR_MORE_DATA`; the current probe fails closed rather than publishing a partial result. Bounded retry may be added in a later worker step.
- Real Windows mounted-folder and API-ABI behavior requires operator-host validation; mock tests alone are not hardware acceptance.
- Values are point-in-time diagnostic metadata and may change between runs.
