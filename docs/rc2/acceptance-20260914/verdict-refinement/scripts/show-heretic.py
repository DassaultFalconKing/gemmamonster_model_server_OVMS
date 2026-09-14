import json, pathlib
s = json.loads(pathlib.Path(r'C:\Users\testc\AppData\Local\Temp\opencode\rc2-roundtrip-forensics\heretic\run-001\summary.json').read_text(encoding='utf-8'))
t1 = s['turn1']
print('turn1: finish=%s content=%r tools=%d usage=%s FAIL=%s' % (
    t1['finish_reason'], t1['message'].get('content'), len(t1['tool_calls']), t1.get('usage'), t1.get('failure_classes')))
print('turn1_usable:', s['turn1_usable'])
for v, d in s['variants'].items():
    for mode in ('unary', 'stream'):
        m = d[mode]
        content = m['message'].get('content') if 'message' in m else m.get('content')
        print('[%s/%s] finish=%s content=%r tools=%d usage=%s FAIL=%s' % (
            v, mode, m['finish_reason'], (content or '')[:200], len(m['tool_calls']), m.get('usage'), m.get('failure_classes')))
print('localization:', json.dumps(s.get('localization'), ensure_ascii=False)[:800])
