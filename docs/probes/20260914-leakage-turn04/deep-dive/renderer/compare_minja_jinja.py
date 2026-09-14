"""MINJA (openvino_genai) vs Python Jinja2 on the actual chat_template.jinja."""
import difflib
import json
import jinja2
import openvino_genai as g

MODEL = ("C:\\llm\\models\\OpenVINO\\Wondernutts\\"
         "gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov")
TPL = MODEL + "\\chat_template.jinja"
REQ = ("C:\\git\\rc2-908d6695-handoff-docs-20260914\\docs\\probes\\"
       "20260914-leakage-turn04\\sweep-long-context\\turn-02\\request.json")

tok = g.Tokenizer(MODEL)

with open(TPL, encoding="utf-8") as f:
    file_tpl = f.read()
active = tok.chat_template
print("tokenizer.chat_template==file:", active == file_tpl)

req = json.load(open(REQ, encoding="utf-8"))
genai_out = tok.apply_chat_template(
    req["messages"], add_generation_prompt=True, tools=req.get("tools"))

env = jinja2.Environment(undefined=jinja2.ChainableUndefined,
                         keep_trailing_newline=False)
j2 = env.from_string(file_tpl).render(messages=req["messages"],
                                      tools=req.get("tools"),
                                      bos_token="<bos>",
                                      add_generation_prompt=True)

print("genai==jinja2:", genai_out == j2)
print("len genai:", len(genai_out), "len jinja2:", len(j2))
print("tok genai:", len(tok.encode(genai_out).input_ids.data[0]),
      "tok jinja2:", len(tok.encode(j2).input_ids.data[0]),
      "server usage: 371")
ids_default = tok.encode(genai_out).input_ids
print("default:", len(ids_default.data[0]))
try:
    ids_server = tok.encode(genai_out,
                            g.add_special_tokens(False)).input_ids
    print("server-equivalent:", len(ids_server.data[0]))
except Exception as e:
    print("server-equivalent variant failed:", repr(e))
if genai_out != j2:
    print("=== unified diff (genai -> jinja2) ===")
    for line in difflib.unified_diff(genai_out.splitlines(),
                                     j2.splitlines(), lineterm="",
                                     n=2):
        print(line)
    print("=== repr of differing regions ===")
    sm = difflib.SequenceMatcher(None, genai_out, j2, autojunk=False)
    for tag, a0, a1, b0, b1 in sm.get_opcodes():
        if tag != "equal":
            print(tag, "genai:", repr(genai_out[max(0, a0 - 60):a1 + 60]))
            print(tag, "jinja2:", repr(j2[max(0, b0 - 60):b1 + 60]))
