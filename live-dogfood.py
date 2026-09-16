"""Tool-focused README protocol: one warmup and three identical measured rounds.
Uses actual bounded local read tools; never executes model-produced shell commands.
"""
from pathlib import Path
import json, time, urllib.request, urllib.error, hashlib

OUT = Path(__file__).parent / 'live'
ROOT = Path(r'C:\git\gemma4-rc-main-promotion-20260916\acceptance\gemma4-live-20260916-corrective').resolve()
BASE = 'http://127.0.0.1:18091/v3'
MODEL = 'gemma4-26-heretic'
for sub in ['requests','responses','streams','tools']:
    (OUT/sub).mkdir(parents=True,exist_ok=True)

def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

TOOLS = [
    {'type':'function','function':{'name':'list_dir','description':'List files in an acceptance workspace directory.','parameters':{'type':'object','properties':{'path':{'type':'string'}},'required':['path'],'additionalProperties':False}}},
    {'type':'function','function':{'name':'read_file','description':'Read up to 5000 characters of a text file in the acceptance workspace.','parameters':{'type':'object','properties':{'path':{'type':'string'}},'required':['path'],'additionalProperties':False}}}
]

def local_call(call):
    assert call.get('id') and call.get('type')=='function', 'missing tool identity'
    fn=call['function']; assert fn['name'] in ['list_dir','read_file'], 'unknown tool'
    args=json.loads(fn['arguments'])
    assert isinstance(args,dict) and set(args)=={'path'} and isinstance(args['path'],str), 'schema violation'
    target=(ROOT/args['path']).resolve()
    assert target==ROOT or ROOT in target.parents, 'out-of-workspace path'
    if fn['name']=='list_dir':
        assert target.is_dir(), 'not a directory'
        value='\n'.join(sorted(p.name for p in target.iterdir()))
    else:
        assert target.is_file(), 'not a file'
        value=target.read_text(encoding='utf-8-sig')[:5000]
    return args,value

