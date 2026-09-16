# BUG: streaming named tool_choice degenerates to whitespace (unary OK on identical prompt)

Status: REPRODUCED once, isolated to streaming path. Needs stronger investigation.
Date: 2026-09-16. Reporter: Muse Spark (prep session for upstream Gemma4 PR).

## Provenance (exact binary/source/model)

- Binary: `C:\git\gemma4-upstream-refit-clean-20260915\dist\windows\ovms\ovms.exe`
  SHA256 `3DFC2D11E614BD03924E6730AD8053DB00A6E5564F41E11F966A0929B44F65FE`
  == accepted 2026.5 RC source `43bc254`; equals branch
  `origin/upstream/gemma4-tool-calling` `src/` modulo ONE blank line at EOF
  of `src/llm/io_processing/gemma4/gemma4_tool_parser.cpp` (semantically null).
- Model: `C:\llm\models\OpenVINO\Wondernutts\gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov`
  served as `gemma4-26-heretic`, GPU, `VLM_CB`, `--tool_parser gemma4`,
  `--reasoning_parser gemma4`, `--enable_tool_guided_generation true`,
  u4 KV cache, prefix caching on, `max_num_batched_tokens 4096`.
- Server log: `C:\git\artifacts\gemma4-upstream-pr-20260916\dogfood-server-26b.log`
  (no generation errors/warnings around the requests).

## Repro

Endpoint `POST /v3/chat/completions`, `temperature: 0.0`, `max_tokens: 512`,
tools = get_weather / search_docs / calculator (standard object-root schemas),
`tool_choice: {"type":"function","function":{"name":"search_docs"}}`,
single user message = `"Context:\n" + LONG_DOC + "\nFind runbook guidance on dead-letter prefix handling."`
where LONG_DOC = 5-sentence runbook paragraph repeated x60 (~27k chars, ~5.2k tokens).
ONLY difference between failing and passing: `"stream": true` vs `false`.

## Evidence matrix

| # | stream | context | result |
|---|--------|---------|--------|
| 3 | true | 5-sent x60 | DEGENERATE: ~100 tokens of `\n\t` spam, `finish_reason:length`, NO tool call |
| 3b | false | 3-sent x60 (shorter, confounded) | OK: `search_docs{"query":"dead-letter prefix handling runbook guidance"}` |
| 3c | false | 5-sent x60 (EXACT same as #3, 5234 prompt tokens) | OK: `search_docs{"query":"dead-letter prefix handling"}`, 23 completion tokens |

Raw captures:
- `dogfood-3-stream-named.sse.txt` (1401 bytes, 3 data chunks, zero `tool_calls`, ends `length` + `[DONE]`)
- `dogfood-3c-named-unary-long5.json` (408 bytes, `finish_reason:tool_calls`)
- `dogfood-3b-named-unary.json`, `dogfood-1-auto-long.json` (5421-token input OK),
  `dogfood-2-required.json`, `dogfood-4-responses.json` (parallel calls OK),
  `dogfood-5-long-output.json` (reasoning + 2 parallel calls OK)

## Deduction (why this is a streaming-path bug, not model quirk)

1. temperature 0 = greedy = deterministic given identical generation inputs.
2. #3 vs 3c: identical prompt (~5234 tokens), identical tools, identical named choice,
   identical guided-generation policy object (built once per request in
   `parseConfigFromRequest`, stream-flag independent).
3. Unary emits the call in 23 tokens; streaming emits whitespace to 512 cap.
   Therefore the token streams diverged => generation inputs (prompt/grammar/sampler/
   stop-conditions) or generation loop behavior MUST differ between stream and unary.
4. Ruled out: model incapability (3c proves the call), policy layer (unary named works),
   server-side errors (none in log), context length (5234 tokens fine in 3c),
   tool registry/validation (same tools pass elsewhere).

## Candidate areas (pointers, not conclusions)

1. `src/llm/io_processing/generation_config_builder.hpp` (`Gemma4GenerationConfigBuilder`):
   verify `structured_output_config` installed identically for stream/unary; check
   `stop_after_first`, `TriggeredTags`/`TagsWithSeparator` whitespace handling around
   the tool tag (grep shows NO Gemma4-specific whitespace handling exists today —
   other parsers have `find_first_not_of(" \t\n\r\f\v")` guards, Gemma4 has none).
2. CB scheduling/generation loop: any `stream`-flag-dependent branch affecting
   `max_tokens`, stop strings, EOS handling, or grammar application per step.
3. `src/llm/ovms_text_streamer.cpp` decode-mode reconcile + `OutputParser` streaming
   state: confirm the whitespace is model-generated (not a streamer artifact hiding
   a real call — though `finish_reason:length` proves generation ran to cap).
4. Prefix-cache interaction across the two requests (shared 5k prefix, different
   suffix flag?) — should be inert under greedy, but worth ruling out with cache off.
5. Historical context: whitespace control around structural tags was a known concern
   on the 2026.4 line (XGrammar `max_whitespace_cnt` companion-patch discussion);
   current pins (`versions.mk`, GenAI `fe818c04`) carry no such patch — check whether
   leading-whitespace-before-tag is constrained at all in streaming guided mode.

## Suggested next experiments (cheapest first)

1. Re-run #3 streaming verbatim → determinism check (expect identical whitespace).
2. #3 streaming with `--verbose_response`-equivalent raw prompt/response capture
   (or server-side generation trace) → compare ACTUAL token streams stream vs unary.
3. Same named streaming with short prompt → does streaming named EVER work?
   (if yes: length/context interaction in streaming path only).
4. Streaming named with prefix caching disabled.
5. Inspect `structured_output_config` JSON effectively sent to GenAI in both modes
   (log at `parseConfigFromRequest` / grammar-adapt point in `servable.cpp`).

## Impact on upstream PR

Does NOT block the PR: unary policy (the PR's core: none/auto/required/named,
parallel, Responses) is proven live; streaming defect is bounded to
named+streaming+long-context and needs the experiments above. File as follow-up
with this report attached. Do NOT mask with prompt tweaks.
