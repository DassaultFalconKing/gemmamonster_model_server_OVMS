# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""PGP-05: strict, offline read-only screen of matched CIB2 A0/A1/B0/B1 receipts.

This does NOT benchmark hardware, validate attestation, or authorize a runtime arm.
All input values are untrusted operator claims until separate native receipts pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

SCHEMA = "cib2.pgp05_screen.v1"
OUTPUT_SCHEMA = "cib2.pgp05_review.v1"
MAX_BYTES = 4 * 1024 * 1024
MAX_SAMPLES = 1000
SHA_KEYS = ("checkpoint_sha", "export_sha", "tokenizer_sha", "quant_profile_sha",
            "ovms_build_sha", "genai_build_sha", "gpu_plugin_sha")
COHORT_KEYS = SHA_KEYS + ("model_key", "driver_version", "sdk_version", "device_key")
SCENARIO_KEYS = ("workload_key", "context_tokens", "slots", "offload_ratio",
                 "phase", "cache_state", "prompt_family")
GATE_KEYS = ("source_build_verified", "compiled_eligible", "native_pack_verified",
             "gpu_logits_parity", "agentic_parity", "lease_integrity",
             "no_gpu_reset", "no_swap_storm", "trace_complete")
SAMPLE_KEYS = ("index", "accepted_target_tokens", "wall_seconds", "ttft_ms",
               "tpot_p95_ms", "tpot_p99_ms", "startup_ms", "unique_memory_bytes",
               "physical_io")
ARMS = {
    "A0": ("identity", "usm_device"),
    "A1": ("optimized", "usm_device"),
    "B0": ("identity", "usm_host"),
    "B1": ("optimized", "usm_host"),
}
COMPARISONS = ("A1", "B0", "B1")


class ScreenError(ValueError):
    """Invalid or untrustworthy benchmark receipt; refuse evaluation."""


def _object(value, allowed, where):
    if type(value) is not dict or set(value) != set(allowed):
        raise ScreenError(f"{where}: expected exactly {sorted(allowed)}")
    return value


def _string(value, where, *, sha=False):
    if type(value) is not str or not value or len(value) > 128:
        raise ScreenError(f"{where}: expected a bounded nonempty string")
    if sha and (len(value) != 64 or any(c not in '0123456789abcdef' for c in value)):
        raise ScreenError(f"{where}: expected a lowercase SHA-256")
    if not sha and not all(c.isalnum() and ord(c) < 128 or c in "._:-" for c in value):
        raise ScreenError(f"{where}: unsanitized identifier")
    return value


