# Sweep classification (first reproducible deviation)

- sweep task: 32 sequential echo calls (sweep-item-1..32), tool_choice=auto, temperature=0, max_tokens=256, same echo schema every turn, fresh history, Heretic GPU VLM_CB, RC2 908d6695, PID 11220
- turn 1..3 (tool turns 1..3): canonical `tool_calls[]` echo sweep-item-1/2/3, finish_reason=tool_calls, content="", 21 completion tokens each
- turn 4 (iter=4, prompt_tokens=437): finish_reason=length, completion_tokens=256, content="", tool_calls=[] — zero usable output
- repro turn-04-retry-256: identical (length, 256 tok, empty) — REPRODUCED, deterministic (temperature=0)
- budget probe turn-04-budget-1024: finish_reason=length, completion_tokens=1024, content="", tool_calls=[] — NOT a tight-budget artifact; generation burns the whole budget with zero visible output
- stream probe: 3 SSE chunks only (role-only delta, empty delta + length, [DONE]) — zero content/tool/reasoning deltas emitted

Primary class: B. GRAMMAR_THRASH (generation reaches max_tokens inside an uncompleted frame/suppressed channel; no completable tool frame, no visible content)
Consequence: E. EMPTY_POST_TOOL_TURN (empty assistant turn right after a tool result)
Not observed: A (no repeated sig), C (no reasoning text leaked anywhere), D (no <call:, no bare call: in any response of the whole campaign)

Note on "long context": prompt at failure is only 437 tokens — this is a post-tool multi-turn continuation pathology, not KV/cache long-context degradation. Matches the known RC2 roundtrip defect (empty continuation after tool result), now localized to Heretic GPU VLM_CB at tool-turn 3->4 with echo.
Checkpoints 8/16/24/32 NOT reached: sweep stopped at first reproducible point per protocol.
Deeper-turn DIALECT_DRIFT (D) therefore untested — but D never appeared in any of 12 server exchanges in this campaign.
