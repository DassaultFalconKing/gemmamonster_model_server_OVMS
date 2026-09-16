from pathlib import Path
import json, xml.etree.ElementTree as ET, shutil, subprocess
out=Path(__file__).parent
root=Path(r'C:\git\gemma4-rc-main-promotion-20260916')
head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
assert head==(out/'tested-head.txt').read_text().strip()
assert (out/'exit-code.txt').read_text().strip()=='0'
results=[]
for short in ['generation_policy','phantom_tool_call','chunk_invariance','rendered_prompt_state','f7_contract','f10_guard']:
    name=f'gemma4_{short}_test'
    src=root/'bazel-testlogs/src/test/llm/gemma4_generation'/name
    tree=ET.parse(src/'test.xml')
    cases=list(tree.iter('testcase'))
    bad=[c.attrib for c in cases if c.find('failure') is not None or c.find('error') is not None or c.find('skipped') is not None or c.attrib.get('status')=='notrun']
    assert cases and not bad, (name,len(cases),bad)
    target=out/'test-results'/name; target.mkdir(parents=True,exist_ok=True)
    for f in ['test.xml','test.log']:
        shutil.copy2(src/f,target/f)
    results.append({'target':f'//src/test/llm/gemma4_generation:{name}','status':'PASS','tests':len(cases),'skipped':0,'failures':0})
events=[json.loads(line) for line in (out/'test-events.json').read_text().splitlines() if line.strip()]
summaries=[e['testSummary'] for e in events if 'testSummary' in e]
assert len(summaries)==6 and all(s['overallStatus']=='PASSED' for s in summaries)
assert all(s.get('totalNumCached',0)==0 for s in summaries), summaries
data={'tested_head':head,'status':'PASS','cache_test_results':False,'total_tests':sum(r['tests'] for r in results),'targets':results}
(out/'test-summary.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data,indent=2))
