import json
import time
import urllib.request
import csv
import os

BASE_URL = "http://localhost:8000/v3/chat/completions"
RUNS = 10
JSON_DIR = r"C:\Users\testc\AppData\Local\Temp\opencode"
LOG_FILE = os.path.join(JSON_DIR, "hybrid_log.csv")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Get current stock price for a ticker",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_info",
            "description": "Get company fundamentals and recent news",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_financial_ratio",
            "description": "Calculate a financial ratio from raw data",
            "parameters": {
                "type": "object",
                "properties": {
                    "ratio": {"type": "string", "enum": ["P/E", "P/B", "ROE", "Debt/Equity", "Current Ratio"]},
                    "numerator": {"type": "number"},
                    "denominator": {"type": "number"}
                },
                "required": ["ratio", "numerator", "denominator"]
            }
        }
    }
]


def stream_request(body_obj, timeout=120):
    """Stream request, return metrics + raw chunks for tool call extraction."""
    body_obj["stream"] = True
    body_obj["stream_options"] = {"include_usage": True}
    data = json.dumps(body_obj).encode("utf-8")
    req = urllib.request.Request(BASE_URL, data=data, headers={"Content-Type": "application/json"}, method="POST")

    t_start = time.time()
    ttft = None
    first_token_time = None
    chunks = []
    completion_tokens = 0
    prompt_tokens = 0

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        while True:
            raw = resp.readline()
            if not raw:
                break
            line = raw.decode("utf-8").strip()
            if not line or not line.startswith("data: "):
                continue
            if line == "data: [DONE]":
                break
            now = time.time()
            payload = json.loads(line[6:])
            chunks.append(payload)

            if ttft is None:
                choices = payload.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    tc = delta.get("tool_calls")
                    if content is not None or tc is not None:
                        ttft = now - t_start
                        first_token_time = now

            usage = payload.get("usage")
            if usage:
                completion_tokens = usage.get("completion_tokens", 0) or 0
                prompt_tokens = usage.get("prompt_tokens", 0) or 0

    total_time = time.time() - t_start
    if ttft is None:
        ttft = total_time
    gen_time = total_time - ttft if first_token_time else 0
    tok_s_gen = completion_tokens / gen_time if gen_time > 0 else 0

    finish = "unknown"
    for ch in reversed(chunks):
        choices = ch.get("choices", [])
        if choices and choices[0].get("finish_reason"):
            finish = choices[0]["finish_reason"]
            break

    return {
        "ttft": ttft, "gen_time": gen_time, "total_time": total_time,
        "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
        "tok_s_gen": tok_s_gen, "finish_reason": finish, "chunks": chunks,
    }


def extract_tool_calls(chunks):
    """Reconstruct tool_calls from streaming chunks."""
    tool_calls = []
    for ch in chunks:
        choices = ch.get("choices", [])
        if not choices:
            continue
        delta = choices[0].get("delta", {})
        tc = delta.get("tool_calls")
        if tc:
            for t in tc:
                idx = t.get("index", 0)
                while len(tool_calls) <= idx:
                    tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                if t.get("id"):
                    tool_calls[idx]["id"] = t["id"]
                fn = t.get("function", {})
                if fn.get("name"):
                    tool_calls[idx]["function"]["name"] = fn["name"]
                if fn.get("arguments"):
                    tool_calls[idx]["function"]["arguments"] += fn["arguments"]
    return tool_calls


