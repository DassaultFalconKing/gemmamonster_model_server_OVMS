# Quoted-key findings (2026-09-19, C6-preflight server, heretic model)

Terminology (do NOT confuse):
- C5 = pinned candidate, branch test/gemma4-frankenstein-newxgrammar-20260917,
  dist C:\git\gemmamonster-C5\dist, model gemma4-26-heretic (Wondernutts).
- C5fixed = agentic line (history-normalization fix), dist C:\llm\ovms-C5fixed,
  model gemma4 (google-current). DIFFERENT model, DIFFERENT branch. Not this report's subject
  except where explicitly noted.

## Observed symptoms (all live, :18091)

1. opencode session: tool args arrive as `{"\"command\"":"ls -la"}` (key wrapped in
   literal quotes) -> harness rejects format. Same for `workdir`.
2. Direct probe, `tool_choice=required`, bash/1-prop: 5/5 `args={"":""}` (empty key+value).
3. Same, bash/2-prop: 3/3 `args={"\"command\"":"ls -la C:/","\"workdir\"":"/"}` (quoted keys, correct values).
4. Same, calculator/1-prop: 3/3 `args={"\"expression\"":"6*7"}`.
5. `tool_choice=auto` + same prompts: sometimes `finish=length` prose tutorial, no call.
6. Canonical calculator probes (temp 0.0/0.1, max 256, "Calculate 17*23"): historically CLEAN
   `{"expression":"17 * 23"}` on C5/C5fixed.

## What the pattern says

- Quoting hits KEYS, values stay correct -> key-serialization path, not values.
- Single-prop `{}`-ish cases collapse to `{"":""}`; multi-prop cases keep values.
- Deterministic under `required` (5/5, 3/3, 3/3 identical).
- Auto mode wanders (prose tutorial) — model-side, separate phenomenon.

## Leading hypothesis (NOT yet proven)

Old procedural `parseObjectParameter` body (split/mask loop + `escapeAsJsonString(key)`)
does not strip standard JSON `"` quotes from keys — it only handles `<|"|>` delimiters.
For already-valid-JSON input `{"command":"ls"}`, key arrives as `"command"` (with quotes)
and gets escaped again -> `"\"command\""`. The NativeValueParser path (parseKey via
rapidjson GetString) handles quoted keys correctly — so IF the running code takes the
old body, the symptom is explained exactly (including `{"":""}` for degenerate inputs).

## Why not yet pinned

- The decisive control (same probes on C5 dist = known new-pipeline parser) is BLOCKED:
  C5 dies twice at `Initializing VLM CB servable` (silent, 22GB RAM free) -> suspect
  wedged GPU, reboot required before the control can run.
- No raw pre-parser envelope captured (server logs don't dump generation text).
- Canonical clean fills ran on different server/model combos; variable isolation incomplete.

## Incidental (methodology)

- PowerShell inline single-quoted JSON with `{` breaks silently in this shell -> several
  probe runs VOID (tools=null -> text answers). Rule: build tool JSON from files, never inline.
- First 7-probe run clobbered C5fixed raws (wrong OutDir) — recorded in handoff.

## Next to settle it (needs reboot first)

1. Reboot (wedged GPU), relaunch C5, run identical required-bash/calculator probes.
2. Clean keys on C5 + mangled on pre-C6 => parser-build delta confirmed; diff the two
   parser implementations key-path line by line.
3. Mangled on both => model-emission hypothesis (raw envelope needed; GenAI-python
   direct generation path staged but blocked on tokenizers module).
