#!/usr/bin/env python3
"""Tests for the CIB2 static verifier; no model, GPU or SDK is needed."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "cib2"
sys.path.insert(0, str(SCRIPTS))

from preflight_rc3b import (  # noqa: E402
    BASE, EXPECTED, MANIFEST, PARENT, PARENT_TAG, TAG,
    Check, check_file, check_plugin_pair, safe_changed_paths, sha256,
    verify_manifest,
)


def mock_manifest():
    return {
        "name": TAG, "accepted": False, "parent_tag": PARENT_TAG,
        "parent": PARENT, "branch": "semantic-refit-2026.4",
        "build": {"config": "win_mp_on_py_off",
                  "sdk": "openvino_genai_windows_2026.4.0.0rc1_x86_64 isolated package",
                  "gpu_plugin": "stock SDK GPU, not custom moe38545 21a2fd9f"},
        "binaries": [
            {"path": f"bazel-bin/src/{kind}.exe", "bytes": size, "sha256": digest}
            for kind, (digest, size) in EXPECTED.items()
        ],
    }


class StaticContractTest(unittest.TestCase):
    def test_release_manifest_pass(self):
        self.assertEqual(verify_manifest(mock_manifest()), [])

    def test_rejects_wrong_parent_and_sdk(self):
        doc = mock_manifest()
        doc["parent"] = "bad"
        doc["build"]["sdk"] = "2026.5 nightly"
        errors = verify_manifest(doc)
        self.assertTrue(any("parent" in x for x in errors))
        self.assertTrue(any("2026.4.0.0rc1" in x for x in errors))

    def test_rejects_replaced_binary_identity(self):
        doc = mock_manifest()
        doc["binaries"][0]["sha256"] = "0" * 64
        self.assertTrue(any("ovms.exe" in x for x in verify_manifest(doc)))

    def test_preflight_scope_does_not_allow_runtime_edits(self):
        self.assertEqual(safe_changed_paths([
            "docs/cib2/STATE.md", "scripts/cib2/preflight_rc3b.py",
            "tests/cib2/test_preflight_rc3b.py"]), [])
        self.assertEqual(safe_changed_paths([
            "src/llm/io_processing/gemma4/generation_config_builder.hpp",
            "docs/qwenmonster/RELEASE-CANDIDATE-20261023-RC3B-IDENTITY.json",
            "docs/cib2evil/hidden.txt",
        ]), [
            "src/llm/io_processing/gemma4/generation_config_builder.hpp",
            "docs/qwenmonster/RELEASE-CANDIDATE-20261023-RC3B-IDENTITY.json",
            "docs/cib2evil/hidden.txt",
        ])

    def test_sha256_binary_and_stock_gpu_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            sdk = Path(tmp) / "sdk.dll"
            active = Path(tmp) / "active.dll"
            sdk.write_bytes(b"known-sdk-plugin")
            active.write_bytes(b"known-sdk-plugin")
            expected_hash = hashlib.sha256(b"known-sdk-plugin").hexdigest()
            self.assertEqual(sha256(sdk), expected_hash)

            checks = []
            check_file(checks, "dummy", sdk, (expected_hash, sdk.stat().st_size))
            self.assertEqual(checks[-1].status, "PASS")
            check_file(checks, "dummy", sdk, ("0" * 64, sdk.stat().st_size))
            self.assertEqual(checks[-1].status, "FAIL")
            check_plugin_pair(checks, sdk, active)
            self.assertEqual(checks[-1].status, "PASS")
            active.write_bytes(b"modified-plugin")
            check_plugin_pair(checks, sdk, active)
            self.assertEqual(checks[-1].status, "FAIL")

    def test_absent_runtime_is_not_run(self):
        checks = []
        check_file(checks, "binary", None, EXPECTED["ovms"])
        check_plugin_pair(checks, None, None)
        self.assertEqual([x.status for x in checks], ["NOT_RUN", "NOT_RUN"])


if __name__ == "__main__":
    unittest.main()
