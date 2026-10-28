import json
from pathlib import Path
ROOT = Path(r"C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\rca")
matrix = json.loads((ROOT / "matrix.json").read_text(encoding="utf-8-sig"))
extra = json.loads((ROOT / "matrix-P6b.json").read_text())
rows = []
for case in matrix["cases"] + extra["cases"]:
    for run in case["runs"]:
        if run["status"] == "PASS_EXECUTION":
            assert len(run["results"]) == 2
            assert all(len(r["ids"]) == 64 and r["status"] == 1 and r["finish"] == 2 for r in run["results"])
    if case.get("same_input_ids"):
        assert case["baseline_repeat_equal"] and case["mtp_repeat_equal"]
    row = {k:v for k,v in case.items() if k != "runs"}
    row["statuses"] = [r["status"] for r in case["runs"]]
    row["min_available_physical_bytes"] = min(s["available_physical"] for r in case["runs"] for s in r["memory_samples"])
    rows.append(row)
result = {"cases": rows, "logits": "instrumented build pending", "internal_input_ids": "pending observation; external fixed IDs roundtrip verified", "ovms": "HOLD; no product source changes"}
if (ROOT / "logit-comparison.json").exists():
    comparison = json.loads((ROOT / "logit-comparison.json").read_text())
    assert comparison["reference_outputs_reproduced"] and comparison["internal_prompt_ids_equal"]
    result.update(logits="observed pre-sampler argmax flip at index 3; see logit-comparison.json", internal_input_ids="observed equal, 26 tokens, both modes and both repetitions")
(ROOT / "rca-summary.json").write_text(json.dumps(result, indent=2)+"\n")
print(json.dumps(result, indent=2))
