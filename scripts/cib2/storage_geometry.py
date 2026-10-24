# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Read-only Windows storage-geometry and unified-memory probe for CIB2 PGP-00 / UMA-PGP-00.

This stdlib CLI resolves one existing path to the volume that actually hosts it and
reports, from read-only OS interfaces only:

* filesystem/volume identity (NTFS et al. name, volume serial, allocation-unit size);
* OS logical and physical sector sizes (fixed read-only ``fsutil fsinfo sectorinfo``
  query and/or ``IOCTL_STORAGE_QUERY_PROPERTY`` with zero-access handles);
* storage-device identity (bus type, vendor/product/revision, disk number) when exposed;
* physical memory, system commit, this-process commit and per-adapter WDDM video-memory
  budget/current usage remain NOT_EXPOSED pending independently reviewed DXGI bindings.

Policy enforced throughout:

* errors, missing privileges and unsupported platforms produce explicit ``NOT_EXPOSED``
  probe records with a reason --- never zeros, never a guessed ``4096``;
* the tool never reformats, resizes, writes, benchmarks I/O, loads models, spawns
  services, escalates privileges, or assumes SSD NAND erase/page geometry from cluster
  sizes;
* filesystem-logical byte counts are never reported as physical NVMe traffic;
* WDDM budget/free is reported separately and is never added to system free memory.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import platform
import re
import struct
import subprocess
import sys
import uuid
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

SCHEMA_VERSION = "cib2.storage-geometry.v1"
KIND = "cib2_storage_geometry_hardware_snapshot"
SOURCE_REVISION_REFERENCE = "eb76a74f7aa39573d452d95443e189b1f5f4d9e8"

EXPOSED = "EXPOSED"
NOT_EXPOSED = "NOT_EXPOSED"
RUNTIME_ACCEPTANCE_NO = "NO"

_IS_WINDOWS = sys.platform == "win32"
_FSUTIL_TIMEOUT_SECONDS = 30
_MAX_EXTENT_ENTRIES = 64
_MAX_DXGI_ADAPTERS = 32

_FSUTIL_SECTORINFO_PATTERN = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]*?)\s*:\s*([0-9]+)\s*$")

_IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS = 0x00560000
_IOCTL_STORAGE_QUERY_PROPERTY = 0x002D1400
_IOCTL_STORAGE_GET_DEVICE_NUMBER = 0x002D1080
_FILE_SHARE_READ = 0x00000001
_FILE_SHARE_WRITE = 0x00000002
_OPEN_EXISTING = 3

_STORAGE_DEVICE_PROPERTY = 0        # StorageDeviceProperty
_STORAGE_ACCESS_ALIGNMENT_PROPERTY = 6  # StorageAccessAlignmentProperty

_STORAGE_BUS_TYPES = {
    0: "UNKNOWN",
    1: "SCSI",
    2: "ATAPI",
    3: "ATA",
    4: "IEEE1394",
    5: "SSA",
    6: "FIBRE_CHANNEL",
    7: "USB",
    8: "RAID",
    9: "ISCSI",
    10: "SAS",
    11: "SATA",
    12: "SD",
    13: "MMC",
    14: "VIRTUAL",
    15: "FILE_BACKED_VIRTUAL",
    16: "STORAGE_SPACES",
    17: "NVME",
}

_UNIT_POLICY_NOTES = [
    "every field ending _bytes is a byte count; fields named *_sector_size_bytes and "
    "cluster_allocation_unit_bytes are bytes-per-unit; sectors_per_cluster is dimensionless",
    "WDDM video-memory budget/current usage is reported separately and is never added to "
    "system free/available bytes; no fake extra VRAM is synthesized",
    "filesystem volume total/free byte counts are filesystem-logical capacity, not "
    "physical NVMe traffic and not device bytes moved",
]

_LIMITATION_NOTES = [
    "no SSD NAND erase-block or flash page geometry is inferred from cluster/sector sizes",
    "physical sector size comes only from a device-reported read-only probe; missing "
    "privilege or unsupported probes stay NOT_EXPOSED (no default 4096 is inserted)",
    "process commit covers only this probe process, never other server/model processes",
    "no I/O benchmark is executed; nothing is written through unbuffered handles",
    "no admin escalation; probes run with zero-access handles and fixed read-only commands",
    "diagnostic metadata only: sector/cluster values may change and are not pack-layout "
    "identity",
]


class StorageGeometryError(ValueError):
    """CLI input or invariant cannot be satisfied under the read-only policy."""


class PathResolutionError(StorageGeometryError):
    """Requested path does not resolve to an existing volume-hosted file or directory."""


