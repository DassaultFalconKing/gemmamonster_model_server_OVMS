# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Independent PGP-00 Windows volume-selection and ABI regression tests.

All Win32 calls are faked; no model files, drives, listeners or privileged
operations are accessed. The real Windows hardware gate remains NOT_RUN.
"""
from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "cib2"))
import storage_geometry as sg  # noqa: E402


class VolumeIdentityReviewTests(unittest.TestCase):
    def test_drive_roots_are_allowed_but_mountpoint_must_not_be_collapsed(self):
        self.assertEqual(sg._clean_root("c:\\"), "C:")
        self.assertEqual(sg._clean_root("d:/"), "D:")
        self.assertEqual(sg._clean_root("Z:"), "Z:")
        for root in ("C:\\MountD\\", "E:/Models/Weights", "\\\\host\\share\\"):
            with self.subTest(root=root), self.assertRaises(sg.StorageGeometryError):
                sg._clean_root(root)

    def test_mounted_volume_root_is_selected_from_win32_not_path_anchor(self):
        class FakeKernel:
            def GetVolumePathNameW(self, path, destination, characters):
                assert characters == len(destination)
                destination.value = "C:\\MountD\\"
                return 1

        fake_tools = type("FakeTools", (), {"kernel32": FakeKernel()})()
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(sg, "_IS_WINDOWS", True), \
             mock.patch.object(sg, "_win32_tools", return_value=fake_tools):
            result = sg.resolve_path_context(tmp)
        self.assertEqual(result["volume_root"], "C:\\MountD\\")
        self.assertNotEqual(result["volume_root"], "C:\\")

    def test_win32_volume_root_failure_is_explicit_and_not_guessed(self):
        class FakeKernel:
            def GetVolumePathNameW(self, path, destination, characters):
                return 0

        fake_tools = type("FakeTools", (), {"kernel32": FakeKernel()})()
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(sg, "_IS_WINDOWS", True), \
             mock.patch.object(sg, "_win32_tools", return_value=fake_tools), \
             mock.patch.object(sg.ctypes, "get_last_error", return_value=5,
                               create=True):
            with self.assertRaisesRegex(sg.PathResolutionError,
                                        "GetVolumePathNameW failed"):
                sg.resolve_path_context(tmp)

    def test_volume_information_buffer_length_is_wchar_not_byte_size(self):
        seen = []

        class FakeKernel:
            def GetVolumeInformationW(self, root, label, label_chars,
                                      serial, component, flags, filesystem,
                                      fs_chars):
                seen.append((label_chars, len(label), fs_chars, len(filesystem)))
                label.value = "DATA"
                filesystem.value = "NTFS"
                return 1

        fake_tools = type("FakeTools", (), {"kernel32": FakeKernel()})()
        with mock.patch.object(sg, "_win32_tools", return_value=fake_tools):
            result = sg.probe_volume_information("C:\\")
        self.assertEqual(result["status"], sg.EXPOSED)
        self.assertEqual(result["filesystem_name"], "NTFS")
        self.assertEqual(seen, [(261, 261, 261, 261)])

    def test_extent_count_above_bounded_mapping_is_rejected(self):
        # A partial first 64 entries must never be labelled a full disk map.
        raw = struct.pack("<I", sg._MAX_EXTENT_ENTRIES + 1) + b"\0" * 4
        raw += b"\0" * (24 * sg._MAX_EXTENT_ENTRIES)
        with self.assertRaisesRegex(sg.StorageGeometryError,
                                    "partial physical-device mapping"):
            sg.parse_volume_disk_extents(raw)

    def test_one_complete_extent_keeps_disk_number_and_bytes_separate(self):
        raw = struct.pack("<I", 1) + b"\0" * 4
        raw += struct.pack("<I4xqq", 12, 8192, 32768)
        result = sg.parse_volume_disk_extents(raw)
        self.assertEqual(result["disk_numbers"], [12])
        self.assertTrue(result["single_physical_disk"])
        self.assertFalse(result["extents_truncated"])
        self.assertEqual(result["extents"][0]["starting_offset_bytes"], 8192)
        self.assertEqual(result["extents"][0]["extent_length_bytes"], 32768)


if __name__ == "__main__":
    unittest.main()
