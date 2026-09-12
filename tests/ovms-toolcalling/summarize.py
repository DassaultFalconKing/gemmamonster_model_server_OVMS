import csv
import collections

with open(r"C:\Users\testc\AppData\Local\Temp\opencode\test_log.csv", "r") as f:
    rows = list(csv.DictReader(f))

by_test = collections.defaultdict(list)
for r in rows:
    by_test[r["test"]].append(r)

hdr = "{:18s} {:>5s}  {:>4s}  {:>8s}  {:>8s}  {:>8s}  {:>10s}  {}".format(
    "TEST", "OK/10", "RATE", "avg tok/s", "min", "max", "avg comp", "FINISH REASONS"
)
print("=" * 90)
print(hdr)
print("-" * 90)

order = ["baseline","tool_auto","tool_forced","agentic_loop","tool_required","tool_none","stream_tools","complex_schema","parallel_tools"]
for tname in order:
    recs = by_test[tname]
    ok = sum(1 for r in recs if r["status"] == "OK")
    valid = [r for r in recs if r["status"] == "OK" and float(r["tok_per_sec"]) > 0]
    if valid:
        tps_list = [float(r["tok_per_sec"]) for r in valid]
        ct_list = [int(r["tokens_completion"]) for r in valid]
        avg_tps = sum(tps_list)/len(tps_list)
        min_tps = min(tps_list)
        max_tps = max(tps_list)
        avg_ct = sum(ct_list)/len(ct_list)
    else:
        avg_tps = min_tps = max_tps = avg_ct = 0
    finish_counts = collections.Counter(r["finish_reason"] for r in recs)
    finish_str = " ".join("{}:{}".format(k, v) for k, v in finish_counts.most_common())
    line = "{:18s} {:>5s}  {:>3d}%  {:>8.1f}  {:>8.1f}  {:>8.1f}  {:>10.0f}  {}".format(
        tname, "{}/10".format(ok), ok*10, avg_tps, min_tps, max_tps, avg_ct, finish_str
    )
    print(line)

print("-" * 90)
all_ok = sum(1 for r in rows if r["status"] == "OK")
all_fail = sum(1 for r in rows if r["status"] == "FAIL")
all_valid = [r for r in rows if r["status"] == "OK" and float(r["tok_per_sec"]) > 0]
global_avg = sum(float(r["tok_per_sec"]) for r in all_valid)/len(all_valid) if all_valid else 0
print("TOTAL: {} OK / {} FAIL / {} requests".format(all_ok, all_fail, len(rows)))
print("GLOBAL AVG tok/s: {:.1f}".format(global_avg))
print("=" * 90)
