import importlib.util
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "skill_portability.py"
spec = importlib.util.spec_from_file_location("skill_portability_self", MODULE)
port = importlib.util.module_from_spec(spec); spec.loader.exec_module(port)
class SelfBundleTests(unittest.TestCase):
    def test_self_audit_passes(self):
        report = port.audit_skill(ROOT)
        self.assertTrue(report["pass"], report)
if __name__ == "__main__": unittest.main()
