"""Live GPU pack-serve: correctness + speed metrics (TTFT / TPS / wall).

Assumes OVMS already listening on OVMS_REST_PORT (default 8000).
Writes JSON receipt. runtime_acceptance stays NO.

Env:
  LIVE_RECEIPT, OFFLOAD_RATIO, OVMS_REST_PORT, OVMS_MODEL_NAME, SMOKE_WAIT_S
  LIVE_LOAD_LABEL=busy|free|…  (tagged into receipt for busy-vs-free compare)
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from moe_otd_trace import parse_moe_otd_trace  # noqa: E402

ROOT = Path(r"C:\git\cib2-packv2-build-20261024")
PORT = int(os.environ.get("OVMS_REST_PORT", "8000"))
MODEL = os.environ.get("OVMS_MODEL_NAME", "qwen")
BASE = f"http://127.0.0.1:{PORT}"
URLS = [f"{BASE}/v3/chat/completions", f"{BASE}/v1/chat/completions"]
RATIO = os.environ.get("OFFLOAD_RATIO", "20")
LOAD_LABEL = os.environ.get("LIVE_LOAD_LABEL", "unspecified")
OUT = Path(os.environ.get("LIVE_RECEIPT", str(ROOT / f"live-gpu-r{RATIO}-metrics-{LOAD_LABEL}.json")))
TRACE_PATH = Path(os.environ.get("MOE_OTD_TRACE", str(ROOT / f"moe-otd-trace-r{RATIO}-{LOAD_LABEL}.log")))
UMA_PROBE = Path(os.environ.get("UMA_PROBE_EXE", str(ROOT / "probe_windows_uma.exe")))


def post(url: str, messages: list, max_tokens: int, temperature: float = 0.0) -> tuple[int, dict | str, float]:
    body = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
    ).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            dt = time.perf_counter() - t0
            try:
                return resp.status, json.loads(raw), dt
            except json.JSONDecodeError:
                return resp.status, raw, dt
    except urllib.error.HTTPError as exc:
        dt = time.perf_counter() - t0
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw), dt
        except json.JSONDecodeError:
            return exc.code, raw, dt
    except Exception as exc:  # noqa: BLE001
        return -1, str(exc), time.perf_counter() - t0


def stream_ttft(
    url: str, messages: list, max_tokens: int, temperature: float = 0.0
) -> dict:
    """SSE chat completion: TTFT = first contentful token/chunk; e2e wall; rough decode TPS."""
    body = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    t0 = time.perf_counter()
    ttft = None
    pieces: list[str] = []
    usage: dict = {}
    http = -1
    err = None
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            http = resp.status
            while True:
                line = resp.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if not text or text.startswith(":"):
                    continue
                if not text.startswith("data:"):
                    continue
                data = text[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj.get("usage"), dict):
                    usage = obj["usage"]
                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                # TTFT = first visible token (content preferred; reasoning counts if model thinks first)
                chunk = delta.get("content") or ""
                if not chunk:
                    chunk = delta.get("reasoning_content") or ""
                if chunk:
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    pieces.append(chunk)
    except urllib.error.HTTPError as exc:
        http = exc.code
        err = exc.read().decode("utf-8", errors="replace")[:400]
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
    wall = time.perf_counter() - t0
    completion = int(usage.get("completion_tokens") or 0)
    if completion <= 0:
        # fallback rough token estimate if usage missing
        completion = max(1, len("".join(pieces).split())) if pieces else 0
    decode_s = (wall - ttft) if (ttft is not None and wall > ttft) else None
    decode_tps = (completion / decode_s) if (decode_s and decode_s > 0 and completion > 0) else None
    e2e_tps = (completion / wall) if (wall > 0 and completion > 0) else None
    return {
        "http": http,
        "ttft_s": round(ttft, 4) if ttft is not None else None,
        "wall_s": round(wall, 4),
        "decode_s": round(decode_s, 4) if decode_s is not None else None,
        "prompt_tokens": int(usage.get("prompt_tokens") or 0) or None,
        "completion_tokens": completion or None,
        "decode_tokens_per_s": round(decode_tps, 3) if decode_tps is not None else None,
        "e2e_tokens_per_s": round(e2e_tps, 3) if e2e_tps is not None else None,
        "chars": len("".join(pieces)),
        "preview": "".join(pieces)[:200],
        "pass": http == 200 and ttft is not None and completion > 0,
        "error": err,
        "usage": usage,
    }


def content_of(payload: dict | str) -> str:
    """Prefer message.content; fall back to reasoning_content (qwen3 reasoning parser)."""
    if not isinstance(payload, dict):
        return str(payload)
    try:
        msg = payload["choices"][0]["message"]
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning_content") or ""
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning
        return content or reasoning or ""
    except Exception:  # noqa: BLE001
        return json.dumps(payload)[:500]


def usage_of(payload: dict | str) -> dict:
    if isinstance(payload, dict) and isinstance(payload.get("usage"), dict):
        return payload["usage"]
    return {}


def pick_url() -> str | None:
    probe = [{"role": "user", "content": "ping"}]
    for url in URLS:
        code, _, _ = post(url, probe, max_tokens=4)
        if code == 200:
            return url
        if code not in (-1, 404, 503):
            # unexpected but endpoint exists
            return url
    return None


def sample_uma(label: str) -> dict:
    """One-shot Windows UMA/WDDM sample via probe_windows_uma.exe (N3 probe)."""
    import subprocess

    if not UMA_PROBE.is_file():
        return {"label": label, "present": False, "error": f"missing {UMA_PROBE}"}
    try:
        raw = subprocess.check_output([str(UMA_PROBE)], text=True, timeout=30)
        line = raw.strip().splitlines()[-1] if raw.strip() else ""
        obj = json.loads(line) if line.startswith("{") else {"raw": line}
        obj["label"] = label
        obj["present"] = True
        obj["ts"] = time.time()
        # helpers
        if "system_total_bytes" in obj and "system_available_bytes" in obj:
            used = int(obj["system_total_bytes"]) - int(obj["system_available_bytes"])
            obj["system_used_bytes"] = used
            obj["system_used_GB"] = round(used / (1024**3), 3)
            obj["system_available_GB"] = round(int(obj["system_available_bytes"]) / (1024**3), 3)
        if "wddm_process_usage_bytes" in obj:
            obj["wddm_process_usage_GB"] = round(int(obj["wddm_process_usage_bytes"]) / (1024**3), 3)
        if "wddm_remaining_bytes" in obj:
            obj["wddm_remaining_GB"] = round(int(obj["wddm_remaining_bytes"]) / (1024**3), 3)
        return obj
    except Exception as exc:  # noqa: BLE001
        return {"label": label, "present": False, "error": str(exc)}


def wait_ready(timeout_s: int = 1800) -> str:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        url = pick_url()
        if url:
            # confirm non-error generation
            code, payload, _ = post(url, [{"role": "user", "content": "Reply with OK"}], 8)
            last = f"{url} {code} {str(payload)[:120]}"
            if code == 200 and "OK" in content_of(payload).upper() or code == 200:
                return url
        time.sleep(5)
    raise TimeoutError(f"OVMS not ready within {timeout_s}s last={last}")


def main() -> int:
    url = wait_ready(int(os.environ.get("SMOKE_WAIT_S", "1800")))
    cases = []
    uma_samples = [sample_uma("before_speed")]
    # Note hit/miss: requires OVMS started with MOE_OTD_TRACE=<path> (same path as TRACE_PATH).
    trace_before = parse_moe_otd_trace(TRACE_PATH)

    # Correctness: short asks but enough max_tokens for qwen3 reasoning_content spill
    correct_prompts = [
        ("math", "What is 17+25? Reply with only the number 42 at the end.", "42"),
        ("identity", "Eventually reply with exactly the word PACKED on its own line.", "PACKED"),
    ]
    for name, prompt, expect in correct_prompts:
        code, payload, dt = post(url, [{"role": "user", "content": prompt}], max_tokens=256)
        text = content_of(payload).strip()
        ok = code == 200 and expect.lower() in text.lower()
        cases.append(
            {
                "kind": "correctness",
                "name": name,
                "http": code,
                "latency_s": round(dt, 3),
                "expect_substr": expect,
                "got": text[:400],
                "pass": ok,
                "usage": usage_of(payload),
            }
        )

    # --- Speed: medium + long prompts/completions (primary measurement) ---
    # Medium ~1–2k chars in, ~256–384 tokens out; long ~4–6k chars in, ~512 tokens out.
    medium_blob = (
        "Background on Pack V2 / OTDPACK1 for MoE expert offload. "
        "Each layer stores 256 experts with nine-slice records, placement permutation, "
        "and residency hints. Seal publishes an immutable generation with SHA256 digests. "
        "Runtime loads packs via OFFLOAD_RATIO on GPU with demand paging. "
    ) * 12  # ~2k+ chars
    long_blob = (
        "Extended context for prefill stress. Logical expert ids map to physical slots; "
        "miss stalls, UMA pressure, and decode batching matter for TTFT and tokens/s. "
        "Repeat marker EXPERT_PACK_LAYER for retrieval: "
    ) + ("EXPERT_PACK_LAYER " * 180)  # ~4k+ chars

    speed = []
    ttft_runs = []

    def _record_nonstream(cell: str, run: int, prompt: str, max_tokens: int) -> None:
        code, payload, dt = post(url, [{"role": "user", "content": prompt}], max_tokens=max_tokens)
        usage = usage_of(payload)
        completion = int(usage.get("completion_tokens") or 0)
        prompt_tok = int(usage.get("prompt_tokens") or 0)
        tps = (completion / dt) if dt > 0 and completion > 0 else None
        speed.append(
            {
                "cell": cell,
                "run": run,
                "mode": "non_stream",
                "http": code,
                "wall_s": round(dt, 3),
                "prompt_chars": len(prompt),
                "prompt_tokens": prompt_tok,
                "completion_tokens": completion,
                "max_tokens": max_tokens,
                "completion_tokens_per_s": round(tps, 3) if tps is not None else None,
                "pass": code == 200 and completion >= max(32, max_tokens // 8),
                "preview": content_of(payload)[:200],
            }
        )

    def _record_stream(cell: str, run: int, prompt: str, max_tokens: int) -> None:
        tr = stream_ttft(url, [{"role": "user", "content": prompt}], max_tokens=max_tokens)
        tr.update(
            {
                "cell": cell,
                "run": run,
                "mode": "stream",
                "prompt_chars": len(prompt),
                "max_tokens": max_tokens,
                "pass": bool(tr.get("pass")) and (tr.get("completion_tokens") or 0) >= max(32, max_tokens // 8),
            }
        )
        ttft_runs.append(tr)

    # Warmup (discard) — medium-ish so caches settle
    warmup = post(
        url,
        [{"role": "user", "content": medium_blob[:800] + "\nWarmup: write two sentences on MoE packing."}],
        64,
    )
    stream_ttft(
        url,
        [{"role": "user", "content": medium_blob[:600] + "\nWarmup stream: write three sentences."}],
        48,
    )

    # Medium cell: 2 non-stream + 2 stream
    for i in range(2):
        prompt = (
            f"{medium_blob}\n\nTask run={i}: Write a detailed ~200-word technical explanation of "
            f"how OFFLOAD_RATIO interacts with expert pack residency and decode latency. "
            f"Use concrete steps; do not stop early."
        )
        _record_nonstream("medium", i, prompt, max_tokens=320)
        _record_stream("medium", i, prompt + "\n(stream measurement)", max_tokens=320)

    # Long cell: 1 non-stream + 2 stream (TTFT under heavier prefill)
    for i in range(2):
        prompt = (
            f"{long_blob}\n\nTask run={i}: Using the context above, write a structured ~350-word brief covering "
            f"(1) prefill cost, (2) TTFT, (3) decode tokens/s, (4) risks when seal verify contends for disk/CPU. "
            f"End with a one-line summary. Keep generating until the budget is used."
        )
        if i == 0:
            _record_nonstream("long", i, prompt, max_tokens=512)
        _record_stream("long", i, prompt + "\n(stream measurement)", max_tokens=512)
        if i == 0:
            uma_samples.append(sample_uma("after_long_0"))

    uma_samples.append(sample_uma("after_speed"))
    trace_after = parse_moe_otd_trace(TRACE_PATH)

    corr_pass = all(c["pass"] for c in cases if c["kind"] == "correctness")
    speed_pass = all(s["pass"] for s in speed)
    ttft_pass = all(t["pass"] for t in ttft_runs)

    def _stat(vals: list[float]) -> dict:
        if not vals:
            return {"mean": None, "stdev": None, "min": None, "max": None}
        return {
            "mean": round(statistics.mean(vals), 4),
            "stdev": round(statistics.pstdev(vals), 4) if len(vals) > 1 else 0.0,
            "min": round(min(vals), 4),
            "max": round(max(vals), 4),
        }

    def _cell_stats(cell: str) -> dict:
        ns = [s for s in speed if s.get("cell") == cell]
        st = [t for t in ttft_runs if t.get("cell") == cell]
        return {
            "non_stream_tps": _stat([s["completion_tokens_per_s"] for s in ns if s.get("completion_tokens_per_s") is not None]),
            "non_stream_wall_s": _stat([s["wall_s"] for s in ns]),
            "ttft_s": _stat([t["ttft_s"] for t in st if t.get("ttft_s") is not None]),
            "decode_tps": _stat([t["decode_tokens_per_s"] for t in st if t.get("decode_tokens_per_s") is not None]),
            "prompt_tokens_mean": _stat([float(s["prompt_tokens"]) for s in ns if s.get("prompt_tokens")]),
            "completion_tokens_mean": _stat([float(s["completion_tokens"]) for s in ns if s.get("completion_tokens")]),
        }

    tps_vals = [s["completion_tokens_per_s"] for s in speed if s["completion_tokens_per_s"] is not None]
    ttft_vals = [t["ttft_s"] for t in ttft_runs if t["ttft_s"] is not None]
    decode_tps_vals = [t["decode_tokens_per_s"] for t in ttft_runs if t["decode_tokens_per_s"] is not None]

    # delta hit/miss during this run (if trace grew)
    expert_stats = {
        "trace_env": str(TRACE_PATH),
        "before": trace_before,
        "after": trace_after,
        "delta": None,
        "note": "Enable with MOE_OTD_TRACE before starting ovms; E lines carry hit=0/1 per expert touch",
    }
    if trace_after.get("present") and trace_before.get("present"):
        dh = int(trace_after.get("hits") or 0) - int(trace_before.get("hits") or 0)
        dm = int(trace_after.get("misses") or 0) - int(trace_before.get("misses") or 0)
        tot = dh + dm
        expert_stats["delta"] = {
            "hits": dh,
            "misses": dm,
            "hit_rate": round(dh / tot, 4) if tot else None,
            "miss_bytes": int(trace_after.get("miss_bytes") or 0) - int(trace_before.get("miss_bytes") or 0),
            "miss_read_s": round(
                float(trace_after.get("miss_read_s") or 0) - float(trace_before.get("miss_read_s") or 0), 4
            ),
            "miss_transform_s": round(
                float(trace_after.get("miss_transform_s") or 0) - float(trace_before.get("miss_transform_s") or 0), 4
            ),
            "miss_copy_s": round(
                float(trace_after.get("miss_copy_s") or 0) - float(trace_before.get("miss_copy_s") or 0), 4
            ),
        }
    elif trace_after.get("present"):
        expert_stats["delta"] = {
            "hits": trace_after.get("hits"),
            "misses": trace_after.get("misses"),
            "hit_rate": trace_after.get("hit_rate"),
            "miss_bytes": trace_after.get("miss_bytes"),
            "miss_read_s": trace_after.get("miss_read_s"),
            "miss_transform_s": trace_after.get("miss_transform_s"),
            "miss_copy_s": trace_after.get("miss_copy_s"),
        }

    uma = {
        "samples": uma_samples,
        "note": "N3 probe (GlobalMemoryStatusEx + DXGI WDDM). Global OTD reservation still OFF/NOT_DONE.",
    }
    if len(uma_samples) >= 2 and uma_samples[0].get("present") and uma_samples[-1].get("present"):
        try:
            uma["delta_system_available_GB"] = round(
                float(uma_samples[-1]["system_available_GB"]) - float(uma_samples[0]["system_available_GB"]), 3
            )
            uma["delta_wddm_process_usage_GB"] = round(
                float(uma_samples[-1].get("wddm_process_usage_GB") or 0)
                - float(uma_samples[0].get("wddm_process_usage_GB") or 0),
                3,
            )
        except Exception:  # noqa: BLE001
            pass

    # contention snapshot (busy vs free)
    contention = {
        "load_label": LOAD_LABEL,
        "seal_verify_pid_alive": False,
        "note": "Set LIVE_LOAD_LABEL=busy while packv2 seal extra-verify still runs; free after it exits",
    }
    try:
        import subprocess

        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'packv2_pipeline.py seal' } | Select-Object -ExpandProperty ProcessId"],
            text=True,
            timeout=30,
        )
        pids = [int(x) for x in out.split() if x.strip().isdigit()]
        contention["seal_verify_pids"] = pids
        contention["seal_verify_pid_alive"] = bool(pids)
    except Exception as exc:  # noqa: BLE001
        contention["seal_probe_error"] = str(exc)

    # Primary gate = speed/TTFT; correctness is advisory (reasoning parser often hides content)
    speed_ok = speed_pass and ttft_pass
    receipt = {
        "scope": "Live GPU pack-serve medium/long speed+TTFT+expert-hit+UMA; NOT runtime_acceptance",
        "runtime_acceptance": "NO",
        "offload_ratio": RATIO,
        "load_label": LOAD_LABEL,
        "contention": contention,
        "endpoint": url,
        "model": MODEL,
        "correctness": cases,
        "expert_cache": expert_stats,
        "uma": uma,
        "speed": {
            "warmup_http": warmup[0],
            "warmup_s": round(warmup[2], 3),
            "cells": {"medium": _cell_stats("medium"), "long": _cell_stats("long")},
            "non_stream_runs": speed,
            "non_stream_completion_tps": _stat(tps_vals),
            "non_stream_wall_s": _stat([s["wall_s"] for s in speed]),
            "stream_ttft_runs": ttft_runs,
            "ttft_s": _stat(ttft_vals),
            "stream_decode_tps": _stat(decode_tps_vals),
            "runs": speed,
            "completion_tps_mean": _stat(tps_vals)["mean"],
            "completion_tps_stdev": _stat(tps_vals)["stdev"],
            "wall_s_mean": _stat([s["wall_s"] for s in speed])["mean"],
            "ttft_s_mean": _stat(ttft_vals)["mean"],
            "decode_tps_mean": _stat(decode_tps_vals)["mean"],
        },
        "verdict": "PASS" if speed_ok else "FAIL",
        "correctness_pass": corr_pass,
        "speed_pass": speed_pass,
        "ttft_pass": ttft_pass,
        "expert_trace_present": bool(trace_after.get("present")),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = {
        "verdict": receipt["verdict"],
        "load_label": LOAD_LABEL,
        "correctness_pass": corr_pass,
        "speed_pass": speed_pass,
        "ttft_pass": ttft_pass,
        "ttft_s_mean": receipt["speed"]["ttft_s_mean"],
        "decode_tps_mean": receipt["speed"]["decode_tps_mean"],
        "completion_tps_mean": receipt["speed"]["completion_tps_mean"],
        "wall_s_mean": receipt["speed"]["wall_s_mean"],
        "cells": receipt["speed"]["cells"],
        "expert_hit_rate": (expert_stats.get("delta") or {}).get("hit_rate"),
        "expert_misses": (expert_stats.get("delta") or {}).get("misses"),
        "uma_delta_avail_GB": uma.get("delta_system_available_GB"),
        "uma_delta_wddm_proc_GB": uma.get("delta_wddm_process_usage_GB"),
        "contention": contention,
        "runtime_acceptance": "NO",
    }
    print(json.dumps(summary, indent=2))
    print("wrote", OUT)
    return 0 if receipt["verdict"] == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print("LIVE_METRICS_EXCEPTION:", exc, file=sys.stderr)
        raise SystemExit(2)
