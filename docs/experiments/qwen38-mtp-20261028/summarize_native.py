"""Summarize the isolated native GenAI probe, never the OVMS HTTP matrix."""
import csv
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(r"C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\runs")
groups = {}
for mode in ("baseline", "mtp"):
    for row in csv.DictReader((ROOT / f"native-{mode}.csv").open()):
        if int(row["rep"]) < 0:
            continue
        key = (mode, int(row["nat"]))
        groups.setdefault(key, []).append(row)
reference = (ROOT / "native-baseline-nat0-rep0.txt").read_bytes()
summary = []
for (mode, nat), rows in groups.items():
    assert len(rows) == 5, (mode, nat, len(rows))
    matches = [
        (ROOT / f"native-{mode}-nat{nat}-rep{r['rep']}.txt").read_bytes() == reference
        for r in rows
    ]
    assert all(int(r["tokens"]) == 64 for r in rows), rows
    summary.append({
        "mode": mode, "nat": nat, "n": len(rows),
        "median_seconds": statistics.median(float(r["seconds"]) for r in rows),
        "median_tokens_per_wall_second": statistics.median(64 / float(r["seconds"]) for r in rows),
        "output_matches_baseline": sum(matches),
        "raw_statuses": sorted({int(r["status"]) for r in rows}),
        "raw_finish_reasons": sorted({int(r["finish_reason"]) for r in rows}),
    })
baseline = next(r["median_seconds"] for r in summary if r["mode"] == "baseline")
for row in summary:
    row["speedup_by_median_wall_time"] = baseline / row["median_seconds"]
result = {
    "scope": "Native GenAI CB, RC4 DLLs, GPU, one short text prompt, 64 generated tokens; NOT OVMS acceptance",
    "warmups_per_configuration": 2,
    "reference_output_sha256": hashlib.sha256(reference).hexdigest(),
    "results": summary,
    "not_run": ["OVMS patched build", "HTTP/SSE/tools", "long context", "image input", "full A/B/C matrix", "acceptance rate"],
}
(ROOT / "native-summary.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
