import json, urllib.request, urllib.error
BASE = "http://127.0.0.1:18091/v3/chat/completions"

def post(payload):
    req = urllib.request.Request(BASE, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    try:
        r = urllib.request.urlopen(req, timeout=240)
    except urllib.error.HTTPError as e:
        r = e
    with r:
        return r.status, json.loads(r.read())

QTOOL = {"type": "function", "function": {
    "name": "question", "description": "Ask one question.",
    "parameters": {"type": "object",
        "properties": {"questions": {"type": "array", "items": {"type": "object",
            "properties": {"question": {"type": "string"}, "header": {"type": "string"},
                "options": {"type": "array", "items": {"type": "object",
                    "properties": {"label": {"type": "string"}, "description": {"type": "string"}},
                    "required": ["label", "description"], "additionalProperties": False}},
                "multiple": {"type": "boolean"}, "custom": {"type": "boolean"}},
            "required": ["question", "header", "options"], "additionalProperties": False}}},
        "required": ["questions"], "additionalProperties": False}}}

code, t1 = post({"model": "gemma4",
    "messages": [{"role": "user", "content": "Ask me one simple test question using the question tool. Do not explain instead."}],
    "tools": [QTOOL], "tool_choice": "required", "temperature": 0.0, "max_tokens": 256, "stream": False})
calls = t1['choices'][0]['message']['tool_calls']
tid = calls[0]['id']
print('turn1 tid:', tid)
code, t2 = post({"model": "gemma4", "messages": [
    {"role": "user", "content": "Ask me one simple test question using the question tool."},
    {"role": "assistant", "content": None, "tool_calls": calls},
    {"role": "tool", "tool_call_id": tid, "content": json.dumps({"answer": "A"})}],
    "tools": [QTOOL], "tool_choice": "auto", "temperature": 0.0, "max_tokens": 256, "stream": False})
m = t2['choices'][0]['message']
print('turn2:', code, t2['choices'][0].get('finish_reason'), repr(m.get('content')), len(m.get('tool_calls', [])), t2.get('usage'))
print('MARKER_TID:', tid)
