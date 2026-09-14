import json, urllib.request, urllib.error, pathlib
BASE="http://127.0.0.1:18091/v3/chat/completions"
EVID=pathlib.Path(r'C:\Users\testc\AppData\Local\Temp\opencode\rc2-acceptance-20260914\manual-probes')
EVID.mkdir(parents=True,exist_ok=True)

def post(payload, name):
    (EVID/f"{name}.request.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    req=urllib.request.Request(BASE,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    try: r=urllib.request.urlopen(req,timeout=240)
    except urllib.error.HTTPError as e: r=e
    with r:
        raw=r.read(); code=r.status
    (EVID/f"{name}.response.json").write_bytes(raw)
    print(f"[{name}] HTTP={code} {raw[:800].decode('utf-8',errors='replace')}")
    try: return code, json.loads(raw)
    except Exception: return code, {}

QTOOL={
    "type": "function",
    "function": {
        "name": "question",
        "description": "Ask the user one or more interactive questions.",
        "parameters": {"type":"object","properties":{"questions":{"type":"array","items":{"type":"object","properties":{"question":{"type":"string"},"header":{"type":"string"},"options":{"type":"array","items":{"type":"object","properties":{"label":{"type":"string"},"description":{"type":"string"}},"required":["label","description"],"additionalProperties":False}},"multiple":{"type":"boolean"},"custom":{"type":"boolean"}},"required":["question","header","options"],"additionalProperties":False}}},"required":["questions"],"additionalProperties":False},
    },
}

# 1. turn1 fresh
code1,obj1=post({"model":"gemma4","messages":[{"role":"user","content":"Ask me one simple test question using the question tool. Do not explain instead."}],"tools":[QTOOL],"tool_choice":"required","temperature":0.0,"max_tokens":256,"stream":False},"rt-clean-turn1")
calls=obj1.get('choices',[{}])[0].get('message',{}).get('tool_calls',[])
tid=calls[0].get('id') if calls else None
print("TURN1 tool_id:",tid)

# 2a. turn2 with CLEANED assistant content (None) - isolate <eos> poisoning
if tid:
    assistant_clean={"role":"assistant","content":None,"tool_calls":calls}
    code2a,obj2a=post({"model":"gemma4","messages":[{"role":"user","content":"Ask me one simple test question using the question tool."},assistant_clean,{"role":"tool","tool_call_id":tid,"content":json.dumps({"answer":"A"})}],"tools":[QTOOL],"tool_choice":"auto","temperature":0.0,"max_tokens":256,"stream":False},"rt-clean-turn2-clean-history")
    m2a=obj2a.get('choices',[{}])[0].get('message',{}) if code2a==200 else {}
    print("TURN2-clean content:",repr(m2a.get('content'))[:300],"tools:",m2a.get('tool_calls'))

    # 2b. turn2 with empty-string content
    assistant_empty={"role":"assistant","content":"","tool_calls":calls}
    code2b,obj2b=post({"model":"gemma4","messages":[{"role":"user","content":"Ask me one simple test question using the question tool."},assistant_empty,{"role":"tool","tool_call_id":tid,"content":json.dumps({"answer":"A"})}],"tools":[QTOOL],"tool_choice":"auto","temperature":0.0,"max_tokens":256,"stream":False},"rt-clean-turn2-empty-history")
    m2b=obj2b.get('choices',[{}])[0].get('message',{}) if code2b==200 else {}
    print("TURN2-empty content:",repr(m2b.get('content'))[:300],"tools:",m2b.get('tool_calls'))

# 3. repeated same tool: get_weather x3 Berlin/Munich/Hamburg + get_timezone Berlin
WTOOL=lambda name,desc,props,req: {"type":"function","function":{"name":name,"description":desc,"parameters":{"type":"object","properties":props,"required":req,"additionalProperties":False}}}
tools=[WTOOL("get_weather","Get weather",{"city":{"type":"string"}},["city"]),WTOOL("get_timezone","Get timezone",{"city":{"type":"string"}},["city"])]
code3,obj3=post({"model":"gemma4","messages":[{"role":"user","content":"Call get_weather for Berlin, get_weather for Munich, get_weather for Hamburg, and get_timezone for Berlin. Use tools, do not explain instead."}],"tools":tools,"tool_choice":"required","temperature":0.0,"max_tokens":512,"stream":False},"parallel-repeated-same-tool")
try:
    c3=obj3['choices'][0]['message'].get('tool_calls',[])
    print("REPEATED count:",len(c3),"names:",[c['function']['name'] for c in c3])
    for c in c3: print("  -",c['function']['name'],c['function']['arguments'][:200])
except Exception as e: print("REPEATED parse err",e)
