# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""PGP-02 tests: deterministic offline Pack V1 logical->physical placement.

These tests are synthetic/offline only.  They never read model weights, BIN
files, real traces, or pack files, and they do not claim runtime/profile/pack
acceptance or native full-payload parity.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pack_layout"
sys.path.insert(0, str(ROOT / "scripts" / "cib2"))

import pack_layout as pl  # noqa: E402
from pack_layout import LayoutError, ProfileError  # noqa: E402

PROVENANCE = ("checkpoint_sha", "export_sha", "compiled_layer_key",
              "quant_profile_sha", "profile_key")


def _read_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _load(name: str):
    data = _read_bytes(name)
    return data, pl.load_profile_bytes(data), hashlib.sha256(data).hexdigest()


def _base_profile() -> dict:
    return copy.deepcopy(json.loads(_read_bytes("identity_empty.json").decode("utf-8")))


def _objective(order, pairs):
    position = {logical: physical for physical, logical in enumerate(order)}
    return sum(weight * abs(position[a] - position[b]) for a, b, weight in pairs)


def _pairs(profile):
    return [(pair.expert_a, pair.expert_b, pair.weight) for pair in profile.coaccess
            if pair.weight > 0.0]


class ProfileValidationTest(unittest.TestCase):
    def assert_rejected(self, mutate, fragment):
        profile = _base_profile()
        mutate(profile)
        with self.assertRaises(ProfileError) as ctx:
            pl.validate_profile(profile)
        self.assertIn(fragment, str(ctx.exception))

    def test_valid_fixtures_are_explicitly_synthetic_and_complete(self):
        for name in ("identity_empty.json", "frequency_ties.json",
                     "coaccess_cluster.json", "sparse_unseen.json"):
            with self.subTest(fixture=name):
                _data, profile, _sha = _load(name)
                self.assertTrue(profile.synthetic)
                self.assertTrue(profile.provenance["sanitized"])
                self.assertEqual(profile.provenance["source"], "synthetic")

    def test_incomplete_marker_is_rejected(self):
        with self.assertRaises(ProfileError) as ctx:
            pl.load_profile_bytes(_read_bytes("incomplete_marker.json"))
        self.assertIn("incomplete", str(ctx.exception))

    def test_provenance_mismatch_is_rejected(self):
        with self.assertRaises(ProfileError) as ctx:
            pl.load_profile_bytes(_read_bytes("provenance_mismatch.json"))
        self.assertIn("provenance mismatch", str(ctx.exception))

    def test_nonfinite_cost_is_rejected(self):
        with self.assertRaises(ProfileError) as ctx:
            pl.load_profile_bytes(_read_bytes("nonfinite_cost.json"))
        self.assertIn("non-finite", str(ctx.exception))

    def test_missing_and_unsafe_fields_are_rejected(self):
        self.assert_rejected(lambda p: p.pop("complete"), "missing required")
        self.assert_rejected(lambda p: p.update({"payload_bytes": [0] * 8}), "unknown field")
        self.assert_rejected(lambda p: p["provenance"].update({"tensors": "hot"}),
                             "unknown field")
        self.assert_rejected(lambda p: p["experts"].append({
            "logical_expert_id": 0, "miss_count": 1, "read_cost_us": 1.0, "hotness": 9,
        }), "unknown field")

    def test_duplicate_and_out_of_range_experts_are_rejected(self):
        def duplicate(profile):
            profile["experts"] = [
                {"logical_expert_id": 1, "miss_count": 1, "read_cost_us": 1.0},
                {"logical_expert_id": 1, "miss_count": 2, "read_cost_us": 2.0},
            ]

        def out_of_range(profile):
            profile["experts"] = [
                {"logical_expert_id": 8, "miss_count": 1, "read_cost_us": 1.0},
            ]

        def too_many(profile):
            profile["experts"] = [
                {"logical_expert_id": index, "miss_count": 1, "read_cost_us": 1.0}
                for index in range(9)
            ]

        self.assert_rejected(duplicate, "duplicate logical_expert_id")
        self.assert_rejected(out_of_range, "outside 0..7")
        self.assert_rejected(too_many, "more entries than expert_count")

    def test_negative_counts_and_costs_are_rejected(self):
        def negative_miss(profile):
            profile["experts"] = [
                {"logical_expert_id": 0, "miss_count": -1, "read_cost_us": 1.0},
            ]

        def negative_cost(profile):
            profile["experts"] = [
                {"logical_expert_id": 0, "miss_count": 1, "read_cost_us": -0.5},
            ]

        self.assert_rejected(negative_miss, "outside 0")
        self.assert_rejected(negative_cost, "outside 0.0")

    def test_duplicate_self_and_negative_coaccess_are_rejected(self):
        def duplicate(profile):
            profile["coaccess"] = [
                {"expert_a": 0, "expert_b": 1, "weight": 1.0},
                {"expert_a": 1, "expert_b": 0, "weight": 2.0},
            ]

        def self_pair(profile):
            profile["coaccess"] = [{"expert_a": 2, "expert_b": 2, "weight": 1.0}]

        def negative(profile):
            profile["coaccess"] = [{"expert_a": 0, "expert_b": 1, "weight": -1.0}]

        def out_of_range(profile):
            profile["coaccess"] = [{"expert_a": 0, "expert_b": 8, "weight": 1.0}]

        self.assert_rejected(duplicate, "duplicate coaccess pair")
        self.assert_rejected(self_pair, "repeats expert")
        self.assert_rejected(negative, "outside 0.0")
        self.assert_rejected(out_of_range, "outside 0..7")

    def test_complete_synthetic_and_sanitized_markers_are_strict(self):
        self.assert_rejected(lambda p: p.update({"complete": False}), "incomplete")
        self.assert_rejected(lambda p: p.update({"complete": 1}), "boolean")
        self.assert_rejected(lambda p: p.update({"synthetic": "yes"}), "boolean")
        self.assert_rejected(lambda p: p["provenance"].update({"sanitized": False}),
                             "must be true")
        self.assert_rejected(lambda p: p["provenance"].update({"source": "runtime"}),
                             "expected one of")

    def test_duplicate_json_keys_are_rejected(self):
        raw = _read_bytes("identity_empty.json").decode("utf-8")
        raw = raw.replace('"expert_count": 8', '"expert_count": 8, "expert_count": 8')
        with self.assertRaises(ProfileError) as ctx:
            pl.load_profile_bytes(raw.encode("utf-8"))
        self.assertIn("duplicate JSON key", str(ctx.exception))


