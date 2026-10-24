# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "cib2"))
import pack_cohorts as cohorts


class CohortPlanTest(unittest.TestCase):
    def layer(self):
        return {"pack_layer_key": "0000000000000001", "placement": [2, 0, 3, 1],
                "resident_tiers": [2, 0, 1, 0]}

    def test_contiguous_physical_and_all_experts(self):
        item = cohorts.group_layer(self.layer())
        seen = [x for g in item["groups"] for x in g["logical_experts"]]
        self.assertCountEqual(seen, [0, 1, 2, 3])
        self.assertEqual([g["start_physical"] for g in item["groups"]], [0, 2, 3])
        self.assertEqual([g["tier"] for g in item["groups"]], [0, 2, 1])

    def test_split_bounded_not_a_pack_shard(self):
        l = self.layer()
        l["resident_tiers"] = [0, 0, 0, 0]
        groups = cohorts.group_layer(l, 2)["groups"]
        self.assertEqual([len(g["logical_experts"]) for g in groups], [2, 2])
        self.assertTrue(cohorts.group_layer(l)["advisory_only"])

    def test_fail_closed_invalid(self):
        for name, value in (("placement", [0, 1, 1, 3]),
                            ("resident_tiers", [0, 1, 2]),
                            ("resident_tiers", [0, 1, 3, 0])):
            item = self.layer()
            item[name] = value
            with self.subTest(name=name, value=value), self.assertRaises(cohorts.CohortError):
                cohorts.group_layer(item)
        with self.assertRaises(cohorts.CohortError):
            cohorts.group_layer(self.layer(), 0)

    def test_advisory_envelope(self):
        result = cohorts.build_cohorts({"schema": "cib2.pack_placement_plans.v2",
                                         "pack_acceptance": "NO", "layers": [self.layer()]})
        self.assertEqual(result["status"], "ADVISORY_NO_SHARDING")
        self.assertEqual(result["native_record_abi"], "OTDPACK1_UNCHANGED")
        with self.assertRaises(cohorts.CohortError):
            cohorts.build_cohorts({"schema": "cib2.pack_placement_plans.v2",
                                     "pack_acceptance": "YES", "layers": [self.layer()]})


if __name__ == "__main__":
    unittest.main()
