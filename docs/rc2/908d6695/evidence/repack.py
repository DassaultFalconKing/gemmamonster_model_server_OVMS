import os, shutil, hashlib, json, zipfile, subprocess, time, urllib.request
from pathlib import Path

source = Path(r'C:\gemmamonster-artifacts\candidates\2026.4\908d6695-maintainer-rc2-rc2-product-20260913T223554Z')
root = Path(r'C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914')
root.mkdir(exist_ok=False)
logs = root / 'logs'
logs.mkdir()
runtime = root / 'ovms'
shutil.copytree(source / 'ovms', runtime)
def digest(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
hashes = {p.relative_to(runtime).as_posix(): digest(p) for p in runtime.rglob('*') if p.is_file()}
for rel,h in hashes.items():
    assert digest(source / 'ovms' / rel) == h, rel
(root / 'SHA256SUMS.txt').write_text(''.join(f'{h}  ovms/{rel}\n' for rel,h in sorted(hashes.items())), encoding='ascii')
archive = root / 'ovms.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for rel in hashes: z.write(runtime / rel, 'ovms/' + rel)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    z.extractall(root / 'extracted')
test_runtime = root / 'extracted' / 'ovms'
for rel,h in hashes.items(): assert digest(test_runtime / rel) == h, rel
print('ZIP_ROUNDTRIP_PASS', len(hashes), archive.stat().st_size, flush=True)