class FsutilParseError(StorageGeometryError):
    """fsutil sectorinfo output could not be parsed; never guess a value."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _not_exposed_record(probe: str, reason: str) -> Dict[str, Any]:
    """Build an explicit NOT_EXPOSED record; never zeros, never a guessed value."""
    return {
        "status": NOT_EXPOSED,
        "probe": probe,
        "reason": str(reason),
        "captured_at_utc": _utc_now(),
    }


def _expose_probe(probe: str, source: str,
                  collect: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    """Run one read-only probe, converting any failure into a NOT_EXPOSED record."""
    captured = _utc_now()
    try:
        data = collect()
    except Exception as exc:  # noqa: BLE001 - probe boundary; reason must surface
        record = {
            "status": NOT_EXPOSED,
            "probe": probe,
            "reason": f"{type(exc).__name__}: {exc}",
            "captured_at_utc": captured,
        }
        if source:
            record["source"] = source
        return record
    record = {"status": EXPOSED, "probe": probe, "source": source, "captured_at_utc": captured}
    record.update(data)
    return record


def resolve_path_context(path_text: str) -> Dict[str, Any]:
    """Resolve one existing path to its hosting volume root. Read-only, no escalation."""
    if not isinstance(path_text, str) or not path_text.strip():
        raise PathResolutionError("--path must be a non-empty string")
    candidate = Path(path_text).expanduser()
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PathResolutionError(f"cannot resolve path {path_text!r}: {exc}") from exc
    if not resolved.is_dir() and not resolved.is_file():
        raise PathResolutionError(
            f"path {str(resolved)!r} is neither an existing directory nor a file"
        )
    anchor = resolved.anchor or str(resolved.drive)
    if _IS_WINDOWS:
        # Path.anchor identifies the path's syntactic drive, not necessarily the
        # hosting volume. An NTFS mounted folder may live on another volume.
        # Ask Windows for the nearest volume mount point instead.
        volume_path = ctypes.create_unicode_buffer(32768)
        if not _win32_tools().kernel32.GetVolumePathNameW(
            str(resolved), volume_path, len(volume_path)
        ):
            raise PathResolutionError(
                f"GetVolumePathNameW failed for the resolved path "
                f"(Win32 error {ctypes.get_last_error()}); refusing a drive-root guess"
            )
        anchor = volume_path.value
    if not anchor:
        raise PathResolutionError(f"path {str(resolved)!r} has no filesystem volume root")
    return {
        "requested_path": path_text,
        "resolved_path": str(resolved),
        "kind": "directory" if resolved.is_dir() else "file",
        "volume_root": anchor,
        "volume_root_note": "volume actually hosting the resolved path (not assumed C:)",
    }


# ---------------------------------------------------------------------------
# Volume/filesystem and allocation-unit probes
# ---------------------------------------------------------------------------


def probe_volume_information(root: str) -> Dict[str, Any]:
    """Read-only filesystem identification of the hosting volume."""
    def _collect() -> Dict[str, Any]:
        tools = _win32_tools()
        label_buf = ctypes.create_unicode_buffer(261)
        fs_buf = ctypes.create_unicode_buffer(261)
        serial = wintypes.DWORD()
        max_component = wintypes.DWORD()
        flags = wintypes.DWORD()
        if not tools.kernel32.GetVolumeInformationW(
            root, label_buf, len(label_buf), ctypes.byref(serial),
            ctypes.byref(max_component), ctypes.byref(flags), fs_buf,
            len(fs_buf),
        ):
            raise OSError(ctypes.get_last_error(), "GetVolumeInformationW failed")
        serial_value = serial.value
        return {
            "filesystem_name": fs_buf.value,
            "volume_label": label_buf.value,
            "volume_serial_number_raw": serial_value,
            "volume_serial_number_formatted": "%04X-%04X" % (
                serial_value & 0xFFFF, (serial_value >> 16) & 0xFFFF,
            ),
            "max_component_length": max_component.value,
            "filesystem_flags": flags.value,
        }

    return _expose_probe(f"GetVolumeInformationW({root!r})",
                         "Win32 API: kernel32 GetVolumeInformationW", _collect)


def allocation_geometry_from_raw(sectors_per_cluster: int, bytes_per_sector: int,
                                 free_clusters: int, total_clusters: int,
                                 total_logical_bytes: int, available_bytes: int,
                                 free_logical_bytes: int) -> Dict[str, Any]:
    """Convert raw GetDiskFreeSpace/Ex values, keeping units explicitly separated."""
    if sectors_per_cluster <= 0 or bytes_per_sector <= 0:
        raise StorageGeometryError(
            "GetDiskFreeSpaceW reported zero sector/cluster fields; refusing to guess"
        )
    cluster_allocation_unit_bytes = sectors_per_cluster * bytes_per_sector
    return {
        "logical_sector_size_bytes": bytes_per_sector,
        "sectors_per_cluster": sectors_per_cluster,
        "cluster_allocation_unit_bytes": cluster_allocation_unit_bytes,
        "free_clusters": free_clusters,
        "total_clusters": total_clusters,
        "volume_total_logical_bytes": total_logical_bytes,
        "volume_available_to_caller_logical_bytes": available_bytes,
        "volume_free_logical_bytes": free_logical_bytes,
        "volume_total_from_cluster_math_bytes": total_clusters * cluster_allocation_unit_bytes,
    }


def probe_volume_allocation(root: str) -> Dict[str, Any]:
    """Read-only allocation-unit (NTFS cluster) and filesystem-logical capacity probe."""
    def _collect() -> Dict[str, Any]:
        tools = _win32_tools()
        spc = wintypes.DWORD()
        bps = wintypes.DWORD()
        free_clusters = wintypes.DWORD()
        total_clusters = wintypes.DWORD()
        if not tools.kernel32.GetDiskFreeSpaceW(
            root, ctypes.byref(spc), ctypes.byref(bps),
            ctypes.byref(free_clusters), ctypes.byref(total_clusters),
        ):
            raise OSError(ctypes.get_last_error(), "GetDiskFreeSpaceW failed")
        total_bytes = ctypes.c_uint64()
        available = ctypes.c_uint64()
        free_bytes = ctypes.c_uint64()
        if not tools.kernel32.GetDiskFreeSpaceExW(
            root, ctypes.byref(available), ctypes.byref(total_bytes),
            ctypes.byref(free_bytes),
        ):
            raise OSError(ctypes.get_last_error(), "GetDiskFreeSpaceExW failed")
        geometry = allocation_geometry_from_raw(
            spc.value, bps.value, free_clusters.value, total_clusters.value,
            total_bytes.value, available.value, free_bytes.value,
        )
        geometry["capacity_note"] = (
            "allocation unit from GetDiskFreeSpaceW; volume byte totals are "
            "filesystem-logical capacity, not physical NVMe traffic"
        )
        return geometry

    return _expose_probe(f"GetDiskFreeSpaceW/GetDiskFreeSpaceExW({root!r})",
                         "Win32 API: kernel32 GetDiskFreeSpaceW/GetDiskFreeSpaceExW",
                         _collect)


def parse_fsutil_sectorinfo(text: str) -> Dict[str, int]:
    """Parse ``fsutil fsinfo sectorinfo`` output; refuse to guess on any failure."""
    if not isinstance(text, str) or not text.strip():
        raise FsutilParseError("fsutil output was empty")
    fields: Dict[str, int] = {}
    for line in text.splitlines():
        match = _FSUTIL_SECTORINFO_PATTERN.match(line)
        if match:
            fields[match.group(1)] = int(match.group(2))
    if not fields:
        raise FsutilParseError("fsutil output contained no 'key : integer' lines")
    if "LogicalSectorSize" not in fields:
        raise FsutilParseError("fsutil output missing LogicalSectorSize; refusing to "
                               "default it")
    return fields


def probe_sector_sizes_fsutil(root: str) -> Dict[str, Any]:
    """Fixed read-only ``fsutil fsinfo sectorinfo`` probe for OS logical/physical sectors."""
    try:
        fsutil_root = _clean_root(root)
    except StorageGeometryError:
        fsutil_root = root
    command = ["fsutil", "fsinfo", "sectorinfo", fsutil_root]
    source = "fixed read-only fsutil fsinfo sectorinfo command"

    def _collect() -> Dict[str, Any]:
        try:
            proc = subprocess.run(  # noqa: S603 - fixed read-only command, no shell
                command, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=_FSUTIL_TIMEOUT_SECONDS, check=False,
                creationflags=0x08000000 if _IS_WINDOWS else 0,  # CREATE_NO_WINDOW
            )
        except FileNotFoundError as exc:
            raise FsutilParseError(f"fsutil not available on this host: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise FsutilParseError("fsutil fsinfo sectorinfo timed out") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip().splitlines()
            reason = detail[0] if detail else f"fsutil exited with code {proc.returncode}"
            return {
                "status": NOT_EXPOSED,
                "reason": reason,
                "explanation": (
                    "fsutil fsinfo sectorinfo commonly requires an elevated session; "
                    "this tool never escalates privileges, so the probe records "
                    "NOT_EXPOSED instead of a default value"
                ),
                "exit_code": proc.returncode,
                "probe_command": " ".join(command),
            }
        fields = parse_fsutil_sectorinfo(proc.stdout)
        payload: Dict[str, Any] = {"raw_fields": fields, "exit_code": proc.returncode}
        if "LogicalSectorSize" in fields:
            payload["logical_sector_size_bytes"] = fields["LogicalSectorSize"]
        if "PhysicalSectorSize" in fields:
            payload["device_reported_physical_sector_size_bytes"] = fields["PhysicalSectorSize"]
        payload["nand_note"] = (
            "reported sector sizes are the OS/device interface sizes; they do not expose "
            "SSD NAND erase-block or flash page geometry"
        )
        return payload

    return _expose_probe(f"fsutil fsinfo sectorinfo {root!r}", source, _collect)


# ---------------------------------------------------------------------------
# Win32 handle plumbing (read-only, zero-access handles, no escalation)
# ---------------------------------------------------------------------------


class _Tools:
    """Lazy-bound kernel32/psapi prototypes so import stays safe on non-Windows hosts."""

    def __init__(self) -> None:
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.psapi = ctypes.WinDLL("psapi", use_last_error=True)
        k = self.kernel32
        k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID]
        k.CreateFileW.restype = wintypes.HANDLE
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CloseHandle.restype = wintypes.BOOL
        k.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID,
                                      wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                      ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
        k.DeviceIoControl.restype = wintypes.BOOL
        k.GetDiskFreeSpaceW.argtypes = [wintypes.LPCWSTR, wintypes.LPDWORD,
                                        wintypes.LPDWORD, wintypes.LPDWORD, wintypes.LPDWORD]
        k.GetDiskFreeSpaceW.restype = wintypes.BOOL
        k.GetDiskFreeSpaceExW.argtypes = [wintypes.LPCWSTR,
                                          ctypes.POINTER(ctypes.c_uint64),
                                          ctypes.POINTER(ctypes.c_uint64),
                                          ctypes.POINTER(ctypes.c_uint64)]
        k.GetDiskFreeSpaceExW.restype = wintypes.BOOL
        k.GetVolumeInformationW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR,
                                            wintypes.DWORD, wintypes.LPDWORD,
                                            wintypes.LPDWORD, wintypes.LPDWORD,
                                            wintypes.LPWSTR, wintypes.DWORD]
        k.GetVolumeInformationW.restype = wintypes.BOOL
        k.GetVolumePathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR,
                                        wintypes.DWORD]
        k.GetVolumePathNameW.restype = wintypes.BOOL
        k.GlobalMemoryStatusEx.argtypes = [ctypes.c_void_p]
        k.GlobalMemoryStatusEx.restype = wintypes.BOOL
        k.GetCurrentProcess.restype = wintypes.HANDLE
        p = self.psapi
        p.GetPerformanceInfo.argtypes = [ctypes.c_void_p, wintypes.DWORD]
        p.GetPerformanceInfo.restype = wintypes.BOOL
        p.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        p.GetProcessMemoryInfo.restype = wintypes.BOOL


_TOOLS: Optional[_Tools] = None


def _win32_tools() -> _Tools:
    global _TOOLS
    if not _IS_WINDOWS:
        raise OSError("non-Windows platform: read-only Win32 probes unavailable")
    if _TOOLS is None:
        _TOOLS = _Tools()
    return _TOOLS


class _ZeroAccessDeviceHandle:
    """Opens one device path with access 0 for read-only DeviceIoControl queries."""

    def __init__(self, device_path: str) -> None:
        self.device_path = device_path
        handle = _win32_tools().kernel32.CreateFileW(
            device_path, 0, _FILE_SHARE_READ | _FILE_SHARE_WRITE, None,
            _OPEN_EXISTING, 0, None,
        )
        invalid_values = (0, 0xFFFFFFFF, 18446744073709551615)
        raw = handle.value if hasattr(handle, "value") else int(handle or 0)
        if handle is None or raw in invalid_values:
            raise OSError(
                ctypes.get_last_error(),
                f"CreateFileW failed or returned invalid handle for {device_path!r}",
            )
        self.handle = handle

    def close(self) -> None:
        if self.handle is not None:
            _win32_tools().kernel32.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self) -> "_ZeroAccessDeviceHandle":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _device_io_control_read_only(handle: Any, ioctl: int, in_buffer: bytes,
                                 out_size: int) -> bytes:
    out = (ctypes.c_ubyte * out_size)()
    returned = wintypes.DWORD(0)
    in_ptr = ctypes.create_string_buffer(in_buffer, max(len(in_buffer), 1))
    ok = _win32_tools().kernel32.DeviceIoControl(
        handle, ioctl, in_ptr, len(in_buffer), out, out_size,
        ctypes.byref(returned), None,
    )
    if not ok:
        raise OSError(ctypes.get_last_error(), f"DeviceIoControl(0x{ioctl:08X}) failed")
    if returned.value > out_size:
        raise StorageGeometryError("DeviceIoControl reported impossible return size")
    return bytes(out[: returned.value])


def _clean_root(root: str) -> str:
    """Normalize a volume anchor to ``X:`` for ``\\\\.\\X:`` device paths."""
    text = (root or "").strip()
    # A mounted folder such as C:\\MountD\\ is NOT C:'s root. Mapping it
    # to PhysicalDrive(C:) would publish an incorrect disk identity.
    match = re.fullmatch(r"([A-Za-z]):[\\\\/]*", text)
    if match:
        return match.group(1).upper() + ":"
    raise StorageGeometryError(
        f"volume root {root!r} is not a drive-letter volume; read-only device mapping "
        "for non-drive-letter (UNC/mounted) roots is not implemented, so the probe joins "
        "NOT_EXPOSED instead of guessing"
    )


# ---------------------------------------------------------------------------
# Device identity parsing (pure helpers; unit-tested)
# ---------------------------------------------------------------------------


def parse_volume_disk_extents(buffer: bytes) -> Dict[str, Any]:
    """Parse IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS output."""
    if len(buffer) < 4:
        raise StorageGeometryError("disk-extents output shorter than the count field")
    count = struct.unpack_from("<I", buffer, 0)[0]
    if count > _MAX_EXTENT_ENTRIES:
        raise StorageGeometryError(
            f"volume has {count} disk extents, exceeding the "
            f"{_MAX_EXTENT_ENTRIES}-extent read-only safety bound; refusing "
            "a partial physical-device mapping"
        )
    # VOLUME_DISK_EXTENTS has 4 bytes of padding after NumberOfDiskExtents so
    # the DISK_EXTENT array starts at offset 8. Each DISK_EXTENT is 24 bytes:
    # DWORD DiskNumber, 4 bytes padding, two 8-byte LARGE_INTEGER fields.
    extent_array_offset = 8
    extent_size = 24
    usable = min(
        count, _MAX_EXTENT_ENTRIES,
        max((len(buffer) - extent_array_offset) // extent_size, 0),
    )
    if usable < min(count, _MAX_EXTENT_ENTRIES):
        raise StorageGeometryError(
            f"disk-extents buffer is truncated: reported {count} extents, "
            f"only {usable} fit in {len(buffer)} bytes"
        )
    extents: List[Dict[str, Any]] = []
    disk_numbers: List[int] = []
    for index in range(usable):
        base = extent_array_offset + index * extent_size
        disk_number = struct.unpack_from("<I", buffer, base)[0]
        starting_offset, extent_length = struct.unpack_from("<qq", buffer, base + 8)
        disk_numbers.append(disk_number)
        extents.append({
            "disk_number": disk_number,
            "starting_offset_bytes": starting_offset,
            "extent_length_bytes": extent_length,
        })
    return {
        "extent_count_reported": count,
        "extents_truncated": usable < count,
        "extents": extents,
        "disk_numbers": disk_numbers,
        "single_physical_disk": len(set(disk_numbers)) == 1 if count else False,
    }


def parse_storage_device_descriptor(buffer: bytes) -> Dict[str, Any]:
    """Parse STORAGE_DEVICE_DESCRIPTOR fields/strings (ntddstor.h layout)."""
    if len(buffer) < 36:
        raise StorageGeometryError(
            f"storage descriptor shorter than its fixed header: {len(buffer)} bytes"
        )
    version, size, device_type, _modifier = struct.unpack_from("<IIBB", buffer, 0)
    removable, queued = buffer[10], buffer[11]
    vendor_offset, product_offset, revision_offset, serial_offset = struct.unpack_from(
        "<IIII", buffer, 12
    )
    bus_raw = buffer[28]
    raw_length = struct.unpack_from("<I", buffer, 32)[0]

    def _string(offset: int) -> Optional[str]:
        if offset <= 0 or offset >= len(buffer):
            return None
        end = buffer.find(b"\x00", offset)
        piece = buffer[offset: end if end != -1 else len(buffer)]
        value = piece.decode("ascii", "replace").strip()
        return value or None

    # Version/Size sanity: reject values that could indicate a mid-parse layout change.
    if version < 36 or size < 36 or size > len(buffer):
        raise StorageGeometryError(
            f"storage descriptor validation failed (version={version}, size={size}, "
            f"buffer={len(buffer)}); NOT_EXPOSED rather than misparse"
        )
    return {
        "descriptor_version": version,
        "descriptor_size": size,
        "device_type": device_type,
        "removable_media": bool(removable),
        "command_queueing": bool(queued),
        "bus_type_raw": bus_raw,
        "bus_type_label": _STORAGE_BUS_TYPES.get(bus_raw, f"BUS_TYPE_{bus_raw}"),
        "vendor_id": _string(vendor_offset),
        "product_id": _string(product_offset),
        "product_revision": _string(revision_offset),
        "serial_number": _string(serial_offset),
        "serial_number_exposed": serial_offset > 0,
        "raw_properties_length": raw_length,
    }


def parse_access_alignment_descriptor(buffer: bytes) -> Dict[str, Any]:
    """Parse STORAGE_ACCESS_ALIGNMENT_DESCRIPTOR per ntddstor.h (all-ULONG layout):

    Version(0) Size(4) BytesPerCacheLine(8) BytesOffsetForCacheAlignment(12)
    BytesPerLogicalSector(16) BytesPerPhysicalSector(20) BytesOffsetForSectorAlignment(24).
    """
    if len(buffer) < 28:
        raise StorageGeometryError(
            f"access-alignment descriptor shorter than documented layout: {len(buffer)} bytes"
        )
    version, size, cache_line, cache_offset, logical, physical, logical_start = (
        struct.unpack_from("<7I", buffer, 0)
    )
    # Observed Windows returns Version == Size == 28 for this descriptor;
    # accept the documented legacy version 1 as well, but reject anything else
    # rather than misparse a different property payload.
    if version not in (1, 28) or size < 28 or size > len(buffer):
        raise StorageGeometryError(
            "access-alignment descriptor version/size validation failed; refusing to "
            "report because offsets could not be verified"
        )
    if not _plausible_sector_bytes(logical) or not _plausible_sector_bytes(physical):
        raise StorageGeometryError(
            "parsed sector sizes failed plausibility validation (powers of two, "
            "128..65536 expected); NOT_EXPOSED rather than reporting a misparse"
        )
    return {
        "descriptor_version": version,
        "descriptor_size": size,
        "bytes_per_cache_line": cache_line,
        "bytes_offset_for_cache_alignment": cache_offset,
        "device_logical_sector_size_bytes": logical,
        "device_physical_sector_size_bytes": physical,
        "device_bytes_offset_for_sector_alignment": logical_start,
        "nand_note": "physical sector here is the interface geometry; it does not expose "
                     "NAND erase-block or flash page sizes",
    }


def _plausible_sector_bytes(value: int) -> bool:
    if value < 128 or value > 65536:
        return False
    return value & (value - 1) == 0


# ---------------------------------------------------------------------------
# Storage-device identity probe
# ---------------------------------------------------------------------------


class _StoragePropertyQuery(ctypes.Structure):
    # STORAGE_PROPERTY_QUERY is 12 bytes: PropertyId, QueryType, then a
    # one-byte AdditionalParameters array padded to DWORD alignment.
    _fields_ = [("property_id", wintypes.DWORD), ("query_type", wintypes.DWORD),
                ("additional_parameters", wintypes.BYTE * 1)]


def _query_storage_device_property(handle: Any, property_id: int, out_size: int) -> bytes:
    query = _StoragePropertyQuery(property_id, 0)  # 0 = PropertyStandardQuery
    return _device_io_control_read_only(handle, _IOCTL_STORAGE_QUERY_PROPERTY,
                                        bytes(bytearray(query)), out_size)


def _device_identity_record(disk_number: int) -> Dict[str, Any]:
    """Read-only identity + alignment probes for one physical disk (per-disk status)."""
    device_path = f"\\\\.\\PhysicalDrive{disk_number}"
    record: Dict[str, Any] = {"disk_number": disk_number, "device_path": device_path}
    try:
        with _ZeroAccessDeviceHandle(device_path) as disk_handle:
            descriptor = parse_storage_device_descriptor(
                _query_storage_device_property(disk_handle.handle,
                                               _STORAGE_DEVICE_PROPERTY, 4096))
            record["identity"] = {"status": EXPOSED, "probe": (
                f"IOCTL_STORAGE_QUERY_PROPERTY(StorageDeviceProperty) {device_path!r} "
                "with access-0 handle"), "captured_at_utc": _utc_now(), **descriptor}
    except Exception as exc:  # noqa: BLE001
        record["identity"] = {
            "status": NOT_EXPOSED,
            "probe": f"IOCTL_STORAGE_QUERY_PROPERTY(StorageDeviceProperty) "
                     f"{device_path!r}",
            "reason": f"{type(exc).__name__}: {exc}",
            "captured_at_utc": _utc_now(),
        }
    try:
        with _ZeroAccessDeviceHandle(device_path) as disk_handle:
            alignment = parse_access_alignment_descriptor(
                _query_storage_device_property(disk_handle.handle,
                                               _STORAGE_ACCESS_ALIGNMENT_PROPERTY, 64))
        record["alignment"] = {"status": EXPOSED, "probe": (
            f"IOCTL_STORAGE_QUERY_PROPERTY(StorageAccessAlignmentProperty) "
            f"{device_path!r} with access-0 handle"),
            "captured_at_utc": _utc_now(), **alignment}
    except Exception as exc:  # noqa: BLE001
        record["alignment"] = {
            "status": NOT_EXPOSED,
            "probe": f"IOCTL_STORAGE_QUERY_PROPERTY(StorageAccessAlignmentProperty) "
                     f"{device_path!r}",
            "reason": f"{type(exc).__name__}: {exc}",
            "captured_at_utc": _utc_now(),
        }
    return record


def probe_device_identity(root: str) -> Dict[str, Any]:
    """Read-only mapping volume -> physical disk(s) and device identity when exposed."""
    def _collect() -> Dict[str, Any]:
        volume_device_path = f"\\\\.\\{_clean_root(root)}"
        with _ZeroAccessDeviceHandle(volume_device_path) as volume_handle:
            extents_buffer = _device_io_control_read_only(
                volume_handle.handle, _IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS, b"", 8192,
            )
            cross_check = _query_volume_device_number(volume_handle.handle)
        extents = parse_volume_disk_extents(extents_buffer)
        if not extents["disk_numbers"]:
            raise StorageGeometryError("volume extent mapping returned zero disks")
        disks = [_device_identity_record(number)
                 for number in sorted(set(extents["disk_numbers"]))]
        mapping = {
            "volume_device_path": volume_device_path,
            "extent_count_reported": extents["extent_count_reported"],
            "extents_truncated": extents["extents_truncated"],
            "single_physical_disk": extents["single_physical_disk"],
            "disk_numbers": extents["disk_numbers"],
            "get_device_number_cross_check": cross_check,
        }
        return {"disk_extent_mapping": mapping, "disks": disks, "extents": extents["extents"]}

    return _expose_probe(
        "IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS + IOCTL_STORAGE_QUERY_PROPERTY "
        "(zero-access handles)",
        "Win32 DeviceIoControl read-only queries (no admin escalation)",
        _collect,
    )


def _query_volume_device_number(handle: Any) -> Dict[str, Any]:
    """Optional IOCTL_STORAGE_GET_DEVICE_NUMBER cross-check of the extent mapping."""
    try:
        buffer = _device_io_control_read_only(
            handle, _IOCTL_STORAGE_GET_DEVICE_NUMBER, b"", 16,
        )
        if len(buffer) < 12:
            raise StorageGeometryError(
                f"GET_DEVICE_NUMBER output too short: {len(buffer)} bytes"
            )
        device_type_raw, device_number, partition_number = struct.unpack_from("<3I", buffer, 0)
        return {
            "status": "EXPOSED",
            "probe": "IOCTL_STORAGE_GET_DEVICE_NUMBER (access-0 volume handle)",
            "captured_at_utc": _utc_now(),
            "device_type_raw": device_type_raw,
            "device_number": device_number,
            "partition_number": partition_number,
        }
    except Exception as exc:  # noqa: BLE001 - cross-check is best-effort only
        return {"status": NOT_EXPOSED, "reason": f"{type(exc).__name__}: {exc}",
                "probe": "IOCTL_STORAGE_GET_DEVICE_NUMBER (access-0 volume handle)",
                "captured_at_utc": _utc_now(),
                "note": "cross-check only; extent mapping remains authoritative"}

# ---------------------------------------------------------------------------
# Memory probes
# ---------------------------------------------------------------------------


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("cb_length", wintypes.DWORD), ("memory_load_percent", wintypes.DWORD),
        ("total_physical", ctypes.c_uint64), ("available_physical", ctypes.c_uint64),
        ("total_pagefile", ctypes.c_uint64), ("available_pagefile", ctypes.c_uint64),
        ("total_virtual", ctypes.c_uint64), ("available_virtual", ctypes.c_uint64),
        ("available_extended_virtual", ctypes.c_uint64),
    ]


class _PerformanceInformation(ctypes.Structure):
    # Layout verified on Windows 10/11 x64 hosts by reading the raw buffer that
    # GetPerformanceInfo returned: cb DWORD (the OS writes 104), then ten SIZE_T
    # counters at offsets 8..80, then DWORD HandleCount/ProcessCount/ThreadCount
    # at 88/92/96, padded to sizeof = 104. There is no PhysicalPeak member here
    # (the old all-DWORD 60-byte variant fails with ERROR_BAD_LENGTH).
    # Empirical invariants observed: kernel_total == kernel_paged + kernel_nonpaged
    # exactly; physical_total x page_size == GlobalMemoryStatusEx total.
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("commit_total", ctypes.c_size_t), ("commit_limit", ctypes.c_size_t),
        ("commit_peak", ctypes.c_size_t),
        ("physical_total", ctypes.c_size_t), ("physical_available", ctypes.c_size_t),
        ("system_cache", ctypes.c_size_t),
        ("kernel_total", ctypes.c_size_t), ("kernel_paged", ctypes.c_size_t),
        ("kernel_nonpaged", ctypes.c_size_t),
        ("page_size", ctypes.c_size_t),
        ("handle_count", wintypes.DWORD), ("process_count", wintypes.DWORD),
        ("thread_count", wintypes.DWORD),
    ]


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("page_fault_count", wintypes.DWORD),
        ("peak_working_set", ctypes.c_size_t), ("working_set", ctypes.c_size_t),
        ("quota_peak_paged_pool", ctypes.c_size_t),
        ("quota_paged_pool", ctypes.c_size_t),
        ("quota_peak_non_paged_pool", ctypes.c_size_t),
        ("quota_non_paged_pool", ctypes.c_size_t),
        ("pagefile_usage", ctypes.c_size_t), ("peak_pagefile_usage", ctypes.c_size_t),
    ]


def probe_physical_memory() -> Dict[str, Any]:
    """GlobalMemoryStatusEx: physical memory and Windows memory-load indicator."""
    def _collect() -> Dict[str, Any]:
        status = _MemoryStatusEx()
        status.cb_length = ctypes.sizeof(status)
        if not _win32_tools().kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError(ctypes.get_last_error(), "GlobalMemoryStatusEx failed")
        return {
            "total_physical_bytes": status.total_physical,
            "available_physical_bytes": status.available_physical,
            "memory_load_percent_windows": status.memory_load_percent,
            "pagefile_committed_limit_reported_bytes": status.total_pagefile,
            "pagefile_committed_available_reported_bytes": status.available_pagefile,
            "note": (
                "single physical pool; this record is a separate ledger and is never "
                "combined with the WDDM video-memory record"
            ),
        }

    return _expose_probe("GlobalMemoryStatusEx",
                         "Win32 API: kernel32 GlobalMemoryStatusEx", _collect)


def system_commit_from_performance_fields(commit_total: int, commit_limit: int,
                                          commit_peak: int, physical_total: int,
                                          physical_available: int, system_cache: int,
                                          kernel_total: int, kernel_paged: int,
                                          kernel_nonpaged: int, page_size: int,
                                          handle_count: int, process_count: int,
                                          thread_count: int) -> Dict[str, Any]:
    """Convert GetPerformanceInfo page counts into byte fields (pure helper; tested).

    Memory counters other than the last three are PAGES; converting to bytes requires
    multiplying by the reported page size. Counts stay counts --- units stay separated.
    """
    if page_size <= 0:
        raise StorageGeometryError("GetPerformanceInfo reported zero page size")
    return {
        "system_commit_current_bytes": commit_total * page_size,
        "system_commit_limit_bytes": commit_limit * page_size,
        "system_commit_peak_bytes": commit_peak * page_size,
        "physical_total_bytes": physical_total * page_size,
        "physical_available_bytes": physical_available * page_size,
        "system_cache_standing_bytes": system_cache * page_size,
        "kernel_total_bytes": kernel_total * page_size,
        "kernel_paged_bytes": kernel_paged * page_size,
        "kernel_nonpaged_bytes": kernel_nonpaged * page_size,
        "page_size_bytes": page_size,
        "handle_count": handle_count,
        "process_count": process_count,
        "thread_count": thread_count,
    }


def probe_system_commit() -> Dict[str, Any]:
    """GetPerformanceInfo: system commit counters (pages converted to bytes)."""
    def _collect() -> Dict[str, Any]:
        info = _PerformanceInformation()
        assert ctypes.sizeof(info) == 104, "PERFORMANCE_INFORMATION layout drifted"
        info.cb = ctypes.sizeof(info)
        crosscheck = _MemoryStatusEx()
        crosscheck.cb_length = ctypes.sizeof(crosscheck)
        if not _win32_tools().kernel32.GlobalMemoryStatusEx(ctypes.byref(crosscheck)):
            raise OSError(ctypes.get_last_error(), "GlobalMemoryStatusEx (cross-check) failed")
        if not _win32_tools().psapi.GetPerformanceInfo(ctypes.byref(info), info.cb):
            raise OSError(ctypes.get_last_error(), "GetPerformanceInfo failed")
        derived_total = info.physical_total * info.page_size
        if abs(derived_total - crosscheck.total_physical) > crosscheck.total_physical // 1000:
            raise StorageGeometryError(
                "GetPerformanceInfo physical_total cross-check vs GlobalMemoryStatusEx "
                f"failed ({derived_total} vs {crosscheck.total_physical}); refusing to "
                "report rather than publishing a misparsed layout"
            )
        derived_available = info.physical_available * info.page_size
        if abs(derived_available
               - crosscheck.available_physical) > crosscheck.total_physical // 10000:
            raise StorageGeometryError(
                "GetPerformanceInfo physical_available cross-check vs "
                f"GlobalMemoryStatusEx failed ({derived_available} vs "
                f"{crosscheck.available_physical}); refusing to report"
            )
        kernel_sum = info.kernel_paged + info.kernel_nonpaged
        if abs(kernel_sum - info.kernel_total) > 0:
            raise StorageGeometryError(
                "GetPerformanceInfo kernel_total != kernel_paged + kernel_nonpaged "
                f"({info.kernel_total} != {kernel_sum}); refusing to report a "
                "possibly misparsed layout"
            )
        return {
            **system_commit_from_performance_fields(
                info.commit_total, info.commit_limit, info.commit_peak,
                info.physical_total, info.physical_available, info.system_cache,
                info.kernel_total, info.kernel_paged, info.kernel_nonpaged,
                info.page_size, info.handle_count, info.process_count, info.thread_count,
            ),
            "note": "commit counters cover the whole system; bytes = pages x page size",
            "layout_cross_check": {
                "method": "GetPerformanceInfo physical totals vs GlobalMemoryStatusEx "
                          "within tolerance; kernel_total == kernel_paged + "
                          "kernel_nonpaged asserted by struct layout verification",
                "globalmemory_total_physical_bytes": crosscheck.total_physical,
                "globalmemory_available_physical_bytes": crosscheck.available_physical,
                "result": "PASSED",
            },
        }

    return _expose_probe("GetPerformanceInfo", "Win32 API: psapi GetPerformanceInfo",
                         _collect)


def probe_process_commit() -> Dict[str, Any]:
    """GetProcessMemoryInfo for THIS probe process only."""
    def _collect() -> Dict[str, Any]:
        tools = _win32_tools()
        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        handle = tools.kernel32.GetCurrentProcess()
        if not tools.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters),
                                                counters.cb):
            raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
        return {
            "process_commit_current_bytes": counters.pagefile_usage,
            "process_commit_peak_bytes": counters.peak_pagefile_usage,
            "working_set_bytes": counters.working_set,
            "page_fault_count": counters.page_fault_count,
            "note": ("this record covers this geometry-probe process only, never "
                     "model/server processes"),
        }

    return _expose_probe("GetProcessMemoryInfo(current process)",
                         "Win32 API: psapi GetProcessMemoryInfo", _collect)


# ---------------------------------------------------------------------------
# WDDM (DXGI) probe: separate ledger, never added to system free
# ---------------------------------------------------------------------------

_GUID_IDXGIFACTORY1 = "{770aae78-f26f-4db7-a266-5322e5496962}"
_GUID_IDXGIADAPTER3 = "{645967a4-0b98-4857-9049-0a3f32b38a0f}"


def probe_wddm_video_memory() -> Dict[str, Any]:
    """WDDM remains unknown until an independently reviewed DXGI binding exists."""
    return _not_exposed_record(
        "DXGI QueryVideoMemoryInfo",
        "DXGI probe disabled by coordinator: generated COM vtable slots and ABI "
        "were incorrect. No native DXGI call is executed. Requires separately "
        "reviewed bindings and process-local versus adapter-wide attribution.",
    )


def _iter_records(node: Any) -> Iterable[Dict[str, Any]]:
    stack = [node]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            if item.get("status") is not None:
                yield item
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)


_UNIT_POLICY_FORBIDDEN_KEYS = (
    "combined_free_bytes",
    "total_free_with_wddm",
    "wddm_free_plus_system_free",
    "combined_available_bytes",
)


def _iter_keys(node: Any) -> Iterable[str]:
    stack = [node]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, value in item.items():
                yield key
                stack.append(value)
        elif isinstance(item, list):
            stack.extend(item)


def validate_report(report: Dict[str, Any]) -> List[str]:
    """Static invariants: record statuses, provenance, no fabricated budget/capacity."""
    if report.get("schema") != SCHEMA_VERSION or report.get("kind") != KIND:
        raise StorageGeometryError("unexpected report schema/kind")
    if report.get("runtime_acceptance") != RUNTIME_ACCEPTANCE_NO:
        raise StorageGeometryError("runtime_acceptance must remain NO")
    provenance = report.get("provenance") or {}
    if provenance.get("read_only") is not True:
        raise StorageGeometryError("provenance must record that the probe is read-only")
    if provenance.get("admin_escalation_used"):
        raise StorageGeometryError("no admin escalation is ever allowed")
    if not report.get("generated_at_utc"):
        raise StorageGeometryError("report missing generated_at_utc")
    violations: List[str] = []
    for record in _iter_records(report):
        status = record.get("status")
        if status not in (EXPOSED, NOT_EXPOSED):
            violations.append(f"probe record has unsupported status {status!r}: {record}")
            continue
        if not record.get("captured_at_utc"):
            violations.append(f"probe record missing captured_at_utc: {record}")
        if status == NOT_EXPOSED:
            if not record.get("reason"):
                violations.append(f"NOT_EXPOSED record missing reason: {record}")
            if not record.get("probe"):
                violations.append(f"NOT_EXPOSED record missing probe name: {record}")
            for key, value in record.items():
                if key.endswith("_bytes"):
                    violations.append(
                        f"NOT_EXPOSED record fabricates a byte value {key}={value!r}"
                    )
    for key in _iter_keys(report):
        if key in _UNIT_POLICY_FORBIDDEN_KEYS:
            violations.append(f"report contains forbidden unit-mixing key {key!r}")
    return violations


def build_report(path_text: str) -> Dict[str, Any]:
    """Assemble one complete hardware snapshot. Every probe is read-only."""
    context = resolve_path_context(path_text)
    root = context["volume_root"]
    report: Dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "kind": KIND,
        "generated_at_utc": _utc_now(),
        "source_revision_reference": {
            "revision": SOURCE_REVISION_REFERENCE,
            "reference_only": True,
            "note": "design-context reference only; not a build identity of this snapshot",
        },
        "provenance": {
            "python_version": platform.python_version(),
            "platform_release": platform.platform(),
            "machine": platform.machine(),
            "timestamp_format": "UTC (ISO 8601, Z suffix)",
            "read_only": True,
            "admin_escalation_used": False,
            "network_used": False,
            "probes_are_point_in_time": True,
        },
        "path": context,
        "volume": {
            "filesystem_information": probe_volume_information(root),
            "allocation_geometry": probe_volume_allocation(root),
            "sector_sizes_fsutil": probe_sector_sizes_fsutil(root),
        },
        "device": probe_device_identity(root),
        "memory": {
            "physical": probe_physical_memory(),
            "system_commit": probe_system_commit(),
            "process_commit": probe_process_commit(),
            "video_wddm_always_separate_ledger": probe_wddm_video_memory(),
        },
        "unit_policy": _UNIT_POLICY_NOTES,
        "limitations": _LIMITATION_NOTES,
        "runtime_acceptance": RUNTIME_ACCEPTANCE_NO,
    }
    violations = validate_report(report)
    if violations:
        raise StorageGeometryError("internal invariants violated: " + "; ".join(violations))
    return report


def summarize_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Public stdout summary: statuses and path context only --- no device serials."""
    statuses: Dict[str, Any] = {}
    volume_sections = report.get("volume", {})
    for section, payload in volume_sections.items():
        if isinstance(payload, dict) and "status" in payload:
            statuses[f"volume.{section}"] = payload["status"]
    for name, payload in (report.get("memory", {}) or {}).items():
        if isinstance(payload, dict) and "status" in payload:
            statuses[f"memory.{name}"] = payload["status"]
    device = report.get("device", {})
    statuses["device.identity"] = device.get("status", "MISSING")
    for disk in device.get("disks", []) or []:
        for key in ("identity", "alignment"):
            sub = disk.get(key)
            if sub is not None:
                statuses[f"device.disk{disk.get('disk_number')}.{key}"] = sub.get(
                    "status", "MISSING")
    return {
        "schema": report["schema"],
        "kind": report["kind"],
        "generated_at_utc": report["generated_at_utc"],
        "resolved_path": report["path"]["resolved_path"],
        "volume_root": report["path"]["volume_root"],
        "probe_statuses": statuses,
        "runtime_acceptance": report["runtime_acceptance"],
        "read_only": True,
        "note": "full detail (including device identity strings) is only in the private output file",
    }


