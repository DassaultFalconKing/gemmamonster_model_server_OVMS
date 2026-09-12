import json
import time
import urllib.request
import csv
import os
import sys

BASE_URL = "http://localhost:8000/v3/chat/completions"
MODEL = "gemma4-26-heretic"
RUNS = 10
JSON_DIR = r"C:\Users\testc\AppData\Local\Temp\opencode"
LOG_FILE = os.path.join(JSON_DIR, "bench_log.csv")

TESTS = [
    ("baseline",       "test1.json"),
    ("tool_auto",      "test2.json"),
    ("tool_forced",    "test3b.json"),
    ("agentic_loop",   "test4.json"),
    ("tool_required",  "test5.json"),
    ("tool_none",      "test_none.json"),
    ("complex_schema", "test_complex.json"),
    ("parallel_tools", "test_multi_tool.json"),
]

def stream_request(body_obj, timeout=120):
    """Send request with stream=true, measure TTFT and gen time."""
    body_obj["stream"] = True
    body_obj["stream_options"] = {"include_usage": True}
    data = json.dumps(body_obj).encode("utf-8")
    req = urllib.request.Request(BASE_URL, data=data, headers={"Content-Type": "application/json"}, method="POST")

    t_start = time.time()
    ttft = None
    first_token_time = None
    last_chunk_time = None
    chunks = []
    completion_tokens = 0
    prompt_tokens = 0

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        buffer = ""
        while True:
            raw = resp.readline()
            if not raw:
                break
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            if line == "data: [DONE]":
                break
            if not line.startswith("data: "):
                continue

            now = time.time()
            payload = json.loads(line[6:])
            chunks.append(payload)

            if ttft is None:
                delta = payload.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                tc = delta.get("tool_calls")
                if content is not None or tc is not None:
                    ttft = now - t_start
                    first_token_time = now

            usage = payload.get("usage")
            if usage:
                completion_tokens = usage.get("completion_tokens", 0) or 0
                prompt_tokens = usage.get("prompt_tokens", 0) or 0

            last_chunk_time = now

    total_time = time.time() - t_start
    if ttft is None:
        ttft = total_time

    gen_time = total_time - ttft if last_chunk_time and first_token_time else 0
    tok_s_gen = completion_tokens / gen_time if gen_time > 0 else 0
    tok_s_total = completion_tokens / total_time if total_time > 0 else 0

    finish = "unknown"
    if chunks:
        last_ch = chunks[-1].get("choices", [{}])
        if last_ch:
            finish = last_ch[0].get("finish_reason", "unknown")

    return {
        "ttft": ttft,
        "gen_time": gen_time,
        "total_time": total_time,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tok_s_gen": tok_s_gen,
        "tok_s_total": tok_s_total,
        "finish_reason": finish,
    }

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("run,test,finish_reason,prompt_tok,comp_tok,ttft_s,gen_time_s,total_s,tok_s_gen,tok_s_total,status\n")

for r in range(1, RUNS + 1):
    print(f"\n=== RUN {r} / {RUNS} ===", flush=True)
    for tname, tfilename in TESTS:
        fpath = os.path.join(JSON_DIR, tfilename)
        with open(fpath, "r", encoding="utf-8") as jf:
            body = json.load(jf)

        try:
            res = stream_request(body)
            status = "OK"
            print(f"  {tname:18s} ttft={res['ttft']:.3f}s  gen={res['gen_time']:.3f}s  "
                  f"total={res['total_time']:.3f}s  {res['completion_tokens']}tok  "
                  f"gen={res['tok_s_gen']:.1f} tok/s  avg={res['tok_s_total']:.1f} tok/s  [{res['finish_reason']}]", flush=True)
        except Exception as e:
            res = {"ttft":0,"gen_time":0,"total_time":0,"prompt_tokens":0,"completion_tokens":0,
                   "tok_s_gen":0,"tok_s_total":0,"finish_reason":"ERROR"}
            status = "FAIL"
            print(f"  {tname:18s} ERROR: {e}", flush=True)

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{r},{tname},{res['finish_reason']},{res['prompt_tokens']},{res['completion_tokens']},"
                    f"{res['ttft']:.3f},{res['gen_time']:.3f},{res['total_time']:.3f},"
                    f"{res['tok_s_gen']:.1f},{res['tok_s_total']:.1f},{status}\n")

print(f"\n=== DONE. Log: {LOG_FILE} ===")
