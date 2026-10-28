"""Canonical existing-server speed protocol. No process/config mutations."""
import datetime,hashlib,importlib.util,json,statistics
from pathlib import Path
root=Path(__file__).parent
source=Path('C:/gm/qwenmonster/benchmarks/speed-20261024/run_ab.py')
spec=importlib.util.spec_from_file_location('canonical',source)
bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench)
bench.URL='http://127.0.0.1:8137'
model='qwen36-35b-a3b-heretic-int4'
prompt=Path('C:/gm/qwenmonster/semantic-refit-2026.4-hub/tasks/C12/reports/live-long-prompt.txt').read_text(encoding='utf-8')
body={'model':model,'messages':[{'role':'user','content':prompt+'\n\nContinue the briefing in detail. Do not call tools.'}],
      'temperature':0,'max_tokens':256,'stream':True,'stream_options':{'include_usage':True},'chat_template_kwargs':{'enable_thinking':False}}
state={'model':model,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runner':str(source),'runner_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'warmups':[],'measured':[],'status':'RUNNING'}
for phase,count in [('warmups',2),('measured',3)]:
    for i in range(count):
        row=bench.request(body,root/(phase+'-'+str(i)+'.sse'))
        state[phase].append(row)
        (root/'RESULT.json').write_text(json.dumps(state,indent=2))
        print(json.dumps({'phase':phase,'rep':i,**row}),flush=True)
state.update(status='PASS',median_decode_tok_s=statistics.median(r['decode_tok_s_estimate'] for r in state['measured']),median_ttft_s=statistics.median(r['ttft_s'] for r in state['measured']))
(root/'RESULT.json').write_text(json.dumps(state,indent=2))
print(json.dumps({'median_decode_tok_s':state['median_decode_tok_s'],'median_ttft_s':state['median_ttft_s']}))
