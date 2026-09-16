"""Complete the valid list_dir-first trajectories from the unchanged strict probes.
Original FAIL receipts remain intact; this is a separately recorded continuation.
"""
from pathlib import Path
import json

script=Path(__file__).with_name('live-dogfood.py')
# Load only the harness's definitions, never rerun its top-level campaign.
definitions=script.read_text(encoding='utf-8').split('\nsummary=[]\n',1)[0]
ns={'__file__':str(script)}
exec(compile(definitions,str(script),'exec'),ns)
out=ns['OUT']; request=ns['request']; execute=ns['execute']; save=ns['save']
summary=[]
for phase in ['warmup','measured-1','measured-2','measured-3']:
    original=f'{phase}-stream-required'
    body=json.loads((out/'requests'/f'{original}.json').read_text())
    initial=json.loads((out/'responses'/f'{original}.json').read_text())
    messages=body['messages']; msg=initial['message']; finish=initial['finish_reason']
    performed=[]
    try:
        for turn in range(1,9):
            calls=msg.get('tool_calls') or []
            if not calls:
                assert ('read_file','binary-provenance.txt') in performed, 'file never read'
                assert finish=='stop' and '2026.5.0.b722aa440' in msg.get('content',''), 'final not complete/grounded'
                summary.append({'case':original,'status':'PASS','total_assistant_turns':turn,'performed':performed,'final':msg['content']})
                break
            assert finish=='tool_calls'
            for call in calls:
                a=json.loads(call['function']['arguments'])
                performed.append((call['function']['name'],Path(a['path']).as_posix()))
            tag=f'{original}-continuation{turn}'
            messages += [msg]+execute(tag,msg)
            msg,finish=request(tag,messages,choice='auto',stream=True,parallel=False)
        else:
            raise AssertionError('no final within eight turns')
    except Exception as exc:
        summary.append({'case':original,'status':'FAIL','error':str(exc),'performed':performed})
    print(json.dumps(summary[-1]),flush=True)
    save(out/'stream-continuation-summary.json',summary)
    if summary[-1]['status']=='FAIL' and any(s in summary[-1]['error'] for s in ['HTTP Error','timed out','GPU fatal/quarantine']):
        break
