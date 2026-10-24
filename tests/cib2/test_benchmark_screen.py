# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Synthetic-only strict PGP-05 screen tests, never a hardware acceptance receipt."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "cib2"))
import benchmark_screen as s  # noqa: E402


def fixture(ids=("A0", "A1", "B0", "B1"), io_exposed=False):
    cohort = {k: "a"*64 for k in s.SHA_KEYS}
    cohort.update(model_key="model1", driver_version="32.0.1", sdk_version="2026.4rc1", device_key="arc140v")
    scenario = {"workload_key": "tools", "context_tokens": 2048, "slots": 2,
                "offload_ratio": 40, "phase": "decode", "cache_state": "cold", "prompt_family": "agentic"}
    arms = []
    for n, key in enumerate(ids):
        layout, resident = s.ARMS[key]
        arms.append({"id": key, "layout": layout, "resident_mode": resident,
                     "profile_sha": "b"*64 if layout == "optimized" else None,
                     "pack_manifest_sha": chr(ord("a") + n)*64,
                     "cohort": copy.deepcopy(cohort), "scenario": copy.deepcopy(scenario),
                     "gates": {k: True for k in s.GATE_KEYS}, "warmups": 1,
                     "samples": [{"index": i, "accepted_target_tokens": 100,
                                  "wall_seconds": 10.0 - n * 0.5, "ttft_ms": 2000,
                                  "tpot_p95_ms": 30, "tpot_p99_ms": 45,
                                  "startup_ms": 20000, "unique_memory_bytes": 100000000,
                                  "physical_io": ({"status": "EXPOSED", "source": "device_counter",
                                                   "device_read_bytes": 40960}
                                                  if io_exposed else {"status": "NOT_EXPOSED", "reason": "no_counters"})}
                                 for i in range(3)]})
    return {"schema": s.SCHEMA, "synthetic": True, "arms": arms}


class PGP05ScreenTests(unittest.TestCase):
    def test_four_arm_screen_cannot_promote_synthetic(self):
        report = s.screen_receipt(fixture(), "c"*64)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["runtime_acceptance"], "NO")
        self.assertFalse(report["promotion_authorized"])
        self.assertTrue(report["matrix_complete"])
        self.assertIsNone(report["comparisons"]["A1_vs_A0"]["physical_device_bytes_per_accepted_token_delta_pct"])
        self.assertGreater(report["comparisons"]["A1_vs_A0"]["median_accepted_target_tps_delta_pct"], 0)

    def test_physical_counters_are_not_summed_with_logical_bytes(self):
        report = s.screen_receipt(fixture(io_exposed=True), "d"*64)
        self.assertEqual(report["summary"]["A0"]["physical_io_status"], "EXPOSED")
        self.assertEqual(report["summary"]["A0"]["physical_device_bytes_per_accepted_token"], 409.6)

    def test_mismatched_build_rejected(self):
        data = fixture()
        data["arms"][1]["cohort"]["gpu_plugin_sha"] = "c"*64
        with self.assertRaisesRegex(s.ScreenError, "cohort/scenario mismatch"):
            s.screen_receipt(data, "e"*64)

    def test_mismatched_workload_rejected(self):
        data = fixture()
        data["arms"][1]["scenario"]["slots"] = 4
        with self.assertRaises(s.ScreenError):
            s.screen_receipt(data, "e"*64)

    def test_partial_matrix_is_blocked(self):
        report = s.screen_receipt(fixture(("A0", "A1")), "e"*64)
        self.assertFalse(report["matrix_complete"])
        self.assertIn("A0/A1/B0/B1 matrix incomplete", report["blockers"])

    def test_gate_false_blocks_not_promotes(self):
        data = fixture()
        data["synthetic"] = False
        data["arms"][2]["gates"]["lease_integrity"] = False
        result = s.screen_receipt(data, "e"*64)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("B0.lease_integrity=false", result["blockers"])

    def test_untrusted_true_gates_never_cause_runtime_pass(self):
        data = fixture()
        data["synthetic"] = False
        result = s.screen_receipt(data, "f"*64)
        self.assertEqual(result["status"], "OFFLINE_REVIEW_ONLY")
        self.assertFalse(result["promotion_authorized"])
        self.assertEqual(result["runtime_acceptance"], "NO")

    def test_acceptance_guard_refuses_fake_io(self):
        data = fixture()
        data["arms"][0]["samples"][0]["physical_io"] = {"status": "EXPOSED", "source": "logical_read", "device_read_bytes": 1}
        with self.assertRaisesRegex(s.ScreenError, "device_counter"):
            s.screen_receipt(data, "e"*64)

    def test_no_silent_nan_or_infinite(self):
        for val in (float('nan'), float('inf'), -(float('inf')), -1):
            data = fixture()
            data["arms"][0]["samples"][0]["wall_seconds"] = val
            with self.subTest(val=val), self.assertRaises(s.ScreenError):
                s.screen_receipt(data, "f"*64)

    def test_overflow_integer_rejected_cleanly(self):
        data = fixture()
        data["arms"][0]["samples"][0]["wall_seconds"] = 10**400
        with self.assertRaises(s.ScreenError):
            s.screen_receipt(data, "e"*64)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(s.ScreenError, "duplicate JSON field"):
            s._load(b'{"schema":"x","schema":"y"}')

    def test_unknown_fields_rejected_including_private_prompt(self):
        data = fixture()
        data["arms"][0]["samples"][0]["prompt_text"] = "secret"
        with self.assertRaises(s.ScreenError):
            s.screen_receipt(data, "e"*64)

    def test_tpot_ordering_rejected(self):
        data = fixture()
        data["arms"][0]["samples"][0]["tpot_p99_ms"] = 1
        with self.assertRaises(s.ScreenError):
            s.screen_receipt(data, "e"*64)

    def test_sample_count_mismatch_rejected(self):
        data = fixture()
        data["arms"][0]["samples"].append(copy.deepcopy(data["arms"][0]["samples"][-1]))
        data["arms"][0]["samples"][-1]["index"] = 3
        with self.assertRaises(s.ScreenError):
            s.screen_receipt(data, "e"*64)

    def test_cli_success_and_reject_code2(self):
        data = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipts.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(s.main(["--input", str(path)]), 0)
            self.assertEqual(json.loads(stdout.getvalue())["runtime_acceptance"], "NO")
            path.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            stderr = StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(s.main(["--input", str(path)]), 2)
            self.assertEqual(json.loads(stderr.getvalue())["status"], "REJECTED")


if __name__ == '__main__':
    unittest.main()
