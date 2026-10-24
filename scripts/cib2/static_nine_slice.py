# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Static co-occurrence of nine routed expert storage names.

This reader never opens a weights BIN, never loads a model, and never
promotes a static XML name to a compiled expert kind.
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


PROJECTIONS = ("gate", "up", "down")
KINDS = ("weight", "scale", "zp")
NINE_SLOTS = tuple("%s/%s" % (proj, kind) for proj in PROJECTIONS for kind in KINDS)
_BLOCK_RE = re.compile(r"layers\.(\d+)\.")
_PROJ_TOKEN = {"gate": "gate_proj", "up": "up_proj", "down": "down_proj"}
# Match a complete routed projection segment; substring matching would accept
# misleading names such as "other_down_proj/scale".
_ROUTED_CONST_RE = re.compile(
    r"\.mlp\.experts\.(gate_proj|up_proj|down_proj)(?:/(scale|zero_point))?$"
)


def classify_routed_const(name: str) -> Optional[str]:
    """Return a nine-slot key, or None when the Const is not one of those slots."""
    if "shared_expert" in name:
        return None
    match = _ROUTED_CONST_RE.search(name)
    if match is None:
        return None
    token, marker = match.groups()
    projection = token.removesuffix("_proj")
    kind = {"scale": "scale", "zero_point": "zp", None: "weight"}[marker]
    return "%s/%s" % (projection, kind)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _int_attr(attrs: Dict[str, str], key: str) -> Optional[int]:
    raw = attrs.get(key)
    if raw is None or not re.fullmatch(r"[0-9]+", raw):
        return None
    return int(raw)


def analyze_root(root: ET.Element, graph_name: str) -> Dict[str, Any]:
    records: List[Dict[str, Any]] = []
    ordinal = 0
    for layer in root.iter():
        if _local(layer.tag) != "layer":
            continue
        layer_ordinal = ordinal
        ordinal += 1
        if layer.get("type") != "Const":
            continue
        name = layer.get("name") or ""
        slot = classify_routed_const(name)
        if slot is None:
            continue
        data_attrs: Dict[str, str] = {}
        for child in list(layer):
            if _local(child.tag) == "data":
                data_attrs = dict(child.attrib)
                break
        block_match = _BLOCK_RE.search(name)
        records.append(
            {
                "graph": graph_name,
                "ordinal": layer_ordinal,
                "layer_id": layer.get("id"),
                "name": name,
                "slot": slot,
                "block": int(block_match.group(1)) if block_match else None,
                "offset": _int_attr(data_attrs, "offset"),
                "size": _int_attr(data_attrs, "size"),
            }
        )
    by_block: Dict[int, set] = {}
    slot_counts = {slot: 0 for slot in NINE_SLOTS}
    for rec in records:
        slot_counts[rec["slot"]] += 1
        if rec["block"] is not None:
            by_block.setdefault(rec["block"], set()).add(rec["slot"])
    complete = sorted(block for block, slots in by_block.items() if len(slots) == 9)
    return {
        "schema": "cib2.static-nine-slice.v1",
        "graph": graph_name,
        "compiled_kind": "UNKNOWN",
        "runtime_acceptance": "NO",
        "bin_opened": False,
        "layer_count": ordinal,
        "matched_const_count": len(records),
        "slot_counts": slot_counts,
        "block_count": len(by_block),
        "blocks_with_all_nine": len(complete),
        "complete_blocks": complete,
        "records": records,
    }


def analyze_xml(path: Path, graph_name: Optional[str] = None) -> Dict[str, Any]:
    source = Path(path)
    root = ET.parse(source).getroot()
    return analyze_root(root, graph_name or source.name)


def _block_zero(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = [rec for rec in report["records"] if rec["block"] == 0]
    return [
        {
            "slot": rec["slot"],
            "ordinal": rec["ordinal"],
            "layer_id": rec["layer_id"],
            "offset": rec["offset"],
            "size": rec["size"],
        }
        for rec in rows
    ]


def render_markdown(report: Dict[str, Any], source: str) -> str:
    lines = [
        "# Static nine-slice co-occurrence",
        "",
        "Compiled expert kind: **UNKNOWN**. Runtime acceptance: **NO**.",
        "Weights BIN was not opened. Name co-occurrence is not compiled eligibility.",
        "",
        "- Graph: `%s`" % report["graph"],
        "- Source: `%s`" % source,
        "- Layers seen: %d" % report["layer_count"],
        "- Matched routed Const slots: %d" % report["matched_const_count"],
        "- Blocks with a routed slot: %d" % report["block_count"],
        "- Blocks with all nine slots: %d" % report["blocks_with_all_nine"],
        "",
        "| Slot | Count |",
        "| --- | ---: |",
    ]
    for slot in NINE_SLOTS:
        lines.append("| `%s` | %d |" % (slot, report["slot_counts"][slot]))
    lines.extend(["", "## Block 0", "", "| Slot | Ordinal | Layer id | Offset | Size |", "| --- | ---: | --- | ---: | ---: |"])
    block0 = _block_zero(report)
    if not block0:
        lines.append("| none |  |  |  |  |")
    for rec in block0:
        lines.append(
            "| `%s` | %s | %s | %s | %s |"
            % (rec["slot"], rec["ordinal"], rec["layer_id"], rec["offset"], rec["size"])
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Static nine-slot routed Const co-occurrence")
    parser.add_argument("--xml", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    xml_path = args.xml.resolve()
    output = args.output.resolve()
    if output.suffix.lower() != ".json":
        raise SystemExit("output must be a .json file")
    if output == xml_path or xml_path.parent in output.parents:
        raise SystemExit("refusing to write the report inside the XML directory")
    # Validate *all* destinations before any write. In particular, arbitrary
    # --markdown paths must never overwrite a different model's .bin weights
    # or the JSON report. Only .md is an accepted Markdown destination.
    md = args.markdown.resolve() if args.markdown is not None else None
    if md is not None:
        if md.suffix.lower() != ".md":
            raise SystemExit("markdown output must be a .md file")
        if md == output:
            raise SystemExit("markdown output must differ from JSON output")
        if xml_path.parent in md.parents:
            raise SystemExit("refusing to write markdown inside the XML directory")
    report = analyze_xml(xml_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if md is not None:
        md.parent.mkdir(parents=True, exist_ok=True)
        # Do not leak operator-local absolute paths to versioned Markdown.
        md.write_text(render_markdown(report, xml_path.name), encoding="utf-8")
    summary = {
        "graph": report["graph"],
        "compiled_kind": report["compiled_kind"],
        "blocks_with_all_nine": report["blocks_with_all_nine"],
        "slot_counts": report["slot_counts"],
        "runtime_acceptance": "NO",
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
