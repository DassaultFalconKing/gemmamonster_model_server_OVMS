"""Sequential, isolated-process native RCA matrix. No runtime/model mutations."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(os.environ.get("RCA_OUTPUT_ROOT", r"C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\rca"))
RUNTIME = Path(os.environ.get("RCA_RUNTIME_DIR", r"C:\gm\qwenmonster\releases\gemmamonster-2026.4-rc4\extracted-py_off\ovms"))
class Memory(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(k, ctypes.c_ulonglong) for k in ("total", "available", "commit_total", "commit_available", "virtual", "virtual_available", "extended")]
def memory():
    m = Memory(); m.length = ctypes.sizeof(m)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)): raise ctypes.WinError()
    return {"available_physical": m.available, "available_commit": m.commit_available}
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
env = dict(os.environ)
env["PATH"] = str(RUNTIME) + r";C:\Windows\System32;C:\Windows"
env.pop("PYTHONHOME", None); env.pop("PYTHONPATH", None)
matrix = [("P0", "u4", 128, "default"), ("P1", "u8", 128, "default"), ("P2", "u4", 0, "default"), ("P3", "f16", 0, "default"), ("P4", "f16", 128, "default"), ("P5", "u8", 0, "default"), ("P6", "u4", 128, "BY_TOKEN")]
suffix = ""
if len(sys.argv) > 1:
    matrix += [("P6b", "u8", 128, "BY_TOKEN")]
    matrix = [row for row in matrix if row[0] == sys.argv[1]]
    assert matrix, "unknown case"
    suffix = "-" + sys.argv[1]
report = {"scope": "native GenAI RCA; NOT OVMS acceptance", "input_boundary": "fixed IDs decoded to prompt with exact tokenizer roundtrip; string add_request; internal VLM token IDs NOT_EXPOSED (tensor API rejected)", "nat": 3, "max_new_tokens": 64, "repetitions": 2, "draft_plugin_properties": "same behavior as original probe: scheduler only at draft_model, target properties at CB constructor", "logits": "NOT_EXPOSED", "rejection_trace": "NOT_EXPOSED", "exe_sha256": sha(ROOT / "rca_probe.exe"), "cases": []}
def save(): (ROOT / ("matrix" + suffix + ".json")).write_text(json.dumps(report, indent=2) + "\n")
save()
for priority, kv, dq, key in matrix:
    case = {"priority": priority, "kv": kv, "dq": dq, "key_quant_mode": key, "runs": []}
    report["cases"].append(case)
    for mode in ("baseline", "mtp"):
        prefix = ROOT / f"{priority}-{mode}"
        row = {"mode": mode, "memory_before": memory()}
        case["runs"].append(row)
        if row["memory_before"]["available_physical"] < 3 * 1024**3:
            row["status"] = "BLOCKED_RESOURCE"; row["reason"] = "less than 3 GiB available before admission"; save(); continue
        print(f"START {priority} {mode} {kv} DQ{dq} key={key}", flush=True)
        command = [str(ROOT / "rca_probe.exe"), mode, kv, str(dq), key, str(prefix)]
        if os.environ.get("RCA_TRACE_ROOT"):
            trace_dir = Path(os.environ["RCA_TRACE_ROOT"]) / f"{priority}-{mode}"
            trace_dir.mkdir(parents=True, exist_ok=False)
            env["RCA_TRACE_DIR"] = str(trace_dir)
        row["command"] = command
        started = time.monotonic(); low_since = None; samples = []
        with prefix.with_suffix(".log").open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=ROOT)
            row["pid"] = process.pid
            while process.poll() is None:
                sample = {"elapsed": time.monotonic()-started, **memory()}; samples.append(sample)
                low = min(sample["available_physical"], sample["available_commit"]) < 512 * 1024**2
                low_since = (low_since or time.monotonic()) if low else None
                if low_since and time.monotonic()-low_since > 5:
                    row.update(status="BLOCKED_RESOURCE", reason="host guard: under 512 MiB available physical/commit for 5 seconds; no model reduction")
                    process.kill(); break
                if time.monotonic()-started > 300:
                    row.update(status="BLOCKED_TIMEOUT", reason="300-second case bound")
                    process.kill(); break
                time.sleep(1)
            row["exit_code"] = process.wait()
        row["memory_samples"] = samples
        text = prefix.with_suffix(".log").read_text(errors="replace")
        if "status" not in row:
            if row["exit_code"] == 0: row["status"] = "PASS_EXECUTION"
            elif any(term in text.lower() for term in ("key_cache_quant_mode", "unsupported", "does not support", "not supported")): row["status"] = "BLOCKED_CAPABILITY"
            else: row["status"] = "FAIL"
        receipt = Path(str(prefix) + "-input-ids.txt")
        if receipt.exists(): row["input_ids_sha256"] = sha(receipt)
        row["results"] = [json.loads(Path(str(prefix) + f"-rep{i}.json").read_text()) for i in range(2) if Path(str(prefix) + f"-rep{i}.json").exists()]
        print(f"END {priority} {mode} {row['status']} exit={row['exit_code']}", flush=True)
        save()
    base, draft = case["runs"]
    if len(base.get("results", [])) == len(draft.get("results", [])) == 2:
        assert base["input_ids_sha256"] == draft["input_ids_sha256"], "INPUT DRIFT"
        case["same_input_ids"] = True
        case["baseline_repeat_equal"] = base["results"][0]["ids"] == base["results"][1]["ids"]
        case["mtp_repeat_equal"] = draft["results"][0]["ids"] == draft["results"][1]["ids"]
        a, b = base["results"][0]["ids"], draft["results"][0]["ids"]
        first = next((i for i, (x,y) in enumerate(zip(a,b)) if x != y), min(len(a),len(b)) if len(a)!=len(b) else None)
        case["equivalence"] = "PASS" if first is None else "FAIL"
        case["first_difference_zero_based"] = first
        if first is not None: case["first_different_ids"] = {"baseline": a[first] if first<len(a) else None, "mtp": b[first] if first<len(b) else None, "common_generated_prefix": a[:first]}
        print(f"COMPARE {priority}: {case['equivalence']} first={first}", flush=True)
    save()
print("MATRIX_FINISHED", flush=True)
