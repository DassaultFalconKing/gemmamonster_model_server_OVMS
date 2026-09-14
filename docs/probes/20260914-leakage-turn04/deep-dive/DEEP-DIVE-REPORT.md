# Deep-dive: turn-04 empty-length failure — evidence report (read-only, no code change)

Product: 908d6695, binary SHA 11d74fd9…886a4fb. Model: Heretic 26B GPU VLM_CB.
Single-instance discipline throughout (OOM guard): old DEBUG PID 11220 -> TRACE PID 16708
-> noreason PID 22156 -> standard TRACE PID 8416 (current). Never two at once.

## 0. Reproducibility status (material fact)

The turn-04 failure (finish=length, completion=max_tokens, content="", tool_calls=[],
zero SSE deltas) observed 3x deterministically on the old DEBUG instance (PID 11220)
is NOT reproduced on any fresh instance with the IDENTICAL turn-04 request:
- fresh TRACE instance, cold: turn-04 -> canonical echo sweep-item-4, 21 tok
- after warm replay turns 1-3: canonical
- after FULL campaign replay (echo, real-exa, minimal, required, named, contaminated, t1-t3): canonical
- variants A/B/C/D on identical history: all normal (see below)
Conclusion: the failure was stateful to the old instance (transient executor/cache
state or cache poisoning after a first flake), NOT a deterministic function of
request history. Raw token IDs of a failing generation were therefore never logged
(old instance ran at DEBUG: zero parseChunk lines for failing turns = nothing reached
the parser callback).

## 1. Rendered prompt tail (reconstructed from chat_template.jinja + history; server does not log rendered text)

For turn-03 and turn-04 (identical structure, item numbers differ). enable_thinking=false
(no chat_template_kwargs sent), add_generation_prompt=true (GenAI default):

- 2nd/3rd assistant turns: NO new `<|turn>model` (continue_same_model_turn, prev
  non-tool role is assistant); first assistant turn has `<|turn>model\n`.
- No thinking block (no reasoning/reasoning_content fields in history).
- Assistant tool call: `<|tool_call>call:echo{` + arguments string VERBATIM
  (`{"text":"sweep-item-3"}`) + `}<tool_call|>`.
- Tool response (forward-scanned from following role:tool, id-resolved to echo,
  string body): `<|tool_response>response:echo{value:<|"|>{"echoed":"sweep-item-3"}<|"|>}<tool_response|>`.
- Generation prompt after final tool_response: NO `<|turn>model`; emits the
  thinking-suppression stub `<|channel>thought\n<channel|>` (empty, CLOSED).
- Reasoning marker state at generation start: CLOSED (prompt ends with `<channel|>`,
  not open `<|channel>thought`) => detectAndSetImplicitReasoningStart=false,
  ImplicitStart=false, initial OutputParser phase UNKNOWN (confirmed by TRACE).

## 2. GenerationConfig entering GenAI (derived from RC2 source + request; no per-request
##    log exists — generationConfigJson is only written to the session store, which is disabled)

- max_new_tokens = 256 (1024 in budget probe) from request max_tokens
- tool_choice = "auto" (request string)
- structured_output_config = PRESENT (no "will not be applied ... validation failure"
  logged => validate(tokenizer) passed; unsetStructuredOutputConfig not called)
- StructuralTag = TriggeredTags { triggers = ["<|tool_call>"],
  tags = [1 tag: begin = "<|tool_call>call:echo",
           content = JSONSchema({"type":"object","properties":{"text":{"type":"string",
             "description":"Text to echo."}},"required":["text"],"additionalProperties":false}),
           end = "<tool_call|>"],
  at_least_one = false, stop_after_first = false }
  (parallel_tool_calls defaults true, openai_request.hpp:86; auto => buildAutoToolGrammar)
- schema/tag count: 1 tool tag / 1 JSON schema
- temperature = 0 => do_sample = false (greedy); request carried no stop list
- adaptGemma4HardToolGrammarForRenderedPrompt: NO-OP for auto (root is TriggeredTags,
  not the 2-element Union the hard path builds) and prompt does not end in open reasoning
- decoding method STANDARD; enable_tool_guided_generation graph flag irrelevant for
  gemma4 (Gemma4GenerationConfigBuilder always builds grammar by mode)

## 3. Raw token IDs, failing turn-04

NOT AVAILABLE. Failing generations emitted zero OutputParser::parseChunk calls, zero SSE
deltas, and GenAI-side token streams are not logged at any level without code changes.
What IS captured (success path, turn-04, identical for fresh + noreason runs):
48, 6639, 236787, [17454, 236782, 107], 236775, [1005, 1083, 107], 236775, 167729,
236772, 1582, 236772, [236812, 236775, 107], 236783, 49, 50  (21 tokens)

