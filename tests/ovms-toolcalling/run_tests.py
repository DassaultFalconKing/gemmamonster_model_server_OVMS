import json
import time
import urllib.request
import urllib.error
import csv
import os
import sys

BASE_URL = "http://localhost:8000/v3/chat/completions"
MODEL = "gemma4-26-heretic"
RUNS = 10
JSON_DIR = r"C:\Users\testc\AppData\Local\Temp\opencode"
LOG_FILE = os.path.join(JSON_DIR, "test_log.csv")

TESTS = [
    ("baseline",       "test1.json"),
    ("tool_auto",      "test2.json"),
    ("tool_forced",    "test3b.json"),
    ("agentic_loop",   "test4.json"),
    ("tool_required",  "test5.json"),
    ("tool_none",      "test_none.json"),
    ("stream_tools",   "test_stream.json"),
    ("complex_schema", "test_complex.json"),
    ("parallel_tools", "test_multi_tool.json"),
]

def do_request(body_bytes, timeout=60):
    req = urllib.request.Request(
        BASE_URL,
        data=body_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")

def parse_stream(raw):
    lines = raw.strip().split("\n")
    chunks = []
    for line in lines:
        if line.startswith("data: ") and line != "data: [DONE]":
            try:
                chunks.append(json.loads(line[6:]))
            except:
                pass
    if not chunks:
        return None, 0, 0, 0
    prompt_tok = chunks[0].get("usage", {}).get("prompt_tokens", 0) or 0
    last = chunks[-1]
    comp_tok = last.get("usage", {}).get("completion_tokens", 0) or 0
    total_tok = last.get("usage", {}).get("total_tokens", 0) or 0
    finish = last.get("choices", [{}])[0].get("finish_reason", "unknown")
    return finish, prompt_tok, comp_tok, total_tok

def parse_normal(raw):
    d = json.loads(raw)
    ch = d.get("choices", [{}])[0]
    finish = ch.get("finish_reason", "unknown")
    u = d.get("usage", {})
    return finish, u.get("prompt_tokens", 0), u.get("completion_tokens", 0), u.get("total_tokens", 0)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("run,test,finish_reason,tokens_prompt,tokens_completion,tokens_total,time_sec,tok_per_sec,status\n")

for r in range(1, RUNS + 1):
    print(f"\n=== RUN {r} / {RUNS} ===", flush=True)
    for tname, tfilename in TESTS:
        fpath = os.path.join(JSON_DIR, tfilename)
        with open(fpath, "r", encoding="utf-8") as jf:
            body = jf.read()

        is_stream = (tname == "stream_tools")
        t0 = time.time()
        status = "OK"
        try:
            raw = do_request(body.encode("utf-8"), timeout=120)
            elapsed = time.time() - t0
            if is_stream:
                finish, pt, ct, tt = parse_stream(raw)
            else:
                finish, pt, ct, tt = parse_normal(raw)
            tps = round(ct / elapsed, 1) if elapsed > 0 else 0
            print(f"  {tname:18s} {finish:15s} {ct:4d}tok {elapsed:6.2f}s {tps:6.1f} tok/s", flush=True)
        except urllib.error.URLError as e:
            elapsed = time.time() - t0
            finish, pt, ct, tt, tps = "TIMEOUT", 0, 0, 0, 0
            status = "FAIL"
            print(f"  {tname:18s} TIMEOUT ({elapsed:.1f}s)", flush=True)
        except Exception as e:
            elapsed = time.time() - t0
            finish, pt, ct, tt, tps = "ERROR", 0, 0, 0, 0
            status = "FAIL"
            print(f"  {tname:18s} ERROR: {e}", flush=True)

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{r},{tname},{finish},{pt},{ct},{tt},{elapsed:.2f},{tps},{status}\n")

print(f"\n=== DONE. Log: {LOG_FILE} ===")
