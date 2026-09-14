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
    print('[%s] HTTP=%s finish=%s content=%r tools=%d usage=%s' % (name, code, f, (m.get('content') or '')[:150], len(m.get('tool_calls', [])), u))
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

t = post({"model": "gemma4",
    "messages": [{"role": "user", "content": "Ask me one simple test question using the question tool. Do not explain instead."}],
    "tools": [QTOOL], "tool_choice": "required", "temperature": 0.0, "max_tokens": 256, "stream": False}, 'E6-turn1')
calls = t['choices'][0]['message'].get('tool_calls', []) if t else []
tid = calls[0].get('id') if calls else None
print('tool_id:', tid)
assert tid, 'no turn1 tool call'

print('--- E6a: assistant tool_calls in history, NO tool message, user follow-up ---')
post({"model": "gemma4", "messages": [
    {"role": "user", "content": "Ask me one simple test question using the question tool."},
    {"role": "assistant", "content": None, "tool_calls": calls},
    {"role": "user", "content": "Actually, never mind the tool. Just reply with exactly OK."}],
    "tools": [QTOOL], "tool_choice": "auto", "temperature": 0.0, "max_tokens": 64, "stream": False}, 'E6a-assistant-toolcalls-no-toolmsg')

print('--- E8a: tool result as PLAIN STRING ---')
post({"model": "gemma4", "messages": [
    {"role": "user", "content": "Ask me one simple test question using the question tool."},
    {"role": "assistant", "content": None, "tool_calls": calls},
    {"role": "tool", "tool_call_id": tid, "content": "Blue"}],
    "tools": [QTOOL], "tool_choice": "auto", "temperature": 0.0, "max_tokens": 256, "stream": False}, 'E8a-tool-result-plain-string')

print('--- E8b: tool result as JSON ARRAY string ---')
post({"model": "gemma4", "messages": [
    {"role": "user", "content": "Ask me one simple test question using the question tool."},
    {"role": "assistant", "content": None, "tool_calls": calls},
    {"role": "tool", "tool_call_id": tid, "content": "[\"Blue\"]"}],
    "tools": [QTOOL], "tool_choice": "auto", "temperature": 0.0, "max_tokens": 256, "stream": False}, 'E8b-tool-result-json-array')
print('EVID:', EVID)
