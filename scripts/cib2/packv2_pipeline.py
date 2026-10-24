# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Native placement plan + immutable Pack V2 generation envelope for CIB2.

V2 controls provenance, verified generations and publication. Data records in
this initial V2 envelope remain native OTDPACK1 (9 slices per expert); no new
GPU record ABI or hot/cold sharding is implied. Only the native GPU plugin can
build the canonical payload from compiled PackLayerSpec.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile

try:
    from . import pack_layout, verify_pack_v1
except ImportError:
    import pack_layout
    import verify_pack_v1

BUNDLE_SCHEMA = "cib2.trace_profile_bundle.v1"
PLANS_SCHEMA = "cib2.pack_placement_plans.v2"
MANIFEST_SCHEMA = "cib2.pack_generation.v2"
ACTIVE_SCHEMA = "cib2.active_pack_generation.v2"
MAX_PACKS = 512
MAX_PLAN_BYTES = 16 * 1024 * 1024
READ_BYTES = 1024 * 1024
MAGIC = b"OTDPLACE"
RESIDENT_MAGIC = b"OTDRESID"
HEADER = struct.Struct("<8sIIQ")
CHECKSUM = struct.Struct("<Q")


class GenerationError(ValueError):
    pass


def _canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _read_json(path, limit=MAX_PLAN_BYTES):
    if path.is_symlink() or not path.is_file():
        raise GenerationError("unsafe or missing JSON input")
    if path.stat().st_size > limit:
        raise GenerationError("JSON input exceeds limit")
    def pairs_unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise GenerationError("duplicate JSON key: " + k)
            d[k] = v
        return d
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs_unique,
                      parse_constant=lambda s: (_ for _ in ()).throw(GenerationError("nonfinite JSON")))


def _sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while part := stream.read(READ_BYTES):
            h.update(part)
    return h.hexdigest()


def _native_placement(key, placement):
    if type(key) is not str or len(key) != 16 or any(c not in "0123456789abcdef" for c in key):
        raise GenerationError("invalid 16-hex native layer key")
    if type(placement) is not list or not 1 <= len(placement) <= pack_layout.MAX_EXPERTS or (
        any(type(x) is not int for x in placement) or sorted(placement) != list(range(len(placement)))
    ):
        raise GenerationError("native placement must be an exact permutation")
    header = HEADER.pack(MAGIC, 2, len(placement), int(key, 16))
    data = header + struct.pack("<" + "I" * len(placement), *placement)
    hash_value = verify_pack_v1.fnv_update(verify_pack_v1.FNV_OFFSET, data)
    return data + CHECKSUM.pack(hash_value)


