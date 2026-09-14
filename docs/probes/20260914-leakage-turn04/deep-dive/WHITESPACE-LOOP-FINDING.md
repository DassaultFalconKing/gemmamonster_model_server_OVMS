# ROOT CAUSE: whitespace-stutter loop after tool-call opener (evidence-backed)

## Raw evidence (server-side full decode, TRACE ovms_text_streamer.cpp:214)

- K turn-29 (prefix=false, t=1.0, ptc=false): 256 tokens =
  `<|tool_call>call:echo{` + ~250 newline tokens (ids 109/113/116 = \n-runs)
- F1 turn-23 (prefix=true, t=1.0, ptc=false): 256 tokens =
  `<|tool_call>call:echo{` + newlines, then tabs to budget end
- Files: deep-dive/k-fail-full-decode.txt, deep-dive/f1-fail-full-decode.txt
  (reconstructed across log physical lines; text contains real \n)

## Mechanism

1. MODEL: in multi-turn tool continuation, Heretic falls into a whitespace
   repetition attractor immediately after emitting `<|tool_call>call:echo{`.
   It never emits the next structural token (`"`), burning max_tokens.
2. GRAMMAR: xgrammar TriggeredTags JSON content allows unbounded insignificant
   whitespace, so guided generation does NOT mask the loop out. With
   stop_after_first=false (parallel_tool_calls default true) nothing forces
   termination after a complete frame either.
3. PARSER/VISIBILITY: OutputParser buffers the incomplete tool frame across
   100+ chunks; at finish=LENGTH there is no complete frame, so it emits no
   ToolCallDelta and the consumed whitespace never surfaces as content.
   API returns content="" + tool_calls=[] + finish=length, no diagnostic.
   (272/164 parseChunk inputs in K/F1 windows prove tokens flowed; deltas none.)

## Trigger matrix (echo sweep, Heretic VLM_CB, RC2 binary)

| temp | ptc (stop_after_first) | prefix_cache | result |
|---|---|---|---|
| 0 | default true (=false) | true | FAIL@4 deterministic 3x (old instance 11220) |
| 0 | default true (=false) | true | 32/32 clean (fresh 16708, 4420+repeat) |
| 0 | false (=true) | true | 32/32 clean (F2) |
| 1.0 | false (=true) | false | FAIL@28 (K, proven \n-loop) |
| 1.0 | false (=true) | true | FAIL@22 (F1, proven \n\t-loop) |
| 1.0 | default true (=false) | true | 32/32 clean (F3, stochastic escape) |

Greedy + permissive grammar hits the attractor early and deterministically;
sampling hits it late and stochastically; stop_after_first=true avoids it in
the greedy runs tested. The old-instance @4 is attributed to the same loop
signature (identical observable triple: budget burn + zero deltas + length),
instance-state-gated, not reproduced since.

## What this is NOT

- Not a code regression 9a162626->908d6695 (audit: src/llm identical, deps identical).
- Not GRAMMAR_THRASH in the restart-the-grammar sense: the grammar never breaks,
  it is too permissive (whitespace hole), and generation never attempts recovery.
- Not schema validation failure (no log line, ever), not template rendering
  (byte-identical), not token miscounting (437==437), not `<call:...>` leakage.
