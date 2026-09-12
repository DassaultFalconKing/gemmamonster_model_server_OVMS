import csv
import collections

with open(r"C:\Users\testc\AppData\Local\Temp\opencode\bench_log.csv", "r") as f:
    rows = list(csv.DictReader(f))

by_test = collections.defaultdict(list)
for r in rows:
    by_test[r["test"]].append(r)

print("=" * 105)
print("  OVMS gemma4-26-heretic | 10 runs x 8 tests | TTFT + GEN SPEED")
print("=" * 105)
print("{:18s} | {:>5s} | {:>7s} {:>7s} {:>7s} | {:>7s} {:>7s} {:>7s} | {:>6s} {}".format(
    "TEST", "OK", "ttft avg", "ttft mn", "ttft mx",
    "gen avg", "gen mn", "gen mx", "tok", "FINISH"))
print("-" * 105)

order = ["baseline","tool_auto","tool_forced","agentic_loop","tool_required","tool_none","complex_schema","parallel_tools"]

for tname in order:
    recs = by_test[tname]
    ok = sum(1 for r in recs if r["status"] == "OK")
    valid = [r for r in recs if r["status"] == "OK"]

    ttfts = [float(r["ttft_s"]) for r in valid]
    gens = [float(r["tok_s_gen"]) for r in valid]
    cts = [int(r["comp_tok"]) for r in valid]

    avg_ttft = sum(ttfts)/len(ttfts) if ttfts else 0
    min_ttft = min(ttfts) if ttfts else 0
    max_ttft = max(ttfts) if ttfts else 0

    # Filter out garbage gen speeds from 1-3 token responses
    real_gens = [g for g, c in zip(gens, cts) if c >= 5]
    if real_gens:
        avg_gen = sum(real_gens)/len(real_gens)
        min_gen = min(real_gens)
        max_gen = max(real_gens)
    else:
        avg_gen = min_gen = max_gen = 0

    avg_ct = sum(cts)/len(cts) if cts else 0

    finish_counts = collections.Counter(r["finish_reason"] for r in recs)
    finish_str = " ".join("{}:{}".format(k, v) for k, v in finish_counts.most_common())

    print("{:18s} | {:>5s} | {:>6.2f}s {:>6.2f}s {:>6.2f}s | {:>6.1f} {:>6.1f} {:>6.1f} | {:>5.0f} {}".format(
        tname, "{}/10".format(ok),
        avg_ttft, min_ttft, max_ttft,
        avg_gen, min_gen, max_gen,
        avg_ct, finish_str))

print("-" * 105)

# Global stats
all_valid = [r for r in rows if r["status"] == "OK"]
all_ttfts = [float(r["ttft_s"]) for r in all_valid]
all_gens_raw = [(float(r["tok_s_gen"]), int(r["comp_tok"])) for r in all_valid]
real_all_gens = [g for g, c in all_gens_raw if c >= 5]

print("  GLOBAL TTFT:  avg {:.2f}s  min {:.2f}s  max {:.2f}s".format(
    sum(all_ttfts)/len(all_ttfts), min(all_ttfts), max(all_ttfts)))
print("  GLOBAL GEN:   avg {:.1f} tok/s  min {:.1f}  max {:.1f}  (responses >= 5 tok)".format(
    sum(real_all_gens)/len(real_all_gens), min(real_all_gens), max(real_all_gens)))
print("  TOTAL: {} OK / {} FAIL / {} requests".format(
    sum(1 for r in rows if r["status"]=="OK"),
    sum(1 for r in rows if r["status"]=="FAIL"),
    len(rows)))
print("=" * 105)
