import os,json,time,subprocess,urllib.request,urllib.error
from pathlib import Path
root=Path(r'C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914')
runtime=root/"ovms"
root=root/"wondernutts-test"
root.mkdir(exist_ok=False)
logs=root/"logs"
logs.mkdir()
model=Path(r"C:\llm\models\OpenVINO\Wondernutts\gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov")
template=(model/"graph.pbtxt").read_text().replace("./",model.as_posix())
graph=root/'gemma4-smoke.pbtxt'; graph.write_text(template)
config=root/'gemma4-config.json'; config.write_text(json.dumps({'model_config_list':[],'mediapipe_config_list':[{'name':'gemma4','graph_path':str(graph)}]}))
env=os.environ.copy()
for key in ('PYTHONHOME','PYTHONPATH','OVMS_DIR','ESPEAK_DATA_PATH'):env.pop(key,None)
env['PATH']=os.environ['SystemRoot']+'\\System32;'+os.environ['SystemRoot']
out=open(logs/'gemma4-server.stdout.log','wb');err=open(logs/'gemma4-server.stderr.log','wb')
p=subprocess.Popen(['cmd.exe','/d','/c',f'call setupvars.bat && ovms.exe --config_path {config} --rest_port 18086 --port 18087'],cwd=runtime,env=env,stdout=out,stderr=err)
results={}
try:
 ready=False
 for i in range(600):
  if p.poll() is not None:break
  try:
   with urllib.request.urlopen('http://127.0.0.1:18086/v3/models',timeout=2) as r:
    body=r.read();(logs/'gemma4-models.response.json').write_bytes(body)
    ready=any(m.get('id')=='gemma4' for m in json.loads(body).get('data',[]))
    if ready:break
  except Exception:pass
  if "LOADING_PRECONDITION_FAILED" in (logs/"gemma4-server.stdout.log").read_text(errors="replace"):break
  if i%30==0:print('WAITING_FOR_GEMMA4',i,flush=True)
  time.sleep(1)
 results['ready']='PASS' if ready else 'FAIL'
 print('GEMMA4_READY',ready,flush=True)
 if ready:
  payload={'model':'gemma4','messages':[{'role':'user','content':'What is 2 + 2? Reply with only the number.'}],'max_tokens':32,'temperature':0,'stream':False}
  (logs/'gemma4-chat.request.json').write_text(json.dumps(payload))
  req=urllib.request.Request('http://127.0.0.1:18086/v3/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
  try:response=urllib.request.urlopen(req,timeout=180)
  except urllib.error.HTTPError as e:response=e
  with response:body=response.read();code=response.status
  (logs/'gemma4-chat.response.json').write_bytes(body)
  result=json.loads(body);print('GEMMA4_CHAT',code,result,flush=True)
  choices=result.get('choices',[])
  results['chat']={'http_status':code,'status':'PASS' if code==200 and choices and choices[0].get('message',{}).get('content','').strip()=='4' and choices[0].get('finish_reason')=='stop' else 'FAIL','response':result}
except Exception as e:results['exception']=repr(e);print('ERROR',repr(e),flush=True)
finally:
 subprocess.run(['taskkill.exe','/PID',str(p.pid),'/T','/F'],capture_output=True)
 p.wait(timeout=30);out.close();err.close()
 (root/'gemma4-test-results.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2),flush=True)
