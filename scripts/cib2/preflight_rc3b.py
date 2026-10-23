#!/usr/bin/env python3
"""CIB2 RC3B provenance preflight. Standard library only; does not run inference.

Exit 0: no failures (NOT_RUN checks may remain); exit 2: failure;
exit 3: --strict with unverified mandatory static gates. JSON stdout or --output file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

TAG = "qwm-semantic-refit-2026.4-rc3b"
PARENT_TAG = "qwm-semantic-refit-2026.4-rc3"
BASE = "b77b0f23fa7417e61778ef86ecb0ca739cc85f14"
PARENT = "b12a913ba492b951eb3384583e46541ffe467763"
MANIFEST = "docs/qwenmonster/RELEASE-CANDIDATE-20261023-RC3B-IDENTITY.json"
EXPECTED = {
    "ovms": ("2beed15ee7f6af9a2c45854005caff24886562c8da5586f052bd2133e3d671c2", 22589440),
    "ovms_test": ("aacd1f136a0142ade962f24543a8f3c4fb69b111689b353be3e2b397bc122f2c", 40527872),
}
ALLOWED_PREFIXES = ("docs/cib2/", "scripts/cib2/", "tests/cib2/")


@dataclass
class Check:
    id: str
    status: str
    detail: str


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=False, encoding="utf-8",
    )
    if r.returncode:
        raise RuntimeError("git " + " ".join(args) + ": " + r.stderr.strip())
    return r.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_changed_paths(paths: list[str]) -> list[str]:
    return [p for p in paths if not p.startswith(ALLOWED_PREFIXES)]


def verify_manifest(document: dict) -> list[str]:
    errors = []
    for key, value in (
        ("name", TAG),
        ("accepted", False),
        ("parent_tag", PARENT_TAG),
        ("parent", PARENT),
        ("branch", "semantic-refit-2026.4"),
    ):
        if document.get(key) != value:
            errors.append(f"{key}: expected {value!r}, got {document.get(key)!r}")
    build = document.get("build") or {}
    if build.get("config") != "win_mp_on_py_off":
        errors.append("build.config does not match win_mp_on_py_off")
    if "2026.4.0.0rc1" not in build.get("sdk", ""):
        errors.append("build.sdk is not the pinned isolated 2026.4.0.0rc1 SDK")
    if "stock SDK GPU" not in build.get("gpu_plugin", ""):
        errors.append("build.gpu_plugin does not claim stock SDK GPU")
    binaries = document.get("binaries") or []
    for kind, (expected_hash, expected_size) in EXPECTED.items():
        rows = [item for item in binaries if Path(item.get("path", "")).name == kind + ".exe"]
        if len(rows) != 1:
            errors.append(f"{kind}.exe: expected exactly one binary identity")
        elif rows[0].get("sha256", "").lower() != expected_hash or rows[0].get("bytes") != expected_size:
            errors.append(f"{kind}.exe: hash or size differs from RC3B identity")
    return errors


def check_file(checks: list[Check], name: str, path: Path | None, expected: tuple[str, int]) -> None:
    if path is None:
        checks.append(Check(name, "NOT_RUN", "Binary path not supplied; recorded hash is not live verification"))
        return
    if not path.is_file():
        checks.append(Check(name, "FAIL", f"Missing binary: {path.name}"))
        return
    actual_hash, actual_size = sha256(path), path.stat().st_size
    if actual_hash == expected[0] and actual_size == expected[1]:
        checks.append(Check(name, "PASS", f"SHA256 and size matched ({actual_size} bytes)"))
    else:
        checks.append(Check(name, "FAIL", f"Expected {expected[0]}/{expected[1]}, got {actual_hash}/{actual_size}"))


def check_plugin_pair(checks: list[Check], sdk: Path | None, active: Path | None) -> None:
    if sdk is None and active is None:
        checks.append(Check("stock_gpu_plugin", "NOT_RUN", "Supply both --sdk-gpu-plugin and --active-gpu-plugin"))
        return
    if sdk is None or active is None:
        checks.append(Check("stock_gpu_plugin", "FAIL", "Both plugin paths must be supplied together"))
        return
    if not sdk.is_file() or not active.is_file():
        checks.append(Check("stock_gpu_plugin", "FAIL", "SDK or active plugin path is not a file"))
        return
    a, b = sha256(sdk), sha256(active)
    checks.append(Check("stock_gpu_plugin", "PASS" if a == b else "FAIL",
                        f"SDK stock SHA256={a}; active SHA256={b}; exact binary equality={a == b}"))


def run(args: argparse.Namespace) -> tuple[dict, int]:
    checks: list[Check] = []
    repo = args.repo.resolve()
    try:
        top = Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
        if top != repo:
            checks.append(Check("repo_root", "FAIL", f"Expected repo root {repo}; actual root {top}"))
        else:
            checks.append(Check("repo_root", "PASS", "Repository root confirmed"))
        tag_sha = git(repo, "rev-parse", f"refs/tags/{TAG}^{{commit}}")
        parent_sha = git(repo, "rev-parse", f"refs/tags/{PARENT_TAG}^{{commit}}")
        checks.append(Check("rc3b_tag", "PASS" if tag_sha == BASE else "FAIL", f"{TAG} -> {tag_sha}"))
        checks.append(Check("rc3_parent_tag", "PASS" if parent_sha == PARENT else "FAIL",
                            f"{PARENT_TAG} -> {parent_sha}"))
        parent_of_base = git(repo, "rev-parse", f"{BASE}^")
        checks.append(Check("rc3b_direct_parent", "PASS" if parent_of_base == PARENT else "FAIL",
                            f"{BASE}^ -> {parent_of_base}"))
        try:
            git(repo, "merge-base", "--is-ancestor", BASE, "HEAD")
            checks.append(Check("head_ancestry", "PASS", f"HEAD descends from {BASE}"))
        except RuntimeError:
            checks.append(Check("head_ancestry", "FAIL", "HEAD does not descend from RC3B"))
        changed = git(repo, "diff", "--name-only", BASE, "HEAD").splitlines()
        unexpected = safe_changed_paths(changed)
        checks.append(Check("preflight_scope", "FAIL" if unexpected else "PASS",
                            f"Changed {len(changed)} committed paths; outside preflight scope: {unexpected}"))
        original = git(repo, "show", f"{BASE}:{MANIFEST}")
        checked_in = (repo / MANIFEST).read_text(encoding="utf-8").strip()
        checks.append(Check("manifest_immutable", "PASS" if original == checked_in else "FAIL",
                            "Working manifest equals tag content" if original == checked_in else "Manifest was changed"))
        problems = verify_manifest(json.loads(original))
        checks.append(Check("manifest_identity", "FAIL" if problems else "PASS",
                            "; ".join(problems) if problems else "All RC3B fields and recorded executable identities match"))
    except (RuntimeError, OSError, ValueError, json.JSONDecodeError) as exc:
        checks.append(Check("source_verification", "FAIL", str(exc).replace(str(repo), "<repo>")))

    check_file(checks, "ovms_binary", args.ovms_exe, EXPECTED["ovms"])
    check_file(checks, "ovms_test_binary", args.ovms_test_exe, EXPECTED["ovms_test"])
    check_plugin_pair(checks, args.sdk_gpu_plugin, args.active_gpu_plugin)
    checks.append(Check("sdk_rc1_source_abi", "NOT_RUN", "Exact 2026.4.0.0rc1 SDK source/ABI audit required on host"))
    checks.append(Check("full_ovms_test", "NOT_RUN", "Owner's full suite not covered by this static preflight"))
    checks.append(Check("gpu_live_perf", "NOT_RUN", "This preflight deliberately does not launch inference"))
    checks.append(Check("owner_signoff", "NOT_RUN", "RC3B manifest explicitly marks accepted=false"))
    statuses = [c.status for c in checks]
    verdict = "FAIL" if "FAIL" in statuses else ("INCOMPLETE" if "NOT_RUN" in statuses else "PASS")
    report = {
        "schema": "cib2-rc3b-preflight-v1",
        "base_tag": TAG,
        "base_sha": BASE,
        "verdict": verdict,
        "checks": [asdict(c) for c in checks],
        "counts": {s: statuses.count(s) for s in ("PASS", "FAIL", "NOT_RUN")},
        "acceptance": "NOT_ACCEPTED",
    }
    mandatory = {
        "repo_root", "rc3b_tag", "rc3_parent_tag", "rc3b_direct_parent",
        "head_ancestry", "preflight_scope", "manifest_immutable",
        "manifest_identity", "ovms_binary", "ovms_test_binary", "stock_gpu_plugin",
    }
    mandatory_incomplete = any(c.status == "NOT_RUN" and c.id in mandatory for c in checks)
    exit_code = 2 if verdict == "FAIL" else (3 if args.strict and mandatory_incomplete else 0)
    return report, exit_code


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=Path.cwd())
    p.add_argument("--ovms-exe", type=Path)
    p.add_argument("--ovms-test-exe", type=Path)
    p.add_argument("--sdk-gpu-plugin", type=Path)
    p.add_argument("--active-gpu-plugin", type=Path)
    p.add_argument("--output", type=Path, help="Write JSON report (no private paths should be committed)")
    p.add_argument("--strict", action="store_true", help="Return nonzero if any mandatory static gate is NOT_RUN")
    args = p.parse_args()
    report, code = run(args)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
