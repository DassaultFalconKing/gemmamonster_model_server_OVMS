#!/usr/bin/env python3
"""MAP-02: static family/layer memory inventory mapper (read-only).

CIB2 MAP-01/02 support for CIB2-02/07. Scans a model directory, never reads BIN
contents or imports OpenVINO, and emits a versioned JSON inventory:

- OpenVINO GenAI-style JSON model configs (config.json, openvino_config.json,
  generation/processor configs): architectures, model_type, nested
  text_config/vision_config. Legacy XML configs remain supported as input.
- IR graph layer IDs/node ids taken verbatim from graph XML (never invented),
  plus transformer_block_index parsed from names such as ".layers.7.".
- Per-layer / per-graph tensor roles with conservative name/shape evidence;
  packed aggregate expert tensors (e.g. "...mlp.experts.down_proj") are marked
  routed_expert without inventing per-expert IDs; dense "mlp.gate_proj" is NOT
  a router (only "router"-named or MoE "mlp.gate.weight" tensors are).
- Const metadata from actual IR <data element_type/shape/offset/size> children
  and <port><dim> children; comma- or space-separated shapes; zero-sized
  tensors (shape "[0]", size="0") are valid EMPTY tensors, not malformed IR.
- Byte accounting per BIN keyed by model-relative file identity (subdirectory
  files do not collapse) with alias/overlap dedup via interval union.
- Explicit missing/partial statuses instead of fabricating models.

This is a STATIC file inventory only. It is NOT compiled-OTD eligibility, NOT
hotness/router-trace evidence, NOT a runtime memory peak, and it implies no
fixed hot/cold policy and no offload capability beyond offline inspection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

SCHEMA = "cib2.family_map/2"
HASH_LIMIT_XML_BYTES = 64 * 1024 * 1024  # hash XML/config files within this size
JSON_PARSE_LIMIT_BYTES = 1 * 1024 * 1024  # parse small JSON configs only

NOT_STATEMENTS = [
    "Static graph inventory is NOT compiled-OTD kernel eligibility.",
    "Static graph inventory is NOT weight-hotness or router-trace evidence.",
    "Static graph inventory is NOT a runtime memory peak or resident-set measure.",
    "No fixed hot/cold policy is derived from this report.",
    "Read-only file stat/hash only; BIN contents are never opened or hashed.",
    "Packed expert aggregates are whole-tensor evidence; no per-expert IDs are invented.",
]

VIS_RE = re.compile(r"(vision|vit[._/]|patch_embed|visual[._/])", re.I)
ROUTER_RE = re.compile(r"(router|(^|[./])mlp\.gate\.weight)")
SHARED_RE = re.compile(r"shared[._/]?expert")
EXPERT_INDEXED_RE = re.compile(r"experts?[._/](\d+)")
EXPERT_AGG_RE = re.compile(r"\.experts\.([A-Za-z_][A-zA-Z0-9_]*(?:\.[A-Za-z0-9_]+)*)")
PROJ_SUFFIX_RE = re.compile(r"(ov_)?(gate|up|down)_proj|\bproj\b|weight(_openvino_orig)?")
ATTN_RE = re.compile(
    r"(attention|attn[._]|present|past_key|\.key[._/]|\.value[._/]|"
    r"k_proj|v_proj|q_proj|kv_cache|kvchanrec|recurrent|state|lstm|gru|conv1d)"
)
ABS_EMB_RE = re.compile(r"(embed|tok_emb|word_emb)")
OUT_RE = re.compile(r"(lm_head|logits|cls_|\.cls\b|output_head)")
UNINDEXED_EXPERT_HINT = re.compile(r"expert", re.I)
SLIDING_HINT = re.compile(r"sliding", re.I)
FULL_ATTN_HINT = re.compile(r"(query|q_proj|\.attention[._/]|attn[._/]|full_attention)", re.I)
LINEAR_ATTN_HINT = re.compile(r"linear_attn|linear_attention|in_proj|conv1d_state|recurrent", re.I)
MOE_OP_HINT = re.compile(r"(moe|moeCompressed)", re.I)
BLOCK_RE = re.compile(r"\.layers\.(\d+)\.?|\bblocks\.(\d+)\.?")
ATTN_STATE_HINT = re.compile(r"(recurrent|state|lstm|gru|conv1d)", re.I)


def _local(tag: str) -> str:
    """Strip any XML namespace/prefix, keeping the local name."""
    if tag.startswith("{"):
        tag = tag.split("}", 1)[1]
    return tag.split(":", 1)[-1] if ":" in tag else tag


def _norm_attrs(elem: ET.Element) -> Dict[str, str]:
    return {_local(k): v for k, v in elem.attrib.items()}


def _union_intervals(ranges: List[Tuple[int, int]]) -> List[List[int]]:
    out: List[List[int]] = []
    for lo, hi in sorted(ranges):
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def _int_or_none(text: Optional[str]) -> Tuple[bool, Optional[int]]:
    """Validate an offset/size string: must be a non-negative decimal int."""
    if text is None:
        return False, None
    t = text.strip()
    if not re.fullmatch(r"\d+", t):
        return False, None
    return True, int(t)


def _digest(path: Path, limit: int) -> Optional[str]:
    try:
        if path.stat().st_size > limit:
            return None  # too large: do not hash, record as refused
    except OSError:
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _split_dims(text: Optional[str]) -> Optional[List[str]]:
    """Split a shape string on commas and/or whitespace; empty stays []."""
    if text is None:
        return None
    parts = [p for p in re.split(r"[,\s]+", text.strip()) if p]
    return parts


def _class_layers(
    name: str,
    op: str,
    num_experts: Optional[int],
    shape: Optional[List[str]],
) -> Tuple[str, List[str]]:
    """Conservative role classification with recorded evidence."""
    evidence: List[str] = []
    m = VIS_RE.search(name)
    if m:
        return "vision", ["name~vision:%r" % m.group(0)]
    m = ROUTER_RE.search(name)
    if m:
        evidence.append("name~router_or_mlp_gate_weight:%r" % m.group(0))
        return "router", evidence
    m = SHARED_RE.search(name)
    if m:
        return "shared_expert", ["name~shared_expert:%r" % m.group(0)]
    mi = EXPERT_INDEXED_RE.search(name)
    if mi:
        return "routed_expert", ["name~indexed-expert-id=%s(no per-tensor ID invented)" % mi.group(1)]
    ma = EXPERT_AGG_RE.search(name)
    if ma and PROJ_SUFFIX_RE.search(ma.group(1)):
        evidence.append(
            "name~aggregate-expert-tensor:%r (no explicit expert index in name)"
            % ma.group(0)
        )
        if num_experts is not None and shape:
            first = shape[0]
            if first.lstrip("-").isdigit():
                if int(first) == num_experts:
                    evidence.append(
                        "shape[0]=%s==config.num_experts=%d corroborates packing" % (first, num_experts)
                    )
                else:
                    evidence.append(
                        "shape[0]=%s != config.num_experts=%d (conservative, still name-based)"
                        % (first, num_experts)
                    )
            else:
                evidence.append("shape[0]=%r non-numeric" % first)
        elif num_experts is None:
            evidence.append("config.num_experts unknown; classification rests on name form")
        return "routed_expert", evidence
    m = ATTN_RE.search(name)
    if m:
        return "attention_kv_or_state", ["name~attention-state:%r" % m.group(0)]
    m = ABS_EMB_RE.search(name)
    if m:
        return "embeddings", ["name~embeddings:%r" % m.group(0)]
    m = OUT_RE.search(name)
    if m:
        return "output", ["name~output:%r" % m.group(0)]
    if UNINDEXED_EXPERT_HINT.search(name):
        evidence.append("name~expert-without-recognized-form=conservative_unknown")
    if MOE_OP_HINT.search(op):
        evidence.append("op~moe-op (role stays unknown)")
    return "unknown", evidence


def _parse_ports(layer: ET.Element) -> List[Dict[str, Any]]:
    """Extract output/input port records using actual <port><dim> children."""
    ports: List[Dict[str, Any]] = []
    for section in layer:
        sec_tag = _local(section.tag)
        if sec_tag not in ("output", "input"):
            continue
        for port in section:
            if _local(port.tag) != "port":
                continue
            pattrs = _norm_attrs(port)
            dims: List[str] = []
            for child in port:
                if _local(child.tag) == "dim":
                    dims.append((child.text or "").strip())
            ports.append(
                {
                    "direction": sec_tag,
                    "id": pattrs.get("id"),
                    "precision": pattrs.get("precision"),
                    "dims": dims,
                }
            )
    return ports


def _guess_bin_rel(
    graph_path: Path,
    model_dir: Path,
    bin_sizes: Dict[str, int],
) -> Optional[str]:
    """Associate a BIN by model-relative identity; never collapse namesakes."""
    rel_dir = graph_path.parent.relative_to(model_dir).as_posix()
    same_dir = [k for k in bin_sizes if PurePosixPath(k).parent.as_posix() == rel_dir]
    stem = graph_path.stem + ".bin"
    for cand in (stem, graph_path.name + ".bin"):
        key = (rel_dir + "/" + cand) if rel_dir != "." else cand
        if key in bin_sizes:
            return key
    if len(same_dir) == 1:
        return same_dir[0]
    if len(bin_sizes) == 1:
        return next(iter(bin_sizes))
    return None


def parse_graph(
    path: Path,
    bin_sizes: Dict[str, int],
    model_dir: Path,
    num_experts: Optional[int] = None,
    config_hints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Parse one IR graph XML into an inventory record."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        root = ET.fromstring(raw)
    except Exception as exc:  # noqa: BLE001 - malformed file is a report fact
        return {
            "file": path.name,
            "kind": "unparseable_xml",
            "status": "invalid",
            "errors": ["xml_parse_error: %s" % exc],
            "layers": [],
            "constants": [],
            "role_summary": {},
            "byte_accounting": None,
            "family_profile": {"architecture_label": "unknown_unparsed"},
        }
    attrs = _norm_attrs(root)
    graph_name = attrs.get("name", path.stem)
    rel = path.relative_to(model_dir).as_posix()
    default_bin = _guess_bin_rel(path, model_dir, bin_sizes)

    layers: List[Dict[str, Any]] = []
    band_refs: List[Tuple[int, int]] = []
    valid_ranges: List[Tuple[int, int]] = []
    declared_sum = 0
    errors: List[str] = []
    sliding_seen = False
    full_seen = False
    state_seen = False
    linear_seen = False
    moe_ops: List[str] = []

    layer_elems = [e for e in root.iter() if _local(e.tag) == "layer"]
    for order, le in enumerate(layer_elems):
        la = _norm_attrs(le)
        name = la.get("name", "")
        op = _local(la.get("type", ""))
        layer_id = la.get("id", str(order))
        ports = _parse_ports(le)

        # Const metadata lives on the <data> child in actual IR syntax.
        data_attrs: Dict[str, str] = {}
        shape: Optional[List[str]] = None
        et = la.get("element_type") or la.get("precision")
        offset = None
        size = None
        const_errors: List[str] = []
        for child in le.iter():
            if _local(child.tag) == "data":
                data_attrs = _norm_attrs(child)
                break
        if data_attrs:
            shape = _split_dims(data_attrs.get("shape"))
            et = et or data_attrs.get("element_type")
            offset_ok, offset = _int_or_none(data_attrs.get("offset"))
            size_ok, size = _int_or_none(data_attrs.get("size"))
            if data_attrs.get("offset") is None and op.lower() in ("const", "constant"):
                const_errors.append("missing_offset")
            elif op.lower() in ("const", "constant") and not offset_ok and data_attrs.get("offset") is not None:
                const_errors.append("offset_not_nonnegative_integer")
            if data_attrs.get("size") is None and op.lower() in ("const", "constant"):
                const_errors.append("missing_size")
            elif op.lower() in ("const", "constant") and not size_ok and data_attrs.get("size") is not None:
                const_errors.append("size_not_nonnegative_integer")

        is_const = op.lower() in ("const", "constant")
        role, ev = _class_layers(name, op, num_experts, shape)
        if SLIDING_HINT.search(name):
            sliding_seen = True
        if FULL_ATTN_HINT.search(name):
            full_seen = True
        if LINEAR_ATTN_HINT.search(name):
            linear_seen = True
        if role == "attention_kv_or_state" and ATTN_STATE_HINT.search(name):
            state_seen = True
        if MOE_OP_HINT.search(op) and op not in moe_ops:
            moe_ops.append(op)

        rec: Dict[str, Any] = {
            "layer_id": layer_id,
            "name": name,
            "op": op,
            "role": role,
            "role_evidence": ev,
        }
        block = None
        mb = BLOCK_RE.search(name)
        if mb:
            block = int(mb.group(1) or mb.group(2))
            ev.append("block_index=%d parsed from name (not node id)" % block)
            rec["role_evidence"] = ev
        rec["transformer_block_index"] = block
        if ports:
            rec["ports"] = ports

        const_rec: Optional[Dict[str, Any]] = None
        if is_const:
            bin_rel = la.get("bin") or default_bin or "<unresolved>"
            bin_size = bin_sizes.get(bin_rel) if bin_rel != "<unresolved>" else None
            if offset_ok and size_ok and bin_size is not None:
                if offset + size > bin_size:
                    const_errors.append(
                        "out_of_bounds: const range [%d,%d) exceeds %s size %d"
                        % (offset, offset + size, bin_rel, bin_size)
                    )
            elif offset_ok and size_ok and bin_size is None:
                const_errors.append("bin_not_present_for_bounds_check")
            empty = size == 0 or bool(shape and all(d == "0" for d in shape))
            const_rec = {
                "binary": bin_rel,
                "offset": offset,
                "size": size,
                "element_type": et,
                "shape": shape,
                "empty_tensor": empty,
                "valid": not const_errors,
                "errors": const_errors,
                "evidence": {"raw_data_attrs": data_attrs},
            }
            rec["const"] = const_rec
            if const_rec["valid"]:
                rng = (offset, offset + size)
                declared_sum += size
                valid_ranges.append(rng)
            else:
                errors.extend(const_errors)
            band_refs.append((offset or 0, (offset or 0) + (size or 0)))
        layers.append(rec)

    union = banded = None
    if band_refs:
        banded = _union_intervals(band_refs)
        union = sum(hi - lo for lo, hi in banded)
    bin_rel_acc = default_bin
    bin_size = bin_sizes.get(bin_rel_acc) if bin_rel_acc else None

    accounting: Dict[str, Any] = {
        "weights_bin": bin_rel_acc,
        "bin_file_size_bytes": bin_size,
        "declared_const_bytes_sum": declared_sum,
        "referenced_unique_bytes": union,
        "aliased_shared_bytes_saved": (
            declared_sum - union if union is not None else None
        ),
        "referenced_intervals": banded or [],
        "unreferenced_bytes": (
            bin_size - union
            if bin_size is not None and union is not None and union <= bin_size
            else None
        ),
        "note": "shared/aliased Const offsets counted once via interval union; BIN never opened",
    }

    if sliding_seen and full_seen:
        attn_style = "hybrid_sliding_full_evidence"
    elif linear_seen and full_seen:
        attn_style = "hybrid_linear_full_evidence"
    elif linear_seen:
        attn_style = "linear_attention_evidence"
    elif sliding_seen:
        attn_style = "sliding_window_evidence"
    elif full_seen:
        attn_style = "full_attention_evidence"
    else:
        attn_style = "unknown"
    if state_seen and "recurrent_state_evidence" not in attn_style:
        attn_style += "+recurrent_state_evidence"
    n_routed = sum(1 for l in layers if l["role"] == "routed_expert")
    n_shared = sum(1 for l in layers if l["role"] == "shared_expert")
    n_router = sum(1 for l in layers if l["role"] == "router")
    if (n_routed or n_shared) and n_router:
        arch_label = "moe_with_shared_expert_evidence" if n_shared else "moe_evidence"
    elif n_routed and not n_router:
        arch_label = "expert_tensors_without_router_evidence"
    elif n_routed or n_shared:
        arch_label = "moe_partial_evidence"
    else:
        arch_label = (
            "dense_evidence"
            if any(
                l["role"] in ("attention_kv_or_state", "embeddings", "output")
                for l in layers
            )
            else "unknown"
        )

    profile: Dict[str, Any] = {
        "architecture_label": arch_label,
        "attention_style": attn_style,
        "routed_expert_layers": n_routed,
        "shared_expert_layers": n_shared,
        "router_layers": n_router,
        "recurrent_state_evidence": state_seen,
        "aggregation_note": (
            "packed expert tensors classified as routed_expert without inventing "
            "per-expert IDs; offsets/sizes are aggregate"
            if n_routed
            else None
        ),
    }
    if config_hints:
        profile["config_corroboration"] = config_hints

    role_summary: Dict[str, int] = {}
    for l in layers:
        role_summary[l["role"]] = role_summary.get(l["role"], 0) + 1

    status = "ok"
    if errors:
        status = "invalid"  # never PASS malformed IR
    if not layers:
        status = "partial" if status == "ok" else status

    return {
        "file": path.name,
        "kind": "ir_graph_xml",
        "graph_name": graph_name,
        "relative": rel,
        "status": status,
        "errors": errors,
        "raw_evidence": {
            "layer_count": len(layers),
            "moe_ops_observed": moe_ops,
            "sliding_hint": sliding_seen,
            "linear_attention_hint": linear_seen,
            "full_attention_hint": full_seen,
        },
        "layers": layers,
        "role_summary": role_summary,
        "family_profile": profile,
        "byte_accounting": accounting,
    }


# ---------------------------------------------------------------------------
# Config parsing: JSON (actual GenAI format) with legacy XML support
# ---------------------------------------------------------------------------

_CONFIG_XML_KEEP_KEYS = (
    "arch",
    "model_type",
    "weights_path",
    "run_time",
    "version",
    "export",
    "key",
)
_JSON_KEEP_KEYS = (
    "architectures",
    "model_type",
    "num_experts",
    "num_hidden_layers",
)
_JSON_NESTED_KEYS = ("text_config", "vision_config", "audio_config")


def parse_config_json(path: Path, rel: str) -> Dict[str, Any]:
    rec: Dict[str, Any] = {
        "file": path.name,
        "relative": rel,
        "kind": "json_config",
    }
    try:
        size = path.stat().st_size
    except OSError as exc:
        rec["status"] = "unreadable"
        rec["errors"] = ["stat_error: %s" % exc]
        return rec
    if size > JSON_PARSE_LIMIT_BYTES:
        rec["status"] = "skipped_size"
        rec["file_bytes"] = size
        rec["errors"] = [
            "json file larger than parse limit %d bytes; metadata not parsed" % JSON_PARSE_LIMIT_BYTES
        ]
        return rec
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        rec["status"] = "unparseable_json"
        rec["file_bytes"] = size
        rec["errors"] = ["json_parse_error: %s" % exc]
        return rec
    rec["status"] = "ok"
    rec["file_bytes"] = size
    rec["evidence"] = {}
    for k in _JSON_KEEP_KEYS:
        if isinstance(data, dict) and k in data:
            rec["evidence"][k] = data[k]
    rec["nested"] = {
        k: data[k] for k in _JSON_NESTED_KEYS if isinstance(data, dict) and k in data
    }
    rec["sha256"] = _digest(path, HASH_LIMIT_XML_BYTES)
    return rec


def parse_config_xml(path: Path, rel: str) -> Dict[str, Any]:
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        return {
            "file": path.name,
            "relative": rel,
            "kind": "xml_config",
            "status": "unparseable_xml",
            "errors": ["xml_parse_error: %s" % exc],
            "evidence": {},
        }
    rec: Dict[str, Any] = {
        "file": path.name,
        "relative": rel,
        "kind": "xml_config",
        "status": "ok",
        "top_level_tag": _local(root.tag),
        "evidence": {},
        "nested": {},
    }
    for elem in root.iter():
        for k, v in _norm_attrs(elem).items():
            if k in _CONFIG_XML_KEEP_KEYS and k not in rec["evidence"]:
                rec["evidence"][k] = v
        name = _local(elem.tag)
        if name in _CONFIG_XML_KEEP_KEYS and name not in rec["evidence"]:
            rec["evidence"][name] = (elem.text or "").strip()
    for child in root:
        tag = _local(child.tag)
        if tag in ("text", "vision", "audio", "speech"):
            rec["nested"][tag] = _elem_to_dict(child)
    rec["sha256"] = _digest(path, HASH_LIMIT_XML_BYTES)
    return rec


def _elem_to_dict(elem: ET.Element) -> Dict[str, Any]:
    d: Dict[str, Any] = {"attributes": _norm_attrs(elem)}
    kids = [_elem_to_dict(c) for c in elem]
    if kids:
        d["children"] = {_local(c.tag): c_rec for c, c_rec in zip(elem, kids)}
    if elem.text and elem.text.strip():
        d["text"] = elem.text.strip()
    return d


# ---------------------------------------------------------------------------
# Directory inventory
# ---------------------------------------------------------------------------

def scan_model_dir(model_dir: Path) -> Dict[str, Any]:
    model_dir = Path(model_dir)
    xmls = sorted(model_dir.rglob("*.xml"))
    bins = sorted(model_dir.rglob("*.bin"))
    jsons = sorted(model_dir.rglob("*.json"))

    bin_sizes: Dict[str, int] = {}
    for b in bins:
        rel = b.relative_to(model_dir).as_posix()  # identity, not basename
        try:
            bin_sizes[rel] = b.stat().st_size
        except OSError:
            bin_sizes[rel] = -1

    configs: List[Dict[str, Any]] = []
    for p in jsons:
        rel = p.relative_to(model_dir).as_posix()
        configs.append(parse_config_json(p, rel))
    for p in xmls:
        try:
            root = ET.fromstring(p.read_text(encoding="utf-8", errors="replace"))
            is_graph = any(_local(e.tag) == "layer" for e in root.iter())
        except Exception:  # noqa: BLE001
            is_graph = False
        rel = p.relative_to(model_dir).as_posix()
        if not is_graph:
            configs.append(parse_config_xml(p, rel))

    first_arch = first_model_type = first_num_experts = None
    for c in configs:
        if c.get("status") != "ok":
            continue
        ev = c.get("evidence") or {}
        if first_arch is None and ev.get("architectures"):
            archev = ev["architectures"]
            first_arch = archev[0] if isinstance(archev, list) and archev else archev
        if first_model_type is None and ev.get("model_type"):
            first_model_type = ev["model_type"]
        nested = c.get("nested") or {}
        if first_num_experts is None:
            if isinstance(nested.get("text_config"), dict) and "num_experts" in nested["text_config"]:
                first_num_experts = nested["text_config"]["num_experts"]
            elif ev.get("num_experts") is not None:
                first_num_experts = ev["num_experts"]
    # legacy XML config fallback: architecture may be stored as raw "arch"
    for c in configs:
        if c.get("status") != "ok":
            continue
        ev = c.get("evidence") or {}
        if first_arch is None and ev.get("arch") is not None:
            first_arch = ev["arch"]

    graph_records: List[Dict[str, Any]] = []
    config_hints: Dict[str, Any] = {}
    for c in configs:
        if c.get("status") != "ok":
            continue
        nested = c.get("nested") or {}
        tc = nested.get("text_config")
        if isinstance(tc, dict):
            if "layer_types" in tc:
                from collections import Counter
                config_hints["text_config_layer_types"] = dict(Counter(tc["layer_types"]))
            if "full_attention_interval" in tc:
                config_hints["text_config_full_attention_interval"] = tc["full_attention_interval"]
            if "num_hidden_layers" in tc:
                config_hints["text_config_num_hidden_layers"] = tc["num_hidden_layers"]
            if "shared_expert_intermediate_size" in tc:
                config_hints["text_config_shared_expert_intermediate_size"] = tc["shared_expert_intermediate_size"]
        if "model_type" in (c.get("evidence") or {}) and "config_model_type" not in config_hints:
            config_hints["config_model_type"] = c["evidence"]["model_type"]
    for p in xmls:
        try:
            root = ET.fromstring(p.read_text(encoding="utf-8", errors="replace"))
            is_graph = any(_local(e.tag) == "layer" for e in root.iter())
        except Exception:  # noqa: BLE001
            is_graph = False
        if not is_graph:
            continue
        g = parse_graph(p, bin_sizes, model_dir, first_num_experts, config_hints or None)
        rel = p.relative_to(model_dir).as_posix()
        g["relative"] = rel
        g["file_bytes"] = p.stat().st_size
        g["sha256"] = _digest(p, HASH_LIMIT_XML_BYTES)
        graph_records.append(g)

    # Model-level per-BIN union across graphs (alias counted once).
    bin_records: List[Dict[str, Any]] = []
    for name in sorted(bin_sizes):
        size = bin_sizes[name]
        spans: List[Tuple[int, int]] = []
        for g in graph_records:
            acc = g.get("byte_accounting") or {}
            if acc.get("weights_bin") == name:
                for lo, hi in acc.get("referenced_intervals", []):
                    spans.append((lo, hi))
        ivals = _union_intervals(spans)
        union = sum(hi - lo for lo, hi in ivals)
        ok = size >= 0 and union <= size
        bin_records.append(
            {
                "relative": name,
                "file_size_bytes": size,
                "sha256": None,
                "contents_read": False,  # BIN contents are never opened
                "referenced_unique_bytes": union if ok else None,
                "referenced_intervals": ivals,
                "unknown_unreferenced_bytes": (size - union) if ok else None,
                "accounting_consistent": ok,
            }
        )

    ok_cfgs = [c for c in configs if c.get("status") == "ok"]
    has_cfg = bool(ok_cfgs)
    if not configs and not graph_records:
        model_status, reason = "missing", "no configs and no IR graph files found"
    elif graph_records and has_cfg:
        model_status, reason = "complete", ""
    elif graph_records and not has_cfg:
        model_status, reason = "partial", "IR graph files present but no model config"
    else:
        model_status = "partial" if configs else "missing"
        reason = (
            "model config present but no real language/model IR graph file; "
            "no model is fabricated from config alone"
        )
    invalid = [g["relative"] for g in graph_records if g["status"] == "invalid"]
    if model_status == "complete" and invalid:
        model_status = "partial"
        reason = (
            "malformed IR detected in: %s; model status downgraded, invalid IR is "
            "never PASSed" % ", ".join(invalid)
        )
    if model_status == "complete" and not graph_records:
        model_status = "partial"

    model_config: Dict[str, Any] = {
        "status": "found" if configs else "missing",
        "files": [c["relative"] for c in configs],
        "architecture": first_arch,
        "model_type": first_model_type,
        "num_experts": first_num_experts,
        "nested": {c["relative"]: c.get("nested", {}) for c in configs},
    }

    return {
        "schema": SCHEMA,
        "generated_utc": None,  # filled by main() for CLI runs
        "model_dir": str(model_dir),
        "model_status": model_status,
        "model_status_reason": reason,
        "malformed_ir_never_pass": bool(invalid) or model_status in ("missing", "partial"),
        "model_config": model_config,
        "configs": configs,
        "graphs": graph_records,
        "binaries": bin_records,
        "static_only_notice": NOT_STATEMENTS,
    }


def generate_inventory(model_dir: Path) -> Dict[str, Any]:
    return scan_model_dir(model_dir)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="MAP-02 static family/layer memory inventory (read-only)"
    )
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args(argv)

    model_dir = Path(args.model_dir)
    if not model_dir.is_dir():
        sys.stderr.write("--model-dir does not exist or is not a directory: %s\n" % model_dir)
        return 2

    inv = generate_inventory(model_dir)
    inv["generated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    out = json.dumps(inv, indent=2, default=str)
    with Path(args.output).open("w", encoding="utf-8") as fh:
        fh.write(out + "\n")
    n_invalid = sum(1 for g in inv["graphs"] if g.get("status") == "invalid")
    sys.stdout.write(
        "family_map: model_status=%s graphs=%d invalid=%d bins=%d -> %s\n"
        % (inv["model_status"], len(inv["graphs"]), n_invalid, len(inv["binaries"]), args.output)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