class DeterministicLayoutTest(unittest.TestCase):
    def test_identity_is_the_exact_full_permutation(self):
        _data, profile, sha = _load("frequency_ties.json")
        layout = pl.build_layout(profile, "identity", source_sha256=sha)
        self.assertEqual(layout["placement"], [0, 1, 2, 3, 4, 5])
        self.assertEqual(layout["order"], [0, 1, 2, 3, 4, 5])
        self.assertEqual(layout["strategy_effective"], "identity")
        self.assertFalse(layout["fallback"]["used"])
        pl.validate_layout(layout)

    def test_frequency_ties_use_score_then_logical_id(self):
        _data, profile, sha = _load("frequency_ties.json")
        layout = pl.build_layout(profile, "frequency", seed=99, source_sha256=sha)
        # score 20: 0,1,3; score 10: 2; zero evidence: 4,5.
        self.assertEqual(layout["order"], [0, 1, 3, 2, 4, 5])
        self.assertEqual(layout["placement"], [0, 1, 3, 2, 4, 5])
        self.assertEqual(layout["objective"]["evidence"]["evidenced_expert_ids"], [0, 1, 3, 2])
        self.assertEqual(layout["objective"]["evidence"]["tie_break"],
                         "descending score, then ascending logical_expert_id")
        self.assertEqual(layout["source_profile"]["sha256"], sha)
        self.assertEqual(layout["source_profile"]["sha256"],
                         hashlib.sha256(_read_bytes("frequency_ties.json")).hexdigest())

    def test_repeated_runs_are_byte_identical_and_seed_is_recorded(self):
        _data, profile, sha = _load("frequency_ties.json")
        first = pl.build_layout(profile, "frequency", seed=7, source_sha256=sha)
        second = pl.build_layout(profile, "frequency", seed=7, source_sha256=sha)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(first["seed"], 7)
        self.assertEqual(first["seed_used_for"], "coaccess tie-break only")

    def test_sparse_experts_are_not_given_invented_hotness(self):
        _data, profile, sha = _load("sparse_unseen.json")
        layout = pl.build_layout(profile, "frequency", source_sha256=sha)
        # observed positive scores: 5 (6.0), 1 (4.0); then all zero/unseen by ID.
        self.assertEqual(layout["order"], [5, 1, 0, 2, 3, 4, 6, 7])
        evidence = layout["objective"]["evidence"]
        self.assertEqual(evidence["evidenced_expert_ids"], [5, 1])
        self.assertEqual(evidence["zero_cost_expert_ids"], [6])
        self.assertEqual(evidence["unseen_expert_ids"], [0, 2, 3, 4, 7])
        self.assertEqual(evidence["score_total"], 10.0)

    def test_coaccess_greedy_beats_identity_on_offline_objective(self):
        _data, profile, sha = _load("coaccess_cluster.json")
        layout = pl.build_layout(profile, "coaccess", seed=0, source_sha256=sha)
        pairs = _pairs(profile)
        identity_order = list(range(profile.expert_count))
        identity_value = _objective(identity_order, pairs)
        candidate_value = _objective(layout["order"], pairs)
        self.assertLess(candidate_value, identity_value)
        self.assertEqual(layout["objective"]["identity_baseline_value"], identity_value)
        self.assertEqual(layout["objective"]["candidate_value"], candidate_value)
        self.assertFalse(layout["fallback"]["used"])
        position = {logical: physical for physical, logical in enumerate(layout["order"])}
        self.assertEqual(abs(position[0] - position[2]), 1)
        self.assertEqual(abs(position[1] - position[3]), 1)
        self.assertEqual(layout["validation"],
                         {"permutation": True, "logical_ids_preserved": True,
                          "inverse_consistent": True, "physical_positions_complete": True})

    def test_coaccess_is_deterministic_for_the_same_seed(self):
        _data, profile, sha = _load("coaccess_cluster.json")
        runs = [pl.build_layout(profile, "coaccess", seed=11, source_sha256=sha)
                for _ in range(3)]
        self.assertEqual(runs[0]["order"], runs[1]["order"])
        self.assertEqual(runs[0]["order"], runs[2]["order"])
        self.assertEqual(runs[0]["placement"], runs[2]["placement"])
        pl.validate_layout(runs[0])

    def test_coaccess_seed_controls_documented_tie_break(self):
        _data, profile, sha = _load("coaccess_cluster.json")
        first = pl.build_layout(profile, "coaccess", seed=0, source_sha256=sha)
        again = pl.build_layout(profile, "coaccess", seed=0, source_sha256=sha)
        other = pl.build_layout(profile, "coaccess", seed=2, source_sha256=sha)
        self.assertEqual(first["order"], again["order"])
        self.assertNotEqual(first["order"], other["order"])
        self.assertEqual(other["seed"], 2)
        pl.validate_layout(other)

    def test_coaccess_without_pairs_falls_back_to_identity(self):
        _data, profile, sha = _load("identity_empty.json")
        layout = pl.build_layout(profile, "coaccess", source_sha256=sha)
        self.assertEqual(layout["order"], list(range(8)))
        self.assertTrue(layout["fallback"]["used"])
        self.assertEqual(layout["fallback"]["reason"], "no_coaccess_evidence")
        self.assertEqual(layout["placement"], list(range(8)))

    def test_coaccess_without_improvement_retains_identity(self):
        profile = _base_profile()
        profile["expert_count"] = 3
        profile["experts"] = []
        profile["coaccess"] = [
            {"expert_a": 0, "expert_b": 1, "weight": 10.0},
            {"expert_a": 1, "expert_b": 2, "weight": 10.0},
            {"expert_a": 0, "expert_b": 2, "weight": 1.0},
        ]
        sha = "0" * 64
        layout = pl.build_layout(pl.validate_profile(profile), "coaccess", source_sha256=sha)
        self.assertEqual(layout["order"], [0, 1, 2])
        self.assertTrue(layout["fallback"]["used"])
        self.assertEqual(layout["fallback"]["reason"], "coaccess_no_offline_improvement")

    def test_frequency_without_positive_evidence_falls_back_to_identity(self):
        _data, profile, sha = _load("identity_empty.json")
        layout = pl.build_layout(profile, "frequency", source_sha256=sha)
        self.assertEqual(layout["order"], list(range(8)))
        self.assertTrue(layout["fallback"]["used"])
        self.assertEqual(layout["fallback"]["reason"], "no_observed_frequency_evidence")

    def test_no_profile_uses_explicit_identity_fallback(self):
        layout = pl.build_layout(None, "frequency", expert_count=4)
        self.assertEqual(layout["placement"], [0, 1, 2, 3])
        self.assertEqual(layout["expert_count"], 4)
        self.assertEqual(layout["strategy_effective"], "identity")
        self.assertEqual(layout["fallback"]["reason"], "no_profile_supplied")
        self.assertIsNone(layout["scope"])
        self.assertFalse(layout["source_profile"]["supplied"])
        with self.assertRaises(LayoutError):
            pl.build_layout(None, "identity")

    def test_supplied_profile_requires_its_source_sha(self):
        _data, profile, _sha = _load("identity_empty.json")
        with self.assertRaises(LayoutError):
            pl.build_layout(profile, "identity")
        with self.assertRaises(LayoutError):
            pl.build_layout(profile, "identity", source_sha256="not-a-sha")


