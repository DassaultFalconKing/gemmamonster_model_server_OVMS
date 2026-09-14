import json, urllib.request, urllib.error, pathlib
BASE = "http://127.0.0.1:18091/v3/chat/completions"
EVID = pathlib.Path(r'C:\Users\testc\AppData\Local\Temp\opencode\rc2-roundtrip-forensics\hypotheses')
EVID.mkdir(parents=True, exist_ok=True)

def post(payload, name):
    (EVID / (name + '.request.json')).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    req = urllib.request.Request(BASE, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    try:
        r = urllib.request.urlopen(req, timeout=240)
    except urllib.error.HTTPError as e:
        r = e
    with r:
        raw = r.read(); code = r.status
    (EVID / (name + '.response.json')).write_bytes(raw)
    try:
        o = json.loads(raw)
        m = o['choices'][0]['message']; f = o['choices'][0].get('finish_reason')
        u = o.get('usage')
    except Exception:
        print('[%s] HTTP=%s UNPARSEABLE %s' % (name, code, raw[:200])); return None
    print('[%s] HTTP=%s finish=%s content=%r tools=%d usage=%s' % (name, code, f, (m.get('content') or '')[:120], len(m.get('tool_calls', [])), u))
    return o

QTOOL = {"type": "function", "function": {
    "name": "question", "description": "Ask the user one or more interactive questions.",
    "parameters": {"type": "object",
        "properties": {"questions": {"type": "array", "items": {"type": "object",
            "properties": {"question": {"type": "string"}, "header": {"type": "string"},
                "options": {"type": "array", "items": {"type": "object",
                    "properties": {"label": {"type": "string"}, "description": {"type": "string"}},
                    "required": ["label", "description"], "additionalProperties": False}},
                "multiple": {"type": "boolean"}, "custom": {"type": "boolean"}},
            "required": ["question", "header", "options"], "additionalProperties": False}}},
        "required": ["questions"], "additionalProperties": False}}}

print('--- E3: plain 2-turn, no tools at all ---')
t1 = post({"model": "gemma4", "messages": [{"role": "user", "content": "What is 2 + 2? Reply with only the number."}], "max_tokens": 32, "temperature": 0, "stream": False}, 'E3-turn1-plain')
if t1:
    a1 = t1['choices'][0]['message']
    post({"model": "gemma4", "messages": [
        {"role": "user", "content": "What is 2 + 2? Reply with only the number."},
        {"role": "assistant", "content": a1.get('content')},
        {"role": "user", "content": "And what is 3 + 3? Reply with only the number."}],
        "max_tokens": 32, "temperature": 0, "stream": False}, 'E3-turn2-plain-followup')

print('--- fresh turn1 for E1/E2/E4 ---')
t = post({"model": "gemma4",
    "messages": [{"role": "user", "content": "Ask me one simple test question using the question tool. Do not explain instead."}],
    "tools": [QTOOL], "tool_choice": "required", "temperature": 0.0, "max_tokens": 256, "stream": False}, 'E-turn1')
calls = t['choices'][0]['message'].get('tool_calls', []) if t else []
tid = calls[0].get('id') if calls else None
print('tool_id:', tid)
if not tid:
    raise SystemExit('no turn1 tool call, abort')

base_hist = [
    {"role": "user", "content": "Ask me one simple test question using the question tool."},
    {"role": "assistant", "content": None, "tool_calls": calls},
]

print('--- E1: tool history, NO tools param ---')
post({"model": "gemma4", "messages": base_hist + [
    {"role": "tool", "tool_call_id": tid, "content": json.dumps({"answer": "A"})}],
    "temperature": 0.0, "max_tokens": 256, "stream": False}, 'E1-turn2-no-tools-param')

print('--- E2: tool history, tools + tool_choice none ---')
post({"model": "gemma4", "messages": base_hist + [
    {"role": "tool", "tool_call_id": tid, "content": json.dumps({"answer": "A"})}],
    "tools": [QTOOL], "tool_choice": "none", "temperature": 0.0, "max_tokens": 256, "stream": False}, 'E2-turn2-choice-none')

print('--- E4: exact history, LONGER tool result ---')
post({"model": "gemma4", "messages": [
    {"role": "user", "content": "Ask me one simple test question using the question tool."},
    {"role": "assistant", "content": "<eos>", "tool_calls": calls},
    {"role": "tool", "tool_call_id": tid, "content": json.dumps({"answer": "Blue, because it reminds me of the ocean and the sky on a clear summer day", "confidence": 0.95, "extra": [1, 2, 3]})}],
    "tools": [QTOOL], "tool_choice": "auto", "temperature": 0.0, "max_tokens": 256, "stream": False}, 'E4-turn2-long-tool-result')

print('--- E5: exact history, temp 0.7, max_tokens 512 ---')
post({"model": "gemma4", "messages": [
    {"role": "user", "content": "Ask me one simple test question using the question tool."},
    {"role": "assistant", "content": "<eos>", "tool_calls": calls},
    {"role": "tool", "tool_call_id": tid, "content": json.dumps({"answer": "A"})}],
    "tools": [QTOOL], "tool_choice": "auto", "temperature": 0.7, "max_tokens": 512, "stream": False}, 'E5-turn2-temp07')
print('EVID:', EVID)
