# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""CIB2-00 static component lock tests (stdlib only, no target execution)."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "cib2"))

import source_lock as sl  # noqa: E402
from source_lock import (  # noqa: E402
    ComponentError,
    ManifestError,
    build_manifest,
    collect_component,
    load_manifest,
    main,
    validate_manifest,
)


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StaticCollectionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.exe = _write(self.tmp / "ovms.exe", b"MZ-static-executable")
        self.dll = _write(self.tmp / "openvino.dll", b"MZ-static-dll")
        self.cfg = _write(self.tmp / "config.json", b'{"device":"GPU"}')

    def tearDown(self):
        self._tmp.cleanup()

    def test_successful_collection_is_static_and_not_accepted(self):
        manifest = build_manifest([
            ("ovms", str(self.exe)),
            ("openvino", str(self.dll)),
            ("config", str(self.cfg)),
        ], captured_at="2026-10-24T00:00:00Z")
        validate_manifest(manifest)
        self.assertEqual(manifest["schema"], "cib2.component-manifest.v1")
        self.assertIs(manifest["accepted"], False)
        self.assertEqual(manifest["provenance"]["file_bytes"]["status"], "VERIFIED")
        self.assertEqual(manifest["provenance"]["source_build_association"]["status"], "UNVERIFIED")
        self.assertEqual(manifest["provenance"]["loaded_dll_evidence"]["status"], "NOT_RUN")
        self.assertEqual(manifest["provenance"]["runtime_acceptance"]["status"], "NO")
        self.assertEqual(manifest["generated_at_utc"], "2026-10-24T00:00:00Z")
        self.assertEqual(manifest["source_revision"], sl.FROZEN_SOURCE_REVISION)
        self.assertEqual(manifest["summary"]["component_count"], 3)

        by_name = {c["name"]: c for c in manifest["components"]}
        for name, path in (("ovms", self.exe), ("openvino", self.dll), ("config", self.cfg)):
            component = by_name[name]
            self.assertEqual(component["resolved_path"], str(path.resolve()))
            self.assertEqual(component["size_bytes"], path.stat().st_size)
            self.assertEqual(component["sha256"], _digest(path))
            self.assertEqual(component["role"], {
                "ovms": "executable", "openvino": "dll", "config": "config",
            }[name])
            self.assertIs(component["digest_verification"]["computed_from_file_bytes"], True)
            self.assertIs(
                component["digest_verification"]["caller_supplied_sha_used_as_identity"], False
            )
            self.assertEqual(component["provenance"]["runtime_acceptance"], "NO")

    def test_modified_file_mismatches_expected_digest(self):
        manifest = build_manifest([("ovms", str(self.exe))])
        validate_manifest(manifest, verify_files=True)
        # Same size, different bytes: the stored SHA256 must detect the change.
        self.exe.write_bytes(b"MZ-static-EXECUTABLE")
        with self.assertRaises(ManifestError) as ctx:
            validate_manifest(manifest, verify_files=True)
        self.assertIn("digest mismatch", str(ctx.exception))

    def test_supplied_expected_digest_is_comparison_only(self):
        actual = _digest(self.exe)
        manifest = build_manifest([("ovms", str(self.exe))], expected_digests={"ovms": actual})
        component = manifest["components"][0]
        self.assertEqual(component["sha256"], actual)
        self.assertEqual(component["digest_verification"]["expected_sha256"], actual)
        self.assertIs(component["digest_verification"]["match"], True)
        self.assertIs(component["digest_verification"]["caller_supplied_sha_used_as_identity"], False)
        with self.assertRaises(ComponentError):
            build_manifest([("ovms", str(self.exe))], expected_digests={"ovms": "0" * 64})

    def test_expected_digest_names_match_case_insensitively(self):
        actual = _digest(self.exe)
        manifest = build_manifest([("ovms", str(self.exe))], expected_digests={"OVMS": actual})
        component = manifest["components"][0]
        self.assertEqual(component["name"], "ovms")
        self.assertEqual(component["digest_verification"]["expected_sha256"], actual)
        self.assertIs(component["digest_verification"]["match"], True)
        # A mis-cased expected digest must still be compared, not skipped.
        with self.assertRaises(ComponentError) as ctx:
            build_manifest([("ovms", str(self.exe))], expected_digests={"OvMs": "0" * 64})
        self.assertIn("do not match", str(ctx.exception))

    def test_unknown_expected_digest_name_is_rejected(self):
        actual = _digest(self.exe)
        with self.assertRaises(ComponentError) as ctx:
            build_manifest([("ovms", str(self.exe))], expected_digests={"ovsm": actual})
        self.assertIn("unknown component", str(ctx.exception))

    def test_conflicting_duplicate_expected_aliases_are_rejected(self):
        actual = _digest(self.exe)
        with self.assertRaises(ComponentError) as ctx:
            build_manifest(
                [("ovms", str(self.exe))],
                expected_digests={"ovms": actual, "OVMS": "0" * 64},
            )
        self.assertIn("conflicting duplicate expected digest name aliases", str(ctx.exception))

    def test_model_weight_bin_is_refused(self):
        weights = _write(self.tmp / "model.bin", b"\x00\x01")
        with self.assertRaises(ComponentError) as ctx:
            build_manifest([("weights", str(weights))])
        self.assertIn("model-weight BIN", str(ctx.exception))

    def test_write_and_load_manifest(self):
        manifest = build_manifest([("ovms", str(self.exe)), ("openvino", str(self.dll))])
        out = self.tmp / "manifest.json"
        sl.write_manifest(str(out), manifest)
        loaded = load_manifest(str(out))
        self.assertEqual(loaded["components"], manifest["components"])
        self.assertIs(loaded["accepted"], False)


class IdentityRejectionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.a = _write(self.tmp / "a.exe", b"aaa")
        self.b = _write(self.tmp / "b.dll", b"bbb")

    def tearDown(self):
        self._tmp.cleanup()

    def _manifest(self):
        return build_manifest([("a", str(self.a)), ("b", str(self.b))])

    def test_duplicate_component_name_or_path_is_rejected(self):
        with self.assertRaises(ComponentError):
            build_manifest([("same", str(self.a)), ("same", str(self.b))])
        with self.assertRaises(ComponentError) as ctx:
            build_manifest([("one", str(self.a)), ("two", str(self.a))])
        self.assertIn("duplicate component file identity", str(ctx.exception))

    def test_missing_component_identity_is_rejected(self):
        manifest = self._manifest()
        broken = copy.deepcopy(manifest)
        del broken["components"][0]["sha256"]
        with self.assertRaises(ManifestError) as ctx:
            validate_manifest(broken)
        self.assertIn("incomplete identity tuple", str(ctx.exception))

        broken = copy.deepcopy(manifest)
        broken["components"] = []
        with self.assertRaises(ManifestError):
            validate_manifest(broken)

        broken = copy.deepcopy(manifest)
        broken["components"][1]["name"] = broken["components"][0]["name"]
        with self.assertRaises(ManifestError) as ctx:
            validate_manifest(broken)
        self.assertIn("duplicate component name", str(ctx.exception))

    def test_wrong_schema_version_and_incomplete_provenance_are_rejected(self):
        manifest = self._manifest()
        broken = copy.deepcopy(manifest)
        broken["schema"] = "cib2.component-manifest.v2"
        with self.assertRaises(ManifestError) as ctx:
            validate_manifest(broken)
        self.assertIn("unsupported schema version", str(ctx.exception))

        broken = copy.deepcopy(manifest)
        del broken["provenance"]["loaded_dll_evidence"]
        with self.assertRaises(ManifestError) as ctx:
            validate_manifest(broken)
        self.assertIn("missing categories", str(ctx.exception))

        broken = copy.deepcopy(manifest)
        del broken["components"][0]["digest_verification"]
        with self.assertRaises(ManifestError):
            validate_manifest(broken)

    def test_absent_loaded_and_build_provenance_is_strictly_refused(self):
        manifest = self._manifest()
        # Default manifest is valid as static evidence, but cannot satisfy strict gates.
        validate_manifest(manifest)
        with self.assertRaises(ManifestError) as ctx:
            validate_manifest(manifest, require_loaded_evidence=True)
        self.assertIn("loaded DLL/module evidence is absent", str(ctx.exception))
        with self.assertRaises(ManifestError) as ctx:
            validate_manifest(manifest, require_source_build_evidence=True)
        self.assertIn("source-build association evidence is absent", str(ctx.exception))

        broken = copy.deepcopy(manifest)
        broken["provenance"]["source_build_association"]["status"] = "VERIFIED"
        with self.assertRaises(ManifestError) as ctx:
            validate_manifest(broken)
        self.assertIn("without independent evidence", str(ctx.exception))

        broken = copy.deepcopy(manifest)
        broken["provenance"]["loaded_dll_evidence"]["status"] = "VERIFIED"
        with self.assertRaises(ManifestError) as ctx:
            validate_manifest(broken)
        self.assertIn("without a module-list evidence", str(ctx.exception))

        broken = copy.deepcopy(manifest)
        broken["accepted"] = True
        with self.assertRaises(ManifestError):
            validate_manifest(broken)


class CliTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.exe = _write(self.tmp / "ovms.exe", b"MZ-cli")
        self.dll = _write(self.tmp / "openvino.dll", b"MZ-dll-cli")

    def tearDown(self):
        self._tmp.cleanup()

    def test_cli_collects_static_manifest_without_paths_on_stdout(self):
        out_path = self.tmp / "private-components.json"
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            rc = main([
                "--component", f"ovms={self.exe}",
                "--component", f"openvino={self.dll}",
                "--output", str(out_path),
            ])
        self.assertEqual(rc, 0)
        summary = json.loads(stdout.getvalue())
        self.assertIs(summary["accepted"], False)
        self.assertEqual(summary["runtime_acceptance"], "NO")
        self.assertEqual(summary["loaded_dll_evidence"], "NOT_RUN")
        self.assertNotIn(str(self.exe.resolve()), stdout.getvalue())
        manifest = load_manifest(str(out_path))
        self.assertIs(manifest["accepted"], False)
        self.assertEqual(manifest["summary"]["component_count"], 2)

    def test_cli_expected_name_case_and_unknown(self):
        actual = _digest(self.exe)
        ok_out = self.tmp / "ok.json"
        with redirect_stdout(io.StringIO()):
            rc = main([
                "--component", f"ovms={self.exe}",
                "--expected", f"OVMS={actual}",
                "--output", str(ok_out),
            ])
        self.assertEqual(rc, 0)
        manifest = load_manifest(str(ok_out))
        self.assertEqual(manifest["components"][0]["digest_verification"]["expected_sha256"], actual)

        unknown_out = self.tmp / "unknown.json"
        err = io.StringIO()
        with redirect_stderr(err):
            rc = main([
                "--component", f"ovms={self.exe}",
                "--expected", f"ovsm={actual}",
                "--output", str(unknown_out),
            ])
        self.assertEqual(rc, 2)
        self.assertIn("unknown component", err.getvalue())
        self.assertFalse(unknown_out.exists())

        alias_out = self.tmp / "alias.json"
        with redirect_stderr(io.StringIO()):
            rc = main([
                "--component", f"ovms={self.exe}",
                "--expected", f"ovms={actual}",
                "--expected", f"OVMS={actual}",
                "--output", str(alias_out),
            ])
        self.assertEqual(rc, 2)
        self.assertFalse(alias_out.exists())

    def test_cli_rejects_duplicate_bin_and_expected_mismatch(self):
        out_path = self.tmp / "unused.json"
        for argv in (
            ["--component", f"a={self.exe}", "--component", f"a={self.dll}", "--output", str(out_path)],
            ["--component", f"weights={_write(self.tmp / 'w.bin', b'x')}", "--output", str(out_path)],
            ["--component", f"ovms={self.exe}", "--expected", "ovms=" + "0" * 64,
             "--output", str(out_path)],
        ):
            err = io.StringIO()
            with redirect_stderr(err):
                rc = main(argv)
            self.assertEqual(rc, 2, argv)
            payload = json.loads(err.getvalue())
            self.assertIs(payload["accepted"], False)
        self.assertFalse(out_path.exists())

    def test_cli_help_is_available(self):
        with redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(SystemExit) as ctx:
                main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("--component", out.getvalue())
        self.assertIn("--output", out.getvalue())


class SchemaDocumentTest(unittest.TestCase):
    def test_schema_document_matches_static_manifest_shape(self):
        schema_path = ROOT / "docs" / "cib2" / "manifest.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["properties"]["schema"]["const"], sl.SCHEMA_VERSION)
        self.assertEqual(schema["properties"]["accepted"]["const"], False)
        required = set(schema["required"])
        self.assertTrue({"schema", "accepted", "provenance", "components"} <= required)
        component_required = set(schema["$defs"]["component"]["required"])
        self.assertTrue({
            "name", "role", "resolved_path", "size_bytes", "sha256", "provenance",
        } <= component_required)
        self.assertEqual(
            schema["$defs"]["provenance"]["properties"]["file_bytes"]["allOf"][1]
            ["properties"]["status"]["const"],
            "VERIFIED",
        )


if __name__ == "__main__":
    unittest.main()
