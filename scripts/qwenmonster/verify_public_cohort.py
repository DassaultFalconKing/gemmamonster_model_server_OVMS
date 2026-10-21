#!/usr/bin/env python3
"""Offline source-cohort preflight. Verifies Git HEADs + semantic source markers.

No checkout, CMake, compilation, device, grammar matcher or live server is run.
A PASS here is SOURCE ONLY; it must never be reported as BUILD/UNIT/LIVE GREEN.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "docs/qwenmonster/public-source-lock.json"

# Source-level smoke signatures, not a substitute for unit or live acceptance.
SIGNATURES = {
    "genai": [
        ("src/cpp/include/openvino/genai/generation_config.hpp",
         ["std::optional<int> max_whitespace_cnt",
          "std::optional<int> whitespace_bound = std::nullopt",
          "struct QwenXMLParametersFormat",
          "qwen_xml_parameter"]),
    ],
    "xgrammar": [
        ("cpp/grammar_parser.cc",
         ["int32_t EBNFParser::ParseExcludeToken()",
          "AddExcludeTokenSet(token_ids)",
          "The complement of an empty set accepts any token"]),
        ("cmake/config.cmake",
         ["option(XGRAMMAR_BUILD_PYTHON_BINDINGS", "option(XGRAMMAR_BUILD_CXX_TESTS"]),
    ],
    "minja": [
        ("include/minja/chat-template.hpp",
         ["renders_tool_arguments", "call:ipython", "supports_tool_calls"]),
    ],
    "openvino": [
        ("src/common/transformations/src/ov_ops/moe_compressed.cpp",
         ["MOE::get_config()", "visit_attributes"]),
    ],
}


def git(directory, *args):
    try:
        p = subprocess.run(["git", "-C", str(directory), *args],
                           text=True, capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    return (p.stdout.strip(), "") if p.returncode == 0 else (None, p.stderr.strip())


def inspect_source(name, path):
    failures = []
    for relative, markers in SIGNATURES.get(name, []):
        file = path / relative
        try:
            content = file.read_text(encoding="utf-8")
        except OSError as exc:
            failures.append(f"{relative}: {exc}")
            continue
        for marker in markers:
            if marker not in content:
                failures.append(f"{relative}: expected source marker absent: {marker}")
        if name == "xgrammar" and relative == "cpp/grammar_parser.cc":
            pos = content.find("int32_t EBNFParser::ParseExcludeToken()")
            if pos != -1:
                fragment = content[pos:pos + 1400]
                if 'ExcludeToken() requires at least one integer argument' in fragment:
                    failures.append("ExcludeToken still refuses the empty argument list")
    return failures


def check_one(name, directory, pinned, allow_descendant, strict_clean):
    result = {"component": name, "path": str(directory.resolve()),
              "pinned_sha": pinned, "status": "FAIL", "issues": []}
    if not directory.is_dir():
        result["issues"].append("Directory does not exist")
        return result
    head, err = git(directory, "rev-parse", "HEAD")
    if head is None:
        result["issues"].append(f"git HEAD unavailable: {err}")
        return result
    result["actual_sha"] = head
    if head != pinned:
        if allow_descendant:
            ancestor, _ = git(directory, "merge-base", "--is-ancestor", pinned, head)
            # A successful merge-base --is-ancestor has zero stdout and exit status 0.
            if ancestor is None:
                result["issues"].append("OVMS checkout does not descend from locked C6 SHA")
        else:
            result["issues"].append("HEAD does not match locked source commit")
    dirty, err = git(directory, "status", "--porcelain")
    if dirty is None:
        result["issues"].append(f"git status failed: {err}")
    result["dirty"] = bool(dirty) if dirty is not None else None
    if strict_clean and dirty:
        result["issues"].append("Git checkout is dirty under --strict-clean")
    result["issues"].extend(inspect_source(name, directory))
    result["status"] = "SOURCE PASS" if not result["issues"] else "FAIL"
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("genai", "xgrammar", "openvino", "minja"):
        p.add_argument(f"--{name}", type=Path, required=True)
    p.add_argument("--tokenizers", type=Path,
                   help="Optional: verify the upstream tokenizers source revision")
    p.add_argument("--ovms", type=Path, default=ROOT,
                   help="OVMS checkout; descendants of original C6 are permitted")
    p.add_argument("--strict-clean", action="store_true",
                   help="Fail on working tree modifications")
    p.add_argument("--json-report", type=Path, help="Write machine-readable evidence")
    args = p.parse_args()

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    checks = []
    for name in ("genai", "xgrammar", "openvino", "minja"):
        checks.append(check_one(name, getattr(args, name),
                                lock["components"][name]["sha"], False,
                                args.strict_clean))
    checks.append(check_one("ovms", args.ovms,
                            lock["components"]["ovms"]["sha"], True,
                            args.strict_clean))
    if args.tokenizers:
        checks.append(check_one("tokenizers", args.tokenizers,
                                lock["components"]["tokenizers"]["sha"],
                                False, args.strict_clean))
    else:
        checks.append({"component": "tokenizers", "status": "NOT CHECKED",
                       "issues": ["Provide --tokenizers to check the optional pinned source"]})

    report = {"cohort": lock["cohort"], "source_checks": checks,
              "acceptance": "SOURCE ONLY - BUILD/UNIT/LIVE NOT ESTABLISHED",
              "cmake_overrides": {
                  "FETCHCONTENT_SOURCE_DIR_XGRAMMAR": str(args.xgrammar.resolve()).replace("\\", "/"),
                  "FETCHCONTENT_SOURCE_DIR_MINJA": str(args.minja.resolve()).replace("\\", "/")}}
    for check in checks:
        print(f'{check["component"]}: {check["status"]}' +
              (f' ({check.get("actual_sha", "unavailable")[:12]})' if check.get("actual_sha") else ""))
        for issue in check["issues"]:
            print(f"  - {issue}")
    print("GenAI configure must explicitly override XGrammar and Minja sources:")
    for key, value in report["cmake_overrides"].items():
        print(f"  -D{key}={value}")
    print(report["acceptance"])
    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 1 if any(c["status"] == "FAIL" for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