## 4. Independent decode (tokenizer.json + tokenizers 0.23.2, analysis-env only)

- skip_special_tokens=false:
  '<|tool_call>call:echo{\n"text":\n"sweep-item-4"\n}<tool_call|><|tool_response>'
  (byte-identical in structure to server chunk text= fields)
- skip_special_tokens=true:
  'call:echo{\n"text":\n"sweep-item-4"\n}'
  NOTE: this is exactly the literal text the model emitted in variants A/B below.
- per-token map: 48=<|tool_call> 6639=call 236787=: 17454=echo 236782={ 107=\n
  236775=" 1005=text 1083=": 167729=sweep 236772=- 1582=item 236812=4 236783=}
  49=<tool_call|> 50=<|tool_response>. No thought-channel tokens (100/101) anywhere.

## 5. Parser phases (TRACE OutputParser::parseChunk), success path

UNKNOWN for tokens 48,6639,236787,[17454,236782,107] -> TOOL_CALLS_PROCESSING_TOOL
for the remainder -> final chunk (0 tokens, finish=1/STOP). REASONING never entered.
Returned-Delta variant per chunk is not logged (only parseChunk inputs); response-level
evidence: ToolCallDelta(+FinishDelta) present, ReasoningDelta/ContentDelta absent
(no reasoning_content/content keys in unary; no reasoning deltas in stream probe).
16 parseChunk calls for 21 tokens.

## 6. Usage (all confirmed)

| case | prompt | completion | finish |
|---|---|---|---|
| turn-03 ok | 404 | 21 | tool_calls |
| turn-04 FAIL (old inst.) | 437 | 256 (=max) | length |
| turn-04 budget probe | 437 | 1024 (=max) | length |
| turn-04 ok (fresh/noreason) | 437 | 21 | tool_calls |
| A no-tools / B choice-none | 382 | 17 | stop |
Completions 256/1024 exactly equal max_tokens => budget exhaustion is exact.

## 7. Variants, identical turn-04 history (single TRACE instance)

- A (no tools): stop, content = `call:echo{text:sweep-item-4}` (17 tok)
- B (tools, choice none): stop, content = `call:echo{text:sweep-item-4}` (17 tok)
- C (auto): canonical tool_calls echo (21 tok)
- D (required): canonical tool_calls echo (21 tok)
Finding: unguided, the model natively emits the bare recovery-path dialect
`call:echo{...}` as free text (it is the special-stripped form of the canonical frame,
see item 4). Angle-bracketed `<call:...>` NEVER observed in any exchange.

## 8. Reasoning parser disabled via launch config only

Graph node option `reasoning_parser: "none"` (= PARSER_DISABLED_VALUE,
parser_config_validation.cpp:53) in deep-dive/noreason-graph/. Server:
"Reasoning parser explicitly disabled", tool_parser gemma4. turn-04 auto =>
canonical, byte-identical token IDs and phases (reasoning parser "N/A" in
OutputParser init). Reasoning parser is uninvolved in this path (it never engages:
no REASONING phase even when enabled).

## 9. Classification (post raw-token evidence)

- NOT GRAMMAR_THRASH: no raw-token evidence of grammar approach/restart (per order
  §9, the label is withheld — failing token stream was never captured).
- NOT PARSER/STREAMER LOSS: no raw decode showing normal text swallowed.
- MODEL/TEMPLATE/REASONING LOOP: unconfirmed (a thought loop would have surfaced as
  reasoning_content had the parser emitted it; nothing was emitted at all).
- GUIDED-GENERATION path: historical failure co-occurred with tools+auto, but auto
  (and required) are clean on fresh instances; no validation-failure log anywhere.
- CHAT-TEMPLATE / MODEL STATE / VLM_CB continuation: most consistent — same history
  fails on one instance state, succeeds cold; full history replay does not re-trigger.
  Plausibly transient executor/prefix-cache state (or cache poisoning after a first
  flake: retries then failed deterministically on identical prefix).
- Verdict: signature LENGTH_WITH_EMPTY_OUTPUT (ex-B) with mechanism UNDETERMINED;
  stateful/transient, single-instance observation, NOT reproduced in deep-dive.
  The `<call:...>` leakage question is unaffected: still NOT_REPRODUCED anywhere.

## Evidence

deep-dive/{instance-note.txt, turn-03-trace, turn-04-trace, repro-warm, repro-full,
variants-ABCD, noreason-graph, noreason-turn-04, decode.py}
each with request.json / response.raw.json / summary / server-window.log /
parsechunks-parsed.txt. parse-chunks.ps1 = extractor used.
