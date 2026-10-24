"""Regression tests for moe_otd_trace E/C field indices and delta windows."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE_GPU = HERE.parent
FIXTURE = HERE / "fixtures" / "sample_moe_otd_trace.txt"
sys.path.insert(0, str(LIVE_GPU))

from moe_otd_trace import (  # noqa: E402
    aggregate_delta,
    parse_moe_otd_trace,
    stream_e_records,
)


class TestERecordIndices(unittest.TestCase):
    def test_miss_copy_uses_parts_12_not_transform(self) -> None:
        r = parse_moe_otd_trace(FIXTURE)
        self.assertTrue(r["present"])
        # Three misses: copy_ns 2e6+2.5e6+300 ns → seconds
        self.assertEqual(r["misses"], 3)
        self.assertEqual(r["hits"], 2)
        self.assertAlmostEqual(r["miss_copy_s"], 0.0045, places=4)
        self.assertAlmostEqual(r["miss_transform_s"], 0.0005, places=4)
        self.assertAlmostEqual(r["miss_read_s"], 0.0025, places=4)
        self.assertEqual(r["miss_bytes"], 1634304 + 1634304 + 1000)


class TestCRecordIndices(unittest.TestCase):
    def test_status_is_parts_6_not_routed_count(self) -> None:
        r = parse_moe_otd_trace(FIXTURE)
        self.assertEqual(r["calls_ok"], 1)
        self.assertEqual(r["calls_overflow"], 1)


class TestDeltaWindow(unittest.TestCase):
    def test_skip_first_n_e_records(self) -> None:
        # Skip first 2 E lines → remaining: hit, miss(overflow path), hit
        # E order: miss, hit, miss, miss, hit → skip 2 → miss, miss, hit
        r = parse_moe_otd_trace(FIXTURE, skip_e=2, take_e=3)
        self.assertEqual(r["e_records"], 3)
        self.assertEqual(r["hits"], 1)
        self.assertEqual(r["misses"], 2)
        self.assertEqual(r["miss_bytes"], 1634304 + 1000)
        self.assertAlmostEqual(r["miss_copy_s"], 0.0025, places=4)

    def test_aggregate_delta_matches_before_after(self) -> None:
        before = {"hits": 1, "misses": 1, "miss_bytes": 100, "miss_read_s": 0.001, "miss_copy_s": 0.002}
        after = {"hits": 3, "misses": 4, "miss_bytes": 1100, "miss_read_s": 0.011, "miss_copy_s": 0.022}
        d = aggregate_delta(before, after)
        self.assertEqual(d["hits"], 2)
        self.assertEqual(d["misses"], 3)
        self.assertEqual(d["touches"], 5)
        self.assertAlmostEqual(d["hit_rate"], 0.4, places=4)
        self.assertEqual(d["miss_bytes"], 1000)
        self.assertAlmostEqual(d["miss_read_s"], 0.01, places=6)
        self.assertAlmostEqual(d["miss_copy_s"], 0.02, places=6)

    def test_stream_does_not_require_full_read(self) -> None:
        n = sum(1 for _ in stream_e_records(FIXTURE))
        self.assertEqual(n, 5)


if __name__ == "__main__":
    unittest.main()
