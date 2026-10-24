"""CIB2 static Resident Pack prototype (offline only; never used to serve weights).

Consumes OpenVINO IR Const offsets. Does NOT infer lifetime residency from an
OTD E-trace or rewrite the model XML/compiled GPU graph. A reviewed allowlist
is required to copy bytes; routed weights are forbidden.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET

SCHEMA = "cib2.static_resident_inventory.v1"
PACK_SCHEMA = "cib2.static_resident_pack.v1"
SELECT_SCHEMA = "cib2.static_resident_selection.v1"
MAX_XML = 256 * 1024 * 1024
CHUNK = 1024 * 1024
ALIGN = 4096


class ResidentError(ValueError):
    pass


def _read_json(path: Path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 128 * 1024 * 1024:
        raise ResidentError(f"missing/unsafe/oversized JSON: {path}")
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ResidentError(f"duplicate JSON key: {k}")
            out[k] = v
        return out
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda v: (_ for _ in ()).throw(ResidentError(f"invalid numeric value {v}")))


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _regular(path: Path):
    if path.is_symlink() or not path.is_file():
        raise ResidentError(f"not a regular source file: {path}")


def _int(v, label: str) -> int:
    if not isinstance(v, str) or not v.isascii() or not v.isdecimal():
        raise ResidentError(f"invalid {label}: {v!r}")
    return int(v)


def inventory(xml: Path, binary: Path) -> dict:
    _regular(xml)
    _regular(binary)
    if xml.stat().st_size > MAX_XML:
        raise ResidentError("IR XML exceeds safety limit")
    # The IR graph is not the compiled GPU graph: 'unknown' remains unknown.
    root = ET.parse(xml).getroot()
    layers = {x.attrib["id"]: x for x in root.findall("./layers/layer")}
    if len(layers) != len(root.findall("./layers/layer")):
        raise ResidentError("duplicate layer identifiers")
    consumers: dict[str, list[tuple[str, int]]] = {}
    for edge in root.findall("./edges/edge"):
        to_id = edge.get("to-layer", "")
        consumers.setdefault(edge.get("from-layer", ""), []).append((
            layers[to_id].get("type", "") if to_id in layers else "", _int(edge.get("to-port"), "to-port")))
    records = []
    size = binary.stat().st_size
    for layer_id, layer in layers.items():
        if layer.get("type") != "Const":
            continue
        data = layer.find("data")
        if data is None:
            raise ResidentError(f"Const {layer_id} has no data")
        off = _int(data.get("offset"), "offset")
        length = _int(data.get("size"), "size")
        if not length or off > size or length > size - off:
            raise ResidentError(f"Const {layer_id}: source range exceeds BIN")
        uses = consumers.get(layer_id, [])
        routed = any("MOECompressed" in t and 3 <= p <= 11 for t, p in uses)
        shared = any("MOECompressed" in t and 12 <= p <= 21 for t, p in uses)
        role = "routed" if routed else "shared" if shared else "unknown"
        records.append({"layer_id": _int(layer_id, "layer id"), "name": layer.get("name", ""),
                        "offset": off, "size": length, "element_type": data.get("element_type", ""),
                        "role": role})
    records.sort(key=lambda x: x["layer_id"])
    if len({x["layer_id"] for x in records}) != len(records):
        raise ResidentError("duplicate Const identifiers")
    return {"schema": SCHEMA, "runtime_acceptance": "NO", "source_xml_sha256": _sha(xml),
            "source_bin_sha256": _sha(binary), "source_bin_bytes": size,
            "role_scope": "IR direct consumers only; compiled GPU layout unverified", "constants": records}


def _align(f):
    pad = (-f.tell()) % ALIGN
    if pad:
        f.write(b"\x00" * pad)


def _copy_range(src, dst, offset: int, length: int) -> str:
    src.seek(offset)
    h = hashlib.sha256()
    remain = length
    while remain:
        data = src.read(min(remain, CHUNK))
        if not data:
            raise ResidentError("source BIN changed during read")
        dst.write(data)
        h.update(data)
        remain -= len(data)
    return h.hexdigest()


def build(inventory_path: Path, selection_path: Path, binary: Path, output_dir: Path) -> dict:
    inv, selections = _read_json(inventory_path), _read_json(selection_path)
    _regular(binary)
    if inv.get("schema") != SCHEMA or inv.get("runtime_acceptance") != "NO":
        raise ResidentError("wrong inventory schema")
    if selections.get("schema") != SELECT_SCHEMA or not isinstance(selections.get("selections"), list):
        raise ResidentError("wrong selection schema")
    if not selections["selections"]:
        raise ResidentError("empty reviewed selection")
    for key in ("source_xml_sha256", "source_bin_sha256"):
        if selections.get(key) != inv.get(key):
            raise ResidentError(f"selection provenance mismatch: {key}")
    if binary.stat().st_size != inv["source_bin_bytes"] or _sha(binary) != inv["source_bin_sha256"]:
        raise ResidentError("BIN changed since inventory")
    consts = {x["layer_id"]: x for x in inv["constants"]}
    chosen = []
    seen = set()
    for sel in selections["selections"]:
        if type(sel) is not dict or set(sel) != {"layer_id", "evidence"}:
            raise ResidentError("selection requires exact layer_id and evidence")
        idx, ev = sel["layer_id"], sel["evidence"]
        if type(idx) is not int or idx in seen or idx not in consts:
            raise ResidentError("unknown/duplicate layer_id")
        if type(ev) is not str or not 12 <= len(ev) <= 512:
            raise ResidentError("per-constant reviewed evidence is required")
        record = consts[idx]
        if record["role"] == "routed":
            raise ResidentError(f"refusing to pack routed expert Const {idx}")
        chosen.append((record, ev))
        seen.add(idx)
    # New immutable generation directory. Never overwrite published packs.
    if output_dir.exists() or not output_dir.parent.is_dir():
        raise ResidentError("output generation exists or parent is missing")
    tmp = Path(tempfile.mkdtemp(prefix=".resident-staging-", dir=output_dir.parent))
    try:
        entries = []
        with binary.open("rb") as src, (tmp / "resident.pack").open("wb") as dst:
            for rec, evidence in sorted(chosen, key=lambda x: x[0]["layer_id"]):
                _align(dst)
                pack_offset = dst.tell()
                digest = _copy_range(src, dst, rec["offset"], rec["size"])
                entries.append({"layer_id": rec["layer_id"], "name": rec["name"], "role": rec["role"],
                                "source_offset": rec["offset"], "pack_offset": pack_offset,
                                "size": rec["size"], "sha256": digest, "evidence": evidence})
            dst.flush()
            os.fsync(dst.fileno())
        if _sha(binary) != inv["source_bin_sha256"]:
            raise ResidentError("source BIN modified while building")
        manifest = {"schema": PACK_SCHEMA, "runtime_acceptance": "NO", "consumption": "OFFLINE_ONLY",
                    "source_xml_sha256": inv["source_xml_sha256"], "source_bin_sha256": inv["source_bin_sha256"],
                    "pack_sha256": _sha(tmp / "resident.pack"), "pack_bytes": (tmp / "resident.pack").stat().st_size,
                    "records": entries}
        with (tmp / "manifest.json").open("wb") as dst:
            dst.write(_canonical(manifest))
            dst.flush()
            os.fsync(dst.fileno())
        os.rename(tmp, output_dir)
        return manifest
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)


def verify(pack_dir: Path, binary: Path | None = None) -> dict:
    manifest_path = pack_dir / "manifest.json"
    pack_path = pack_dir / "resident.pack"
    _regular(pack_path)
    man = _read_json(manifest_path)
    if man.get("schema") != PACK_SCHEMA or man.get("runtime_acceptance") != "NO" or man.get("consumption") != "OFFLINE_ONLY":
        raise ResidentError("wrong resident pack manifest")
    pack_size = pack_path.stat().st_size
    if pack_size != man["pack_bytes"] or _sha(pack_path) != man["pack_sha256"]:
        raise ResidentError("pack digest/size mismatch")
    seen = set()
    with pack_path.open("rb") as pf:
        for rec in man["records"]:
            idx, off, size = rec["layer_id"], rec["pack_offset"], rec["size"]
            if idx in seen or type(off) is not int or type(size) is not int or off < 0 or size <= 0 or off % ALIGN or off + size > pack_size:
                raise ResidentError("invalid/duplicate record range")
            seen.add(idx)
            pf.seek(off)
            remaining = size
            h = hashlib.sha256()
            while remaining:
                chunk = pf.read(min(remaining, CHUNK))
                if not chunk:
                    raise ResidentError("pack truncated")
                h.update(chunk)
                remaining -= len(chunk)
            if h.hexdigest() != rec["sha256"]:
                raise ResidentError(f"record checksum mismatch: {idx}")
    if binary is not None:
        _regular(binary)
        if _sha(binary) != man["source_bin_sha256"]:
            raise ResidentError("source BIN digest mismatch")
    return {"validation_status": "OK", "record_count": len(seen), "runtime_acceptance": "NO"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest="command", required=True)
    x = subs.add_parser("inventory")
    x.add_argument("--xml", type=Path, required=True)
    x.add_argument("--bin", type=Path, required=True)
    x.add_argument("--out", type=Path, required=True)
    x = subs.add_parser("build")
    x.add_argument("--inventory", type=Path, required=True)
    x.add_argument("--selection", type=Path, required=True)
    x.add_argument("--bin", type=Path, required=True)
    x.add_argument("--out-dir", type=Path, required=True)
    x = subs.add_parser("verify")
    x.add_argument("--pack-dir", type=Path, required=True)
    x.add_argument("--bin", type=Path)
    a = p.parse_args()
    try:
        if a.command == "inventory":
            report = inventory(a.xml, a.bin)
            if a.out.exists():
                raise ResidentError("inventory output exists")
            a.out.write_bytes(_canonical(report))
        elif a.command == "build":
            report = build(a.inventory, a.selection, a.bin, a.out_dir)
        else:
            report = verify(a.pack_dir, a.bin)
        print(json.dumps({k: v for k, v in report.items() if k != "constants" and k != "records"}, indent=2))
    except (OSError, ValueError, ET.ParseError, KeyError, TypeError) as exc:
        p.exit(2, f"Resident Pack rejected: {exc}\n")


if __name__ == "__main__":
    main()
