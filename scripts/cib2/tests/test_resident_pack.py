import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

try:
    from scripts.cib2 import resident_pack as rp
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import resident_pack as rp


class ResidentPackTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.xml = self.root / "model.xml"
        self.bin = self.root / "model.bin"
        self.bin.write_bytes(b"0123456789ABCDEFGHIJKLMNOPQRST")
        self.xml.write_text('''<net><layers>
          <layer id="1" name="routed" type="Const"><data offset="0" size="4" element_type="u8"/></layer>
          <layer id="2" name="shared" type="Const"><data offset="4" size="6" element_type="u8"/></layer>
          <layer id="3" name="embed" type="Const"><data offset="10" size="8" element_type="u8"/></layer>
          <layer id="4" name="moe" type="MOECompressed"/><layer id="5" name="dense" type="MatMul"/>
          </layers><edges>
          <edge from-layer="1" to-layer="4" to-port="3"/>
          <edge from-layer="2" to-layer="4" to-port="12"/>
          <edge from-layer="3" to-layer="5" to-port="1"/>
          </edges></net>''', encoding="utf-8")
        self.inv = rp.inventory(self.xml, self.bin)
        self.inv_path = self.root / "inventory.json"
        self.inv_path.write_text(json.dumps(self.inv))

    def select(self, ids):
        p = self.root / "selection.json"
        p.write_text(json.dumps({"schema": rp.SELECT_SCHEMA,
                                 "source_xml_sha256": self.inv["source_xml_sha256"],
                                 "source_bin_sha256": self.inv["source_bin_sha256"],
                                 "selections": [{"layer_id": i, "evidence": "Reviewed GPU compiled graph 2026-10-24"} for i in ids]}))
        return p

    def test_roles_and_unknown(self):
        self.assertEqual([x["role"] for x in self.inv["constants"]], ["routed", "shared", "unknown"])

    def test_build_verify_source_parity(self):
        target = self.root / "generation"
        built = rp.build(self.inv_path, self.select([2, 3]), self.bin, target)
        self.assertEqual(built["consumption"], "OFFLINE_ONLY")
        self.assertEqual(rp.verify(target, self.bin)["record_count"], 2)
        with (target / "resident.pack").open("rb") as f:
            for rec in built["records"]:
                f.seek(rec["pack_offset"])
                self.assertEqual(f.read(rec["size"]), self.bin.read_bytes()[rec["source_offset"]:rec["source_offset"] + rec["size"]])

    def test_routed_never_packed(self):
        with self.assertRaisesRegex(rp.ResidentError, "routed"):
            rp.build(self.inv_path, self.select([1]), self.bin, self.root / "generation")

    def test_stale_source_fails_closed(self):
        self.bin.write_bytes(self.bin.read_bytes() + b"!")
        with self.assertRaisesRegex(rp.ResidentError, "changed"):
            rp.build(self.inv_path, self.select([2]), self.bin, self.root / "generation")

    def test_detect_corrupt_pack(self):
        target = self.root / "generation"
        rp.build(self.inv_path, self.select([2]), self.bin, target)
        with (target / "resident.pack").open("r+b") as f:
            f.write(b"X")
        with self.assertRaisesRegex(rp.ResidentError, "digest"):
            rp.verify(target)

    def test_existing_generation_fail(self):
        target = self.root / "generation"
        rp.build(self.inv_path, self.select([2]), self.bin, target)
        with self.assertRaisesRegex(rp.ResidentError, "exists"):
            rp.build(self.inv_path, self.select([2]), self.bin, target)

    def test_missing_review_evidence_fails(self):
        p = self.select([3]); obj = json.loads(p.read_text()); obj["selections"][0]["evidence"] = "ok"; p.write_text(json.dumps(obj))
        with self.assertRaisesRegex(rp.ResidentError, "evidence"):
            rp.build(self.inv_path, p, self.bin, self.root / "generation")


if __name__ == "__main__":
    unittest.main()
