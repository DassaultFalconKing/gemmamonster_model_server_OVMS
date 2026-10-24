# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Convert a COMPLETE native GPU moe_otd_trace v1 into scoped PGP-02 profiles.

This is a profile adapter, not a GPU trace producer or provenance authenticator.
Refuses incomplete, truncated, incoherent and oversized traces. No model BIN is read.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

try:
    from . import pack_layout
except ImportError:
    import pack_layout

MAX_TRACE_BYTES = 128 * 1024 * 1024
MAX_EVENTS = 2_000_000
MAX_LAYERS = 512
MAX_LINE = 4096
END_RE = re.compile(r"^# end,calls=(\d+),experts=(\d+),incomplete_calls=(\d+),incomplete_experts=(\d+)$")
HEX16 = re.compile(r"^[0-9a-f]{1,16}$")


class TraceError(ValueError):
    pass


def _number(text, label, maximum=(1 << 53) - 1):
    if not text or not text.isascii() or not text.isdecimal():
        raise TraceError(label + ": expected unsigned decimal")
    value = int(text)
    if value > maximum:
        raise TraceError(label + ": exceeds bound")
    return value


def _identity(data):
    if type(data) is not dict or set(data) != {"schema", "model_key", "checkpoint_sha", "export_sha", "quant_profile_sha", "profile_key", "layers"}:
        raise TraceError("identity: exact versioned keys required")
    if data["schema"] != "cib2.trace_identity.v1":
        raise TraceError("identity schema mismatch")
    for key in ("checkpoint_sha", "export_sha", "quant_profile_sha"):
        if not pack_layout.SHA256_RE.fullmatch(str(data[key])):
            raise TraceError("identity invalid SHA: " + key)
    if not pack_layout.MODEL_KEY_RE.fullmatch(str(data["model_key"])):
        raise TraceError("identity invalid model_key")
    if not pack_layout.PROFILE_KEY_RE.fullmatch(str(data["profile_key"])):
        raise TraceError("identity invalid profile_key")
    if not isinstance(data["layers"], list) or not 1 <= len(data["layers"]) <= MAX_LAYERS:
        raise TraceError("identity must enumerate 1..512 observed layers")
    by_id = {}
    for layer in data["layers"]:
        if type(layer) is not dict or set(layer) != {"trace_layer", "logical_layer_id", "compiled_layer_key", "pack_layer_key"}:
            raise TraceError("identity layer has unexpected fields")
        n = layer["trace_layer"]
        if type(n) is not int or not 0 <= n < MAX_LAYERS or n in by_id:
            raise TraceError("duplicate or invalid trace_layer")
        if type(layer["logical_layer_id"]) is not int or not 0 <= layer["logical_layer_id"] <= pack_layout.MAX_LAYER_ID:
            raise TraceError("invalid logical layer ID")
        if not pack_layout.COMPILED_LAYER_KEY_RE.fullmatch(str(layer["compiled_layer_key"])):
            raise TraceError("invalid compiled layer key")
        if not HEX16.fullmatch(str(layer["pack_layer_key"])):
            raise TraceError("invalid pack key")
        by_id[n] = layer
    return by_id


