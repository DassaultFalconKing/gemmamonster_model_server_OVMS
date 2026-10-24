"""One-shot chat smoke against attributed pack serve (REST).

Waits until /v3/chat/completions or /v1/chat/completions answers, then one short prompt.
Does NOT claim runtime_acceptance.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

port = int(os.environ.get("OVMS_REST_PORT", "8000"))
base = f"http://127.0.0.1:{port}"
model = os.environ.get("OVMS_MODEL_NAME", "qwen")
timeout_s = int(os.environ.get("SMOKE_WAIT_S", "1800"))
prompt = os.environ.get("SMOKE_PROMPT", "Say only: pack-serve-ok")


def post_chat(url: str) -> tuple[int, str]:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 32,
            "temperature": 0,
            "stream": False,
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return -1, str(exc)


def main() -> int:
    candidates = [
        f"{base}/v3/chat/completions",
        f"{base}/v1/chat/completions",
    ]
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        for url in candidates:
            code, text = post_chat(url)
            last = f"{url} -> {code} {text[:300]}"
            print(last)
            if code == 200:
                out = {
                    "scope": "One-shot pack serve chat smoke; NOT runtime_acceptance",
                    "url": url,
                    "http": code,
                    "response": json.loads(text) if text.startswith("{") else text,
                    "runtime_acceptance": "NO",
                }
                path = os.environ.get(
                    "SMOKE_RECEIPT",
                    r"C:\git\cib2-packv2-build-20261024\pack-serve-chat-smoke.json",
                )
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(out, fh, indent=2)
                print("PASS wrote", path)
                return 0
            if code in (404, -1):
                continue
            # 503/ loading — keep waiting
        time.sleep(5)
    print("TIMEOUT last=", last)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