def _is_volume_root(path: Path) -> bool:
    """True for drive roots such as ``C:\\`` where containment spans the volume."""
    resolved = path.resolve()
    try:
        return resolved == Path(resolved.anchor)
    except (OSError, RuntimeError, ValueError):
        return False


def validate_output_target(source_path: Path, output: str) -> Path:
    """Refuse non-JSON or in-tree outputs so weights/profiles cannot be overwritten.

    Ordinary directories (model trees, pack dirs) cannot host the snapshot.
    Volume roots are an exception: nearly every same-drive path is "inside" them,
    so containment would make drive-root diagnostics impossible. Overwriting the
    exact probed path is still refused.
    """
    target = Path(output)
    if target.suffix.lower() != ".json":
        raise StorageGeometryError("output must be a .json diagnostic file")
    source = source_path.resolve()
    resolved_target = target.resolve()
    if resolved_target == source:
        raise StorageGeometryError("output must not overwrite the probed source path")
    if source.is_dir() and not _is_volume_root(source):
        try:
            resolved_target.relative_to(source)
        except ValueError:
            pass
        else:
            raise StorageGeometryError(
                "output must not be written inside the probed source directory"
            )
    return target


def write_report(path_text: str, output: str):
    """Build the report, write the private JSON file, return (report, summary)."""
    context = resolve_path_context(path_text)
    target = validate_output_target(Path(context["resolved_path"]), output)
    report = build_report(path_text)
    if str(target.parent):
        target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    summary = summarize_report(report)
    summary["output"] = str(target)
    return report, summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--path", required=True, metavar="PATH",
                        help="existing file/directory whose hosting volume is probed")
    parser.add_argument("--output", required=True, metavar="JSON_PATH",
                        help="write the private hardware snapshot JSON to this path")
    args = parser.parse_args(argv)
    try:
        _report, summary = write_report(args.path, args.output)
    except Exception as exc:  # noqa: BLE001 - CLI boundary; report every failure as JSON
        json.dump({
            "schema": SCHEMA_VERSION,
            "kind": "storage_geometry_error",
            "error": f"{type(exc).__name__}: {exc}",
            "runtime_acceptance": RUNTIME_ACCEPTANCE_NO,
        }, sys.stderr, indent=2)
        sys.stderr.write("\n")
        return 2
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