TESTS = {
    "hybrid_simple": {
        "type": "single",
        "body": {
            "model": "gemma4-26-heretic",
            "messages": [
                {"role": "system", "content": "You are a senior financial analyst. When analyzing stocks, first gather data using tools, then provide a thorough analysis with clear reasoning."},
                {"role": "user", "content": "Analyze Tesla (TSLA) for me. Get the current price, company info, calculate P/E ratio (earnings per share is $3.12), and give me your investment thesis with bull and bear cases. Be thorough and show your reasoning."}
            ],
            "tools": TOOLS,
            "tool_choice": "auto",
            "max_tokens": 512
        }
    },
    "hybrid_multi_tool": {
        "type": "single",
        "body": {
            "model": "gemma4-26-heretic",
            "messages": [
                {"role": "system", "content": "You are a quantitative analyst. Think step by step, show your reasoning."},
                {"role": "user", "content": "I have a portfolio: 40%% AAPL, 30%% MSFT, 20%% NVDA, 10%% TSLA. Get current prices for all 4, calculate my portfolio allocation drift from target, and explain step by step what rebalancing trades I need. Show all math."}
            ],
            "tools": TOOLS,
            "tool_choice": "auto",
            "max_tokens": 1024
        }
    },
    "hybrid_reasoning_chain": {
        "type": "multi",
        "turn1": {
            "model": "gemma4-26-heretic",
            "messages": [
                {"role": "system", "content": "You are a senior financial analyst. Think step by step."},
                {"role": "user", "content": "Compare Apple and Microsoft. Get both stock prices, both company info, and calculate P/E for both (Apple EPS $6.42, Microsoft EPS $12.88). Then give me a detailed comparison."}
            ],
            "tools": TOOLS,
            "tool_choice": "auto",
            "max_tokens": 256
        },
        "turn2_messages": [
            {"role": "system", "content": "You are a senior financial analyst. Think step by step."},
            {"role": "user", "content": "Compare Apple and Microsoft. Get both stock prices, both company info, and calculate P/E for both (Apple EPS $6.42, Microsoft EPS $12.88). Then give me a detailed comparison."}
        ],
        "turn2_tool_results": [
            {"role": "tool", "tool_call_id": "c1", "content": '{"ticker":"AAPL","price":220.15,"change":-1.2}'},
            {"role": "tool", "tool_call_id": "c2", "content": '{"ticker":"MSFT","price":420.50,"change":+0.8}'},
            {"role": "tool", "tool_call_id": "c3", "content": '{"ticker":"AAPL","sector":"Technology","market_cap":"3.4T","pe_ratio":34.3,"recent_news":"iPhone 17 launch, AI features expansion"}'},
            {"role": "tool", "tool_call_id": "c4", "content": '{"ticker":"MSFT","sector":"Technology","market_cap":"3.1T","pe_ratio":32.6,"recent_news":"Azure AI growth, Copilot enterprise adoption"}'},
            {"role": "tool", "tool_call_id": "c5", "content": '{"ratio":"P/E","result":34.27}'},
            {"role": "tool", "tool_call_id": "c6", "content": '{"ratio":"P/E","result":32.61}'}
        ],
        "turn2_tools": TOOLS,
        "turn2_tool_choice": "none",
        "turn2_max_tokens": 512
    }
}


with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("run,test,finish_reason,prompt_tok,comp_tok,ttft_s,gen_time_s,total_s,tok_s_gen,status\n")

for r in range(1, RUNS + 1):
    print(f"\n=== RUN {r} / {RUNS} ===", flush=True)

    for tname, tconf in TESTS.items():
        try:
            if tconf["type"] == "single":
                res = stream_request(tconf["body"].copy())
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{r},{tname},{res['finish_reason']},{res['prompt_tokens']},{res['completion_tokens']},"
                            f"{res['ttft']:.3f},{res['gen_time']:.3f},{res['total_time']:.3f},"
                            f"{res['tok_s_gen']:.1f},OK\n")
                print(f"  {tname:25s} ttft={res['ttft']:.3f}s  gen={res['tok_s_gen']:.1f} tok/s  "
                      f"{res['completion_tokens']}tok  [{res['finish_reason']}]", flush=True)

            elif tconf["type"] == "multi":
                # Turn 1: get tool calls
                res1 = stream_request(tconf["turn1"].copy())
                tool_calls = extract_tool_calls(res1["chunks"])

                # Turn 2: feed tool results, force text response
                t2_msgs = list(tconf["turn2_messages"])
                t2_msgs.append({
                    "role": "assistant", "content": None, "tool_calls": tool_calls
                })
                for tr in tconf["turn2_tool_results"]:
                    t2_msgs.append(dict(tr))

                turn2_body = {
                    "model": "gemma4-26-heretic",
                    "messages": t2_msgs,
                    "tools": tconf["turn2_tools"],
                    "tool_choice": tconf["turn2_tool_choice"],
                    "max_tokens": tconf["turn2_max_tokens"]
                }
                res2 = stream_request(turn2_body)

                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{r},{tname},{res2['finish_reason']},{res2['prompt_tokens']},{res2['completion_tokens']},"
                            f"{res2['ttft']:.3f},{res2['gen_time']:.3f},{res2['total_time']:.3f},"
                            f"{res2['tok_s_gen']:.1f},OK\n")
                print(f"  {tname:25s} ttft={res2['ttft']:.3f}s  gen={res2['tok_s_gen']:.1f} tok/s  "
                      f"{res2['completion_tokens']}tok  [{res2['finish_reason']}]", flush=True)

        except Exception as e:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{r},{tname},ERROR,0,0,0,0,0,0,FAIL\n")
            print(f"  {tname:25s} ERROR: {e}", flush=True)

print(f"\n=== DONE. Log: {LOG_FILE} ===")
