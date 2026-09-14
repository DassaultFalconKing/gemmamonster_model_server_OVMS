import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "skill_portability.py"
spec = importlib.util.spec_from_file_location("skill_portability", MODULE)
port = importlib.util.module_from_spec(spec)
spec.loader.exec_module(port)

class SkillPortabilityTests(unittest.TestCase):
    def make_skill(self, root: Path, *, hard_bound=False):
        root.mkdir(parents=True)
        (root / "SKILL.md").write_text("---\nname: demo-skill\ndescription: Use when testing portability.\n---\n\n# Demo\n", encoding="utf-8")
        readme = "# Demo\n"
        install = "# Install\n"
        if hard_bound:
            install += "git clone --branch feature/demo https://github.com/example/private-layout.git /tmp/source\n"
        (root / "README.md").write_text(readme, encoding="utf-8")
        (root / "INSTALL.md").write_text(install, encoding="utf-8")
        (root / "install.py").write_text("print(\"install\")\n", encoding="utf-8")
        (root / "install.sh").write_text("#!/usr/bin/env sh\n", encoding="utf-8")
        (root / "install.ps1").write_text("param()\n", encoding="utf-8")

    def test_audit_detects_origin_repo_dependency(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "demo-skill"
            self.make_skill(root, hard_bound=True)
            report = port.audit_skill(root)
            self.assertFalse(report["pass"])
            self.assertIn("ORIGIN_REPOSITORY_REQUIRED", {i["code"] for i in report["issues"]})

    def test_refresh_metadata_then_audit_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "demo-skill"
            self.make_skill(root)
            port.refresh_metadata(root, version="1.2.3")
            report = port.audit_skill(root)
            self.assertTrue(report["pass"], report)
            manifest = json.loads((root / "MANIFEST.json").read_text())
            self.assertEqual(manifest["version"], "1.2.3")

    def test_deterministic_zip_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "demo-skill"
            self.make_skill(root)
            port.refresh_metadata(root, version="1.0.0")
            a = Path(td) / "a.zip"
            b = Path(td) / "b.zip"
            port.package_skill(root, a)
            port.package_skill(root, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with zipfile.ZipFile(a) as z:
                self.assertIn("demo-skill/SKILL.md", z.namelist())
                self.assertIn("demo-skill/MANIFEST.json", z.namelist())

    def test_pack_excludes_transient_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "demo-skill"
            self.make_skill(root)
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "x.pyc").write_bytes(b"x")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("x")
            port.refresh_metadata(root, version="1")
            out = Path(td) / "x.zip"
            port.package_skill(root, out)
            with zipfile.ZipFile(out) as z:
                names = z.namelist()
            self.assertFalse(any("__pycache__" in n or "/.git/" in n or n.endswith(".pyc") for n in names))

if __name__ == "__main__":
    unittest.main()