def _int(value, where, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ScreenError(f"{where}: expected an integer in {low}..{high}")
    return value


def _number(value, where, low=0, *, strictly_positive=False):
    if type(value) not in (float, int):
        raise ScreenError(f"{where}: expected a finite number")
    if isinstance(value, int) and (value < low or value > 10**18):
        raise ScreenError(f"{where}: numeric bound exceeded")
    try:
        x = float(value)
    except (OverflowError, ValueError) as exc:
        raise ScreenError(f"{where}: cannot convert to finite number") from exc
    if not math.isfinite(x) or x < low or x > 1e18 or (strictly_positive and x == 0):
        raise ScreenError(f"{where}: nonfinite or out-of-range value")
    return x


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ScreenError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _load(data):
    if len(data) > MAX_BYTES:
        raise ScreenError("input exceeds 4 MiB limit")
    try:
        return json.loads(data.decode("utf-8-sig"), object_pairs_hook=_unique_pairs,
                          parse_constant=lambda s: (_ for _ in ()).throw(ScreenError("nonfinite JSON: " + s)))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ScreenError(f"invalid JSON: {exc}") from exc


def _cohort(value):
    _object(value, COHORT_KEYS, "cohort")
    for key in SHA_KEYS:
        _string(value[key], "cohort." + key, sha=True)
    for key in set(COHORT_KEYS) - set(SHA_KEYS):
        _string(value[key], "cohort." + key)
    return value


def _scenario(value):
    _object(value, SCENARIO_KEYS, "scenario")
    for key in ("context_tokens", "slots"):
        _int(value[key], "scenario." + key, 1, 262144 if key == "context_tokens" else 32)
    _int(value["offload_ratio"], "scenario.offload_ratio", 0, 100)
    for key in ("workload_key", "phase", "cache_state", "prompt_family"):
        _string(value[key], "scenario." + key)
    if value["phase"] not in ("prefill", "decode", "draft", "verify", "mixed"):
        raise ScreenError("scenario.phase unsupported")
    if value["cache_state"] not in ("cold", "warm"):
        raise ScreenError("scenario.cache_state unsupported")
    return value


def _io(value):
    if type(value) is not dict:
        raise ScreenError("physical_io: expected object")
    status = value.get("status")
    if status == "NOT_EXPOSED":
        _object(value, ("status", "reason"), "physical_io")
        _string(value["reason"], "physical_io.reason")
        return None
    if status == "EXPOSED":
        _object(value, ("status", "source", "device_read_bytes"), "physical_io")
        if value["source"] != "device_counter":
            raise ScreenError("physical_io: only actual device_counter source is allowed")
        return _int(value["device_read_bytes"], "physical_io.device_read_bytes", 0, 2**63 - 1)
    raise ScreenError("physical_io.status: EXPOSED or NOT_EXPOSED required")


def _sample(value, expected_index):
    _object(value, SAMPLE_KEYS, f"sample[{expected_index}]")
    if _int(value["index"], "sample.index", 0, MAX_SAMPLES) != expected_index:
        raise ScreenError("samples must be ordered 0..N-1, for matched pair comparisons")
    _int(value["accepted_target_tokens"], "accepted_target_tokens", 1, 10**9)
    _number(value["wall_seconds"], "wall_seconds", strictly_positive=True)
    for key in ("ttft_ms", "tpot_p95_ms", "tpot_p99_ms", "startup_ms"):
        _number(value[key], key)
    if value["tpot_p99_ms"] < value["tpot_p95_ms"]:
        raise ScreenError("tpot_p99_ms below p95")
    _int(value["unique_memory_bytes"], "unique_memory_bytes", 0, 2**63 - 1)
    return _io(value["physical_io"])


def validate_receipt(data):
    _object(data, ("schema", "synthetic", "arms"), "receipt")
    if data["schema"] != SCHEMA or type(data["synthetic"]) is not bool:
        raise ScreenError("unsupported schema or synthetic flag")
    arms = data["arms"]
    if type(arms) is not list or not 2 <= len(arms) <= 4:
        raise ScreenError("receipt must contain 2..4 distinct benchmark arms")
    by_id = {}
    for arm in arms:
        _object(arm, ("id", "layout", "resident_mode", "profile_sha",
                      "pack_manifest_sha", "cohort", "scenario", "gates",
                      "warmups", "samples"), "arm")
        key = arm["id"]
        if key not in ARMS or key in by_id:
            raise ScreenError("unknown or repeated arm ID")
        expected_layout, expected_resident = ARMS[key]
        if arm["layout"] != expected_layout or arm["resident_mode"] != expected_resident:
            raise ScreenError(f"{key}: layout/resident label mismatch")
        if expected_layout == "identity":
            if arm["profile_sha"] is not None:
                raise ScreenError(f"{key}: identity must have null profile_sha")
        else:
            _string(arm["profile_sha"], f"{key}.profile_sha", sha=True)
        _string(arm["pack_manifest_sha"], f"{key}.pack_manifest_sha", sha=True)
        _cohort(arm["cohort"])
        _scenario(arm["scenario"])
        _object(arm["gates"], GATE_KEYS, f"{key}.gates")
        for gate in GATE_KEYS:
            if type(arm["gates"][gate]) is not bool:
                raise ScreenError(f"{key}.gates.{gate}: expected bool")
        _int(arm["warmups"], f"{key}.warmups", 1, 1000)
        samples = arm["samples"]
        if type(samples) is not list or not 3 <= len(samples) <= MAX_SAMPLES:
            raise ScreenError(f"{key}: >=3 measured samples required")
        for index, sample in enumerate(samples):
            _sample(sample, index)
        by_id[key] = arm
    if "A0" not in by_id:
        raise ScreenError("canonical A0 is required for every comparison")
    if "B1" in by_id and not {"A1", "B0"} <= by_id.keys():
        raise ScreenError("B1 requires A1 and B0 controls")
    a0 = by_id["A0"]
    for key, arm in by_id.items():
        if arm["cohort"] != a0["cohort"] or arm["scenario"] != a0["scenario"]:
            raise ScreenError(f"{key}: cohort/scenario mismatch, refusing comparison")
        if arm["warmups"] != a0["warmups"]:
            raise ScreenError(f"{key}: warmups differ from A0")
        if len(arm["samples"]) != len(a0["samples"]):
            raise ScreenError(f"{key}: sample count differs from A0")
        for index, sample in enumerate(arm["samples"]):
            if sample["accepted_target_tokens"] != a0["samples"][index]["accepted_target_tokens"]:
                raise ScreenError(
                    f"{key}: accepted_target_tokens mismatch vs A0 at sample {index}"
                )
    if "A1" in by_id and "B1" in by_id and by_id["A1"]["profile_sha"] != by_id["B1"]["profile_sha"]:
        raise ScreenError("A1/B1 optimized placement must use the same profile SHA")
    # Same layout must share pack identity so resident-mode contrasts are not
    # confounded by different pack files (A0↔B0 identity, A1↔B1 optimized).
    if "B0" in by_id and by_id["B0"]["pack_manifest_sha"] != by_id["A0"]["pack_manifest_sha"]:
        raise ScreenError("A0/B0 identity packs must share pack_manifest_sha")
    if "A1" in by_id and "B1" in by_id and (
            by_id["A1"]["pack_manifest_sha"] != by_id["B1"]["pack_manifest_sha"]):
        raise ScreenError("A1/B1 optimized packs must share pack_manifest_sha")
    return by_id


def _median(vals):
    return statistics.median(vals)


def _summarize(arm):
    samples = arm["samples"]
    tokens = [s["accepted_target_tokens"] for s in samples]
    tps_vals = []
    for sample in samples:
        tps = sample["accepted_target_tokens"] / sample["wall_seconds"]
        if not math.isfinite(tps):
            raise ScreenError(
                "derived accepted_target_tps is nonfinite; wall_seconds too small "
                "relative to accepted_target_tokens"
            )
        tps_vals.append(tps)
    io = [_io(s["physical_io"]) for s in samples]
    summary = {
        "median_accepted_target_tps": _median(tps_vals),
        "median_ttft_ms": _median([s["ttft_ms"] for s in samples]),
        "median_tpot_p95_ms": _median([s["tpot_p95_ms"] for s in samples]),
        "median_tpot_p99_ms": _median([s["tpot_p99_ms"] for s in samples]),
        "median_startup_ms": _median([s["startup_ms"] for s in samples]),
        "max_unique_memory_bytes": max(s["unique_memory_bytes"] for s in samples),
        "physical_device_bytes_per_accepted_token": (
            sum(io) / sum(tokens) if all(x is not None for x in io) else None
        ),
        "physical_io_status": "EXPOSED" if all(x is not None for x in io) else "NOT_EXPOSED",
    }
    # A finite per-sample TPS is not enough: median() on an even-sized
    # sample set can overflow when it averages two very large finite floats.
    for name, value in summary.items():
        if type(value) is float and not math.isfinite(value):
            raise ScreenError("derived %s is nonfinite" % name)
    return summary


def _comparison(a0, candidate):
    result = {}
    for key in ("median_accepted_target_tps", "median_ttft_ms", "median_tpot_p95_ms",
                "median_tpot_p99_ms", "median_startup_ms", "max_unique_memory_bytes",
                "physical_device_bytes_per_accepted_token"):
        baseline, proposed = a0[key], candidate[key]
        delta = (
            (proposed / baseline - 1) * 100 if baseline is not None and proposed is not None and baseline > 0 else None
        )
        if delta is not None and not math.isfinite(delta):
            raise ScreenError("derived %s delta is nonfinite" % key)
        result[key + "_delta_pct"] = delta
    return result


def screen_receipt(data, raw_sha256):
    by_id = validate_receipt(data)
    summary = {key: _summarize(arm) for key, arm in sorted(by_id.items())}
    blockers = []
    for key, arm in sorted(by_id.items()):
        for gate in GATE_KEYS:
            if not arm["gates"][gate]:
                blockers.append(f"{key}.{gate}=false")
    if data["synthetic"]:
        blockers.append("synthetic data is not hardware evidence")
    if set(by_id) != set(ARMS):
        blockers.append("A0/A1/B0/B1 matrix incomplete")
    comparisons = {k + "_vs_A0": _comparison(summary["A0"], summary[k])
                   for k in COMPARISONS if k in summary}
    return {
        "schema": OUTPUT_SCHEMA,
        "source_sha256": raw_sha256,
        "status": "BLOCKED" if blockers else "OFFLINE_REVIEW_ONLY",
        "offline_only": True,
        "runtime_acceptance": "NO",
        "promotion_authorized": False,
        "matrix_complete": set(by_id) == set(ARMS),
        "blockers": blockers,
        "summary": summary,
        "comparisons": comparisons,
        "notes": [
            "Metrics are derived from untrusted receipts, not independently observed hardware.",
            "Device counter bytes are physical-device counters, not exact per-file NVMe attribution.",
            "Physical I/O unknown is null, never zero or inferred from requested_read_bytes.",
            "Even OFFLINE_REVIEW_ONLY is not GPU, pack, provenance or owner acceptance.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="immutable sanitized receipt JSON")
    args = parser.parse_args(argv)
    try:
        p = Path(args.input)
        if not p.is_file() or p.stat().st_size > MAX_BYTES:
            raise ScreenError("input must be a readable <=4 MiB JSON file")
        raw = p.read_bytes()
        result = screen_receipt(_load(raw), hashlib.sha256(raw).hexdigest())
    except (OSError, ScreenError, ValueError, OverflowError) as exc:
        json.dump({"schema": OUTPUT_SCHEMA, "status": "REJECTED", "error": str(exc),
                   "runtime_acceptance": "NO", "promotion_authorized": False}, sys.stderr)
        sys.stderr.write("\n")
        return 2
    try:
        # Validate serialization before writing to stdout. json.dump() can
        # otherwise emit a partial object before rejecting an invalid value.
        encoded = json.dumps(result, indent=2, allow_nan=False)
    except (ValueError, OverflowError) as exc:
        json.dump({"schema": OUTPUT_SCHEMA, "status": "REJECTED", "error": str(exc),
                   "runtime_acceptance": "NO", "promotion_authorized": False}, sys.stderr)
        sys.stderr.write("\n")
        return 2
    sys.stdout.write(encoded + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
