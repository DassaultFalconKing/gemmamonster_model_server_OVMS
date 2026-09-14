import json, urllib.request, urllib.error, pathlib
BASE = "http://127.0.0.1:18091/v3/chat/completions"
EVID = pathlib.Path(r'C:\Users\testc\AppData\Local\Temp\opencode\rc2-roundtrip-forensics\heretic-multiturn')

def post(payload, name):
    (EVID / (name + '.request.json')).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    req = urllib.request.Request(BASE, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    try:
        r = urllib.request.urlopen(req, timeout=900)
    except urllib.error.HTTPError as e:
        r = e
    with r:
        raw = r.read(); code = r.status
    (EVID / (name + '.response.json')).write_bytes(raw)
    o = json.loads(raw)
    m = o['choices'][0]['message']; f = o['choices'][0].get('finish_reason')
    print('[%s] HTTP=%s finish=%s content=%r tools=%s usage=%s keys=%s' % (
        name, code, f, (m.get('content') or '')[:200],
        [(c['function']['name'], c['function']['arguments'][:100]) for c in m.get('tool_calls', [])],
        o.get('usage'), sorted(m.keys())))
    return o

Q = {"type": "function", "function": {"name": "question", "description": "Ask the user one question.",
    "parameters": {"type": "object",
        "properties": {"questions": {"type": "array", "items": {"type": "object",
            "properties": {"question": {"type": "string"}, "header": {"type": "string"},
                "options": {"type": "array", "items": {"type": "object",
                    "properties": {"label": {"type": "string"}, "description": {"type": "string"}},
                    "required": ["label", "description"], "additionalProperties": False}},
                "multiple": {"type": "boolean"}, "custom": {"type": "boolean"}},
            "required": ["question", "header", "options"], "additionalProperties": False}}},
        "required": ["questions"], "additionalProperties": False}}}
E = {"type": "function", "function": {"name": "echo", "description": "Echo text back.",
    "parameters": {"type": "object", "properties": {"text": {"type": "string"}},
    "required": ["text"], "additionalProperties": False}}}

b1 = json.loads((EVID / 'B1-question.response.json').read_text(encoding='utf-8'))
d1 = b1['choices'][0]['message']['tool_calls']
u1 = d1[0]['id']
histb = [
    {"role": "user", "content": "Ask me one simple test question using the question tool."},
    {"role": "assistant", "content": None, "tool_calls": d1},
    {"role": "tool", "tool_call_id": u1, "content": json.dumps({"answer": "A"})},
    {"role": "user", "content": "Now call the echo tool with my answer."},
]
print('--- B2b: same step, max_tokens 1024 ---')
b2b = post({"model": "gemma4", "messages": histb,
    "tools": [Q, E], "tool_choice": "auto", "temperature": 0.0, "max_tokens": 1024, "stream": False}, 'B2b-echo-1024')
d2 = (b2b['choices'][0]['message'].get('tool_calls', []) or []) if b2b else []
if d2:
    u2 = d2[0]['id']
    histb += [
        {"role": "assistant", "content": None, "tool_calls": d2},
        {"role": "tool", "tool_call_id": u2, "content": json.dumps({"echoed": True})},
        {"role": "user", "content": "Now call the echo tool again with the word DONE."},
    ]
    print('--- B3b: third call ---')
    post({"model": "gemma4", "messages": histb,
        "tools": [Q, E], "tool_choice": "auto", "temperature": 0.0, "max_tokens": 1024, "stream": False}, 'B3b-echo-again')
