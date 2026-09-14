#!/usr/bin/env python3
"""Audit and package self-contained portable agent skills using stdlib only."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path
from typing import Any

FORMAT = "portable-agent-skill/v1"
REQUIRED_SURFACE = ["SKILL.md", "README.md", "INSTALL.md", "install.py", "install.sh", "install.ps1", "MANIFEST.json", "SHA256SUMS"]
TRANSIENT_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
TRANSIENT_SUFFIXES = {".pyc", ".pyo", ".tmp", ".swp"}
CORE_DOCS = ["SKILL.md", "README.md", "INSTALL.md"]
ABSOLUTE_PATTERNS = [
    re.compile(r"[A-Za-z]:\\(?:Users|home|git|src|work|tmp)\\", re.I),
    re.compile(r"/(?:home|Users|tmp|var/tmp|workspace)/[^\s`]+"),
]
ORIGIN_INSTALL_PATTERNS = [
    re.compile(r"git\s+clone[^\n]+https?://", re.I),
    re.compile(r"git\s+clone[^\n]+git@", re.I),
]
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.S)
NAME_RE = re.compile(r"^name:\s*([A-Za-z0-9-]+)\s*$", re.M)
DESC_RE = re.compile(r"^description:\s*(.+?)\s*$", re.M)


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def is_transient(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in TRANSIENT_PARTS for part in relative.parts):
        return True
    if path.suffix.lower() in TRANSIENT_SUFFIXES:
        return True
    return False


def payload_files(root: Path) -> list[Path]:
    root = root.resolve()
    return sorted(
        (p for p in root.rglob("*") if p.is_file() and not is_transient(p, root)),
        key=lambda p: rel(p, root),
    )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_skill_frontmatter(root: Path) -> tuple[str | None, str | None, list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    skill = root / "SKILL.md"
    if not skill.is_file():
        return None, None, [{"severity": "error", "code": "MISSING_SKILL_MD", "message": "SKILL.md is required"}]
    text = skill.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.search(text)
    if not match:
        return None, None, [{"severity": "error", "code": "INVALID_FRONTMATTER", "message": "SKILL.md needs YAML frontmatter"}]
    body = match.group("body")
    name_m = NAME_RE.search(body)
    desc_m = DESC_RE.search(body)
    name = name_m.group(1) if name_m else None
    desc = desc_m.group(1).strip() if desc_m else None
    if not name:
        issues.append({"severity": "error", "code": "MISSING_NAME", "message": "frontmatter name is required"})
    if not desc:
        issues.append({"severity": "error", "code": "MISSING_DESCRIPTION", "message": "frontmatter description is required"})
    return name, desc, issues


def _issue(severity: str, code: str, message: str, path: str | None = None) -> dict[str, str]:
    value = {"severity": severity, "code": code, "message": message}
    if path:
        value["path"] = path
    return value


def _manifest_expected(root: Path) -> set[str]:
    return {rel(p, root) for p in payload_files(root)}


def audit_skill(root: Path) -> dict[str, Any]:
    root = root.resolve()
    issues: list[dict[str, str]] = []
    name, description, fm_issues = parse_skill_frontmatter(root)
    issues.extend(fm_issues)

    for filename in REQUIRED_SURFACE:
        if not (root / filename).is_file():
            issues.append(_issue("error", "MISSING_PORTABLE_SURFACE", f"missing {filename}", filename))

    for filename in CORE_DOCS:
        path = root / filename
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(pattern.search(text) for pattern in ORIGIN_INSTALL_PATTERNS):
            issues.append(_issue("error", "ORIGIN_REPOSITORY_REQUIRED", "core install docs require cloning an origin repository", filename))
        for pattern in ABSOLUTE_PATTERNS:
            if pattern.search(text):
                issues.append(_issue("error", "MACHINE_ABSOLUTE_PATH", "core docs contain a machine-specific absolute path", filename))
                break
        if "REQUIRED BACKGROUND:" in text and not re.search(r"(?:if|when)\s+(?:it\s+is\s+)?available", text, re.I):
            issues.append(_issue("error", "EXTERNAL_SKILL_REQUIRED", "skill declares a hard dependency on another skill", filename))

    manifest_path = root / "MANIFEST.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("format") != FORMAT:
                issues.append(_issue("error", "MANIFEST_FORMAT", f"expected {FORMAT}", "MANIFEST.json"))
            if name and manifest.get("name") != name:
                issues.append(_issue("error", "MANIFEST_NAME", "manifest name differs from SKILL.md", "MANIFEST.json"))
            listed = set(manifest.get("files", []))
            actual = _manifest_expected(root)
            if listed != actual:
                missing = sorted(actual - listed)
                stale = sorted(listed - actual)
                issues.append(_issue("error", "MANIFEST_FILESET", f"manifest mismatch missing={missing} stale={stale}", "MANIFEST.json"))
        except (json.JSONDecodeError, TypeError) as exc:
            issues.append(_issue("error", "MANIFEST_INVALID", str(exc), "MANIFEST.json"))

    sums_path = root / "SHA256SUMS"
    if sums_path.is_file():
        expected_files = {rel(p, root): p for p in payload_files(root) if p.name != "SHA256SUMS"}
        seen: set[str] = set()
        for lineno, line in enumerate(sums_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                digest, filename = line.split("  ", 1)
            except ValueError:
                issues.append(_issue("error", "CHECKSUM_SYNTAX", f"line {lineno} is invalid", "SHA256SUMS"))
                continue
            seen.add(filename)
            path = expected_files.get(filename)
            if path is None:
                issues.append(_issue("error", "CHECKSUM_STALE", f"checksum references missing/transient file {filename}", "SHA256SUMS"))
            elif sha256(path) != digest:
                issues.append(_issue("error", "CHECKSUM_MISMATCH", filename, "SHA256SUMS"))
        missing = sorted(set(expected_files) - seen)
        if missing:
            issues.append(_issue("error", "CHECKSUM_MISSING", f"missing checksums: {missing}", "SHA256SUMS"))

    return {
        "format": FORMAT,
        "root": str(root),
        "name": name,
        "description": description,
        "pass": not any(i["severity"] == "error" for i in issues),
        "issues": issues,
    }


def refresh_metadata(root: Path, *, version: str = "1.0.0") -> dict[str, Any]:
    root = root.resolve()
    name, _description, issues = parse_skill_frontmatter(root)
    if issues or not name:
        raise ValueError(f"cannot refresh invalid skill frontmatter: {issues}")

    current = {rel(p, root) for p in payload_files(root)}
    current.update({"MANIFEST.json", "SHA256SUMS"})
    manifest = {
        "format": FORMAT,
        "name": name,
        "version": version,
        "entrypoint": "SKILL.md",
        "files": sorted(current),
    }
    (root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    files_for_sum = [p for p in payload_files(root) if p.name != "SHA256SUMS"]
    lines = [f"{sha256(p)}  {rel(p, root)}" for p in files_for_sum]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def _zip_mode(path: Path) -> int:
    if path.name == "install.sh" or path.suffix == ".py":
        return 0o755
    return 0o644


def package_skill(root: Path, output: Path) -> Path:
    root = root.resolve()
    output = output.resolve()
    report = audit_skill(root)
    if not report["pass"]:
        raise ValueError(f"portability audit failed: {report['issues']}")
    output.parent.mkdir(parents=True, exist_ok=True)
    prefix = root.name
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as zf:
        for path in payload_files(root):
            if path.resolve() == output:
                continue
            arcname = f"{prefix}/{rel(path, root)}"
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (_zip_mode(path) & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_STORED
            zf.writestr(info, path.read_bytes())
    return output


def _print_report(report: dict[str, Any]) -> None:
    print(f"PORTABILITY: {'PASS' if report['pass'] else 'FAIL'}")
    print(f"name: {report.get('name') or 'unknown'}")
    for item in report["issues"]:
        location = f" [{item.get('path')}]" if item.get("path") else ""
        print(f"- {item['severity'].upper()} {item['code']}{location}: {item['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit and package portable agent skills")
    sub = parser.add_subparsers(dest="command", required=True)
    p_audit = sub.add_parser("audit")
    p_audit.add_argument("skill", type=Path)
    p_refresh = sub.add_parser("refresh")
    p_refresh.add_argument("skill", type=Path)
    p_refresh.add_argument("--version", default="1.0.0")
    p_pack = sub.add_parser("package")
    p_pack.add_argument("skill", type=Path)
    p_pack.add_argument("output", type=Path)
    p_pack.add_argument("--version", default="1.0.0")
    args = parser.parse_args(argv)

    if args.command == "audit":
        report = audit_skill(args.skill)
        _print_report(report)
        return 0 if report["pass"] else 1
    if args.command == "refresh":
        refresh_metadata(args.skill, version=args.version)
        report = audit_skill(args.skill)
        _print_report(report)
        return 0 if report["pass"] else 1
    if args.command == "package":
        refresh_metadata(args.skill, version=args.version)
        report = audit_skill(args.skill)
        _print_report(report)
        if not report["pass"]:
            return 1
        output = package_skill(args.skill, args.output)
        print(f"package: {output}")
        print(f"sha256: {sha256(output)}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
