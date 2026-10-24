# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""CIB2 PGP: deterministic advisory hot/warm/cold spans from VERIFIED V2 plans.

Does NOT split OTDPACK1, rewrite hashes, or enable serving a shard.
Native shard ABI, bounded physical read and manifest binding are separate gates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from . import packv2_pipeline
except ImportError:
    import packv2_pipeline


class CohortError(ValueError):
    pass


def group_layer(entry: dict, max_records: int = 64) -> dict:
    if type(max_records) is not int or not 1 <= max_records <= 16384:
        raise CohortError("invalid max_records")
    key = entry.get("pack_layer_key")
    permutation = entry.get("placement")
    tiers = entry.get("resident_tiers")
    if type(key) is not str or len(key) != 16 or any(c not in "0123456789abcdef" for c in key):
        raise CohortError("invalid native compiled key")
    if type(permutation) is not list or not permutation or len(permutation) > 16384 or (
        any(type(i) is not int for i in permutation) or sorted(permutation) != list(range(len(permutation)))
    ):
        raise CohortError("placement is not a permutation")
    if type(tiers) is not list or len(tiers) != len(permutation) or (
        any(type(x) is not int or x not in (0, 1, 2) for x in tiers)
    ):
        raise CohortError("tier vector invalid")
    physical = [None] * len(permutation)
    for logical, slot in enumerate(permutation):
        physical[slot] = (logical, tiers[logical])
    groups = []
    for pos, (logical, tier) in enumerate(physical):
        if (not groups or groups[-1]["tier"] != tier or
                groups[-1]["start_physical"] + len(groups[-1]["logical_experts"]) != pos or
                len(groups[-1]["logical_experts"]) >= max_records):
            groups.append({"tier": tier, "start_physical": pos, "logical_experts": []})
        groups[-1]["logical_experts"].append(logical)
    # Every record appears exactly once and every physical range is disjoint.
    assert sum(map(lambda g: len(g["logical_experts"]), groups)) == len(permutation)
    return {"pack_layer_key": key, "expert_count": len(permutation),
            "groups": groups, "advisory_only": True}


def build_cohorts(plans: dict, max_records: int = 64) -> dict:
    if plans.get("schema") != "cib2.pack_placement_plans.v2" or plans.get("pack_acceptance") != "NO":
        raise CohortError("expected pre-acceptance verified V2 plan")
    entries = plans.get("layers")
    if type(entries) is not list or not entries or len(entries) > 512:
        raise CohortError("invalid layer count")
    results = [group_layer(e, max_records) for e in entries]
    keys = [e["pack_layer_key"] for e in results]
    if len(set(keys)) != len(keys):
        raise CohortError("repeated compiled layer key")
    return {"schema": "cib2.pack_cohort_advisory.v1",
            "status": "ADVISORY_NO_SHARDING", "runtime_acceptance": "NO",
            "native_record_abi": "OTDPACK1_UNCHANGED",
            "max_records": max_records, "layers": sorted(results, key=lambda e: e["pack_layer_key"])}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plans_dir", type=Path)
    p.add_argument("--max-records", type=int, default=64)
    a = p.parse_args(argv)
    try:
        verified = packv2_pipeline._read_plans(a.plans_dir)
        print(json.dumps(build_cohorts(verified, a.max_records), indent=2, sort_keys=True))
    except (CohortError, packv2_pipeline.GenerationError) as exc:
        p.exit(2, f"CIB2 grouping rejected: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