class PermutationAndIsolationTest(unittest.TestCase):
    def test_placement_and_order_are_exact_inverses(self):
        for name in ("frequency_ties.json", "coaccess_cluster.json", "sparse_unseen.json"):
            for strategy in ("identity", "frequency", "coaccess"):
                with self.subTest(fixture=name, strategy=strategy):
                    _data, profile, sha = _load(name)
                    layout = pl.build_layout(profile, strategy, source_sha256=sha)
                    count = profile.expert_count
                    self.assertEqual(sorted(layout["placement"]), list(range(count)))
                    self.assertEqual(sorted(layout["order"]), list(range(count)))
                    inverse = [0] * count
                    for logical, physical in enumerate(layout["placement"]):
                        inverse[physical] = logical
                    self.assertEqual(inverse, layout["order"])

    def test_validate_layout_rejects_tampering(self):
        _data, profile, sha = _load("coaccess_cluster.json")
        layout = pl.build_layout(profile, "coaccess", source_sha256=sha)
        broken = copy.deepcopy(layout)
        broken["placement"][0], broken["placement"][1] = (
            broken["placement"][1], broken["placement"][0])
        with self.assertRaises(LayoutError):
            pl.validate_layout(broken)
        accepted = copy.deepcopy(layout)
        accepted["runtime_acceptance"] = "YES"
        with self.assertRaises(LayoutError):
            pl.validate_layout(accepted)

    def test_scope_keys_are_exact_and_isolated(self):
        _data, profile, sha = _load("frequency_ties.json")
        layout = pl.build_layout(profile, "frequency", source_sha256=sha)
        scope = layout["scope"]
        self.assertEqual(set(scope), {"model_key", "logical_layer_id", *PROVENANCE})
        for key in PROVENANCE:
            self.assertEqual(scope[key], profile.provenance[key])
        self.assertEqual(scope["model_key"], profile.scope["model_key"])
        self.assertEqual(scope["logical_layer_id"], profile.scope["logical_layer_id"])
        self.assertNotEqual(scope["checkpoint_sha"], scope["export_sha"])

        changed = copy.deepcopy(profile)
        changed.provenance["checkpoint_sha"] = "9" * 64
        other = pl.build_layout(changed, "frequency", source_sha256=sha)
        self.assertEqual(other["scope"]["checkpoint_sha"], "9" * 64)
        self.assertEqual(other["scope"]["export_sha"], layout["scope"]["export_sha"])
        self.assertEqual(other["scope"]["compiled_layer_key"],
                         layout["scope"]["compiled_layer_key"])

    def test_output_never_claims_payload_or_runtime_changes(self):
        _data, profile, sha = _load("coaccess_cluster.json")
        layout = pl.build_layout(profile, "coaccess", source_sha256=sha)
        self.assertTrue(layout["offline_only"])
        self.assertEqual(layout["runtime_acceptance"], "NO")
        self.assertEqual(layout["profile_acceptance"], "NO")
        self.assertEqual(layout["pack_acceptance"], "NO")
        self.assertEqual(layout["policy"]["payload_bytes"], "UNCHANGED")
        self.assertEqual(layout["policy"]["tensors"], "UNTOUCHED")
        self.assertFalse(layout["policy"]["pack_v2"])
        self.assertEqual(layout["policy"]["resident_mode"], "UNCHANGED")
        self.assertEqual(layout["policy"]["prefetch"], "OFF")
        self.assertEqual(layout["policy"]["pinning"], "OFF")
        self.assertEqual(layout["handoff"]["native_full_payload_parity"], "NOT_RUN")
        self.assertTrue(any("synthetic profile fixture" in warning
                            for warning in layout["warnings"]))


