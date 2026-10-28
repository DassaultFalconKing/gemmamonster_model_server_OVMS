import difflib
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
DOCS = Path(__file__).resolve().parent
ROOT = Path(r"C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\rca")
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(16*1024**2), b''): h.update(chunk)
    return h.hexdigest()
model=json.loads((DOCS/'model-lock.json').read_text())
for row in model['files']:
    path=Path(model['local_dir'])/row['path']
    assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'], f"MODEL DRIFT: {path}"
print(f"MODEL_LOCK_PASS {len(model['files'])} files",flush=True)
prefix='openvino.genai-5f7f1278107d7eae3990ce906bbcfcb69ac3397f'
patch=[]
with zipfile.ZipFile(ROOT/'genai-source.zip') as archive:
    for relative in ('src/cpp/src/continuous_batching/pipeline_impl.cpp','src/cpp/src/visual_language/inputs_embedder.cpp'):
        old=archive.read(prefix+'/'+relative).decode().splitlines(True)
        new=(ROOT/'source'/prefix/relative).read_text().splitlines(True)
        patch.extend(difflib.unified_diff(old,new,fromfile='a/'+relative,tofile='b/'+relative))
(DOCS/'genai-trace.patch').write_text(''.join(patch))
receipt={"source_commit":prefix.removeprefix('openvino.genai-'),"source_zip_sha256":sha(ROOT/'genai-source.zip'),"observer_patch_sha256":sha(DOCS/'genai-trace.patch'),"trace_dll_sha256":sha(ROOT/'trace-runtime/openvino_genai.dll'),"probe_exe_sha256":sha(ROOT/'rca_probe.exe'),"model_lock_verified_files":len(model['files']),"features":{"BUILD_TOKENIZERS":False,"ENABLE_XGRAMMAR":False,"ENABLE_GGUF":True,"ENABLE_PYTHON":False,"ENABLE_TESTS":False,"ENABLE_SAMPLES":False,"ENABLE_TOOLS":False},"scope":"diagnostic build only; no performance or release acceptance"}
(ROOT/'trace-build-lock.json').write_text(json.dumps(receipt,indent=2)+'\n')
dest=DOCS/'rca-evidence';dest.mkdir(exist_ok=True)
for path in ROOT.glob('*.json'):
    if not path.name.startswith('genai-'): shutil.copy2(path,dest/path.name)
for mode,number in (('baseline',3),('mtp',4)):
    source=ROOT/'traces-v2'/f'P0-{mode}'
    target=dest/'trace-events'/f'P0-{mode}';target.mkdir(parents=True,exist_ok=True)
    for path in source.glob('*.txt'):
        if path.name.startswith('input-') or int(path.name.split('-')[1])<=number:
            shutil.copy2(path,target/path.name)
    shutil.copy2(source/f'event-{number}.bin',target/f'event-{number}.bin')
    for rep in (0,1):
        path=ROOT/'trace-runs-v2'/f'P0-{mode}-rep{rep}.json'
        shutil.copy2(path,dest/('trace-v2-'+path.name))
print('EVIDENCE_FROZEN',flush=True)
