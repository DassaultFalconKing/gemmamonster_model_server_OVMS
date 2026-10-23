"""Offline supervisor controls. The fake pipeline imports no OpenVINO or model."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import psutil


class SupervisorTests(unittest.TestCase):
    def test_timeout_terminates_owned_descendants(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); identity=root/'identity.json'; output=root/'result.json'
            fake='''import json, os, subprocess, sys, time
from pathlib import Path
import psutil
def VLMPipeline(*args, **kwargs):
    p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
    Path(os.environ['TEST_IDENTITY']).write_text(json.dumps({'child':os.getpid(),'grandchild':p.pid,'birth':psutil.Process(p.pid).create_time()}))
    time.sleep(60)
'''
            (root/'openvino_genai.py').write_text(fake,encoding='utf-8')
            env=dict(os.environ,PYTHONPATH=str(root),TEST_IDENTITY=str(identity))
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('smoke.py')),'--model',str(root),'--output',str(output),'--timeout','2'],env=env,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,2,result.stderr)
            state=json.loads(output.read_text())
            self.assertEqual(state['status'],'BLOCKED')
            self.assertEqual(state['reason'],'Timeout')
            self.assertEqual(state['last_child_state']['phase'],'constructing')
            ids=json.loads(identity.read_text())
            time.sleep(.3)
            for key in ('child','grandchild'):
                self.assertFalse(psutil.pid_exists(ids[key]),(key,ids[key]))
            monitor=json.loads(output.with_suffix('.monitor.json').read_text())
            self.assertGreater(max(len(x['processes']) for x in monitor['samples']),1)
            self.assertGreater(max(x['rss'] for x in monitor['samples']),10*1024**2)

    def test_external_python_blocks_without_starting_child(self):
        worker=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])
        try:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);output=root/'result.json'
                result=subprocess.run([sys.executable,str(Path(__file__).with_name('smoke.py')),'--model',str(root),'--output',str(output)],capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,2,result.stderr)
                state=json.loads(output.read_text())
                self.assertEqual(state['reason'],'Another potential inference process')
                self.assertIn(worker.pid,[x['pid'] for x in state['processes']])
                self.assertFalse(output.with_suffix('.monitor.json').exists())
        finally:
            worker.kill();worker.wait(10)

    def test_native_exit_preserves_constructor_phase(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);output=root/'result.json'
            (root/'openvino_genai.py').write_text('import os\ndef VLMPipeline(*args, **kwargs): os._exit(7)\n',encoding='utf-8')
            env=dict(os.environ,PYTHONPATH=str(root))
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('smoke.py')),'--model',str(root),'--output',str(output)],env=env,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,1,result.stderr)
            state=json.loads(output.read_text())
            self.assertEqual(state['status'],'FAIL')
            self.assertEqual(state['returncode'],7)
            self.assertEqual(state['last_child_state']['phase'],'constructing')


if __name__=='__main__':unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,verbosity=2))
