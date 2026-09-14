#!/usr/bin/env python3
from __future__ import annotations
import argparse, shutil
from pathlib import Path

SKILL_NAME = 'autonomous-test-fix-retest'

def main():
    p=argparse.ArgumentParser(description="Install autonomous-test-fix-retest into a local skill root")
    p.add_argument("target_root", nargs="?", type=Path, default=Path.home()/".agents"/"skills")
    args=p.parse_args()
    src=Path(__file__).resolve().parent
    target_root=args.target_root.expanduser().resolve()
    target=target_root/SKILL_NAME
    if target.resolve()==src:
        print(f"already installed: {target}")
        return 0
    target_root.mkdir(parents=True, exist_ok=True)
    if target.exists(): shutil.rmtree(target)
    shutil.copytree(src, target, ignore=shutil.ignore_patterns(".git","__pycache__","*.pyc","*.pyo"))
    print(f"installed: {target}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