class CommandLineTest(unittest.TestCase):
    def _run(self, argv):
        err = io.StringIO()
        with redirect_stderr(err):
            code = pl.main(argv)
        return code, err.getvalue()

    def test_cli_valid_frequency_writes_validated_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "layout.json"
            code, err = self._run([
                "--profile", str(FIXTURES / "frequency_ties.json"),
                "--output", str(out), "--strategy", "frequency",
            ])
            self.assertEqual(code, 0, err)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["order"], [0, 1, 3, 2, 4, 5])
            self.assertEqual(payload["source_profile"]["sha256"],
                             hashlib.sha256(_read_bytes("frequency_ties.json")).hexdigest())
            pl.validate_layout(payload)

    def test_cli_missing_profile_requires_explicit_expert_count(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "layout.json"
            code, err = self._run([
                "--output", str(out), "--strategy", "identity",
            ])
            self.assertEqual(code, 2)
            self.assertIn("expert-count", err)
            self.assertFalse(out.exists())

            code, err = self._run([
                "--output", str(out), "--strategy", "frequency", "--expert-count", "3",
            ])
            self.assertEqual(code, 0, err)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["placement"], [0, 1, 2])
            self.assertEqual(payload["fallback"]["reason"], "no_profile_supplied")

    def test_cli_malformed_supplied_profile_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "layout.json"
            for fixture in ("incomplete_marker.json", "provenance_mismatch.json",
                            "nonfinite_cost.json"):
                with self.subTest(fixture=fixture):
                    code, err = self._run([
                        "--profile", str(FIXTURES / fixture),
                        "--output", str(out), "--strategy", "identity",
                    ])
                    self.assertEqual(code, 2)
                    self.assertIn("REJECTED", err)
                    self.assertFalse(out.exists())

    def test_cli_duplicate_json_key_and_missing_file_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "layout.json"
            duplicate = Path(directory) / "duplicate.json"
            raw = _read_bytes("identity_empty.json").decode("utf-8")
            duplicate.write_text(
                raw.replace('"expert_count": 8', '"expert_count": 8, "expert_count": 8'),
                encoding="utf-8",
            )
            code, err = self._run([
                "--profile", str(duplicate), "--output", str(out),
                "--strategy", "identity",
            ])
            self.assertEqual(code, 2)
            self.assertIn("duplicate JSON key", err)

            code, err = self._run([
                "--profile", str(Path(directory) / "absent.json"),
                "--output", str(out), "--strategy", "identity",
            ])
            self.assertEqual(code, 2)
            self.assertFalse(out.exists())

    def test_cli_refuses_bin_input_without_reading_it(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "weights.bin"
            binary.write_bytes(b"\x00\x01\x02")
            out = Path(directory) / "layout.json"
            code, err = self._run([
                "--profile", str(binary), "--output", str(out), "--strategy", "identity",
            ])
            self.assertEqual(code, 2)
            self.assertIn("refusing .bin", err)
            self.assertFalse(out.exists())

    def test_cli_rejects_profile_and_expert_count_together(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "layout.json"
            code, err = self._run([
                "--profile", str(FIXTURES / "identity_empty.json"),
                "--output", str(out), "--strategy", "identity", "--expert-count", "8",
            ])
            self.assertEqual(code, 2)
            self.assertIn("only valid when --profile is omitted", err)
            self.assertFalse(out.exists())

    def test_cli_rejects_missing_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "absent" / "layout.json"
            code, err = self._run([
                "--profile", str(FIXTURES / "identity_empty.json"),
                "--output", str(out), "--strategy", "identity",
            ])
            self.assertEqual(code, 2)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
