import json, urllib.request, urllib.error, pathlib, time
BASE="http://127.0.0.1:18091/v3/chat/completions"
EVID=pathlib.Path(r'C:\Users\testc\AppData\Local\Temp\opencode\rc2-acceptance-20260914\stability')
EVID.mkdir(parents=True,exist_ok=True)
ECHO={"type":"function","function":{"name":"echo","description":"Return text.","parameters":{"type":"object","properties":{"text":{"type":"string"}},"required":["text"],"additionalProperties":False}}}

def unary(i):
    p={"model":"gemma4","messages":[{"role":"user","content":"Use the echo tool with text test-auto. Do not explain instead."}],"tools":[ECHO],"tool_choice":"auto","temperature":0.0,"max_tokens":64,"stream":False}
    req=urllib.request.Request(BASE,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=240) as r: raw=r.read(); code=r.status
    except urllib.error.HTTPError as e: raw=e.read(); code=e.code
    except Exception as e: return False, f"EXC {e!r}"
    try:
        o=json.loads(raw); m=o['choices'][0]['message']; calls=m.get('tool_calls',[])
        ok = code==200 and len(calls)>=1 and calls[0]['function']['name']=='echo' and json.loads(calls[0]['function']['arguments']).get('text')=='test-auto' and o['choices'][0].get('finish_reason')=='tool_calls'
        return ok, f"HTTP={code} finish={o['choices'][0].get('finish_reason')} content={m.get('content')!r} args={calls[0]['function']['arguments'][:80] if calls else None}"
    except Exception as e: return False, f"PARSE {e!r} raw={raw[:200]}"

def stream_one(i):
    p={"model":"gemma4","messages":[{"role":"user","content":"Use the echo tool with text test-auto. Do not explain instead."}],"tools":[ECHO],"tool_choice":"auto","temperature":0.0,"max_tokens":64,"stream":True}
    req=urllib.request.Request(BASE,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=240) as r:
            code=r.status; raw=b""
            while True:
                line=r.readline()
                if not line: break
                raw+=line
        t=raw.decode('utf-8',errors='replace')
        ok = code==200 and 'data: [DONE]' in t and '"tool_calls"' in t and '<pad>' not in t and '<unused' not in t
        return ok, f"HTTP={code} len={len(t)} hasDONE={'[DONE]' in t} hasTools={'tool_calls' in t}"
    except urllib.error.HTTPError as e: return False, f"HTTP {e.code}"
    except Exception as e: return False, f"EXC {e!r}"

print("== 20 unary ==")
up=uf=0; ulog=[]
for i in range(20):
    ok,info=unary(i); ulog.append({"i":i,"ok":ok,"info":info}); print(f"unary {i:02d} {'PASS' if ok else 'FAIL'} {info}")
    if ok: up+=1
    else: uf+=1
print(f"UNARY {up}/20 pass")
(EVID/'unary-20.json').write_text(json.dumps(ulog,indent=2),encoding='utf-8')

print("== 20 stream ==")
sp=sf=0; slog=[]
for i in range(20):
    ok,info=stream_one(i); slog.append({"i":i,"ok":ok,"info":info}); print(f"stream {i:02d} {'PASS' if ok else 'FAIL'} {info}")
    if ok: sp+=1
    else: sf+=1
print(f"STREAM {sp}/20 pass")
(EVID/'stream-20.json').write_text(json.dumps(slog,indent=2),encoding='utf-8')

# post-run plain chat health
p={"model":"gemma4","messages":[{"role":"user","content":"What is 2 + 2? Reply with only the number."}],"max_tokens":32,"temperature":0,"stream":False}
req=urllib.request.Request(BASE,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
try:
    with urllib.request.urlopen(req,timeout=120) as r: raw=r.read(); code=r.status
    o=json.loads(raw); c=o['choices'][0]['message'].get('content','').strip()
    ok = code==200 and c=='4'
    print(f"POST-RUN PLAIN {'PASS' if ok else 'FAIL'} HTTP={code} content={c!r}")
    (EVID/'post-plain.json').write_text(json.dumps({"http":code,"content":c,"pass":ok},indent=2),encoding='utf-8')
except Exception as e: print("POST-RUN PLAIN FAIL",repr(e))
(EVID/'summary.json').write_text(json.dumps({"unary_pass":up,"unary_fail":uf,"stream_pass":sp,"stream_fail":sf},indent=2),encoding='utf-8')
