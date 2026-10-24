# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "cib2"))
import model_layout_audit as audit


class ModelLayoutAuditTest(unittest.TestCase):
    def setUp(self):
        self.q = {"model_type": "qwen3_5_moe",
                  "text_config": {"model_type": "qwen3_5_moe_text", "num_hidden_layers": 40,
                  "hidden_size": 2048, "num_experts": 256, "num_experts_per_tok": 8,
                  "moe_intermediate_size": 512, "shared_expert_intermediate_size": 512,
                  "layer_types": ["linear_attention"] * 30 + ["full_attention"] * 10}}

    def test_qwen_and_ornith_alias_does_not_reclassify(self):
        item = audit.inspect_config(self.q, "Ornith-1.0-35B-A3B")
        self.assertEqual(item["routed_experts_per_moe_layer"], 256)
        self.assertEqual(item["status"], "MOE_CANDIDATE_COMPILED_GATE_REQUIRED")
        self.assertEqual(item["nine_slice_compiled_eligibility"], "NOT_RUN")

    def test_minicpm_wrapper(self):
        a = copy.deepcopy(self.q)
        a["model_type"] = "minicpmv4_7"
        a["vision_config"] = {"num_hidden_layers": 27}
        self.assertEqual(audit.inspect_config(a)["vision_encoder_layers"], 27)

    def test_dense_rejected_for_moe_packing(self):
        a = copy.deepcopy(self.q)
        a["model_type"] = "qwen3_5"
        a["text_config"] = {"model_type": "qwen3_5_text", "num_hidden_layers": 64,
                            "hidden_size": 5120, "num_experts": 0}
        self.assertEqual(audit.inspect_config(a)["status"], "DENSE_NO_ROUTED_MOE")

    def test_gemma_moe(self):
        a = {"model_type": "gemma4", "text_config": {
            "model_type": "gemma4_text", "enable_moe_block": True,
            "num_hidden_layers": 30, "hidden_size": 2816,
            "num_experts": 128, "top_k_experts": 8, "moe_intermediate_size": 704}}
        self.assertEqual(audit.inspect_config(a)["routed_experts_per_moe_layer"], 128)

    def test_contradictory_wrapper_rejected(self):
        a = copy.deepcopy(self.q)
        a["model_type"] = "gemma4"
        with self.assertRaises(audit.ModelLayoutError):
            audit.inspect_config(a)

    def test_invalid_or_ambiguous_fail_closed(self):
        for change in [
            {"num_experts_per_tok": 257},
            {"num_hidden_layers": True},
            {"layer_types": ["linear_attention"]},
            {"moe_intermediate_size": -1},
        ]:
            a = copy.deepcopy(self.q)
            a["text_config"].update(change)
            with self.subTest(change=change), self.assertRaises(audit.ModelLayoutError):
                audit.inspect_config(a)

    def test_duplicate_and_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.json"
            p.write_text('{"text_config": {}, "text_config": {}}')
            with self.assertRaises(audit.ModelLayoutError):
                audit.inspect_file(p)
            p.write_text(json.dumps(self.q))
            self.assertEqual(audit.inspect_file(p)["num_hidden_layers"], 40)
            link = Path(d) / "link.json"
            try:
                link.symlink_to(p)
            except OSError:
                return
            with self.assertRaises(audit.ModelLayoutError):
                audit.inspect_file(link)


if __name__ == "__main__":
    unittest.main()
