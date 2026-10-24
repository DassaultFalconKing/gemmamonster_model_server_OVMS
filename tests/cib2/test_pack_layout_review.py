"""Independent coordinator regressions for offline layout handoff safety."""
import copy
import io
from contextlib import redirect_stderr
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).parents[2]
sys.path.insert(0,str(ROOT/'scripts/cib2'))
import pack_layout as pl


class IndependentHandoffTest(unittest.TestCase):
    def layout(self):return pl.build_layout(None,'identity',expert_count=4)

    def test_refuses_forged_pack_or_profile_acceptance(self):
        for key in ('pack_acceptance','profile_acceptance'):
            layout=self.layout();layout[key]='YES'
            with self.subTest(key=key),self.assertRaises(pl.LayoutError):pl.validate_layout(layout)

    def test_refuses_modified_runtime_policy(self):
        layout=self.layout();layout['policy']['prefetch']='ON'
        with self.assertRaises(pl.LayoutError):pl.validate_layout(layout)

    def test_unprofiled_identity_cannot_gain_foreign_scope(self):
        layout=self.layout();layout['scope']={'checkpoint_sha':'foreign'}
        with self.assertRaises(pl.LayoutError):pl.validate_layout(layout)

    def test_profiled_layout_requires_all_scope_keys(self):
        data=(ROOT/'tests/cib2/fixtures/pack_layout/frequency_ties.json').read_bytes()
        layout=pl.build_layout(pl.load_profile_bytes(data),'frequency',source_sha256=pl.profile_sha256(data))
        del layout['scope']['quant_profile_sha']
        with self.assertRaises(pl.LayoutError):pl.validate_layout(layout)

    def test_writer_refuses_weight_file_output(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'weights.bin';target.write_bytes(b'ORIGINAL')
            with self.assertRaises(pl.LayoutError):pl.write_layout(str(target),self.layout())
            self.assertEqual(target.read_bytes(),b'ORIGINAL')

    def test_cli_cannot_overwrite_its_source_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'profile.json'
            data=(ROOT/'tests/cib2/fixtures/pack_layout/frequency_ties.json').read_bytes();target.write_bytes(data)
            with redirect_stderr(io.StringIO()):code=pl.main(['--profile',str(target),'--output',str(target),'--strategy','frequency'])
            self.assertEqual(code,2);self.assertEqual(target.read_bytes(),data)


if __name__=='__main__':unittest.main()
