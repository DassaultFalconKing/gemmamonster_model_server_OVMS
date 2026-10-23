"""Independent guard: a nonempty caller assertion is not runtime/build evidence."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('lock_provenance_acceptance',Path(__file__).parents[2]/'scripts/cib2/source_lock.py')
lock=importlib.util.module_from_spec(spec);spec.loader.exec_module(lock)


class ProvenanceAssertionTest(unittest.TestCase):
    def check_forged(self,category,flag):
        with tempfile.TemporaryDirectory() as directory:
            dll=Path(directory)/'runtime.dll';dll.write_bytes(b'MZ-test-only')
            manifest=lock.build_manifest([('runtime',str(dll))])
            manifest['provenance'][category]['status']='VERIFIED'
            manifest['provenance'][category]['evidence']={'assertion':'Trust the caller; no process or build receipt was verified'}
            manifest['components'][0]['provenance'][category]='VERIFIED'
            with self.assertRaises(lock.ManifestError):
                lock.validate_manifest(manifest,**{flag:True})

    def test_forged_nonempty_module_evidence_cannot_pass_strict(self):
        self.check_forged('loaded_dll_evidence','require_loaded_evidence')

    def test_forged_nonempty_source_receipt_cannot_pass_strict(self):
        self.check_forged('source_build_association','require_source_build_evidence')


if __name__=='__main__':unittest.main(verbosity=2)
