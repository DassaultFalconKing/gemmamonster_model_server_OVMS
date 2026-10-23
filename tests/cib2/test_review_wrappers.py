"""Independent review regressions for inventory output identity and expected hashes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).parents[2]
def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts/cib2'/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
inventory=load('inventory_review','run_family_inventory.py')
lock=load('lock_expected_review','source_lock.py')


class ReviewWrapperCases(unittest.TestCase):
    def test_slug_collision_cannot_overwrite_first_model_map(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'models';out=Path(directory)/'maps';root.mkdir()
            for name,arch in [('a b','FirstModel'),('a_b','SecondModel')]:
                model=root/name;model.mkdir()
                (model/'config.json').write_text(json.dumps({'model_type':'fixture','architectures':[arch]}))
                (model/'m.xml').write_text('<net version="11"><layers><layer id="0" name="input" type="Parameter"/></layers></net>')
            result=inventory.run(root,out)
            files=[m['private_full_map'] for m in result['models']]
            self.assertEqual(len(set(files)),2)
            self.assertEqual([json.loads(Path(f).read_text())['model_config']['architecture'] for f in files],['FirstModel','SecondModel'])

    def test_expected_digest_unknown_name_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'ovms.exe';file.write_bytes(b'MZ-test')
            with self.assertRaises(lock.ComponentError):
                lock.build_manifest([('ovms',str(file))],expected_digests={'ovsm':'0'*64})

    def test_expected_digest_case_matches_component_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'ovms.exe';file.write_bytes(b'MZ-test')
            expected=hashlib.sha256(file.read_bytes()).hexdigest()
            result=lock.build_manifest([('ovms',str(file))],expected_digests={'OVMS':expected})
            self.assertTrue(result['components'][0]['digest_verification']['match'])


if __name__=='__main__':unittest.main(verbosity=2)
