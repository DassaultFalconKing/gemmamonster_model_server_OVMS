# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""CIB2 PGP-00 storage-geometry probe tests (stdlib only, read-only).

Bounded checks for parsing/API result conversion, unsupported/permission failure
handling, unit separation, and absence of fabricated budgets/capacities. Tests use
tiny temporary fixtures and never touch model weights, run an I/O benchmark, or
require administrator privileges.
"""

from __future__ import annotations

import io
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "cib2"))

import storage_geometry as sg  # noqa: E402


def _minimal_report(records: dict) -> dict:
    """Assemble a shape-valid report around caller-supplied record dicts."""
    return {
        "schema": sg.SCHEMA_VERSION,
        "kind": sg.KIND,
        "generated_at_utc": "2026-10-24T00:00:00Z",
        "runtime_acceptance": sg.RUNTIME_ACCEPTANCE_NO,
        "provenance": {"read_only": True, "admin_escalation_used": False},
        **records,
    }


class AllocationUnitConversionTest(unittest.TestCase):
    """Unit-separation: logical sector, cluster bytes and volume bytes stay distinct."""

    def test_512_logical_sector_8_per_cluster_units_stay_separated(self):
        geometry = sg.allocation_geometry_from_raw(
            sectors_per_cluster=8, bytes_per_sector=512, free_clusters=10,
            total_clusters=100, total_logical_bytes=100 * 4096,
            available_bytes=60 * 4096, free_logical_bytes=60 * 4096,
        )
        self.assertEqual(geometry["logical_sector_size_bytes"], 512)
        self.assertEqual(geometry["sectors_per_cluster"], 8)
        self.assertEqual(geometry["cluster_allocation_unit_bytes"], 4096)
        # Each unit is stored in its own field; no field collapses the others.
        self.assertIsNot(geometry["logical_sector_size_bytes"],
                          geometry["cluster_allocation_unit_bytes"])
        self.assertEqual(geometry["volume_total_from_cluster_math_bytes"], 100 * 4096)
        self.assertEqual(geometry["volume_total_logical_bytes"], 100 * 4096)

    def test_zero_sector_field_refuses_instead_of_guessing(self):
        with self.assertRaises(sg.StorageGeometryError):
            sg.allocation_geometry_from_raw(0, 4096, 1, 1, 1, 1, 1)
        with self.assertRaises(sg.StorageGeometryError):
            sg.allocation_geometry_from_raw(8, 0, 1, 1, 1, 1, 1)


class FsutilSectorInfoParsingTest(unittest.TestCase):
    """fsutil parse accepts 'key : int' output and never fabricates a missing key."""

    TYPICAL = (
        "   LogicalSectorSize :           512\r\n"
        "   PhysicalSectorSize :          4096\r\n"
        "   PhysicalBytesPerSectorForCache :       4096\r\n"
        "   PhysicalBytesPerSectorForAtomicity :   4096\r\n"
        "   PhysicalBytesPerSectorForPerformance : 4096\r\n"
        "   FileSystemEffectivePhysicalSectorSizeForPerformance : 4096\r\n"
        "   IsSSD :                                 1\r\n"
    )

    def test_typical_output_parses_keys_order_independently(self):
        fields = sg.parse_fsutil_sectorinfo(self.TYPICAL)
        self.assertEqual(fields["LogicalSectorSize"], 512)
        self.assertEqual(fields["PhysicalSectorSize"], 4096)
        self.assertEqual(fields["IsSSD"], 1)

    def test_service_error_text_is_rejected_not_defaulted(self):
        with self.assertRaises(sg.FsutilParseError):
            sg.parse_fsutil_sectorinfo("Error 5: Access is denied.\r\n")
        with self.assertRaises(sg.FsutilParseError):
            sg.parse_fsutil_sectorinfo("")
        with self.assertRaises(sg.FsutilParseError):
            sg.parse_fsutil_sectorinfo("Mangled output only")

    def test_missing_logical_sector_key_is_rejected(self):
        with self.assertRaises(sg.FsutilParseError):
            sg.parse_fsutil_sectorinfo("   PhysicalSectorSize :          4096\r\n")


class VolumeDiskExtentsParsingTest(unittest.TestCase):
    """Extent parsing matches the 24-byte DISK_EXTENT stride used by Windows."""

    def _buffer(self, extents):
        count = len(extents)
        parts = [struct.pack("<I", count)]
        for disk, start, length in extents:
            parts.append(struct.pack("<I4xqq", disk, start, length))
        return b"".join(parts)

    def test_two_extent_buffer_parse(self):
        buffer = self._buffer([(0, 1024, 2048), (1, -1, 4096)])
        parsed = sg.parse_volume_disk_extents(buffer)
        self.assertEqual(parsed["extent_count_reported"], 2)
        self.assertFalse(parsed["extents_truncated"])
        self.assertEqual(parsed["disk_numbers"], [0, 1])
        self.assertFalse(parsed["single_physical_disk"])
        self.assertEqual(parsed["extents"][0]["starting_offset_bytes"], 1024)
        self.assertEqual(parsed["extents"][1]["starting_offset_bytes"], -1)

    def test_truncated_buffer_refuses_quiet_isolation(self):
        buffer = self._buffer([(0, 1024, 2048), (0, 2048, 4096)])
        with self.assertRaises(sg.StorageGeometryError):
            # Reported three extents but only room for two -> refuse, not guess.
            sg.parse_volume_disk_extents(struct.pack("<I", 3) + buffer[4:])

    def test_zero_extent_output_is_not_reported_as_single_disk(self):
        parsed = sg.parse_volume_disk_extents(struct.pack("<I", 0))
        self.assertEqual(parsed["disk_numbers"], [])
        self.assertFalse(parsed["single_physical_disk"])


class StorageDeviceDescriptorParsingTest(unittest.TestCase):
    """STORAGE_DEVICE_DESCRIPTOR string offsets and absent-field handling."""

    def buffer(self, serial_offset: int = 0, version: int = 40) -> bytes:
        raw = bytearray(512)
        struct.pack_into("<IIBB", raw, 0, version, 396, 0, 0)
        raw[10] = 0            # RemovableMedia = FALSE
        raw[11] = 1            # CommandQueueing = TRUE
        struct.pack_into("<IIII", raw, 12, 36, 47, 60, serial_offset)
        raw[28] = 17           # STORAGE_BUS_TYPE NVMe
        struct.pack_into("<I", raw, 32, 0)
        raw[36:47] = b"VendorA\x00"
        raw[47:60] = b"ProductB\x00\x00"
        raw[60:66] = b"ASXA01\x00"
        if serial_offset:
            raw[serial_offset: serial_offset + 6] = b"S12345\x00"
        return bytes(raw[:396])

    def test_fields_and_offsets_parse(self):
        parsed = sg.parse_storage_device_descriptor(self.buffer(serial_offset=66))
        self.assertEqual(parsed["product_id"], "ProductB")
        self.assertEqual(parsed["product_revision"], "ASXA01")
        self.assertEqual(parsed["serial_number"], "S12345")
        self.assertTrue(parsed["serial_number_exposed"])
        self.assertEqual(parsed["bus_type_label"], "NVME")
        self.assertTrue(parsed["command_queueing"])

    def test_absent_serial_offset_is_none_not_queued_guess(self):
        parsed = sg.parse_storage_device_descriptor(self.buffer(serial_offset=0))
        self.assertIsNone(parsed["serial_number"])
        self.assertFalse(parsed["serial_number_exposed"])

    def test_implausible_version_size_is_refused(self):
        with self.assertRaises(sg.StorageGeometryError):
            sg.parse_storage_device_descriptor(self.buffer(version=2))
        truncated = self.buffer()[:20]
        with self.assertRaises(sg.StorageGeometryError):
            sg.parse_storage_device_descriptor(truncated)


class AccessAlignmentParsingTest(unittest.TestCase):
    """Access-alignment descriptor validates version/size before reporting sectors."""

    def buffer(self, version=1, size=28, logical=512, physical=4096) -> bytes:
        return struct.pack("<7I", version, size, 0, 0, logical, physical, 0)

    def test_valid_descriptor_parses_both_sector_units(self):
        parsed = sg.parse_access_alignment_descriptor(self.buffer())
        self.assertEqual(parsed["device_logical_sector_size_bytes"], 512)
        self.assertEqual(parsed["device_physical_sector_size_bytes"], 4096)

    def test_wrong_version_is_never_reported_as_fact(self):
        with self.assertRaises(sg.StorageGeometryError):
            sg.parse_access_alignment_descriptor(self.buffer(version=28))

    def test_non_pow2_or_tiny_values_are_never_reported(self):
        with self.assertRaises(sg.StorageGeometryError):
            sg.parse_access_alignment_descriptor(self.buffer(physical=96))
        with self.assertRaises(sg.StorageGeometryError):
            sg.parse_access_alignment_descriptor(self.buffer(physical=4095))

    def test_plausibility_helper_bounds(self):
        self.assertTrue(sg._plausible_sector_bytes(512))
        self.assertFalse(sg._plausible_sector_bytes(64))
        self.assertFalse(sg._plausible_sector_bytes(4095))


class GetPerformanceInfoConversionTest(unittest.TestCase):
    """Page-to-byte conversion keeps counts separate and never invents page size."""

    def test_pages_are_multiplied_counts_are_not(self):
        payload = sg.system_commit_from_performance_fields(
            commit_total=2, commit_limit=4, commit_peak=6, physical_total=8,
            physical_available=10, system_cache=12, kernel_total=14, kernel_paged=16,
            kernel_nonpaged=18, page_size=4096, handle_count=20, process_count=22,
            thread_count=24,
        )
        self.assertEqual(payload["system_commit_current_bytes"], 2 * 4096)
        self.assertEqual(payload["system_commit_limit_bytes"], 4 * 4096)
        self.assertEqual(payload["physical_total_bytes"], 8 * 4096)
        self.assertEqual(payload["handle_count"], 20)  # count, NOT multiplied
        self.assertEqual(payload["process_count"], 22)
        self.assertEqual(payload["thread_count"], 24)
        self.assertEqual(payload["page_size_bytes"], 4096)

    def test_zero_page_size_refuses(self):
        with self.assertRaises(sg.StorageGeometryError):
            sg.system_commit_from_performance_fields(
                1, 1, 1, 1, 1, 1, 1, 1, 1, page_size=0, handle_count=1,
                process_count=1, thread_count=1)


class NotExposedPropagationTest(unittest.TestCase):
    """Permission/unsupported probes become explicit NOT_EXPOSED without values."""

    def test_raising_probe_becomes_not_exposed_with_reason_and_probe(self):
        def raising():
            raise PermissionError("Access is denied.")

        record = sg._expose_probe("probe-blocking", "TestSource", raising)
        self.assertEqual(record["status"], sg.NOT_EXPOSED)
        self.assertIn("Access is denied", record["reason"])
        self.assertEqual(record["probe"], "probe-blocking")
        self.assertEqual(record["source"], "TestSource")
        self.assertTrue(record["captured_at_utc"])
        # No fabricated byte/size values may appear on a failed probe.
        for key in record:
            self.assertFalse(key.endswith("_bytes"), key)

    def test_fsutil_block_yields_not_exposed_without_4096_default(self):
        record = sg.probe_sector_sizes_fsutil(r"\\auspicious-host-never\share")
        self.assertEqual(record["status"], sg.NOT_EXPOSED)
        self.assertIn("reason", record)
        self.assertNotIn("logical_sector_size_bytes", record)
        self.assertNotIn("device_reported_physical_sector_size_bytes", record)
        for key in record:
            self.assertFalse(key.endswith("_bytes"), key)

    def test_non_windows_platform_probe_records_are_all_not_exposed(self):
        previous = sg._IS_WINDOWS
        try:
            sg._IS_WINDOWS = False
            with tempfile.TemporaryDirectory() as tmp:
                sg._TOOLS = None
                report = sg.build_report(tmp)
            self.assertEqual(report["volume"]["filesystem_information"]["status"],
                             sg.NOT_EXPOSED)
            self.assertEqual(report["volume"]["allocation_geometry"]["status"],
                             sg.NOT_EXPOSED)
            for record in (report["memory"]["physical"],
                           report["memory"]["process_commit"]):
                self.assertEqual(record["status"], sg.NOT_EXPOSED)
                self.assertIn("reason", record)
                for key in record:
                    self.assertFalse(key.endswith("_bytes"), key)
            sg.validate_report(report)  # shape remains valid on unsupported platform
        finally:
            sg._IS_WINDOWS = previous
            sg._TOOLS = None


class ValidateReportTest(unittest.TestCase):
    """Invariant enforcement of statuses, reasons, and unit-mixing bans."""

    def test_ok_report_has_no_violations(self):
        report = _minimal_report({
            "memory": {"physical": {"status": sg.EXPOSED, "probe": "GlobalMemoryStatusEx",
                                    "captured_at_utc": "2026-10-24T00:00:00Z",
                                    "total_physical_bytes": 1024}},
        })
        self.assertEqual(sg.validate_report(report), [])

    def test_not_exposed_record_with_bytes_value_is_flagged(self):
        report = _minimal_report({
            "memory": {"wddm": {"status": sg.NOT_EXPOSED, "probe": "DXGI",
                                "captured_at_utc": "2026-10-24T00:00:00Z",
                                "reason": "unavailable",
                                "budget_bytes": 4096}},
        })
        violations = sg.validate_report(report)
        self.assertTrue(any("fabricates" in item for item in violations))

    def test_missing_reason_or_probe_is_flagged(self):
        record = {"status": sg.NOT_EXPOSED, "probe": "DXGI",
                  "captured_at_utc": "2026-10-24T00:00:00Z"}
        report = _minimal_report({"memory": {"wddm": record}})
        violations = sg.validate_report(report)
        self.assertTrue(any("missing reason" in item for item in violations))

    def test_forbidden_unit_mixed_key_is_flagged_wherever_nested(self):
        report = _minimal_report({
            "memory": {"physical": {"status": sg.EXPOSED, "probe": "GMS",
                                    "captured_at_utc": "2026-10-24T00:00:00Z"},
                       "combined_free_bytes": 12345},
        })
        violations = sg.validate_report(report)
        self.assertTrue(any("combined_free_bytes" in item for item in violations))

    def test_bad_runtime_acceptance_is_refused(self):
        report = _minimal_report({})
        report["runtime_acceptance"] = "YES"
        with self.assertRaises(sg.StorageGeometryError):
            sg.validate_report(report)


class PathResolutionTest(unittest.TestCase):
    def test_existing_file_and_directory_resolve_with_volume_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = sg.resolve_path_context(tmp)
            self.assertEqual(ctx["kind"], "directory")
            self.assertTrue(ctx["volume_root"].startswith("C:")
                            or ctx["volume_root"].startswith("\\"))
            path_file = Path(tmp) / "marker.file"
            path_file.write_bytes(b"x")
            ctx_file = sg.resolve_path_context(str(path_file))
            self.assertEqual(ctx_file["kind"], "file")
            self.assertEqual(ctx_file["volume_root"], ctx["volume_root"])

    def test_missing_path_raises_path_resolution_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = str(Path(tmp) / "definitely-absent")
            with self.assertRaises(sg.PathResolutionError):
                sg.resolve_path_context(missing)


class CliEndToEndTest(unittest.TestCase):
    """Tiny fixture: run the CLI on a temp dir with output outside the probed tree."""

    def test_successful_snapshot_on_temp_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tempfile.gettempdir()) / "cib2_pgp00_test_snapshot.json"
            err, out_text = io.StringIO(), io.StringIO()
            with redirect_stderr(err), redirect_stdout(out_text):
                code = sg.main(["--path", tmp, "--output", str(out)])
            self.assertEqual(code, 0, err.getvalue())
            summary = json.loads(out_text.getvalue())
            self.assertEqual(summary["schema"], sg.SCHEMA_VERSION)
            self.assertEqual(summary["runtime_acceptance"], sg.RUNTIME_ACCEPTANCE_NO)
            self.assertNotIn("serial", out_text.getvalue().lower())
            snapshot = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(sg.validate_report(snapshot), [])
            self.assertEqual(snapshot["path"]["requested_path"], tmp)
            self.assertEqual(snapshot["path"]["volume_root"], summary["volume_root"])
            out.unlink()

    def test_wddm_ledger_stays_separate_from_physical(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tempfile.gettempdir()) / "cib2_pgp00_test_snapshot2.json"
            try:
                report, _ = sg.write_report(tmp, str(out))
            finally:
                out.unlink(missing_ok=True)
            self.assertEqual(sg.validate_report(report), [])
            flat_keys = set(sg._iter_keys(report))
            for forbidden in ("combined_free_bytes", "total_free_with_wddm",
                              "wddm_free_plus_system_free", "combined_available_bytes"):
                self.assertNotIn(forbidden, flat_keys)
            wddm = report["memory"]["video_wddm_always_separate_ledger"]
            physical = report["memory"]["physical"]
            self.assertNotIn("wddm_free_not_added_to_system_free_bytes",
                             physical)  # physical ledger carries no WDDM flag
            if wddm.get("status") == sg.NOT_EXPOSED:
                self.assertIn("reason", wddm)
                self.assertNotIn("budget_bytes", wddm)
                self.assertNotIn("current_usage_bytes", wddm)
            else:
                self.assertTrue(wddm.get("wddm_free_not_added_to_system_free_bytes"))

    def test_missing_path_fails_closed_exit2_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "must-not-exist.json"
            err, out_text = io.StringIO(), io.StringIO()
            with redirect_stderr(err), redirect_stdout(out_text):
                code = sg.main(["--path", str(Path(tmp) / "absent"),
                                "--output", str(out)])
            self.assertEqual(code, 2)
            self.assertIn("storage_geometry_error", err.getvalue())
            self.assertFalse(out.exists())

    def test_output_inside_probed_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            err, out_text = io.StringIO(), io.StringIO()
            with redirect_stderr(err), redirect_stdout(out_text):
                code = sg.main(["--path", tmp,
                                "--output", str(Path(tmp) / "inside.json")])
            self.assertEqual(code, 2)
            self.assertIn("inside the probed source directory", err.getvalue())

    def test_non_json_output_suffix_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tempfile.gettempdir()) / "cib2_pgp00_test_snapshot.bin"
            err, out_text = io.StringIO(), io.StringIO()
            with redirect_stderr(err), redirect_stdout(out_text):
                code = sg.main(["--path", tmp, "--output", str(out)])
            self.assertEqual(code, 2)
            self.assertIn("output must be a .json", err.getvalue())
            self.assertFalse(out.exists())


class SummaryPrivacyTest(unittest.TestCase):
    def test_summary_leaves_serial_and_device_identity_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tempfile.gettempdir()) / "cib2_pgp00_test_summary.json"
            try:
                report, summary = sg.write_report(tmp, str(out))
            finally:
                out.unlink(missing_ok=True)
            summary_text = json.dumps(summary)
            self.assertNotIn("serial_number", summary_text)
            device = report.get("device", {})
            for disk in device.get("disks", []) or []:
                identity = disk.get("identity", {}) or {}
                serial = identity.get("serial_number")
                if serial:
                    self.assertNotIn(str(serial), summary_text,
                                     "device serial must not reach the public summary")


if __name__ == "__main__":
    unittest.main()
