import os,subprocess,json,time,urllib.request
from pathlib import Path
root=Path(r"C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914")
logs=root/"logs"
test_runtime=root/"extracted"/"ovms"
results=json.loads((root/"test-results.json").read_text())
env = os.environ.copy()
for key in ('PYTHONHOME','PYTHONPATH','OVMS_DIR','ESPEAK_DATA_PATH'): env.pop(key,None)
env['PATH'] = str(Path(os.environ['SystemRoot'])/'System32') + ';' + os.environ['SystemRoot']
def command(args):
    return ['cmd.exe', '/d', '/c', 'call setupvars.bat && ovms.exe ' + args]

for name,args in [('version','--version'), ('help','--help')]:
    p = subprocess.run(command(args), cwd=test_runtime, env=env, capture_output=True, timeout=60)
    (logs/(name+'.stdout.log')).write_bytes(p.stdout)
    (logs/(name+'.stderr.log')).write_bytes(p.stderr)
    results[name] = {'exit_code':p.returncode,'status':'PASS' if p.returncode == 0 else 'FAIL'}
    print(name, p.returncode, p.stdout.decode(errors='replace')[:800], flush=True)
model = Path(r'C:\git\ovms-9e34371-clean-20260914\src\test\dummy')
config = root/'smoke-config.json'
config.write_text(json.dumps({'model_config_list':[{'config':{'name':'dummy','base_path':str(model),'target_device':'CPU'}}]}))
out = open(logs/'server.stdout.log','wb'); err = open(logs/'server.stderr.log','wb')
p = subprocess.Popen(command(f'--config_path {config} --rest_port 18086 --port 18087'), cwd=test_runtime, env=env, stdout=out, stderr=err)
try:
    ready = False
    for _ in range(90):
        if p.poll() is not None: break
        try:
            with urllib.request.urlopen('http://127.0.0.1:18086/v1/config', timeout=2) as response:
                body=response.read(); (logs/'config.response.json').write_bytes(body)
                state=json.loads(body)
                ready=any(v.get('state')=='AVAILABLE' for v in state.get('dummy',{}).get('model_version_status',[]))
                if ready: break
        except Exception: pass
        time.sleep(1)
    results['server_ready'] = 'PASS' if ready else 'FAIL'
    print('SERVER_READY',ready,flush=True)
    if ready:
        payload={"inputs":[{"name":"b","shape":[1,10],"datatype":"FP32","data":[1.0]*10}]}
        (logs/'inference.request.json').write_text(json.dumps(payload))
        request=urllib.request.Request('http://127.0.0.1:18086/v2/models/dummy/infer',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        try: response=urllib.request.urlopen(request,timeout=30)
        except urllib.error.HTTPError as e: response=e
        with response:
            body=response.read(); (logs/'inference.response.json').write_bytes(body)
            result=json.loads(body)
        results['inference']={'status':'PASS' if result.get("outputs",[{}])[0].get("data")==[2.0]*10 else 'FAIL','response':result}
        print('INFERENCE',result,flush=True)
finally:
    subprocess.run(['taskkill.exe','/PID',str(p.pid),'/T','/F'],capture_output=True)
    p.wait(timeout=30); out.close(); err.close()
    (root/'test-results.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2),flush=True)
