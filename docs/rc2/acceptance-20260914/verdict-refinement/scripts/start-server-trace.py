import os, json, time, subprocess, urllib.request, hashlib
from pathlib import Path

RC2_EXE = Path(r'C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914\ovms\ovms.exe')
EVID = Path(r'C:\Users\testc\AppData\Local\Temp\opencode\rc2-roundtrip-forensics\server-trace')
EVID.mkdir(parents=True, exist_ok=True)

h = hashlib.sha256(RC2_EXE.read_bytes()).hexdigest()
assert h.lower() == "11d74fd958d1cd2570682fa13562c1bfcf0973dabbf79a0378a8d0cdc886a4fb".lower(), "hash mismatch!"
print("SHA OK")

template = Path(r'C:\git\ovms-9e34371-clean-20260914\src\test\llm\visual_language_model\vlm_cb_regular.pbtxt').read_text()
template = template.replace('/ovms/src/test/llm_testing/OpenVINO/InternVL2-1B-int4-ov','C:/llm/models/OpenVINO/gemma-4-E4B-it-int4-ov')
template = template.replace('cache_size: 1','cache_size: 1\n          device: "CPU"\n          pipeline_type: VLM')
graph = EVID/'gemma4-graph.pbtxt'; graph.write_text(template)
config = EVID/'config.json'
config.write_text(json.dumps({'model_config_list':[],'mediapipe_config_list':[{'name':'gemma4','graph_path':str(graph)}]}))

REST=18091; GRPC=18092
runtime = RC2_EXE.parent
env = os.environ.copy()
for key in ('PYTHONHOME','PYTHONPATH','OVMS_DIR','ESPEAK_DATA_PATH'):
    env.pop(key,None)
env['PATH']=os.environ['SystemRoot']+r'\System32;'+os.environ['SystemRoot']
out=open(EVID/'server.stdout.log','wb'); err=open(EVID/'server.stderr.log','wb')
cmdline=f'call setupvars.bat && ovms.exe --config_path {config} --rest_port {REST} --port {GRPC} --log_level TRACE'
p=subprocess.Popen(['cmd.exe','/d','/c',cmdline],cwd=str(runtime),env=env,stdout=out,stderr=err)
print(f"PID: {p.pid} (TRACE)")
try:
    ready=False
    for i in range(300):
        if p.poll() is not None:
            print(f"EXITED {p.poll()}"); break
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{REST}/v3/models',timeout=2) as r:
                body=r.read()
                try: ready=any(m.get('id')=='gemma4' for m in json.loads(body).get('data',[]))
                except Exception: ready=False
                if ready: break
        except Exception:
            if i%30==0: print(f"WAITING {i}",flush=True)
        time.sleep(1)
    print(f"READY={ready}")
    (EVID/'ready.json').write_text(json.dumps({"ready":ready,"pid":p.pid}))
finally:
    print(f"EVID: {EVID}")
