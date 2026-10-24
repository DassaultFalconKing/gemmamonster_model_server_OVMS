"""CLI compatibility contract tests; exercise the REAL PackV2 pipeline module.

Run in checked out repository: python -m unittest discover -s tests/cib2 -p 'test_packv2_fast*.py' -v
"""
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts' / 'cib2'))
try:
    import packv2_pipeline as v2
    import trace_profile as tp
    from test_packv2_pipeline import identity, trace, write_native_pack, KEY
except ImportError:
    v2 = None


@unittest.skipIf(v2 is None, 'Requires existing repo packv2_pipeline, trace_profile and base synthetic test')
class ActualPipelineCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        bundle = self.root / 'bundle.json'
        bundle.write_text(json.dumps(tp.derive(trace(), identity())), encoding='utf-8')
        self.plan_dir = self.root / 'plans'
        v2.make_plans(bundle, self.plan_dir, 'frequency', seed=0)
        self.native = self.root / 'native'
        self.native.mkdir()
        write_native_pack(self.native / f'otd-{KEY}.pack', [1, 0])
        self.out = self.root / 'out'
        self.out.mkdir()

    def run_cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            rc = v2.main(list(args))
        self.assertIsInstance(rc, int)
        lines = stdout.getvalue().splitlines()
        self.assertEqual(len(lines), 1 if rc == 0 else 0, stderr.getvalue())
        return rc, json.loads(lines[0]) if lines else None, stderr.getvalue()

    def test_drop_in_seal_then_full_verify_and_identity(self):
        old_args = ['seal', '--plans-dir', str(self.plan_dir), '--native-packs', str(self.native),
                    '--output-root', str(self.out)]
        rc, obj, err = self.run_cli(*old_args, '--workers', '1', '--progress', 'jsonl')
        self.assertEqual(rc, 0)
        self.assertEqual(obj['status'], 'VERIFIED_OFFLINE')
        self.assertEqual(obj['runtime_acceptance'], 'NO')
        self.assertEqual(obj['verification_mode'], 'fast')
        self.assertFalse(obj['payload_integrity_checked'])
        self.assertIn('"event": "pack_done"', err)
        active = json.loads((self.out/'active.v2.json').read_text())
        self.assertEqual(active['generation_sha256'], obj['generation'])
        generation_dir = Path(obj['pack_dir'])
        rc, full, _ = self.run_cli('verify', '--generation-dir', str(generation_dir), '--progress', 'off')
        self.assertEqual(rc, 0)
        self.assertTrue(full['payload_integrity_checked'])
        self.assertEqual(full['verification_mode'], 'full')
        manifest = (generation_dir/'manifest.v2.json').read_bytes()
        # Reseal same content with workers=4; native generation identity stays unchanged.
        rc, again, _ = self.run_cli(*old_args, '--workers', '4', '--progress', 'off')
        self.assertEqual(rc, 0)
        self.assertEqual(obj['generation'], again['generation'])
        self.assertEqual(manifest, (generation_dir/'manifest.v2.json').read_bytes())
        self.assertEqual(set(p.name for p in generation_dir.iterdir()), {'manifest.v2.json', f'otd-{KEY}.pack'})

    def test_real_cli_rejects_pre_corruption_if_full_requested(self):
        pack = self.native / f'otd-{KEY}.pack'
        with pack.open('r+b') as fh:
            fh.seek(8192)
            old = fh.read(1)
            fh.seek(8192)
            fh.write(bytes([old[0] ^ 1]))
        rc, obj, err = self.run_cli('seal', '--plans-dir', str(self.plan_dir),
            '--native-packs', str(self.native), '--output-root', str(self.out),
            '--post-seal-verify', 'full', '--progress', 'off')
        self.assertEqual(rc, 2)
        self.assertIsNone(obj)
        self.assertIn('REJECTED', err)
        self.assertFalse((self.out/'active.v2.json').exists())
        self.assertFalse(list(self.out.glob('.generation-*')))

if __name__ == '__main__':
    unittest.main()
