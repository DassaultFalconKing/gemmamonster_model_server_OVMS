import json, pathlib
s = json.loads(pathlib.Path(r'C:\Users\testc\AppData\Local\Temp\opencode\rc2-roundtrip-forensics\run-001\summary.json').read_text(encoding='utf-8'))
print('turn1_usable:', s['turn1_usable'])
for v, d in s['variants'].items():
    for mode in ('unary', 'stream'):
        m = d[mode]
        ttfb = m['timing'].get('ttfb_s')
        total = m['timing'].get('total_s')
        if 'message' in m:
            content = m['message'].get('content')
        else:
            content = m.get('content')
        print('[%s/%s] http=%s finish=%s content=%r tools=%d usage=%s ttfb=%.2f total=%.2f ttft=%s toks=%.3f special=%s FAIL=%s' % (
            v, mode, m['http_status'], m['finish_reason'], content,
            len(m['tool_calls']), m.get('usage'), ttfb or -1, total or -1,
            m['timing'].get('ttft_s'), m['throughput'].get('tokens_per_second_wall') or -1,
            m.get('special_tokens'), m.get('failure_classes')))
        extra = [k for k in m.keys() if k not in ('http_status','transport_error','finish_reason','message','tool_calls','usage','timing','throughput','special_tokens','failure_classes','errors')]
        if extra:
            print('   extra keys:', extra)
print()
print('RUN-level keys:', [k for k in s.keys() if k not in ('variants','turn1')])
for k in ('failure_classes','classification','verdict','overall'):
    if k in s:
        print(k, '=', json.dumps(s[k], indent=2)[:1200])