def request(tag,messages,choice='auto',stream=False,parallel=None,tools=TOOLS):
    log=OUT/'ovms.log'
    if log.exists():
        text=log.read_text(encoding='utf-8',errors='replace').lower()
        assert not any(marker in text for marker in ['gpu_context_fatal','cl_out_of_resources','executor quarantine']), 'GPU fatal/quarantine: stop and inspect server'
    body={'model':MODEL,'messages':messages,'temperature':0,'max_tokens':512,'stream':stream}
    if tools:
        body.update(tools=tools,tool_choice=choice)
    if parallel is not None: body['parallel_tool_calls']=parallel
    if stream: body['stream_options']={'include_usage':True}
    save(OUT/'requests'/f'{tag}.json',body)
    start=time.monotonic(); first=None
    req=urllib.request.Request(BASE+'/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=300) as response:
            status=response.status
            if not stream:
                raw=response.read(); (OUT/'responses'/f'{tag}.raw.json').write_bytes(raw)
                result=json.loads(raw); ch=result['choices'][0]
                msg=ch['message']; finish=ch['finish_reason']; usage=result.get('usage',{})
            else:
                calls={}; text=''; reasoning=''; finish=None; usage={}; done=False
                with (OUT/'streams'/f'{tag}.sse').open('wb') as rawfile:
                    for line in response:
                        rawfile.write(line); rawfile.flush()
                        if not line.startswith(b'data:'): continue
                        payload=line[5:].strip()
                        if payload==b'[DONE]': done=True; break
                        if not payload: continue
                        event=json.loads(payload)
                        if event.get('usage'): usage=event['usage']
                        for ch in event.get('choices',[]):
                            delta=ch.get('delta',{})
                            if any(delta.get(k) for k in ['content','reasoning_content','tool_calls']) and first is None: first=time.monotonic()-start
                            text+=delta.get('content') or ''
                            reasoning+=delta.get('reasoning_content') or ''
                            if ch.get('finish_reason') is not None: finish=ch['finish_reason']
                            for tc in delta.get('tool_calls',[]):
                                idx=tc['index']; item=calls.setdefault(idx,{'id':'','type':'function','function':{'name':'','arguments':''}})
                                if tc.get('id'): item['id']+=tc['id']
                                if tc.get('type'): item['type']=tc['type']
                                for key in ['name','arguments']:
                                    item['function'][key]+=tc.get('function',{}).get(key) or ''
                assert done, 'SSE missing DONE'
                msg={'role':'assistant','content':text}
                if calls: msg['tool_calls']=[calls[k] for k in sorted(calls)]
                if reasoning: msg['reasoning_content']=reasoning
    except Exception as exc:
        error={'error':str(exc),'type':type(exc).__name__,'wall_seconds':time.monotonic()-start}
        if isinstance(exc,urllib.error.HTTPError): error.update(http_status=exc.code,body=exc.read().decode(errors='replace'))
        save(OUT/'responses'/f'{tag}.error.json',error)
        raise
    metric={'http_status':status,'finish_reason':finish,'usage':usage,'wall_seconds':time.monotonic()-start,'ttft_seconds':first,'message':msg}
    save(OUT/'responses'/f'{tag}.json',metric)
    print(f'{tag}: HTTP={status} finish={finish} calls={len(msg.get("tool_calls") or [])} wall={metric["wall_seconds"]:.2f}s',flush=True)
    assert finish!='length', 'generation limit; incomplete task cannot pass'
    return msg,finish

def execute(tag,msg):
    calls=msg.get('tool_calls') or []
    assert calls, 'no executable tool call'
    assert len({c['id'] for c in calls})==len(calls), 'duplicate tool ids'
    results=[]
    for i,call in enumerate(calls):
        args,value=local_call(call)
        save(OUT/'tools'/f'{tag}-{i}.json',{'call':call,'parsed_arguments':args,'result':value})
        results.append({'role':'tool','tool_call_id':call['id'],'content':value})
    return results

def single(tag,stream,choice,parallel,prompt,expected):
    messages=[{'role':'user','content':prompt}]
    msg,finish=request(tag,messages,choice,stream,parallel)
    calls=msg.get('tool_calls') or []
    got=[(c['function']['name'],json.loads(c['function']['arguments']).get('path')) for c in calls]
    assert sorted(got)==sorted(expected), f'ungrounded or wrong calls: {got}'
    assert finish=='tool_calls', f'calls with unexpected finish {finish}'
    replay=execute(tag,msg)
    messages += [msg]+replay+[{'role':'user','content':'Now report the requested facts from the tool results. Do not call any more tools.'}]
    final,fr=request(tag+'-replay',messages,'auto',stream,False)
    assert not final.get('tool_calls'), 'continued tools despite completed read'
    assert final.get('content') and fr=='stop', 'missing final answer'
    assert '2026.5' in final['content'], 'final is not grounded in provenance version'

def agent(tag):
    messages=[{'role':'system','content':'You are a repository inspector. Use the provided tools to gather facts. Never invent file contents. When done, write a 3-sentence summary.'},
              {'role':'user','content':"Inspect the workspace directory: 1) list top-level files, 2) read binary-provenance.txt and report OVMS version + MIXED_OLD_RUNTIME value, 3) list the logs directory. Then summarize what this acceptance run is testing in 3 sentences."}]
    seen=set(); total=0
    for turn in range(1,9):
        msg,finish=request(f'{tag}-turn{turn}',messages)
        calls=msg.get('tool_calls') or []
        if not calls:
            required={('list_dir','.'),('read_file','binary-provenance.txt'),('list_dir','logs')}
            assert required<=seen, f'premature final; missing {required-seen}'
            text=msg.get('content') or ''
            assert finish=='stop' and '2026.5' in text and 'NO' in text, 'ungrounded/missing final facts'
            return {'turns':turn,'tool_calls':total,'final':text}
        assert finish=='tool_calls', f'calls with finish={finish}'
        for c in calls:
            a=json.loads(c['function']['arguments']); seen.add((c['function']['name'],Path(a.get('path','')).as_posix()))
        total+=len(calls)
        messages += [msg]+execute(f'{tag}-turn{turn}',msg)
    raise AssertionError('agent did not terminate within 8 turns')

summary=[]
try:
    with urllib.request.urlopen(BASE+'/models',timeout=10) as response:
        raw=response.read(); (OUT/'responses'/'model-list.json').write_bytes(raw)
        assert MODEL in raw.decode()
    for r in range(4):
        phase='warmup' if r==0 else f'measured-{r}'
        cases=[
            ('unary-named',lambda tag:single(tag,False,{'type':'function','function':{'name':'read_file'}},False,'Read binary-provenance.txt and tell me the OVMS version.',[('read_file','binary-provenance.txt')])),
            ('stream-required',lambda tag:single(tag,True,'required',False,'Read binary-provenance.txt and tell me the OVMS version.',[('read_file','binary-provenance.txt')])),
            ('parallel',lambda tag:single(tag,False,'required',True,'Call read_file for binary-provenance.txt and read_file for README.md. Make both calls in this response.',[('read_file','binary-provenance.txt'),('read_file','README.md')])),
            ('agent-auto',agent)
        ]
        for name,fn in cases:
            tag=f'{phase}-{name}'
            try:
                detail=fn(tag); verdict={'case':tag,'status':'PASS','detail':detail}
            except Exception as exc:
                verdict={'case':tag,'status':'FAIL','error':str(exc)}
            summary.append(verdict); save(OUT/'summary.json',summary)
            print(json.dumps(verdict,ensure_ascii=False),flush=True)
            # Halt on transport faults; do not hammer an unready/quarantined executor.
            if verdict['status']=='FAIL' and any(s in verdict['error'] for s in ['HTTP Error','timed out','GPU fatal/quarantine']):
                raise RuntimeError('transport/readiness failure; inspect server before continuing')
finally:
    save(OUT/'summary.json',summary)
