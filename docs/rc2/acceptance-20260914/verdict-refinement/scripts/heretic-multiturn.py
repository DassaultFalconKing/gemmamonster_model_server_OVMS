import json, urllib.request, urllib.error, pathlib
BASE = "http://127.0.0.1:18091/v3/chat/completions"
EVID = pathlib.Path(r'C:\Users\testc\AppData\Local\Temp\opencode\rc2-roundtrip-forensics\heretic-multiturn')
EVID.mkdir(parents=True, exist_ok=True)

def post(payload, name):
    (EVID / (name + '.request.json')).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    req = urllib.request.Request(BASE, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    try:
        r = urllib.request.urlopen(req, timeout=600)
    except urllib.error.HTTPError as e:
        r = e
    with r:
        raw = r.read(); code = r.status
    (EVID / (name + '.response.json')).write_bytes(raw)
    try:
        o = json.loads(raw)
        m = o['choices'][0]['message']; f = o['choices'][0].get('finish_reason')
    except Exception:
        print('[%s] HTTP=%s UNPARSEABLE' % (name, code)); return None
    calls = m.get('tool_calls', [])
    print('[%s] HTTP=%s finish=%s content=%r tools=%s usage=%s' % (
        name, code, f, (m.get('content') or '')[:120],
        [(c['function']['name'], c['function']['arguments'][:80]) for c in calls], o.get('usage')))
    return o

W = {"type": "function", "function": {"name": "get_weather", "description": "Get current weather for a city.",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}},
    "required": ["city"], "additionalProperties": False}}}

print('=== Chain A: same tool across 3 turns ===')
a1 = post({"model": "gemma4",
    "messages": [{"role": "user", "content": "What is the weather in Berlin? Use the get_weather tool."}],
    "tools": [W], "tool_choice": "auto", "temperature": 0.0, "max_tokens": 256, "stream": False}, 'A1-berlin')
c1 = a1['choices'][0]['message']['tool_calls'] if a1 else []
t1 = c1[0]['id'] if c1 else None
assert t1, 'A1 no tool call'
hist = [
    {"role": "user", "content": "What is the weather in Berlin? Use the get_weather tool."},
    {"role": "assistant", "content": None, "tool_calls": c1},
    {"role": "tool", "tool_call_id": t1, "content": json.dumps({"temp_c": 21, "condition": "sunny"})},
    {"role": "user", "content": "And what about Munich?"},
]
a2 = post({"model": "gemma4", "messages": hist,
    "tools": [W], "tool_choice": "auto", "temperature": 0.0, "max_tokens": 256, "stream": False}, 'A2-munich')
c2 = a2['choices'][0]['message']['tool_calls'] if a2 else []
t2 = c2[0]['id'] if c2 else None
if t2:
    hist += [
        {"role": "assistant", "content": None, "tool_calls": c2},
        {"role": "tool", "tool_call_id": t2, "content": json.dumps({"temp_c": 18, "condition": "cloudy"})},
        {"role": "user", "content": "And Hamburg?"},
    ]
    post({"model": "gemma4", "messages": hist,
        "tools": [W], "tool_choice": "auto", "temperature": 0.0, "max_tokens": 256, "stream": False}, 'A3-hamburg')
else:
    print('A2 produced no second tool call - chain stops')

print()
print('=== Chain B: cross-tool question -> echo -> echo ===')
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
b1 = post({"model": "gemma4",
    "messages": [{"role": "user", "content": "Ask me one simple test question using the question tool."}],
    "tools": [Q, E], "tool_choice": "auto", "temperature": 0.0, "max_tokens": 256, "stream": False}, 'B1-question')
d1 = b1['choices'][0]['message']['tool_calls'] if b1 else []
u1 = d1[0]['id'] if d1 else None
assert u1, 'B1 no tool call'
histb = [
    {"role": "user", "content": "Ask me one simple test question using the question tool."},
    {"role": "assistant", "content": None, "tool_calls": d1},
    {"role": "tool", "tool_call_id": u1, "content": json.dumps({"answer": "A"})},
    {"role": "user", "content": "Now call the echo tool with my answer."},
]
b2 = post({"model": "gemma4", "messages": histb,
    "tools": [Q, E], "tool_choice": "auto", "temperature": 0.0, "max_tokens": 256, "stream": False}, 'B2-echo')
d2 = b2['choices'][0]['message']['tool_calls'] if b2 else []
u2 = d2[0]['id'] if d2 else None
if u2:
    histb += [
        {"role": "assistant", "content": None, "tool_calls": d2},
        {"role": "tool", "tool_call_id": u2, "content": json.dumps({"echoed": True})},
        {"role": "user", "content": "Now call the echo tool again with the word DONE."},
    ]
    post({"model": "gemma4", "messages": histb,
        "tools": [Q, E], "tool_choice": "auto", "temperature": 0.0, "max_tokens": 256, "stream": False}, 'B3-echo-again')
else:
    print('B2 produced no second tool call - chain stops')
print('EVID:', EVID)