def _resident_tiers(profile):
    # Offline proposal: protect a bounded top quartile by observed miss stall.
    # This is soft per-layer prioritization, NOT actual UMA admission or an
    # independent proof of saved latency. Native runtime further caps hot
    # candidates to (available resident slots - 1) for demand progress.
    n = profile.expert_count
    proposals = []
    for e in profile.experts:
        if e.score > 0:
            proposals.append((e.score, e.logical_expert_id))
    proposals.sort(key=lambda item: (-item[0], item[1]))
    result = [0] * n
    for _, expert in proposals:
        result[expert] = 1
    for _, expert in proposals[:min(len(proposals), max(1, n // 4))]:
        result[expert] = 2
    return result


def _native_residency(key, tiers):
    if type(key) is not str or len(key) != 16 or any(c not in "0123456789abcdef" for c in key):
        raise GenerationError("invalid 16-hex native resident policy key")
    if type(tiers) is not list or not 1 <= len(tiers) <= pack_layout.MAX_EXPERTS or any(type(x) is not int or x not in (0, 1, 2) for x in tiers):
        raise GenerationError("invalid priority tiers")
    raw = HEADER.pack(RESIDENT_MAGIC, 2, len(tiers), int(key, 16)) + bytes(tiers)
    return raw + CHECKSUM.pack(verify_pack_v1.fnv_update(verify_pack_v1.FNV_OFFSET, raw))


def _atomic_json(path, obj):
    data = _canonical(obj)
    with tempfile.NamedTemporaryFile(mode="wb", prefix=path.name + ".", suffix=".tmp",
                                     dir=path.parent, delete=False) as stream:
        name = Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            name.unlink(missing_ok=True)
            raise
    try:
        os.replace(name, path)
    except BaseException:
        name.unlink(missing_ok=True)
        raise


def make_plans(bundle_path: Path, target_dir: Path, strategy: str, seed=0):
    bundle = _read_json(bundle_path)
    if type(bundle) is not dict or set(bundle) != {
        "schema", "trace_sha256", "source_identity_claim", "runtime_acceptance", "pack_acceptance", "profiles"
    } or bundle["schema"] != BUNDLE_SCHEMA or bundle["runtime_acceptance"] != "NO":
        raise GenerationError("not a valid offline trace profile bundle")
    entries = bundle["profiles"]
    if type(entries) is not list or not 1 <= len(entries) <= MAX_PACKS or (
        not pack_layout.SHA256_RE.fullmatch(str(bundle["trace_sha256"]))
    ):
        raise GenerationError("invalid layer count or trace digest")
    if target_dir.exists() or not target_dir.parent.is_dir():
        raise GenerationError("placement destination must be a new directory under an existing parent")
    plans = []
    outputs = {}
    seen_keys = set()
    identity_tuple = None
    for e in entries:
        if type(e) is not dict or set(e) != {"trace_layer", "pack_layer_key", "profile"}:
            raise GenerationError("invalid bundle layer")
        key = e["pack_layer_key"]
        if type(key) is not str or len(key) != 16 or any(c not in "0123456789abcdef" for c in key):
            raise GenerationError("pack layer key must be 16 lowercase hex digits")
        if key in seen_keys:
            raise GenerationError("duplicate pack layer key")
        seen_keys.add(key)
        raw = _canonical(e["profile"])
        profile = pack_layout.load_profile_bytes(raw)
        # Only complete, trace-derived evidence may select real native
        # placement/priority files. Synthetic fixtures remain useful to
        # test the pure PGP-02 optimizer, not to configure GPU residency.
        if profile.synthetic or profile.provenance["source"] != "offline_trace_derived":
            raise GenerationError("synthetic/non-trace profile cannot drive native pack build")
        ident = (profile.provenance["checkpoint_sha"], profile.provenance["export_sha"],
                 profile.provenance["quant_profile_sha"], profile.scope["model_key"])
        if identity_tuple is None:
            identity_tuple = ident
        if ident != identity_tuple:
            raise GenerationError("mixed checkpoint/export/quant/model profiles")
        source_sha = hashlib.sha256(raw).hexdigest()
        layout = pack_layout.build_layout(profile, strategy, seed, source_sha256=source_sha)
        pack_layout.validate_layout(layout)
        placement = layout["placement"]
        filename = "otd-" + key + ".placement"
        binary = _native_placement(key, placement)
        tiers = _resident_tiers(profile)
        resident_name = "otd-" + key + ".residency"
        resident_binary = _native_residency(key, tiers)
        outputs[filename] = binary
        outputs[resident_name] = resident_binary
        plans.append({"pack_layer_key": key, "native_plan": filename,
                      "native_residency": resident_name,
                      "native_residency_sha256": hashlib.sha256(resident_binary).hexdigest(),
                      "resident_tiers": tiers,
                      "native_plan_sha256": hashlib.sha256(binary).hexdigest(),
                      "profile_sha256": source_sha, "expert_count": len(placement),
                      "placement": placement, "strategy_effective": layout["strategy_effective"],
                      "logical_layer_id": profile.scope["logical_layer_id"],
                      "compiled_layer_key": profile.provenance["compiled_layer_key"]})
    obj = {"schema": PLANS_SCHEMA, "status": "OFFLINE_PLAN",
           "runtime_acceptance": "NO", "pack_acceptance": "NO",
           "source": dict(zip(("checkpoint_sha", "export_sha", "quant_profile_sha", "model_key"), identity_tuple)),
           "trace_sha256": bundle["trace_sha256"], "strategy": strategy, "seed": seed,
           "layers": sorted(plans, key=lambda e: e["pack_layer_key"])}
    temporary = Path(tempfile.mkdtemp(prefix=".placements-", dir=target_dir.parent))
    try:
        for name, data in outputs.items():
            with (temporary / name).open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        _atomic_json(temporary / "plans.v2.json", obj)
        os.rename(temporary, target_dir)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return obj


def _read_plans(plan_dir: Path):
    plan = _read_json(plan_dir / "plans.v2.json")
    if type(plan) is not dict or set(plan) != {
        "schema", "status", "runtime_acceptance", "pack_acceptance", "source", "trace_sha256",
        "strategy", "seed", "layers"
    } or plan.get("schema") != PLANS_SCHEMA or plan.get("runtime_acceptance") != "NO" or plan.get("pack_acceptance") != "NO":
        raise GenerationError("invalid placement plan contract")
    entries = plan.get("layers")
    if type(entries) is not list or not 1 <= len(entries) <= MAX_PACKS:
        raise GenerationError("invalid placement layer count")
    seen = set()
    for e in entries:
        if type(e) is not dict or set(e) != {"pack_layer_key", "native_plan", "native_plan_sha256",
            "profile_sha256", "expert_count", "placement", "strategy_effective", "logical_layer_id", "compiled_layer_key",
            "native_residency", "native_residency_sha256", "resident_tiers"}:
            raise GenerationError("unexpected placement metadata")
        key, name = e["pack_layer_key"], e["native_plan"]
        if type(key) is not str or len(key) != 16 or any(c not in "0123456789abcdef" for c in key):
            raise GenerationError("invalid layer key")
        if name != "otd-" + key + ".placement" or key in seen:
            raise GenerationError("duplicate or foreign native plan")
        seen.add(key)
        binary = _native_placement(key, e["placement"])
        if not (plan_dir / name).is_file() or (plan_dir / name).is_symlink():
            raise GenerationError("missing or unsafe native placement")
        if (plan_dir / name).read_bytes() != binary or hashlib.sha256(binary).hexdigest() != e["native_plan_sha256"]:
            raise GenerationError("native placement was altered")
        name_resident = e["native_residency"]
        if name_resident != "otd-" + key + ".residency":
            raise GenerationError("foreign resident policy")
        resident_binary = _native_residency(key, e["resident_tiers"])
        if not (plan_dir / name_resident).is_file() or (plan_dir / name_resident).is_symlink():
            raise GenerationError("missing/unsafe resident policy")
        if (plan_dir / name_resident).read_bytes() != resident_binary or hashlib.sha256(resident_binary).hexdigest() != e["native_residency_sha256"]:
            raise GenerationError("resident policy was altered")
        if type(e["expert_count"]) is not int or e["expert_count"] != len(e["placement"]) or len(e["resident_tiers"]) != e["expert_count"]:
            raise GenerationError("expert count mismatch")
        if sorted(e["placement"]) != list(range(e["expert_count"])):
            raise GenerationError("invalid placement permutation")
    return plan


def _verify_one_pack(path, entry):
    if not path.is_file() or path.is_symlink():
        raise GenerationError("missing/unsafe pack file")
    details = verify_pack_v1.inspect_pack(path, expect_key=int(entry["pack_layer_key"], 16),
                                           expect_experts=entry["expert_count"])
    if details["status"] != "OK" or details["corrupt_count"]:
        raise GenerationError("pack payload corruption detected")
    # The native verifier validates permutation integrity but does not expose it;
    # explicitly compare to the exact pinned operator placement plan.
    with path.open("rb") as stream:
        stream.seek(verify_pack_v1.ALIGNMENT)
        raw = stream.read(entry["expert_count"] * 4)
    positions = list(struct.unpack("<" + "I" * entry["expert_count"], raw))
    if positions != entry["placement"]:
        raise GenerationError("pack placement differs from compiled build plan")
    return details


def seal_generation(plans_dir: Path, native_packs: Path, output_root: Path):
    plan = _read_plans(plans_dir)
    if not output_root.is_dir() or not native_packs.is_dir() or output_root.is_symlink() or native_packs.is_symlink():
        raise GenerationError("generation output root and native pack source must be real directories")
    if native_packs.resolve() == output_root.resolve():
        raise GenerationError("native input packs must be outside generation root")
    entries = []
    for e in plan["layers"]:
        name = "otd-" + e["pack_layer_key"] + ".pack"
        path = native_packs / name
        details = _verify_one_pack(path, e)
        entries.append({"file": name, "pack_layer_key": e["pack_layer_key"],
                        "pack_sha256": _sha256_file(path), "pack_bytes": path.stat().st_size,
                        "expert_count": e["expert_count"], "profile_sha256": e["profile_sha256"],
                        "native_plan_sha256": e["native_plan_sha256"],
                        "native_residency_sha256": e["native_residency_sha256"],
                        "resident_tiers": e["resident_tiers"],
                        "placement": e["placement"], "native_payload_format": "OTDPACK1",
                        "record_stride": details["record_stride"]})
    inner = {"schema": MANIFEST_SCHEMA, "pack_format": "OTDPACK1",
             "v2_features": ["immutable_generation", "profile_placement", "full_pack_digest"],
             "runtime_acceptance": "NO", "source": plan["source"],
             "trace_sha256": plan["trace_sha256"], "plan_sha256": hashlib.sha256(_canonical(plan)).hexdigest(),
             "packs": sorted(entries, key=lambda e: e["pack_layer_key"])}
    digest = hashlib.sha256(_canonical(inner)).hexdigest()
    generation = "generation-" + digest
    manifest = {**inner, "generation_sha256": digest}
    target = output_root / generation
    if target.exists():
        verify_generation(target)
        if _read_json(target / "manifest.v2.json") != manifest:
            raise GenerationError("existing generation has different manifest")
    else:
        temporary = Path(tempfile.mkdtemp(prefix=".generation-", dir=output_root))
        try:
            for entry in entries:
                source_path = native_packs / entry["file"]
                with source_path.open("rb") as src, (temporary / entry["file"]).open("xb") as dst:
                    shutil.copyfileobj(src, dst, READ_BYTES)
                    dst.flush()
                    os.fsync(dst.fileno())
                if _sha256_file(temporary / entry["file"]) != entry["pack_sha256"]:
                    raise GenerationError("source pack changed while sealing")
                _verify_one_pack(temporary / entry["file"], next(e for e in plan["layers"] if e["pack_layer_key"] == entry["pack_layer_key"]))
            _atomic_json(temporary / "manifest.v2.json", manifest)
            verify_generation(temporary)
            os.rename(temporary, target)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    pointer = {"schema": ACTIVE_SCHEMA, "generation": generation, "generation_sha256": digest,
               "pack_format": "OTDPACK1", "runtime_acceptance": "NO"}
    _atomic_json(output_root / "active.v2.json", pointer)
    return target


def verify_generation(generation_dir: Path):
    if generation_dir.is_symlink() or not generation_dir.is_dir():
        raise GenerationError("generation directory missing or symlinked")
    manifest = _read_json(generation_dir / "manifest.v2.json")
    if type(manifest) is not dict or set(manifest) != {
        "schema", "pack_format", "v2_features", "runtime_acceptance",
        "source", "trace_sha256", "plan_sha256", "packs", "generation_sha256"
    } or manifest.get("schema") != MANIFEST_SCHEMA or manifest.get("pack_format") != "OTDPACK1":
        raise GenerationError("wrong V2 manifest schema/format")
    identity = dict(manifest)
    generation_sha = identity.pop("generation_sha256", None)
    digest = hashlib.sha256(_canonical(identity)).hexdigest()
    if generation_sha != digest:
        raise GenerationError("V2 manifest generation checksum mismatch")
    if generation_dir.name not in ("generation-" + digest,) and not generation_dir.name.startswith(".generation-"):
        raise GenerationError("V2 directory name mismatch")
    entries = manifest.get("packs")
    if type(entries) is not list or not 1 <= len(entries) <= MAX_PACKS:
        raise GenerationError("invalid manifest pack list")
    expected_files = {"manifest.v2.json"}
    seen = set()
    for e in entries:
        if type(e) is not dict or set(e) != {
            "file", "pack_layer_key", "pack_sha256", "pack_bytes",
            "expert_count", "profile_sha256", "native_plan_sha256",
            "native_residency_sha256", "resident_tiers", "placement",
            "native_payload_format", "record_stride"
        }:
            raise GenerationError("invalid V2 manifest pack entry")
        key, name = e["pack_layer_key"], e["file"]
        if type(key) is not str or len(key) != 16 or any(c not in "0123456789abcdef" for c in key):
            raise GenerationError("invalid native pack identity")
        if name != "otd-" + key + ".pack" or name in seen:
            raise GenerationError("unexpected or repeated pack path")
        seen.add(name)
        expected_files.add(name)
        file = generation_dir / name
        if not file.is_file() or file.is_symlink():
            raise GenerationError("missing/unsafe generated pack")
        if _sha256_file(file) != e["pack_sha256"] or file.stat().st_size != e["pack_bytes"]:
            raise GenerationError("V2 full-file SHA256 mismatch")
        _verify_one_pack(file, e)
    actual_files = {p.name for p in generation_dir.iterdir()}
    if actual_files != expected_files:
        raise GenerationError("unexpected files in sealed generation")
    return {"status": "VERIFIED_OFFLINE", "generation": generation_sha,
            "pack_count": len(entries), "native_payload_format": "OTDPACK1",
            "runtime_acceptance": "NO", "promotion_authorized": False,
            "pack_dir": str(generation_dir.resolve())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plans = sub.add_parser("plans")
    plans.add_argument("--bundle", required=True, type=Path)
    plans.add_argument("--output-dir", required=True, type=Path)
    plans.add_argument("--strategy", choices=pack_layout.STRATEGIES, required=True)
    plans.add_argument("--seed", type=int, default=0)
    seal = sub.add_parser("seal")
    seal.add_argument("--plans-dir", required=True, type=Path)
    seal.add_argument("--native-packs", required=True, type=Path)
    seal.add_argument("--output-root", required=True, type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("--generation-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "plans":
            result = make_plans(args.bundle, args.output_dir, args.strategy, args.seed)
            result = {"status": result["status"], "plan_dir": str(args.output_dir),
                      "layers": len(result["layers"]), "runtime_acceptance": "NO"}
        elif args.command == "seal":
            target = seal_generation(args.plans_dir, args.native_packs, args.output_root)
            result = verify_generation(target)
        else:
            result = verify_generation(args.generation_dir)
        print(json.dumps(result, sort_keys=True))
    except (GenerationError, pack_layout.ProfileError, pack_layout.LayoutError,
            verify_pack_v1.PackError, OSError, ValueError, OverflowError) as exc:
        print(json.dumps({"status": "REJECTED", "error": str(exc),
                          "runtime_acceptance": "NO", "promotion_authorized": False}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
