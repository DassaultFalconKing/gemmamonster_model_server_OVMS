"""Offline runner acceptance tests; no compiler, model, or real process termination.

Usage: python test_r1_runner.py --runner <prepared-run.py>
"""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

def load_runner(path):
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(path.resolve().parent))
    spec=importlib.util.spec_from_file_location('prepared_r1_runner',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = load_runner(Path(__file__).resolve().parents[1]/'r1_runner.py')
NAMES = (
    'empty_min0_epsilon', 'empty_min0_space', 'empty_min0_tab', 'empty_min0_lf',
    'closed_min1_unsatisfiable', 'open_min1_parameter', 'open_min1_empty',
    'open_min1_space', 'declared_min1_parameter', 'declared_min1_empty',
    'required_declared_unset_max_parameter', 'required_declared_unset_max_empty',
    'explicit_max0_epsilon', 'explicit_max0_parameter', 'explicit_max0_space',
    'required_max0_unsatisfiable', 'required_empty_props_empty_OPEN',
    'required_empty_props_spaces_OPEN', 'required_undeclared_open_empty_OPEN',
    'required_undeclared_open_parameter', 'nested_empty_braces', 'json_empty_braces',
    'json_empty_spaced_braces', 'json_no_bare_epsilon', 'json_closed_min1_unsatisfiable',
    'json_declared_min1_empty', 'json_declared_min1_value', 'json_required_empty_props_OPEN',
)
COMPILE_ERRORS = {'closed_min1_unsatisfiable', 'required_max0_unsatisfiable', 'json_closed_min1_unsatisfiable'}
ACCEPTED = {'empty_min0_epsilon', 'open_min1_parameter', 'declared_min1_parameter',
            'required_declared_unset_max_parameter', 'explicit_max0_epsilon',
            'required_undeclared_open_parameter', 'nested_empty_braces',
            'json_empty_braces', 'json_empty_spaced_braces', 'json_declared_min1_value'}

def matrix_log():
    lines = []
    for name in NAMES:
        opened = name.endswith('_OPEN')
        compile_error = name in COMPILE_ERRORS
        lines.append(f"ROW {name} status={'EXPECTED_FAIL_OPEN' if opened else 'PASS'} "
                     f"compile_error={int(compile_error)} accepted={int(opened or name in ACCEPTED)} "
                     f"desired={int(name in ACCEPTED)} phase={'schema_conversion' if compile_error else 'matching'} "
                     f"schema_specific_error={int(compile_error)}")
    return '\n'.join(lines) + '\nSUMMARY rows=28 passed=24 open=4 unexpected=0 ACCEPTED=NO\n'

class RunnerTests(unittest.TestCase):
    def test_preflight_rejects_cwd_relative_external_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'snapshot').mkdir(); (root/'native').mkdir()
            files=[]
            for name,source in [('run.py',Path(RUNNER.__file__)),('r1_gate.py',Path(RUNNER.validate_matrix_log.__code__.co_filename))]:
                target=root/name; target.write_bytes(source.read_bytes())
                files.append({'path':name,'bytes':target.stat().st_size,
                              'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
            (root/'fixture.dll').write_bytes(b'fixture')
            inputs={'files':files,'external_runtime_files':[{'path':'fixture.dll','sha256':hashlib.sha256(b'fixture').hexdigest()}],
                    'external_tools':[],'runtime_root':str(root),
                    'runtime_python_home':str(root),'runtime_python_path':str(root)}
            (root/'INPUTS.json').write_text(json.dumps(inputs))
            with contextlib.chdir(root),patch.object(RUNNER,'ROOT',root):
                with self.assertRaisesRegex(RuntimeError,'absolute'):
                    RUNNER.preflight()

    def test_preflight_binds_executing_runner_not_just_a_sealed_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'snapshot').mkdir(); (root/'native').mkdir()
            actual=Path(RUNNER.__file__)
            files=[]
            for name,source in [('run.py',actual),('r1_gate.py',Path(RUNNER.validate_matrix_log.__code__.co_filename))]:
                target=root/name; target.write_bytes(source.read_bytes())
                files.append({'path':name,'bytes':target.stat().st_size,
                              'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
            inputs={'files':files,'external_runtime_files':[],'external_tools':[],
                    'runtime_python_home':'fixture','runtime_python_path':'fixture'}
            (root/'INPUTS.json').write_text(json.dumps(inputs))
            unsealed=root/'changed-executing-runner.py'
            unsealed.write_bytes(actual.read_bytes()+b'\n# unsealed drift\n')
            with patch.object(RUNNER,'ROOT',root), patch.object(RUNNER,'__file__',str(unsealed)):
                with self.assertRaisesRegex(RuntimeError,'Executing runner'):
                    RUNNER.preflight()

    def invoke(self, log, original_log=None, drift_manifest=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def fake_stage(out, name, argv, timeout, env):
                native = 'SUMMARY failures=0\nACTUAL_MASK lazy=0 whitespace_tokens=425 allowed=0\nACTUAL_MASK lazy=1 whitespace_tokens=425 allowed=0\n'
                return {'exit_code': 2 if name == 'matrix' else 0}, log if name == 'matrix' else (original_log if original_log is not None else native)
            inputs = {'candidate_sha': 'test-fixture', 'runtime_root': str(root),
                      'runtime_python_home':str(root/'python'), 'runtime_python_path':str(root/'site-packages')}
            (root/'INPUTS.json').write_text('{}')
            calls=0
            def preflight():
                nonlocal calls
                calls+=1
                if drift_manifest and calls>1:
                    (root/'INPUTS.json').write_text('{"drift":true}')
                    raise RuntimeError('Fixture manifest drift')
                return inputs
            with patch.object(RUNNER, 'ROOT', root), patch.object(RUNNER, 'preflight', side_effect=preflight), \
                 patch.object(RUNNER, 'commands', return_value=[(n, ['NOT_EXECUTED'], 1) for n in ('configure','build','matrix','original')]), \
                 patch.object(RUNNER, 'stage', side_effect=fake_stage), \
                 patch.object(sys, 'argv', ['run.py','--execute-resource-slot']), contextlib.redirect_stdout(io.StringIO()):
                code = RUNNER.main()
            result = json.loads(next((root/'runs').glob('*/RESULTS.json')).read_text())
            return code, result

    def test_valid_known_open_matrix_remains_open_not_accepted(self):
        code, result = self.invoke(matrix_log())
        self.assertEqual(code, 2)
        self.assertEqual(result['status'], 'OPEN_EXPECTED_FAILURES')
        self.assertFalse(result['accepted'])

    def test_substituted_test_name_fails_even_with_same_counts(self):
        code, _ = self.invoke(matrix_log().replace('empty_min0_tab', 'unrelated_case'))
        self.assertEqual(code, 1)

    def test_missing_row_fails(self):
        code, _ = self.invoke('\n'.join(matrix_log().splitlines()[1:]))
        self.assertEqual(code, 1)

    def test_duplicate_row_fails(self):
        code, _ = self.invoke(matrix_log()+matrix_log().splitlines()[0]+'\n')
        self.assertEqual(code, 1)

    def test_missing_summary_fails(self):
        code, _ = self.invoke('\n'.join(matrix_log().splitlines()[:-1]))
        self.assertEqual(code, 1)

    def test_inconsistent_summary_fails(self):
        code, _ = self.invoke(matrix_log().replace('passed=24', 'passed=28'))
        self.assertEqual(code, 1)

    def test_duplicate_summary_fails(self):
        code, _ = self.invoke(matrix_log()+'SUMMARY rows=28 passed=24 open=4 unexpected=0 ACCEPTED=NO\n')
        self.assertEqual(code, 1)

    def test_pass_label_does_not_hide_wrong_argument_acceptance(self):
        code, _ = self.invoke(matrix_log().replace('accepted=0 desired=0 phase=matching', 'accepted=1 desired=0 phase=matching', 1))
        self.assertEqual(code, 1)

    def test_known_open_label_on_a_different_case_fails(self):
        log = matrix_log().replace('empty_min0_space status=PASS', 'empty_min0_space status=EXPECTED_FAIL_OPEN')
        log = log.replace('required_empty_props_empty_OPEN status=EXPECTED_FAIL_OPEN', 'required_empty_props_empty_OPEN status=PASS')
        code, _ = self.invoke(log)
        self.assertEqual(code, 1)

    def test_wrong_compile_error_phase_fails(self):
        code, _ = self.invoke(matrix_log().replace('phase=schema_conversion', 'phase=matcher_compilation', 1))
        self.assertEqual(code, 1)

    def test_original_requires_both_lazy_modes(self):
        original='SUMMARY failures=0\n'+2*'ACTUAL_MASK lazy=0 whitespace_tokens=425 allowed=0\n'
        code,_=self.invoke(matrix_log(),original)
        self.assertEqual(code,1)

    def test_original_summary_is_not_a_substring(self):
        original='SUMMARY failures=00\nACTUAL_MASK lazy=0 whitespace_tokens=425 allowed=0\nACTUAL_MASK lazy=1 whitespace_tokens=425 allowed=0\n'
        code,_=self.invoke(matrix_log(),original)
        self.assertEqual(code,1)

    def test_manifest_drift_retains_initial_identity_in_failed_result(self):
        code,result=self.invoke(matrix_log(),drift_manifest=True)
        self.assertEqual(code,1)
        self.assertEqual(result['manifest_sha256'],hashlib.sha256(b'{}').hexdigest())

    def test_parent_that_already_exited_is_not_targeted_by_pid(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'INPUTS.json').write_text('{}')
            proc=MagicMock(pid=123456)
            proc.poll.return_value=0
            proc.wait.side_effect=[subprocess.TimeoutExpired('fake-owned-process',1),0]
            with patch.object(RUNNER,'ROOT',root), patch.object(RUNNER.subprocess,'Popen',return_value=proc), \
                 patch.object(RUNNER.subprocess,'run',return_value=subprocess.CompletedProcess(['fake-taskkill'],0)) as cleanup:
                data,_=RUNNER.stage(root,'natural-exit-race',['NOT_EXECUTED'],1,{})
            cleanup.assert_not_called()
            self.assertTrue(data['cleanup_skipped_parent_exited'])
            self.assertEqual(data['status'],'CLEANUP_UNCONFIRMED')

    def test_timeout_cleanup_and_post_kill_wait_are_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'INPUTS.json').write_text('{}')
            proc = MagicMock(pid=123456)
            proc.poll.return_value=None
            proc.wait.side_effect = [subprocess.TimeoutExpired('fake-owned-process',1),0]
            with patch.object(RUNNER,'ROOT',root), patch.object(RUNNER.subprocess,'Popen',return_value=proc), \
                 patch.object(RUNNER.subprocess,'run',return_value=subprocess.CompletedProcess(['fake-taskkill'],0)) as cleanup:
                data, _ = RUNNER.stage(root,'timeout-control',['NOT_EXECUTED'],1,{})
            self.assertTrue(data['timed_out'])
            self.assertIsNotNone(cleanup.call_args.kwargs.get('timeout'))
            self.assertLessEqual(cleanup.call_args.kwargs['timeout'],30)
            self.assertIsNotNone(proc.wait.call_args.kwargs.get('timeout'))

    def test_cleanup_timeout_is_durable_uncertainty(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'INPUTS.json').write_text('{}')
            proc=MagicMock(pid=123456)
            proc.poll.return_value=None
            proc.wait.side_effect=subprocess.TimeoutExpired('fake-owned-process',1)
            with patch.object(RUNNER,'ROOT',root), patch.object(RUNNER.subprocess,'Popen',return_value=proc), \
                 patch.object(RUNNER.subprocess,'run',side_effect=subprocess.TimeoutExpired('fake-taskkill',30)):
                try:
                    data,_=RUNNER.stage(root,'cleanup-timeout',['NOT_EXECUTED'],1,{})
                except subprocess.TimeoutExpired:
                    self.fail('Cleanup timeout escaped without a durable uncertainty receipt')
            self.assertEqual(data['status'],'CLEANUP_UNCONFIRMED')
            self.assertIsNone(data['exit_code'])
            self.assertTrue(data['cleanup_error'])
            self.assertEqual(json.loads((root/'cleanup-timeout.json').read_text())['status'],'CLEANUP_UNCONFIRMED')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--runner',type=Path,default=Path(__file__).resolve().parents[1]/'r1_runner.py')
    args,remaining=parser.parse_known_args()
    RUNNER=load_runner(args.runner)
    unittest.main(argv=[sys.argv[0]]+remaining)
