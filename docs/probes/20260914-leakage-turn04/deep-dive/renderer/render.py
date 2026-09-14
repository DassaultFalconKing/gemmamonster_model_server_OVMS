"""Renderer-only probe: exact turn-03 / turn-04 requests through
openvino_genai.Tokenizer on the Heretic model dir. No generation."""
import json
import openvino_genai as g

MODEL = ("C:\\llm\\models\\OpenVINO\\Wondernutts\\"
         "gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov")
EV = ("C:\\Users\\testc\\AppData\\Local\\Temp\\opencode\\"
      "gemmamonster-leakage-20260914\\deep-dive\\renderer")

CASES = {
    "turn-03-success": ("C:\\git\\rc2-908d6695-handoff-docs-20260914\\docs\\probes\\"
                        "20260914-leakage-turn04\\sweep-long-context\\turn-03\\request.json"),
    "turn-04-length-empty": ("C:\\git\\rc2-908d6695-handoff-docs-20260914\\docs\\probes\\"
                             "20260914-leakage-turn04\\sweep-long-context\\turn-04\\request.json"),
}

import os
os.makedirs(EV, exist_ok=True)

tok = Tokenizer = g.Tokenizer(MODEL)

with open(os.path.join(EV, "original_chat_template.jinja"), "w", encoding="utf-8") as f:
    f.write(tok.get_original_chat_template())
with open(os.path.join(EV, "tokenizer_chat_template.jinja"), "w", encoding="utf-8") as f:
    f.write(tok.chat_template)

meta = {"genai_version": g.__version__, "model_dir": MODEL}
for name, req_path in CASES.items():
    d = os.path.join(EV, name)
    os.makedirs(d, exist_ok=True)
    with open(req_path, encoding="utf-8") as f:
        req = json.load(f)
    with open(os.path.join(d, "messages.json"), "w", encoding="utf-8") as f:
        json.dump(req["messages"], f, ensure_ascii=False, indent=1)
    with open(os.path.join(d, "tools.json"), "w", encoding="utf-8") as f:
        json.dump(req.get("tools", []), f, ensure_ascii=False, indent=1)
    prompt = tok.apply_chat_template(
        req["messages"],
        add_generation_prompt=True,
        tools=req.get("tools"),
    )
    with open(os.path.join(d, "rendered_prompt.txt"), "w", encoding="utf-8") as f:
        f.write(prompt)
    tail = prompt[-1500:]
    with open(os.path.join(d, "tail_repr.txt"), "w", encoding="utf-8") as f:
        f.write(repr(tail))
    enc = tok.encode(prompt)
    ids = enc.input_ids.data[0]
    last128 = [int(x) for x in ids[-128:]]
    with open(os.path.join(d, "last128_ids.json"), "w", encoding="utf-8") as f:
        json.dump(last128, f)
    with open(os.path.join(d, "last128_decode.txt"), "w", encoding="utf-8") as f:
        f.write(tok.decode(last128))
    idx = prompt.rfind("<tool_response|>")
    suffix = prompt[idx + len("<tool_response|>"):] if idx != -1 else "<NO_TOOL_RESPONSE_MARKER>"
    with open(os.path.join(d, "final_suffix_repr.txt"), "w", encoding="utf-8") as f:
        f.write(repr(suffix))
    meta[name] = {
        "prompt_chars": len(prompt),
        "prompt_tokens": len(ids),
        "tail_chars": len(tail),
        "suffix_after_last_tool_response_close": repr(suffix),
    }
    print(name, "chars=", len(prompt), "tokens=", len(ids))
    print("  suffix:", repr(suffix))
with open(os.path.join(EV, "meta.json"), "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=1)
print("saved to", EV)
