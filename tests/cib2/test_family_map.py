"""Unit fixtures for MAP-01 static family/layer memory mapper.

All fixtures are synthetic temporary XML/config and dummy BIN files created in
a TemporaryDirectory. They contain no real model data. BIN contents are dummy
zero bytes because the tool must never read them.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "cib2"
sys.path.insert(0, str(SCRIPTS))

import family_map  # noqa: E402


def write_graph(path: Path, name: str, layers: str, namespaced: bool = False) -> None:
    ns = ' xmlns:ns0="http://tmp/mirror/import"' if namespaced else ""
    pre = "ns0:" if namespaced else ""
    lid = "ns0:" if namespaced else ""
    body = f"""
<{lid}net name="{name}" version="10"{ns}>
 <{lid}layers>
{layers}
 </{lid}layers>
</{lid}net>
"""
    path.write_text(body)


def const_layer(lid, name, offset, size, et="u8", dims="16", extra=""):
    """Actual OpenVINO IR v11 Const syntax: metadata on the <data> child."""
    return (
        f'  <layer id="{lid}" name="{name}" type="Const" version="opset1" {extra}>'
        f'<data element_type="{et}" shape="{dims}" offset="{offset}" size="{size}"/>'
        f'<output><port id="0" precision="{et.upper()}"><dim>{dims.split(",")[0] if dims else "16"}'
        f'</dim></port></output></layer>'
    )


def clayer(lid, name, op, extra=""):
    """Layer whose inner content (e.g. <data/>) is provided via extra."""
    return f'  <layer id="{lid}" name="{name}" type="{op}" version="opset1">{extra}</layer>'


def dense_layers():
    return "\n".join(
        [
            const_layer(1, "tok_embeddings.weight", 0, 4096, "f16", "1024 512"),
            const_layer(2, "blocks.0.attention.wq.weight", 4096, 4096),
            const_layer(3, "blocks.0.attention.wv.weight", 8192, 4096),
            const_layer(4, "lm_head.weight", 12288, 4096),
            const_layer(5, "partition_l_boundary_id_5", 16384, 1000),
        ]
    )


def moe_layers():
    return "\n".join(
        [
            const_layer(1, "tok_embeddings.weight", 0, 2048),
            const_layer(2, "mlp.router.weight", 2048, 2048),
            const_layer(3, "shared_expert.gate_proj.weight", 4096, 4096),
            const_layer(4, "expert_layers", 8192, 4096),
            const_layer(5, "self.experts.3.gate_proj.weight", 12288, 4096),
            const_layer(6, "vertx.experts.3.up_proj.weight", 8192, 4096),
            const_layer(7, "lm_head.weight", 16384, 4096),
        ]
    )


def hybrid_layers():
    return "\n".join(
        [
            const_layer(1, "tok_embeddings.weight", 0, 2048),
            const_layer(2, "blocks.0.attention.sliding_window.wq.weight", 2048, 2048),
            const_layer(3, "blocks.0.attention.sliding_window.wv.weight", 4096, 2048),
            const_layer(4, "blocks.1.attention.wv.weight", 6144, 2048),
            const_layer(5, "blocks.1.recurrent.state.weight", 8192, 2048),
        ]
    )


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def make_config_only_json(self, **extra):
        cfg = {"model_type": "unit_test_model", "architectures": ["TestModel"],
               "num_experts": 256}
        cfg.update(extra)
        (self.dir / "config.json").write_text(json.dumps(cfg))

    def make(self, graph_layers=None, bin_size=0, name="model_graph", xml=None,
             config=True, namespaced=False):
        """Create graph xml (from layers or raw xml), dummy bin and config."""
        graph_path = self.dir / (name + ".xml")
        if xml is not None:
            graph_path.write_text(xml)
        elif graph_layers is not None:
            write_graph(graph_path, name, graph_layers, namespaced=namespaced)
        if bin_size:
            (self.dir / (name + ".bin")).write_bytes(b"\x00" * bin_size)
        if config:
            (self.dir / "config.xml").write_text(
                '<genai model_type="text"><arch pt="1">openvino</arch>'
                "<text><token_limit>4096</token_limit></text>"
                "<vision><iv_limit>64</iv_limit></vision></genai>"
            )

    def inv(self, **kw):
        d = family_map.generate_inventory(self.dir)
        if kw.get("shadow_bin_bytes"):
            # prove BIN contents are never read: tool sees only sizes
            pass
        d["generated_utc"] = "FIXED"
        return d

    def graph(self, name="model_graph.xml"):
        return next(g for g in self.inv()["graphs"] if g["file"] == name)


class TestDenseGraph(Base):
    def test_dense_roles_and_family(self):
        self.make(dense_layers(), bin_size=20000)
        inv = self.inv()
        g = self.graph()
        self.assertEqual(g["status"], "ok")
        self.assertEqual(g["family_profile"]["architecture_label"], "dense_evidence")
        self.assertEqual(g["family_profile"]["attention_style"], "full_attention_evidence")
        roles = {l["name"]: l["role"] for l in g["layers"]}
        self.assertEqual(roles["tok_embeddings.weight"], "embeddings")
        self.assertEqual(roles["blocks.0.attention.wv.weight"], "attention_kv_or_state")
        self.assertEqual(roles["lm_head.weight"], "output")
        # Unknown leftover stays unknown; not forced to expert.
        self.assertEqual(roles["partition_l_boundary_id_5"], "unknown")
        mc = inv["model_config"]
        self.assertEqual(mc["architecture"], "openvino")
        self.assertEqual(mc["model_type"], "text")
        self.assertEqual(set(mc["nested"]["config.xml"]), {"text", "vision"})
        self.assertEqual(inv["model_status"], "complete")


class TestMoeRoles(Base):
    def test_expert_shared_router(self):
        self.make(moe_layers(), bin_size=24000)
        g = self.graph()
        roles = {l["name"]: l["role"] for l in g["layers"]}
        self.assertEqual(roles["mlp.router.weight"], "router")
        self.assertEqual(roles["shared_expert.gate_proj.weight"], "shared_expert")
        self.assertEqual(roles["self.experts.3.gate_proj.weight"], "routed_expert")
        self.assertEqual(roles["vertx.experts.3.up_proj.weight"], "routed_expert")
        # unindexed "expert" word is conservative, must stay unknown
        self.assertEqual(roles["expert_layers"], "unknown")
        self.assertEqual(roles["tok_embeddings.weight"], "embeddings")
        self.assertEqual(roles["lm_head.weight"], "output")
        fp = g["family_profile"]
        self.assertEqual(fp["architecture_label"], "moe_with_shared_expert_evidence")
        self.assertEqual(fp["routed_expert_layers"], 2)
        self.assertEqual(fp["shared_expert_layers"], 1)
        self.assertEqual(fp["router_layers"], 1)
        self.assertEqual(fp["attention_style"], "unknown")


class TestHybridStates(Base):
    def test_hybrid_attention_and_recurrent_state(self):
        self.make(hybrid_layers(), bin_size=11000)
        g = self.graph()
        roles = {l["name"]: l["role"] for l in g["layers"]}
        for n in (
            "blocks.0.attention.sliding_window.wq.weight",
            "blocks.0.attention.sliding_window.wv.weight",
            "blocks.1.attention.wv.weight",
            "blocks.1.recurrent.state.weight",
        ):
            self.assertEqual(roles[n], "attention_kv_or_state")
        fp = g["family_profile"]
        self.assertEqual(fp["attention_style"], "hybrid_sliding_full_evidence+recurrent_state_evidence")
        self.assertTrue(fp["recurrent_state_evidence"])
        self.assertEqual(fp["architecture_label"], "dense_evidence")


class TestByteAccounting(Base):
    def test_alias_dedup_and_partial_overlap(self):
        layers = "\n".join(
            [
                # A: [0,1000); B: [500,1500) partial overlap
                const_layer(1, "const_a", 0, 1000),
                const_layer(2, "const_b", 500, 1000),
                # C aliases A exactly ([0,1000))
                const_layer(3, "const_c", 0, 1000),
                const_layer(4, "const_out", 1500, 2000),
            ]
        )
        self.make(layers, bin_size=3000)
        g = self.graph()
        acc = g["byte_accounting"]
        self.assertEqual(acc["weights_bin"], "model_graph.bin")
        self.assertEqual(acc["bin_file_size_bytes"], 3000)
        # first pass contains an out-of-bounds const -> invalid, bad const excluded
        self.assertEqual(acc["declared_const_bytes_sum"], 3000)
        self.assertEqual(g["status"], "invalid")
        # rebuild with in-bounds values for the alias/overlap assertions:
        layers_v = "\n".join(
            [
                const_layer(1, "const_a", 0, 1000),
                const_layer(2, "const_b", 500, 1000),
                const_layer(3, "const_c", 0, 1000),
                const_layer(4, "const_out", 1500, 1200),
            ]
        )
        (self.dir / "model_graph.xml").unlink()
        write_graph(self.dir / "model_graph.xml", "model_graph", layers_v)
        g = self.graph()
        acc = g["byte_accounting"]
        self.assertEqual(acc["declared_const_bytes_sum"], 4200)
        self.assertEqual(acc["referenced_unique_bytes"], 2700)
        self.assertEqual(acc["aliased_shared_bytes_saved"], 1500)
        self.assertEqual(acc["unreferenced_bytes"], 300)
        # per-BIN model aggregate counts aliased bytes once across graphs
        b = next(x for x in self.inv()["binaries"] if x["relative"] == "model_graph.bin")
        self.assertEqual(b["referenced_unique_bytes"], 2700)
        self.assertEqual(b["unknown_unreferenced_bytes"], 300)
        self.assertTrue(b["contents_read"] is False and b["sha256"] is None)
        self.assertEqual(g["status"], "ok")


class TestMalformedIR(Base):
    def test_out_of_bounds_never_passes(self):
        layers = "\n".join(
            [const_layer(1, "ok_const", 0, 1000), const_layer(2, "bad_const", 2500, 4000)]
        )
        self.make(layers, bin_size=3000)
        g = self.graph()
        self.assertEqual(g["status"], "invalid")
        self.assertTrue(any("out_of_bounds" in e for e in g["errors"]))
        bad = next(c for c in g["layers"] if c["name"] == "bad_const")["const"]
        self.assertFalse(bad["valid"])
        ok = next(c for c in g["layers"] if c["name"] == "ok_const")["const"]
        self.assertTrue(ok["valid"])
        # model status flips so a PASS over malformed IR is impossible
        inv = self.inv()
        self.assertEqual(inv["model_status"], "partial")
        self.assertFalse(all("PASS" in str(g) for g in inv["graphs"]))

    def test_negative_and_missing_fields(self):
        layers = "\n".join(
            [
                clayer(1, "neg_offset", "Const", '<data offset="-5" size="10"/>'),
                clayer(2, "hex_chunk", "Const", '<data offset="0x10" size="abc"/>'),
                clayer(3, "no_fields", "Const", '<data element_type="f32"/>'),
            ]
        )
        self.make(layers, bin_size=4096)
        g = self.graph()
        self.assertEqual(g["status"], "invalid")
        errs = " ".join(g["errors"])
        self.assertIn("offset_not_nonnegative_integer", errs)
        self.assertIn("size_not_nonnegative_integer", errs)
        self.assertIn("missing_offset", errs)
        self.assertIn("missing_size", errs)

    def test_bin_missing_bounds_check(self):
        layers = const_layer(1, "solo_const", 0, 1024)
        (self.dir / "model_graph.xml").write_text("")
        write_graph(self.dir / "model_graph.xml", "model_graph", layers)
        self.inv()
        g = self.graph()
        self.assertEqual(g["status"], "invalid")
        self.assertTrue(any("bin_not_present_for_bounds_check" in e for e in g["errors"]))


class TestMissingGraph(Base):
    def test_config_only_is_partial_not_fabricated(self):
        self.make("", bin_size=0, config=True)
        # remove graph xml so only config remains
        (self.dir / "model_graph.xml").unlink()
        (self.dir / "model_graph.bin").unlink(missing_ok=True)
        inv = self.inv()
        self.assertEqual(inv["model_status"], "partial")
        self.assertIn("no real language/model IR graph file", inv["model_status_reason"])
        self.assertEqual(inv["graphs"], [])
        # config-only must not fabricate a model: no graph record exists
        self.assertEqual(inv["model_config"]["status"], "found")

    def test_empty_dir_is_missing(self):
        inv = self.inv()
        self.assertEqual(inv["model_status"], "missing")
        self.assertIn("no configs and no IR graph files", inv["model_status_reason"])


class TestNamespacedXml(Base):
    def test_namespaced_graph_and_config_parse(self):
        xml = (
            '<ns0:net xmlns:ns0="http://tmp/mirror/import" name="ns_graph" version="10">'
            "<ns0:layers>"
            '<ns0:layer id="7" name="blocks.experts.9.up_proj.weight" type="ns0:Const" version="opset1">'
            '<ns0:data element_type="f16" shape="128,8" offset="0" size="1024">'
            '</ns0:data><ns0:output><ns0:port id="0" precision="F16">'
            "<ns0:dim>128</ns0:dim><ns0:dim>8</ns0:dim></ns0:port></ns0:output></ns0:layer>"
            "</ns0:layers></ns0:net>"
        )
        self.make(None, bin_size=2048, xml=xml, namespaced=True)
        self.graph()  # ensure no exception
        g = self.graph()
        self.assertEqual(g["status"], "ok")
        self.assertEqual(g["graph_name"], "ns_graph")
        lay = g["layers"][0]
        self.assertEqual(lay["layer_id"], "7")
        self.assertEqual(lay["name"], "blocks.experts.9.up_proj.weight")
        self.assertEqual(lay["role"], "routed_expert")
        c = lay["const"]
        self.assertEqual(c["offset"], 0)
        self.assertEqual(c["size"], 1024)
        self.assertEqual(c["element_type"], "f16")
        self.assertEqual(c["shape"], ["128", "8"])


class TestOpenVINORealFormat(Base):
    """Regressions mirroring the actual OpenVINO contract (JSON configs, IR v11)."""

    def test_json_config_const_data_attrs_packed_expert(self):
        (self.dir / "config.json").write_text(json.dumps({
            "architectures": ["Qwen3_5MoeForConditionalGeneration"],
            "model_type": "qwen3_5_moe",
            "text_config": {"num_hidden_layers": 40, "num_experts": 256,
                            "num_experts_per_tok": 8},
        }))
        (self.dir / "openvino_config.json").write_text(json.dumps({"dtype": "int4_int8_int8"}))
        (self.dir / "decoder.bin").write_bytes(bytes(65536))
        (self.dir / "decoder.xml").write_text(
            '<net name="decoder" version="11"><layers>'
            '<layer id="0" name="model.language_model.layers.7.mlp.experts.down_proj.weight" type="Const" version="opset1">'
            '<data element_type="u4" shape="256,16,32" offset="0" size="65536"/>'
            '<output><port id="0" precision="U4"><dim>256</dim><dim>16</dim><dim>32</dim></port></output></layer>'
            '<layer id="5" name="Constant_290778" type="Const" version="opset1">'
            '<data element_type="f32" shape="" offset="0" size="4"/></layer>'
            '<layer id="9" name="inputs_embeds" type="Parameter" version="opset1">'
            '<data shape="1,?,2048" element_type="f32"/>'
            '<output><port id="0" precision="FP32">'
            '<dim>-1</dim><dim>-1</dim><dim>2048</dim></port></output></layer>'
            '</layers><edges/></net>'
        )
        inv = self.inv()
        self.assertEqual(inv["model_config"]["model_type"], "qwen3_5_moe")
        self.assertEqual(inv["model_config"]["architecture"], "Qwen3_5MoeForConditionalGeneration")
        self.assertEqual(inv["model_config"]["num_experts"], 256)
        self.assertIn("text_config", inv["model_config"]["nested"]["config.json"])
        self.assertEqual(inv["model_status"], "complete")
        g = self.graph("decoder.xml")
        weight = next(x for x in g["layers"] if x["name"].endswith("down_proj.weight"))
        # node id preserved separately from transformer block index parsed off the name
        self.assertEqual(weight["layer_id"], "0")
        self.assertEqual(weight["transformer_block_index"], 7)
        self.assertEqual(weight["role"], "routed_expert")
        self.assertTrue(any("no explicit expert index" in e for e in weight["role_evidence"]))
        self.assertTrue(any("num_experts=256" in e for e in weight["role_evidence"]))
        c = weight["const"]
        self.assertEqual(c["element_type"], "u4")
        self.assertEqual(c["shape"], ["256", "16", "32"])
        self.assertEqual(c["offset"], 0)
        self.assertEqual(c["size"], 65536)
        port = weight["ports"][0]
        self.assertEqual(port["dims"], ["256", "16", "32"])
        scalar = next(x for x in g["layers"] if x["op"] == "Const" and x["name"].startswith("Constant_"))
        self.assertEqual(scalar["const"]["shape"], [])
        self.assertNotIn("const", next(
            x for x in g["layers"] if x["op"] == "Parameter").keys())
        # bin accounting keyed by model-relative identity
        self.assertEqual(g["byte_accounting"]["weights_bin"], "decoder.bin")
        self.assertEqual(inv["binaries"][0]["relative"], "decoder.bin")

    def test_zero_size_const_is_valid_empty_tensor(self):
        self.make_config_only_json()
        (self.dir / "m.bin").write_bytes(b"\x00" * 64)
        (self.dir / "m.xml").write_text(
            '<net name="m" version="11"><layers>'
            '<layer id="0" name="constant_zero" type="Const" version="opset1">'
            '<data element_type="f32" shape="0" offset="64" size="0"/>'
            '<output><port id="0" precision="FP32"><dim>0</dim></port></output></layer>'
            "</layers></net>"
        )
        self.inv()
        g = self.graph("m.xml")
        c = g["layers"][0]["const"]
        self.assertTrue(c["empty_tensor"])
        self.assertTrue(c["valid"])
        self.assertEqual(g["status"], "ok")

    def test_dense_gate_proj_not_router_and_moe_gate_weight_is_router(self):
        self.make_config_only_json()
        (self.dir / "d.bin").write_bytes(b"\x00" * 8192)
        (self.dir / "d.xml").write_text(
            '<net name="d" version="11"><layers>'
            '<layer id="0" name="self.model.layers.5.mlp.gate_proj.weight" type="Const" version="opset1">'
            '<data element_type="i4" shape="2048,512" offset="0" size="1024"/></layer>'
            '<layer id="1" name="self.model.layers.5.mlp.experts.down_proj" type="Const" version="opset1">'
            '<data element_type="u4" shape="256,16,32" offset="2048" size="4096"/></layer>'
            '<layer id="2" name="self.model.layers.7.mlp.gate.weight" type="Const" version="opset1">'
            '<data element_type="i8" shape="256,2048" offset="1024" size="1024"/></layer>'
            '<layer id="3" name="mlp.experts/prim::ListConstruct/SequenceMark/Concat" type="Const" version="opset1">'
            '<data element_type="i32" shape="8" offset="6144" size="32"/></layer>'
            "</layers></net>"
        )
        g = self.graph("d.xml")
        roles = {l["name"]: l["role"] for l in g["layers"]}
        # dense gate_proj is NOT a router
        self.assertEqual(roles["self.model.layers.5.mlp.gate_proj.weight"], "unknown")
        # MoE router gate is the router
        self.assertEqual(roles["self.model.layers.7.mlp.gate.weight"], "router")
        # packed aggregate expert tensor, no index invented
        self.assertEqual(roles["self.model.layers.5.mlp.experts.down_proj"], "routed_expert")
        self.assertEqual(roles["mlp.experts/prim::ListConstruct/SequenceMark/Concat"], "unknown")
        fp = g["family_profile"]
        self.assertEqual(fp["routed_expert_layers"], 1)
        self.assertEqual(fp["router_layers"], 1)
        self.assertIn(fp["architecture_label"], ("moe_evidence", "expert_tensors_without_router_evidence"))

    def test_two_subdirs_weight_files_not_collapsed(self):
        a, b = self.dir / "a", self.dir / "b"
        a.mkdir()
        b.mkdir()
        (a / "weights.bin").write_bytes(b"\x00" * 4096)
        (b / "weights.bin").write_bytes(b"\x00" * 2048)
        body = (
            '<layers>'
            '<layer id="0" name="w0" type="Const" version="opset1">'
            '<data element_type="f32" shape="64" offset="0" size="1024"/></layer>'
            '<layer id="1" name="w1" type="Const" version="opset1">'
            '<data element_type="f32" shape="64" offset="0" size="1024"/></layer>'
            "</layers>"
        )
        (a / "m.xml").write_text('<net name="ma" version="11">%s</net>' % body)
        (b / "m.xml").write_text('<net name="mb" version="11">%s</net>' % body)
        self.make_config_only_json()
        inv = self.inv()
        bins = {x["relative"]: x for x in inv["binaries"]}
        self.assertEqual(sorted(bins), ["a/weights.bin", "b/weights.bin"])
        ga, gb = None, None
        for g in inv["graphs"]:
            acc = g["byte_accounting"]
            if g["relative"] == "a/m.xml":
                ga = acc
            if g["relative"] == "b/m.xml":
                gb = acc
        self.assertEqual(ga["weights_bin"], "a/weights.bin")
        self.assertEqual(gb["weights_bin"], "b/weights.bin")
        # 2048 declared within each graph = aliases in the SAME file counted once
        self.assertEqual(ga["declared_const_bytes_sum"], 2048)
        self.assertEqual(ga["referenced_unique_bytes"], 1024)
        self.assertEqual(ga["bin_file_size_bytes"], 4096)
        self.assertEqual(gb["bin_file_size_bytes"], 2048)
        self.assertEqual(bins["a/weights.bin"]["unknown_unreferenced_bytes"], 3072)
        self.assertEqual(bins["b/weights.bin"]["unknown_unreferenced_bytes"], 1024)

    def make_config_only_json(self, **extra):
        cfg = {"model_type": "unit_test_model", "architectures": ["TestModel"],
               "num_experts": 256}
        cfg.update(extra)
        (self.dir / "config.json").write_text(json.dumps(cfg))


class TestReviewFixes(Base):
    """Bounded regressions matching the fresh external review findings."""

    def test_const_without_data_is_invalid_without_exception(self):
        self.make_config_only_json()
        (self.dir / "m.bin").write_bytes(b"\x00" * 3000)
        (self.dir / "m.xml").write_text(
            '<net version="11"><layers><layer id="0" name="c0" type="Const"/></layers></net>'
        )
        inv = self.inv()  # must not raise
        g = self.graph("m.xml")
        self.assertEqual(g["status"], "invalid")
        c = g["layers"][0].get("const") or {}
        self.assertIn("missing_offset", c.get("errors", ["(no const record)"]))
        self.assertIn("missing_size", c.get("errors", ["(no const record)"]))
        # an invalid bare const contributes nothing to byte aggregates
        self.assertEqual(g["byte_accounting"]["declared_const_bytes_sum"], 0)
        self.assertEqual(g["byte_accounting"]["referenced_unique_bytes"], 0)

    def test_invalid_range_never_inflates_union(self):
        self.make_config_only_json()
        (self.dir / "m.bin").write_bytes(b"\x00" * 3000)
        layers = "\n".join(
            [
                const_layer(0, "c0", 0, 1000, "u8", "1000"),
                const_layer(1, "c1", 500, 1000, "u8", "1000"),
                const_layer(2, "c2", 1500, 2000, "u8", "2000"),
            ]
        )
        (self.dir / "m.xml").write_text(
            '<net version="11"><layers>%s</layers></net>' % layers
        )
        inv = self.inv()
        g = self.graph("m.xml")
        self.assertEqual(g["status"], "invalid")
        acc = g["byte_accounting"]
        # valid-only union [0,1500); the out-of-bounds [1500,3500) is excluded
        self.assertEqual(acc["referenced_unique_bytes"], 1500)
        self.assertEqual(acc["declared_const_bytes_sum"], 2000)
        self.assertEqual(acc["aliased_shared_bytes_saved"], 500)
        self.assertEqual(acc["referenced_intervals"], [[0, 1500]])
        self.assertEqual(acc["unreferenced_bytes"], 1500)
        b = next(x for x in inv["binaries"] if x["relative"] == "m.bin")
        self.assertEqual(b["referenced_unique_bytes"], 1500)
        self.assertTrue(b["accounting_consistent"])

    def test_auxiliary_json_is_not_a_model_config(self):
        self.make_config_only_json()
        (self.dir / "m.bin").write_bytes(b"\x00" * 3000)
        (self.dir / "m.xml").write_text(
            '<net version="11"><layers><layer id="0" name="input" type="Parameter"/></layers></net>'
        )
        # remove the real model config, keep auxiliary only
        (self.dir / "config.json").unlink()
        (self.dir / "tokenizer_config.json").write_text(json.dumps({"tokenizer_class": "X"}))
        inv = self.inv()
        self.assertNotEqual(inv["model_status"], "complete")
        self.assertIn("no actual model config", inv["model_status_reason"])
        # model_config must not borrow architecture/model_type from auxiliary JSON
        self.assertIsNone(inv["model_config"]["architecture"])
        self.assertIsNone(inv["model_config"]["model_type"])
        self.assertEqual(inv["configs"], [])
        self.assertEqual(len(inv["auxiliary_configs"]), 1)
        self.assertEqual(inv["auxiliary_configs"][0]["kind"], "json_auxiliary")        # aux + model config together: complete, aux stays separate
        (self.dir / "config.json").write_text(
            json.dumps({"model_type": "fixture_m", "architectures": ["FixtureModel"]})
        )
        inv2 = self.inv()
        self.assertEqual(inv2["model_status"], "complete")
        self.assertEqual([c["relative"] for c in inv2["configs"]], ["config.json"])
        self.assertEqual([c["relative"] for c in inv2["auxiliary_configs"]], ["tokenizer_config.json"])

    def test_missing_node_id_is_not_invented(self):
        self.make_config_only_json()
        (self.dir / "m.bin").write_bytes(b"\x00" * 64)
        (self.dir / "m.xml").write_text(
            '<net version="11"><layers>'
            '<layer name="input" type="Parameter"/>'
            '<layer id="7" name="w" type="Const"><data element_type="u8" shape="8" offset="0" size="8"/></layer>'
            "</layers></net>"
        )
        inv = self.inv()
        g = self.graph("m.xml")
        self.assertEqual(g["status"], "invalid")
        self.assertIsNone(g["layers"][0]["layer_id"])
        self.assertEqual(g["layers"][1]["layer_id"], "7")
        self.assertTrue(any("missing_node_id" in e for e in g["errors"]))
        self.assertEqual(g["layers"][1].get("transformer_block_index"), None)
        # const byte aggregate still valid-only and the file union stays in bounds
        self.assertEqual(g["byte_accounting"]["referenced_unique_bytes"], 8)


if __name__ == "__main__":
    unittest.main()
