"""Verify local files against their pinned HF metadata and retain official sources."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


def run(model, evidence):
    inv=json.loads((evidence/'inventory.json').read_text(encoding='utf-8'))
    checks=[]
    for item in inv['files']:
        meta=item.get('download_metadata',[])
        if not meta: continue
        etag=meta[1].strip('"')
        if len(etag)==64:
            actual=item['sha256']
        else:
            data=(model/item['name']).read_bytes()
            actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        checks.append(dict(name=item['name'],revision=meta[0],etag=etag,actual=actual,status='PASS' if etag==actual else 'FAIL'))
    (evidence/'local-verification.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    revision=next(x['revision'] for x in checks if x['name']=='config.json')
    urls={
        'hf-snapshot.json':f'https://huggingface.co/api/models/OpenVINO/MiniCPM-V-4.7-35B-A3B-int4-ov/revision/{revision}?blobs=true',
        'nightly-vlm_config.cpp':'https://raw.githubusercontent.com/openvinotoolkit/openvino.genai/73c4b0db060/src/cpp/src/visual_language/vlm_config.cpp',
        'nightly-inputs_embedder.cpp':'https://raw.githubusercontent.com/openvinotoolkit/openvino.genai/73c4b0db060/src/cpp/src/visual_language/inputs_embedder.cpp',
        'nightly-vision_encoder.cpp':'https://raw.githubusercontent.com/openvinotoolkit/openvino.genai/73c4b0db060/src/cpp/src/visual_language/vision_encoder.cpp',
    }
    fetched=[]
    for name,url in urls.items():
        try:
            with urllib.request.urlopen(url,timeout=40) as response: data=response.read()
            (evidence/name).write_bytes(data)
            fetched.append(dict(url=url,file=name,sha256=hashlib.sha256(data).hexdigest(),status='PASS'))
        except Exception as e: fetched.append(dict(url=url,status='FAIL',error=str(e)))
    (evidence/'sources.json').write_text(json.dumps(fetched,indent=2),encoding='utf-8')
    print(json.dumps(dict(verified=len(checks),failures=sum(x['status']!='PASS' for x in checks),revisions=sorted(set(x['revision'] for x in checks)),sources=fetched),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    a=p.parse_args();run(a.model,a.evidence)