def derive(trace_bytes: bytes, identity: dict):
    if not isinstance(trace_bytes, bytes) or len(trace_bytes) > MAX_TRACE_BYTES:
        raise TraceError("trace exceeds 128 MiB bound")
    layers_expected = _identity(identity)
    try:
        text = trace_bytes.decode("utf-8")
    except UnicodeError as exc:
        raise TraceError("trace must be UTF-8") from exc
    if not text.endswith("\n"):
        raise TraceError("trace lacks complete final newline")
    lines = text.splitlines()
    if not lines or lines[0] != "# moe_otd_trace v1":
        raise TraceError("not a native moe_otd_trace v1")
    if len(lines) > MAX_EVENTS:
        raise TraceError("event count bound exceeded")
    found = {}
    calls = {}
    stats = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    pairs = defaultdict(Counter)
    seen_end = False
    call_count = 0
    expert_count = 0
    last_timestamp = {}
    for raw in lines[1:]:
        if len(raw) > MAX_LINE:
            raise TraceError("trace line exceeds 4096 characters")
        end = END_RE.fullmatch(raw)
        if end:
            if seen_end:
                raise TraceError("multiple trace end markers")
            seen_end = True
            expected = tuple(int(end.group(i)) for i in range(1, 5))
            if expected != (call_count, expert_count, 0, 0):
                raise TraceError("trace counters/incomplete calls mismatch")
            continue
        if seen_end:
            raise TraceError("data appears after trace end marker")
        if raw.startswith("# incomplete "):
            raise TraceError("native trace contains incomplete calls")
        if raw.startswith("#"):
            raise TraceError("unexpected trace comment")
        fields = raw.split(",")
        kind = fields[0]
        if kind == "L":
            if len(fields) != 7:
                raise TraceError("invalid layer declaration")
            layer = _number(fields[1], "layer", MAX_LAYERS - 1)
            if layer in found or layer not in layers_expected:
                raise TraceError("unmapped or repeated native trace layer")
            if not HEX16.fullmatch(fields[2]) or not HEX16.fullmatch(fields[3]):
                raise TraceError("invalid native trace hashes")
            capacity = _number(fields[4], "capacity", pack_layout.MAX_EXPERTS)
            num_expert = _number(fields[5], "num_expert", pack_layout.MAX_EXPERTS)
            top_k = _number(fields[6], "top_k", pack_layout.MAX_EXPERTS)
            if not 1 <= capacity <= num_expert or not 1 <= top_k <= num_expert:
                raise TraceError("invalid compiled layer capacity/expert count")
            found[layer] = {"count": num_expert, "capacity": capacity, "top_k": top_k}
        elif kind == "C":
            if len(fields) != 8:
                raise TraceError("invalid call event")
            cid = _number(fields[1], "call id")
            start = _number(fields[2], "call timestamp", (1 << 63) - 1)
            layer = _number(fields[3], "call layer", MAX_LAYERS - 1)
            if layer not in found or cid in calls or fields[4] not in ("S", "O") or fields[6] not in ("ok", "overflow"):
                raise TraceError("bad call identity, ordering or status")
            routed = _number(fields[5], "routed count", pack_layout.MAX_EXPERTS)
            unique = [] if not fields[7] else [_number(s, "expert", found[layer]["count"] - 1) for s in fields[7].split(" ")]
            if len(unique) != len(set(unique)) or len(unique) > routed or (fields[4] == "O" and (routed != 1 or len(unique) != 1)):
                raise TraceError("invalid routed expert list")
            if fields[6] == "overflow" and len(unique) <= found[layer]["capacity"]:
                raise TraceError("unexpected overflow call")
            calls[cid] = {"layer": layer, "experts": unique, "events": set(), "overflow": fields[6] == "overflow", "timestamp": start}
            # A rejected oversized call never ran its expert set. Counting
            # it as observed co-access would create artificial hot clusters.
            if fields[6] == "ok":
                for i, a in enumerate(unique):
                    for b in unique[i + 1:]:
                        pair = (min(a, b), max(a, b))
                        pairs[layer][pair] += 1
            call_count += 1
        elif kind == "E":
            if len(fields) != 13:
                raise TraceError("invalid expert event")
            cid = _number(fields[1], "expert call")
            stamp = _number(fields[2], "expert timestamp", (1 << 63) - 1)
            layer = _number(fields[3], "expert layer", MAX_LAYERS - 1)
            eid = _number(fields[4], "expert ID", pack_layout.MAX_EXPERTS - 1)
            if cid not in calls or calls[cid]["layer"] != layer or calls[cid]["overflow"] or eid not in calls[cid]["experts"] or eid in calls[cid]["events"]:
                raise TraceError("orphan, duplicate or forbidden expert event")
            if stamp < calls[cid]["timestamp"]:
                raise TraceError("expert timestamp precedes its call")
            _number(fields[5], "resident slot", found[layer]["capacity"] - 1)
            if fields[6] not in ("0", "1") or not (fields[7] == "-1" or fields[7].isascii() and fields[7].isdecimal()):
                raise TraceError("invalid hit/eviction")
            hit = fields[6] == "1"
            byte_count = _number(fields[8], "logical bytes")
            reads = _number(fields[9], "logical reads")
            read_ns = _number(fields[10], "read ns", (1 << 63) - 1)
            _number(fields[11], "transform ns", (1 << 63) - 1)
            _number(fields[12], "copy ns", (1 << 63) - 1)
            if hit and (byte_count or reads or read_ns):
                raise TraceError("cache hit reported I/O")
            calls[cid]["events"].add(eid)
            stat = stats[layer][eid]
            stat[0] += 1
            if not hit:
                stat[1] += 1
                stat[2] += read_ns
            expert_count += 1
        else:
            raise TraceError("unknown trace record")
    if not seen_end or set(found) != set(layers_expected):
        raise TraceError("trace incomplete or mapping contains absent layers")
    for call in calls.values():
        if not call["overflow"] and set(call["experts"]) != call["events"]:
            raise TraceError("call lacks native expert events")
        if call["overflow"] and call["events"]:
            raise TraceError("overflow call changed resident cache")
    output = []
    for layer, record in sorted(layers_expected.items()):
        observed = found[layer]
        expert_stats = stats[layer]
        experts = [
            {"logical_expert_id": eid, "miss_count": miss, "read_cost_us": round(read_ns / (miss * 1000), 6) if miss else 0.0}
            for eid, (accesses, miss, read_ns) in sorted(expert_stats.items())
        ]
        coaccess = [
            {"expert_a": a, "expert_b": b, "weight": count}
            for (a, b), count in sorted(pairs[layer].items()) if count
        ]
        if len(coaccess) > pack_layout.MAX_COACCESS_PAIRS:
            raise TraceError("coaccess exceeds optimizer bound")
        profile = {
            "schema": pack_layout.PROFILE_SCHEMA,
            "kind": pack_layout.PROFILE_KIND,
            "complete": True,
            "synthetic": False,
            "provenance": {
                "checkpoint_sha": identity["checkpoint_sha"],
                "export_sha": identity["export_sha"],
                "compiled_layer_key": record["compiled_layer_key"],
                "quant_profile_sha": identity["quant_profile_sha"],
                "profile_key": identity["profile_key"],
                "source": "offline_trace_derived",
                "sanitized": True,
            },
            "scope": {"model_key": identity["model_key"], "logical_layer_id": record["logical_layer_id"]},
            "expert_count": observed["count"], "experts": experts, "coaccess": coaccess,
        }
        pack_layout.validate_profile(profile)
        output.append({"trace_layer": layer, "pack_layer_key": record["pack_layer_key"], "profile": profile})
    return {"schema": "cib2.trace_profile_bundle.v1", "trace_sha256": hashlib.sha256(trace_bytes).hexdigest(),
            "source_identity_claim": "operator-supplied; not cryptographically authenticated",
            "runtime_acceptance": "NO", "pack_acceptance": "NO", "profiles": output}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.suffix != ".json" or args.output.resolve() in (args.trace.resolve(), args.identity.resolve()):
            raise TraceError("output must be a separate JSON file")
        if args.trace.stat().st_size > MAX_TRACE_BYTES or args.identity.stat().st_size > 1_000_000:
            raise TraceError("input too large")
        raw_identity = json.loads(args.identity.read_text(encoding="utf-8"),
                                  object_pairs_hook=pack_layout._unique_object)
        result = derive(args.trace.read_bytes(), raw_identity)
        args.output.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (TraceError, OSError, ValueError, OverflowError, pack_layout.ProfileError) as exc:
        print(json.dumps({"status": "REJECTED", "error": str(exc), "runtime_acceptance": "NO"}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
