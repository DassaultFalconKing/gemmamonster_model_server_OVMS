import os, json, time, subprocess, urllib.request, urllib.error, hashlib
from pathlib import Path

RC2_EXE = Path(r'C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914\ovms\ovms.exe')
EVID = Path(r'C:\Users\testc\AppData\Local\Temp\opencode\rc2-acceptance-20260914\live-sanity')
EVID.mkdir(parents=True, exist_ok=True)

# 1. verify binary identity
h = hashlib.sha256(RC2_EXE.read_bytes()).hexdigest()
print(f"RC2_BINARY: {RC2_EXE}")
print(f"RC2_SHA256: {h}")
print(f"RC2_SIZE: {RC2_EXE.stat().st_size}")
assert h.lower() == "11d74fd958d1cd2570682fa13562c1bfcf0973dabbf79a0378a8d0cdc886a4fb".lower(), "hash mismatch!"

# 2. build graph (mirror proven smoke: E4B VLM CPU)
template = Path(r'C:\git\ovms-9e34371-clean-20260914\src\test\llm\visual_language_model\vlm_cb_regular.pbtxt').read_text()
template = template.replace('/ovms/src/test/llm_testing/OpenVINO/InternVL2-1B-int4-ov','C:/llm/models/OpenVINO/gemma-4-E4B-it-int4-ov')
template = template.replace('cache_size: 1','cache_size: 1\n          device: "CPU"\n          pipeline_type: VLM')
graph = EVID/'gemma4-graph.pbtxt'
graph.write_text(template)
config = EVID/'config.json'
config.write_text(json.dumps({'model_config_list':[],'mediapipe_config_list':[{'name':'gemma4','graph_path':str(graph)}]}))
print(f"GRAPH: {graph}")
print(f"CONFIG: {config}")

REST=18091
GRPC=18092
runtime = RC2_EXE.parent
env = os.environ.copy()
for key in ('PYTHONHOME','PYTHONPATH','OVMS_DIR','ESPEAK_DATA_PATH'):
    env.pop(key,None)
env['PATH']=os.environ['SystemRoot']+r'\System32;'+os.environ['SystemRoot']
out=open(EVID/'server.stdout.log','wb'); err=open(EVID/'server.stderr.log','wb')
cmdline=f'call setupvars.bat && ovms.exe --config_path {config} --rest_port {REST} --port {GRPC}'
print(f"CMDLINE: {cmdline}")
print(f"CWD: {runtime}")
p=subprocess.Popen(['cmd.exe','/d','/c',cmdline],cwd=str(runtime),env=env,stdout=out,stderr=err)
print(f"PID: {p.pid}")
(EVID/'server-meta.json').write_text(json.dumps({"pid":p.pid,"executable":str(RC2_EXE),"command_line":cmdline,"rest_port":REST,"grpc_port":GRPC,"model":"gemma4","model_path":"C:/llm/models/OpenVINO/gemma-4-E4B-it-int4-ov","profile":"VLM-CPU (smoke parity)","chat_template_mode":"model-default (no overlay)"},indent=2))
results={}
try:
    ready=False
    for i in range(300):
        if p.poll() is not None:
            print(f"SERVER EXITED EARLY code={p.poll()}")
            break
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{REST}/v3/models',timeout=2) as r:
                body=r.read(); (EVID/'models.response.json').write_bytes(body)
                print(f"MODELS poll {i}: {body[:300]}")
                try:
                    ready=any(m.get('id')=='gemma4' for m in json.loads(body).get('data',[]))
                except Exception: ready=False
                if ready: break
        except Exception as e:
            if i%30==0: print(f"WAITING {i} {e!r}",flush=True)
        time.sleep(1)
    results['server_start']='PASS' if ready or p.poll() is None else 'FAIL'
    results['model_load']='PASS' if ready else 'FAIL'
    print(f"READY={ready}")
    if ready:
        payload={'model':'gemma4','messages':[{'role':'user','content':'What is 2 + 2? Reply with only the number.'}],'max_tokens':32,'temperature':0,'stream':False}
        (EVID/'plain-chat.request.json').write_text(json.dumps(payload,indent=2))
        req=urllib.request.Request(f'http://127.0.0.1:{REST}/v3/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        try: response=urllib.request.urlopen(req,timeout=300)
        except urllib.error.HTTPError as e: response=e
        with response:
            body=response.read(); code=response.status
        (EVID/'plain-chat.response.json').write_bytes(body)
        print(f"PLAIN_CHAT HTTP={code} BODY={body[:1000]}")
        try:
            result=json.loads(body)
            choices=result.get('choices',[])
            ok = code==200 and choices and choices[0].get('message',{}).get('content','').strip()=='4' and choices[0].get('finish_reason')=='stop'
        except Exception: ok=False
        results['plain_chat']='PASS' if ok else 'FAIL'
        results['plain_http']=code
    else:
        results['plain_chat']='FAIL'
finally:
    (EVID/'result.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))
    print(f"EVIDENCE: {EVID}")
    print("SERVER LEFT RUNNING FOR TOOL MATRIX - PID", p.pid)
