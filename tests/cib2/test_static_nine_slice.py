# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Synthetic checks for static nine-slot name co-occurrence.

No model weights, BIN files, or runtime eligibility are involved.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "cib2"))

import static_nine_slice as nine  # noqa: E402


def _const(parent, layer_id, name, offset=None, size=None):
    layer = ET.SubElement(parent, "layer", {"id": str(layer_id), "name": name, "type": "Const"})
    attrs = {}
    if offset is not None:
        attrs["offset"] = str(offset)
    if size is not None:
        attrs["size"] = str(size)
    ET.SubElement(layer, "data", attrs)


def _xml(consts):
    root = ET.Element("net")
    layers = ET.SubElement(root, "layers")
    for item in consts:
        _const(layers, *item)
    return root


class StaticNineSliceTest(unittest.TestCase):
    def test_all_nine_cooccur_in_one_block(self):
        consts = []
        index = 1
        for proj, token in (("gate", "gate_proj"), ("up", "up_proj"), ("down", "down_proj")):
            base = "model.layers.3.mlp.experts.%s" % token
            consts.append((index, base, index * 10, 100))
            consts.append((index + 1, base + "/scale", index * 10 + 1, 4))
            consts.append((index + 2, base + "/zero_point", index * 10 + 2, 4))
            index += 3
        report = nine.analyze_root(_xml(consts), "fixture.xml")
        self.assertEqual(report["compiled_kind"], "UNKNOWN")
        self.assertEqual(report["runtime_acceptance"], "NO")
        self.assertFalse(report["bin_opened"])
        self.assertEqual(report["blocks_with_all_nine"], 1)
        self.assertEqual(report["complete_blocks"], [3])
        self.assertEqual(sum(report["slot_counts"].values()), 9)

    def test_down_only_is_not_nine(self):
        root = _xml(
            [
                (10, "model.layers.0.mlp.experts.down_proj", 5, 8),
                (11, "model.layers.0.mlp.experts.down_proj/scale", 6, 2),
                (12, "model.layers.0.mlp.experts.down_proj/zero_point", 7, 2),
                (13, "model.layers.0.mlp.experts.down_proj/fq_weights_1", 8, 2),
                (14, "model.layers.0.mlp.experts.down_proj/zero_point/subtract", None, None),
                (15, "model.layers.0.mlp.experts.up_proj", None, None),
            ]
        )
        report = nine.analyze_root(root, "fixture.xml")
        self.assertEqual(report["blocks_with_all_nine"], 0)
        self.assertEqual(report["matched_const_count"], 4)
        self.assertEqual(report["slot_counts"]["down/weight"], 1)
        self.assertEqual(report["slot_counts"]["gate/weight"], 0)
        up = [rec for rec in report["records"] if rec["slot"] == "up/weight"]
        self.assertEqual(len(up), 1)
        self.assertIsNone(up[0]["offset"])
        self.assertIsNone(up[0]["size"])

    def test_shared_expert_is_not_routed(self):
        root = _xml(
            [
                (1, "model.layers.0.mlp.shared_expert.gate_proj", 1, 1),
                (2, "model.layers.0.mlp.shared_expert.up_proj/scale", 2, 1),
                (3, "model.layers.0.mlp.shared_expert.down_proj/zero_point", 3, 1),
            ]
        )
        report = nine.analyze_root(root, "fixture.xml")
        self.assertEqual(report["matched_const_count"], 0)

    def test_cli_refuses_to_write_beside_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            xml_path = folder / "graph.xml"
            xml_path.write_text("<net></net>", encoding="utf-8")
            with self.assertRaises(SystemExit):
                nine.main(["--xml", str(xml_path), "--output", str(folder / "out.json")])

    def test_cli_writes_json_outside_xml_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            xml_dir = folder / "model"
            out_dir = folder / "out"
            xml_dir.mkdir()
            xml_path = xml_dir / "openvino_language_model.xml"
            root = _xml([(4, "model.layers.1.mlp.experts.down_proj", 9, 3)])
            xml_path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
            output = out_dir / "report.json"
            code = nine.main(["--xml", str(xml_path), "--output", str(output), "--markdown", str(out_dir / "report.md")])
            self.assertEqual(code, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["compiled_kind"], "UNKNOWN")
            self.assertIn("UNKNOWN", (out_dir / "report.md").read_text(encoding="utf-8"))


class StaticNineSliceIndependentReviewTest(unittest.TestCase):
    def test_projection_substrings_do_not_become_nine_slots(self):
        invalid = (
            "model.layers.0.mlp.experts.not_down_proj/scale",
            "model.layers.0.mlp.experts.down_proj_extra/zero_point",
            "model.layers.0.mlp.experts.gate_proj/up_proj/scale",
            "model.layers.0.mlp.experts.a_up_proj/scale",
            "model.layers.0.mlp.experts.down_proj/scale/matmul",
        )
        for name in invalid:
            with self.subTest(name=name):
                self.assertIsNone(nine.classify_routed_const(name))
        self.assertEqual(
            nine.classify_routed_const("model.layers.0.mlp.experts.down_proj/scale"),
            "down/scale",
        )

    def test_other_projection_substrings_cannot_make_complete_block(self):
        entries = []
        i = 0
        for projection in ("gate", "up", "down"):
            base = "model.layers.1.mlp.experts.fake_%s_proj" % projection
            for suffix in ("", "/scale", "/zero_point"):
                entries.append((i, base + suffix, 1, 1))
                i += 1
        report = nine.analyze_root(_xml(entries), "adversarial.xml")
        self.assertEqual(report["matched_const_count"], 0)
        self.assertEqual(report["blocks_with_all_nine"], 0)

    def test_markdown_must_not_overwrite_bin_or_write_partial_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / "model"
            target = folder / "other_model"
            source.mkdir()
            target.mkdir()
            xml = source / "openvino_language_model.xml"
            xml.write_text("<net><layers /></net>", encoding="utf-8")
            protected = target / "weights.bin"
            protected.write_bytes(b"untouched-weight-sentinel")
            output = folder / "reports" / "summary.json"
            with self.assertRaisesRegex(SystemExit, "markdown output must be a .md"):
                nine.main(["--xml", str(xml), "--output", str(output),
                           "--markdown", str(protected)])
            self.assertEqual(protected.read_bytes(), b"untouched-weight-sentinel")
            self.assertFalse(output.exists())

    def test_invalid_markdown_in_source_dir_leaves_no_partial_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / "model"
            model.mkdir()
            xml = model / "openvino_language_model.xml"
            xml.write_text("<net><layers /></net>", encoding="utf-8")
            output = root / "report.json"
            with self.assertRaisesRegex(SystemExit, "XML directory"):
                nine.main(["--xml", str(xml), "--output", str(output),
                           "--markdown", str(model / "inside.md")])
            self.assertFalse(output.exists())
            self.assertEqual(xml.read_text(encoding="utf-8"), "<net><layers /></net>")

    def test_markdown_does_not_export_absolute_host_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / "private_model"
            out = root / "reports"
            model.mkdir()
            xml = model / "openvino_language_model.xml"
            xml.write_text("<net><layers /></net>", encoding="utf-8")
            self.assertEqual(
                nine.main(["--xml", str(xml), "--output", str(out / "report.json"),
                           "--markdown", str(out / "report.md")]), 0,
            )
            text = (out / "report.md").read_text(encoding="utf-8")
            self.assertNotIn(str(model), text)
            self.assertIn("openvino_language_model.xml", text)


if __name__ == "__main__":
    unittest.main()
