"""Offline reanalysis of moe_otd_trace windows (no OVMS required).

Example (busy r20 receipt window):
  python reanalyze_moe_otd_trace.py ^
    --trace .../moe-otd-trace-r20-busy.log ^
    --skip-e 9418 --take-e 1173733 ^
    --receipt-before-e 9418 --expect-hits 1139305 --expect-misses 34428 ^
    --out-json docs/cib2/evidence/trace-reanalysis-r20-20261024.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from moe_otd_trace import parse_moe_otd_trace, reanalyze_window  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trace", type=Path, required=True)
    ap.add_argument("--skip-e", type=int, required=True, help="E-records to skip (receipt before count)")
    ap.add_argument("--take-e", type=int, required=True, help="E-records in window (after-before)")
    ap.add_argument("--expect-hits", type=int, default=None)
    ap.add_argument("--expect-misses", type=int, default=None)
    ap.add_argument("--expect-miss-bytes", type=int, default=None)
    ap.add_argument("--expect-miss-read-s", type=float, default=None)
    ap.add_argument("--runtime-label", default="cib2-packv2-r20-busy")
    ap.add_argument("--offload-ratio", default="20")
    ap.add_argument("--source-commit", default="")
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--eviction-reload-window", type=int, default=64)
    args = ap.parse_args()

    # Validate full-file after snapshot still matches take+skip if file wasn't extended
    full = parse_moe_otd_trace(args.trace)
    expected_after_e = args.skip_e + args.take_e
    file_extended = False
    if full.get("e_records") != expected_after_e:
        if full.get("e_records", 0) > expected_after_e:
            file_extended = True
        else:
            payload = {
                "validation_status": "INCOMPLETE",
                "error": "trace_shorter_than_receipt_window",
                "full_e_records": full.get("e_records"),
                "expected_after_e": expected_after_e,
            }
            args.out_json.parent.mkdir(parents=True, exist_ok=True)
            args.out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(payload, indent=2))
            return 2

    window = reanalyze_window(
        args.trace,
        skip_e=args.skip_e,
        take_e=args.take_e,
        eviction_reload_window=args.eviction_reload_window,
    )

    checks = {}
    cache = window.get("cache", {})
    mem = window.get("memory_transfer", {})
    if args.expect_hits is not None:
        checks["hits"] = {
            "expected": args.expect_hits,
            "got": cache.get("hits"),
            "ok": cache.get("hits") == args.expect_hits,
        }
    if args.expect_misses is not None:
        checks["misses"] = {
            "expected": args.expect_misses,
            "got": cache.get("misses"),
            "ok": cache.get("misses") == args.expect_misses,
        }
    if args.expect_miss_bytes is not None:
        checks["miss_bytes"] = {
            "expected": args.expect_miss_bytes,
            "got": mem.get("miss_bytes"),
            "ok": mem.get("miss_bytes") == args.expect_miss_bytes,
        }
    if args.expect_miss_read_s is not None:
        got = mem.get("miss_read_s")
        checks["miss_read_s"] = {
            "expected": args.expect_miss_read_s,
            "got": got,
            "ok": got is not None and abs(float(got) - args.expect_miss_read_s) < 0.0015,
        }

    all_ok = all(v.get("ok") for v in checks.values()) if checks else window.get("validation_status") == "OK"
    if window.get("validation_status") == "OK" and checks and not all_ok:
        window["validation_status"] = "MISMATCH"
    if file_extended and window.get("validation_status") == "OK":
        window["validation_status"] = "OK_TRUNCATED_TO_RECEIPT"
        window["note"] = (
            f"trace grew to {full.get('e_records')} E-records; analysis capped at "
            f"skip={args.skip_e} take={args.take_e} per receipt"
        )

    out = {
        "schema": "cib2.trace_reanalysis.v1",
        "runtime_acceptance": "NO",
        "source": {
            "commit": args.source_commit or None,
            "runtime_label": args.runtime_label,
            "offload_ratio": args.offload_ratio,
            "trace_basename": args.trace.name,
            "trace_bytes": args.trace.stat().st_size if args.trace.is_file() else None,
            "full_file_e_records": full.get("e_records"),
            "receipt_window": {"skip_e": args.skip_e, "take_e": args.take_e},
        },
        "receipt_checks": checks,
        "analysis": window,
        "not_measured": {
            "pack_verify_ns": "NOT_MEASURED — MOE_OTD_PERF_LOG / [OTD_PERF] absent in busy serve logs",
            "synchronous_execution_gate_wait_s": "NOT_MEASURED — no trace field",
            "onednn_ocl_drain_wait_s": "NOT_MEASURED — no trace field",
            "moe_otd_trace_overhead_s": "NOT_MEASURED — no control without MOE_OTD_TRACE",
            "seal_verify_cpu_contention": "NOT_MEASURED quantitatively — receipt contention.seal_verify_pid_alive=true only",
        },
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "validation_status": window.get("validation_status"),
                "hits": cache.get("hits"),
                "misses": cache.get("misses"),
                "hit_rate": cache.get("hit_rate"),
                "miss_read_s": mem.get("miss_read_s"),
                "miss_copy_s": mem.get("miss_copy_s"),
                "miss_transform_s": mem.get("miss_transform_s"),
                "out": str(args.out_json),
                "checks_ok": all_ok,
            },
            indent=2,
        )
    )
    return 0 if window.get("validation_status") in ("OK", "OK_TRUNCATED_TO_RECEIPT") and all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
