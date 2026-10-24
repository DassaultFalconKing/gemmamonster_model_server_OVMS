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

    def test_bound_profile_bytes_reject_forged_source_sha(self):
        data=(ROOT/'tests/cib2/fixtures/pack_layout/frequency_ties.json').read_bytes()
        profile=pl.load_profile_bytes(data)
        self.assertEqual(profile.source_sha256,pl.profile_sha256(data))
        with self.assertRaisesRegex(pl.LayoutError,'does not match the exact profile bytes'):
            pl.build_layout(profile,'frequency',source_sha256='0'*64)

    def test_cli_hardlink_alias_cannot_overwrite_source_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'profile.json'
            alias=Path(folder)/'alias.json'
            data=(ROOT/'tests/cib2/fixtures/pack_layout/frequency_ties.json').read_bytes()
            source.write_bytes(data)
            try:
                alias.hardlink_to(source)
            except OSError:
                self.skipTest('hardlinks unavailable on this filesystem')
            with redirect_stderr(io.StringIO()):
                code=pl.main(['--profile',str(source),'--output',str(alias),'--strategy','frequency'])
            self.assertEqual(code,2)
            self.assertEqual(source.read_bytes(),data)

    def test_validate_layout_binds_synthetic_label_to_provenance(self):
        data=(ROOT/'tests/cib2/fixtures/pack_layout/frequency_ties.json').read_bytes()
        layout=pl.build_layout(pl.load_profile_bytes(data),'frequency',source_sha256=pl.profile_sha256(data))
        stripped=copy.deepcopy(layout)
        stripped['source_profile']['synthetic']=False
        with self.assertRaisesRegex(pl.LayoutError,'synthetic'):
            pl.validate_layout(stripped)
        flipped=copy.deepcopy(layout)
        flipped['source_profile']['provenance_source']='offline_trace_derived'
        with self.assertRaisesRegex(pl.LayoutError,'synthetic'):
            pl.validate_layout(flipped)
        no_warning=copy.deepcopy(layout)
        no_warning['warnings']=[w for w in no_warning['warnings'] if 'synthetic profile fixture' not in w]
        with self.assertRaisesRegex(pl.LayoutError,'synthetic'):
            pl.validate_layout(no_warning)


if __name__=='__main__':unittest.main()
