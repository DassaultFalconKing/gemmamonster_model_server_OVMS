"""Attributed OVMS serve of Qwen3.6 with native packs (NO pack-build).

Path A / GPU. runtime_acceptance remains NO until operator signs off.
Uses verified pack-build-smoke dir (V2 sealed generation preferred when present).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

root = Path(r"C:\git\cib2-packv2-build-20261024")
rt = root / "ovms-runtime"
binding = Path(r"C:\git\cib2-packv2-ovms-20261024\bazel-bin\src\python\binding")
model = Path(r"C:\Users\testc\qwen36-35b-a3b-baseline\models\Qwen3.6-35B-A3B-int4-ov")
weights = model / "openvino_language_model.bin"

# Prefer sealed V2 generation if active.v2.json exists; else raw verified packs.
pack_dir = root / "pack-build-smoke"
gens = root / "packv2-generations"
active = gens / "active.v2.json"
if active.is_file():
    import json

    pointer = json.loads(active.read_text(encoding="utf-8"))
    cand = gens / pointer["generation"]
    if cand.is_dir():
        pack_dir = cand
        print("using sealed generation:", pack_dir)
    else:
        print("active.v2.json present but generation missing; falling back to", pack_dir)
else:
    print("no sealed generation yet; using verified packs:", pack_dir)

ratio = os.environ.get("OFFLOAD_RATIO", "20")
rest_port = os.environ.get("OVMS_REST_PORT", "8000")
grpc_port = os.environ.get("OVMS_GRPC_PORT", "9000")
cache = root / f"cache-pack-serve-r{ratio}"
cache.mkdir(parents=True, exist_ok=True)
log_path = root / f"pack-serve-r{ratio}-ovms.log"
receipt = root / f"ovms-pack-serve-r{ratio}-attributed.json"
# Expert hit/miss trace (optional). Set MOE_OTD_TRACE to a writable file path before launch.
if not os.environ.get("MOE_OTD_TRACE"):
    os.environ["MOE_OTD_TRACE"] = str(root / f"moe-otd-trace-r{ratio}.log")
print("MOE_OTD_TRACE=", os.environ["MOE_OTD_TRACE"])

os.environ["PYTHONHOME"] = str(root / "python312")
os.environ["PYTHONPATH"] = str(binding) + os.pathsep + str(rt)
os.environ["PATH"] = str(rt) + os.pathsep + str(root / "python312") + os.pathsep + os.environ.get("PATH", "")

plugin = (
    '{"OFFLOAD_RATIO":'
    + str(int(ratio))
    + ',"WEIGHTS_PATH":"'
    + weights.as_posix()
    + '"}'
)

cmd = [
    str(root / "python312" / "python.exe"),
    str(root / "run-attributed.py"),
    "--receipt",
    str(receipt),
    "--timeout",
    os.environ.get("OVMS_SERVE_TIMEOUT", "14400"),
    "--cwd",
    str(rt),
    "--dll-dir",
    str(rt),
    "--dll-dir",
    str(root / "python312"),
    "--cache-dir",
    str(cache),
    "--",
    str(rt / "ovms.exe"),
    "--moe_experts_pack_dir",
    str(pack_dir),
    "--model_path",
    str(model),
    "--model_name",
    "qwen",
    "--target_device",
    "GPU",
    "--task",
    "text_generation",
    "--tool_parser",
    "qwen3coder",
    "--reasoning_parser",
    "qwen3",
    "--max_num_batched_tokens",
    "16384",
    "--cache_interval_multiplier",
    "64",
    "--plugin_config",
    plugin,
    "--cache_dir",
    str(cache),
    "--port",
    grpc_port,
    "--rest_port",
    rest_port,
    "--log_level",
    "INFO",
    "--log_path",
    str(log_path),
]
print("OFFLOAD_RATIO=", ratio, "rest_port=", rest_port, "grpc_port=", grpc_port)
print("NOTE: no --build_moe_experts_pack; require packs from", pack_dir)
print("runtime_acceptance=NO; Path B OFF")
raise SystemExit(subprocess.call(cmd))
