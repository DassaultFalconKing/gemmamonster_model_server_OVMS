import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class PortableSkillContract(unittest.TestCase):
    def test_self_contained_install_surface_exists(self):
        for name in ["README.md", "install.py", "install.sh", "install.ps1", "MANIFEST.json", "SHA256SUMS"]:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_core_docs_do_not_require_origin_repository(self):
        text = "\n".join((ROOT / n).read_text(encoding="utf-8") for n in ["SKILL.md", "README.md", "INSTALL.md"] if (ROOT/n).exists())
        self.assertNotIn("DassaultFalconKing/gemmamonster_model_server_OVMS", text)
        self.assertNotIn("--branch skills/autonomous-test-fix-retest", text)

    def test_manifest_lists_every_payload_file(self):
        manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
        listed = set(manifest["files"])
        actual = {str(p.relative_to(ROOT)).replace("\\", "/") for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
        self.assertEqual(listed, actual)

    def test_skill_frontmatter_is_portable(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"^---\nname: autonomous-test-fix-retest\n")
        self.assertNotRegex(text, r"(?:[A-Za-z]:\\|/home/|/Users/)")

if __name__ == "__main__":
    unittest.main()
