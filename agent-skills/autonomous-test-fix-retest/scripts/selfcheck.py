#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["SKILL.md", "README.md", "INSTALL.md", "install.py", "install.sh", "install.ps1", "MANIFEST.json", "SHA256SUMS"]
FORBIDDEN = [r"[A-Za-z]:\\", r"/home/[^ <`]+", r"/Users/[^ <`]+", r"DassaultFalconKing/gemmamonster_model_server_OVMS", r"--branch\s+skills/autonomous-test-fix-retest"]

def sha256(path: Path) -> str:
    h = hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()

def main() -> int:
    errors=[]
    for name in REQUIRED:
        if not (ROOT/name).is_file(): errors.append(f"missing: {name}")
    skill=(ROOT/"SKILL.md").read_text(encoding="utf-8") if (ROOT/"SKILL.md").exists() else ""
    if not skill.startswith("---\nname: autonomous-test-fix-retest\n"): errors.append("invalid SKILL.md frontmatter")
    for name in ["SKILL.md","README.md","INSTALL.md"]:
        if not (ROOT/name).exists(): continue
        text=(ROOT/name).read_text(encoding="utf-8")
        for pattern in FORBIDDEN:
            if re.search(pattern,text): errors.append(f"hard binding in {name}: {pattern}")
    if (ROOT/"MANIFEST.json").exists():
        manifest=json.loads((ROOT/"MANIFEST.json").read_text(encoding="utf-8"))
        for rel in manifest.get("files",[]):
            if not (ROOT/rel).is_file(): errors.append(f"manifest missing file: {rel}")
    if (ROOT/"SHA256SUMS").exists():
        for line in (ROOT/"SHA256SUMS").read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            digest, rel=line.split("  ",1)
            p=ROOT/rel
            if not p.is_file(): errors.append(f"checksum missing file: {rel}")
            elif sha256(p)!=digest: errors.append(f"checksum mismatch: {rel}")
    if errors:
        print("PORTABILITY: FAIL")
        for error in errors: print("-",error)
        return 1
    print("PORTABILITY: PASS")
    return 0
if __name__ == "__main__": raise SystemExit(main())
