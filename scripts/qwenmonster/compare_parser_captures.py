#!/usr/bin/env python3
"""Compare recorded vLLM, llama.cpp and OVMS tool outputs to a fixed native Qwen corpus.

Capture adapters are intentionally out of scope: this oracle never guesses the
native wire, runs a model or claims to have executed a peer implementation.
Use one JSONL record per fixture id. Only completed tool calls are accepted.
"""
import argparse
import json
import sys
from pathlib import Path


def jsonl(path):
    with open(path, encoding="utf-8") as source:
        for line_no, line in enumerate(source, 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: {exc}") from exc
            if not isinstance(value, dict) or not isinstance(value.get("id"), str):
                raise ValueError(f"{path}:{line_no}: record requires string id")
            yield value


def read_records(path):
    records = {}
    for record in jsonl(path):
        key = record["id"]
        if key in records:
            raise ValueError(f"Duplicate capture id: {key}")
        records[key] = record
    return records


def extract_calls(record):
    """Read completed OpenAI tool calls or a normalized parser adapter record."""
    message = record
    if "choices" in message:
        choices = message["choices"]
        if len(choices) != 1:
            raise ValueError("Expected exactly one OpenAI choice per capture")
        message = choices[0].get("message", {})
    elif "message" in message:
        message = message["message"]
    calls = message.get("tool_calls", [])
    if not isinstance(calls, list):
        raise ValueError("tool_calls must be a list")

    seen_ids = set()
    normalized = []
    for ordinal, tool in enumerate(calls):
        function = tool.get("function", tool)
        name = function.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"tool {ordinal}: missing function name")
        args = function.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError as exc:
                raise ValueError(f"tool {ordinal}: invalid JSON arguments: {exc}") from exc
        if not isinstance(args, dict):
            raise ValueError(f"tool {ordinal}: function.arguments must decode to object")
        tool_id = tool.get("id")
        if tool_id is not None:
            if not isinstance(tool_id, str) or not tool_id or tool_id in seen_ids:
                raise ValueError(f"tool {ordinal}: duplicate or empty call id")
            seen_ids.add(tool_id)
        index = tool.get("index")
        if index is not None and index != ordinal:
            raise ValueError(f"tool {ordinal}: index {index} is not call-local order")
        normalized.append({"name": name, "arguments": args})
    return normalized


def compare(expected, captures):
    failures = []
    for key, fixture in expected.items():
        if key not in captures:
            failures.append(f"{key}: missing capture")
            continue
        try:
            got = extract_calls(captures[key])
            want = fixture["expected_tool_calls"]
            if got != want:
                failures.append(f"{key}: mismatch\n  expected={json.dumps(want, ensure_ascii=False, sort_keys=True)}\n  actual={json.dumps(got, ensure_ascii=False, sort_keys=True)}")
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            failures.append(f"{key}: invalid capture: {exc}")
    for extra in sorted(captures.keys() - expected.keys()):
        failures.append(f"{extra}: unknown fixture id")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--engine", required=True, help="label only; does not run the engine")
    args = parser.parse_args()
    try:
        fixtures = read_records(args.fixtures)
        captures = read_records(args.capture)
        failures = compare(fixtures, captures)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"{args.engine}: fixtures={len(fixtures)}, captures={len(captures)}, failures={len(failures)}")
    for failure in failures:
        print("FAIL", failure, file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
