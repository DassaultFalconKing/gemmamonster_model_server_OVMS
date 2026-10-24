# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Independent PGP-02 malformed numeric profile refusal regression tests."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "cib2"))
import pack_layout as pl  # noqa: E402

FIXTURE = (Path(__file__).resolve().parent / "fixtures" /
           "pack_layout" / "identity_empty.json")


def _profile():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class NumericFailClosedReviewTests(unittest.TestCase):
    def assert_profile_rejected(self, profile):
        raw = json.dumps(profile, allow_nan=False).encode("utf-8")
        with self.assertRaises(pl.ProfileError):
            pl.load_profile_bytes(raw)

    def test_enormous_json_integer_read_cost_rejected_without_overflow(self):
        profile = _profile()
        profile["experts"] = [
            {"logical_expert_id": 0, "miss_count": 1,
             "read_cost_us": 10 ** 400}
        ]
        self.assert_profile_rejected(profile)

    def test_enormous_json_integer_coaccess_weight_rejected(self):
        profile = _profile()
        profile["coaccess"] = [
            {"expert_a": 0, "expert_b": 1, "weight": 10 ** 400}
        ]
        self.assert_profile_rejected(profile)

    def test_exact_integer_above_float_representable_limit_rejected(self):
        profile = _profile()
        profile["coaccess"] = [
            {"expert_a": 0, "expert_b": 1,
             "weight": int(pl.MAX_COACCESS_WEIGHT) + 1}
        ]
        self.assert_profile_rejected(profile)

    def test_out_of_bounds_integer_read_cost_rejected(self):
        profile = _profile()
        profile["experts"] = [
            {"logical_expert_id": 0, "miss_count": 1,
             "read_cost_us": int(pl.MAX_READ_COST_US) + 1}
        ]
        self.assert_profile_rejected(profile)

    def test_cli_returns_rejected_exit_two_without_output(self):
        profile = _profile()
        profile["coaccess"] = [
            {"expert_a": 0, "expert_b": 1, "weight": 10 ** 400}
        ]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "huge-numeric-profile.json"
            output = Path(directory) / "layout.json"
            source.write_text(json.dumps(profile), encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = pl.main(["--profile", str(source),
                                "--output", str(output),
                                "--strategy", "coaccess"])
            self.assertEqual(code, 2)
            self.assertFalse(output.exists())
            result = json.loads(stderr.getvalue())
            self.assertEqual(result["status"], "REJECTED")
            self.assertEqual(result["runtime_acceptance"], "NO")


if __name__ == "__main__":
    unittest.main()
