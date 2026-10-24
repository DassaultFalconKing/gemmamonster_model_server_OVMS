# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""End-to-end synthetic test for trace -> profile -> placement -> native pack -> V2."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "cib2"))
import trace_profile as tp
import packv2_pipeline as v2
import verify_pack_v1 as v1

ONE = "1" * 64
TWO = "2" * 64
THREE = "3" * 64
KEY = "00000000000000ab"


def identity():
    return {
        "schema": "cib2.trace_identity.v1", "model_key": "test_model",
        "checkpoint_sha": ONE, "export_sha": TWO, "quant_profile_sha": THREE,
        "profile_key": "test_run", "layers": [{
            "trace_layer": 0, "logical_layer_id": 7,
            "compiled_layer_key": "graph.layer.7", "pack_layer_key": KEY
        }]
    }


def trace():
    return (b"# moe_otd_trace v1\n"
            b"L,0,123abc,987abc,1,2,1\n"
            b"C,0,10,0,S,2,overflow,0 1\n"
            b"C,1,20,0,S,1,ok,0\n"
            b"E,1,30,0,0,0,0,-1,16,1,2000,0,100\n"
            b"C,2,40,0,O,1,ok,1\n"
            b"E,2,41,0,1,0,0,0,16,1,6000,0,100\n"
            b"C,3,50,0,O,1,ok,0\n"
            b"E,3,51,0,0,0,1,-1,0,0,0,0,0\n"
            b"# end,calls=4,experts=3,incomplete_calls=0,incomplete_experts=0\n")


def write_native_pack(path, placement):
    n = 2
    sizes = [1] * 9
    offsets, payload, stride, checksums_at, records_at = v1.canonical_layout(sizes, n)
    header = v1.HEADER.pack(v1.MAGIC, 1, v1.ALIGNMENT, int(KEY, 16), n, stride,
                            records_at, v1.ALIGNMENT, checksums_at,
                            *sizes, *offsets, 0)
    header = header[:-8] + struct.pack("<Q", v1.fnv_update(v1.FNV_OFFSET, header))
    data = bytearray(records_at + n * stride)
    data[:len(header)] = header
    data[v1.ALIGNMENT:v1.ALIGNMENT + n * 4] = struct.pack("<2I", *placement)
    checksums = []
    for eid in range(n):
        record = bytearray(payload)
        for offset in offsets:
            record[offset] = eid + 1
        dest = records_at + placement[eid] * stride
        data[dest:dest + payload] = record
        checksums.append(v1.fnv_update(v1.FNV_OFFSET, record))
    data[checksums_at:checksums_at + n * 8] = struct.pack("<2Q", *checksums)
    path.write_bytes(data)


class EndToEnd(unittest.TestCase):
    def test_native_trace_yields_scoped_real_profile(self):
        b = tp.derive(trace(), identity())
        self.assertEqual(b["runtime_acceptance"], "NO")
        self.assertFalse(b["profiles"][0]["profile"]["synthetic"])
        evidence = b["profiles"][0]["profile"]["experts"]
        self.assertEqual([(e["logical_expert_id"], e["miss_count"]) for e in evidence], [(0, 1), (1, 1)])
        self.assertEqual([e["read_cost_us"] for e in evidence], [2.0, 6.0])

    def test_trace_requires_real_complete_footer(self):
        with self.assertRaisesRegex(tp.TraceError, "end|incomplete"):
            tp.derive(trace().split(b"# end,")[0], identity())
        with self.assertRaises(tp.TraceError):
            tp.derive(trace().replace(b"incomplete_calls=0", b"incomplete_calls=1"), identity())
        with self.assertRaises(tp.TraceError):
            tp.derive(trace() + b"garbage\n", identity())

    def test_trace_refuses_fabricated_expert_event(self):
        changed = trace().replace(b"E,2,41,0,1,0", b"E,2,41,0,0,0")
        with self.assertRaisesRegex(tp.TraceError, "orphan"):
            tp.derive(changed, identity())

    def test_identity_mapping_required(self):
        m = identity()
        m["layers"][0]["trace_layer"] = 4
        with self.assertRaises(tp.TraceError):
            tp.derive(trace(), m)

    def test_pack_placement_binary_and_v2_seal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bundle = root / "bundle.json"
            bundle.write_text(json.dumps(tp.derive(trace(), identity())), encoding="utf-8")
            plans = root / "plans"
            obj = v2.make_plans(bundle, plans, "frequency", seed=0)
            self.assertEqual(obj["layers"][0]["placement"], [1, 0])
            self.assertEqual(obj["layers"][0]["strategy_effective"], "frequency")
            self.assertEqual(len((plans / ("otd-" + KEY + ".placement")).read_bytes()), 40)
            self.assertEqual(len((plans / ("otd-" + KEY + ".residency")).read_bytes()), 34)
            self.assertEqual(obj["layers"][0]["resident_tiers"], [1, 2])
            native = root / "native"
            native.mkdir()
            write_native_pack(native / ("otd-" + KEY + ".pack"), [1, 0])
            self.assertEqual(v1.inspect_pack(native / ("otd-" + KEY + ".pack"))["status"], "OK")
            generations = root / "generations"
            generations.mkdir()
            result = v2.seal_generation(plans, native, generations)
            self.assertEqual(v2.verify_generation(result)["status"], "VERIFIED_OFFLINE")
            self.assertTrue((generations / "active.v2.json").is_file())
            same = v2.seal_generation(plans, native, generations)
            self.assertEqual(result, same)
            self.assertEqual(len([x for x in generations.iterdir() if x.is_dir()]), 1)
            # Manifest does not change the original source model or native staging file.
            with (result / ("otd-" + KEY + ".pack")).open("r+b") as stream:
                stream.seek(-v1.ALIGNMENT + 100, 2)
                b = stream.read(1)
                stream.seek(-v1.ALIGNMENT + 100, 2)
                stream.write(bytes([b[0] ^ 0x01]))
            with self.assertRaises((v2.GenerationError, v1.PackError)):
                v2.verify_generation(result)

    def test_seal_rejects_wrong_native_placement(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bundle = root / "bundle.json"
            bundle.write_text(json.dumps(tp.derive(trace(), identity())), encoding="utf-8")
            plans = root / "plans"
            v2.make_plans(bundle, plans, "frequency")
            native = root / "native"
            native.mkdir()
            write_native_pack(native / ("otd-" + KEY + ".pack"), [0, 1])
            generations = root / "gens"
            generations.mkdir()
            with self.assertRaisesRegex(v2.GenerationError, "placement differs"):
                v2.seal_generation(plans, native, generations)
            self.assertFalse((generations / "active.v2.json").exists())

    def test_native_placement_checksum_detects_mutation(self):
        valid = v2._native_placement(KEY, [1, 0])
        self.assertEqual(valid[:8], b"OTDPLACE")
        bad = bytearray(valid)
        bad[-1] ^= 0x01
        self.assertNotEqual(v1.fnv_update(v1.FNV_OFFSET, bad[:-8]),
                            struct.unpack("<Q", bad[-8:])[0])

    def test_bad_bundle_rejected_without_partial_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            b = tp.derive(trace(), identity())
            b["profiles"][0]["profile"]["synthetic"] = True
            raw = root / "bundle.json"
            raw.write_text(json.dumps(b), encoding="utf-8")
            with self.assertRaises(ValueError):
                v2.make_plans(raw, root / "plans", "frequency")
            self.assertFalse((root / "plans").exists())


if __name__ == "__main__":
    unittest.main()
