# Named streaming `\n\t` degeneration — root cause (CURSOR)

**Author:** Cursor Grok 4.6  
**Date:** 2026-09-16  
**Status:** Diagnosed from live capture + OVMS/GenAI/XGrammar source. Not a code fix.  
**Does not block** the Gemma4 tool-calling upstream PR (unary named/required/auto policy is proven). File as follow-up; do not mask with prompt tweaks.

Source bug report: `C:\git\artifacts\gemma4-upstream-pr-20260916\bug-streaming-named-degenerate.md`

---

## Verdict

After the native Gemma4 begin tag (`<|tool_call>call:search_docs`), XGrammar JSONSchema allows unbounded `[ \n\t]*` before `{`. Greedy decode on the long runbook prompt enters that loop and burns `max_tokens` as alternating newline/tab. Unary on the identical prompt escaped into compact JSON; streaming named+long did not. The enabling defect is the missing `max_whitespace_cnt` bound (present on the 2026.4 line, absent from GenAI pin `fe818c04`). This is not a streamer that hid a completed tool call, and not “the model cannot do named choice”.

---

## Evidence (live 26B capture)

| Request | stream | prompt tokens | result |
|---|---|---|---|
| #3 | true | ~5234 | `finish_reason: length`, no `tool_calls`, content = `\n\t` spam |
| #3c | false | 5234 (exact same prompt) | `finish_reason: tool_calls`, `search_docs{"query":"dead-letter prefix handling"}`, 23 completion tokens |

SSE `#3` (`dogfood-3-stream-named.sse.txt`):

- Unique characters in `delta.content`: `\n` and `\t` only
- 253 newlines, 252 tabs, **505** visible chars
- `max_tokens: 512`, `finish_reason: length`
- Handshake chunk (role) + one content dump + `[DONE]`; no `tool_calls`, no `search_docs`, no `reasoning_content`

Accounting: **505 visible whitespace tokens + ~7 skipped tokens ≈ 512**. The skipped ids are almost certainly the begin tag `<|tool_call>call:search_docs` (specials dropped by default `skip_special_tokens=true`). Then one token per `\n` / `\t` until the cap. `{` never appeared.

Unary `#3c` (`dogfood-3c-named-unary-long5.json`): empty `content`, one tool call, 23 tokens — begin tag + compact object + end tag. Same prompt, temperature 0, same tools, same named `tool_choice`.

---

## Mechanism

Named/required grammar installs:

```cpp
tag.begin = "<|tool_call>call:" + toolName;
tag.content = ov::genai::StructuredOutputConfig::JSONSchema(toolSchemaWrapper.stringRepr);
tag.end = "<tool_call|>";
```

(`src/llm/io_processing/generation_config_builder.hpp`, `Gemma4GenerationConfigBuilder::buildToolTag`)

XGrammar `FromJSONSchema` defaults: `any_whitespace=true`, `max_whitespace_cnt=None`. Between JSON elements — **including the position immediately before `{`** — the compiled EBNF is `[ \n\t]*` with no ceiling.

Sequence on the failing sample:

1. Model emits native begin tag (~7 tokens, hidden in SSE by skip-special decode).
2. Grammar is now in JSONSchema. Both `{` and `\n`/`\t` are legal.
3. Long runbook context biases greedy toward pretty-print `\n`, then `\t`.
4. The whitespace production is still legal, so the loop continues until `max_tokens`.
5. Parser never sees `{`, so it never commits a tool call. LENGTH dumps the visible residue as `content`.

This is the same trap closed on 2026.4 with `JSONSchema(schema, max_whitespace_cnt=2)` plus GenAI companion #4477. Current pin:

- OVMS builder: `JSONSchema(toolSchemaWrapper.stringRepr)` — one-arg, unbounded
- GenAI `fe818c04` / baseline header: `JSONSchema` has `value` only; no `max_whitespace_cnt`

Secondary unbounded sink (weaker on this capture): hard-policy Union still offers `thought` with `AnyText()`. A thought opener is ~3 tokens, not ~7; the 7-token hole fits the tool begin tag better.

---

## Why it looks stream-only

VLM_CB unary and streaming both `add_request(promptText, images, generationConfig)`. The OVMS streamer is **not** passed into GenAI; it only decodes ids after the scheduler emits them. Grammar application is the same object.

The only systematic `GenerationConfig` delta from `stream: true`:

```cpp
if (request.stream) {
    request.includeStopStrInOutput = true;
}
```

(`src/llm/apis/openai_api_handler.cpp`) That flag controls whether a matched stop string is kept in the output. It does not explain first-token `{` vs `\n` logits.

What *does* make the SSE look empty of a call:

- Default decode skips specials, so the begin tag is invisible.
- `getPhaseStartTagForToken` only maps tags that `encode(..., add_special_tokens(false))` as **exactly one** token.
- Named parser `startTags` require `{` or `(` after the name (`gemma4_tool_parser.hpp`). Without `{` the tool phase never opens; LENGTH flushes `\n\t` as content.

So streaming **masked** the begin tag and **failed to parse** an incomplete envelope. Generation itself ran to the length cap inside the JSON whitespace loop. Unary on the same prompt took `{` after the begin tag (23 tokens, `tool_calls`). That is a greedy branch on a *legal* trap, not a separate streaming scheduler that forgot the grammar. GPU CB + prefix cache after dogfood #1/#2 also means temperature 0 is not a perfect reproducibility guarantee.

Parser-side `find_first_not_of(" \t\n\r\f\v")` guards exist on Hermes/Phi4/Llama3/Mistral and **not** on Gemma4. Those are parse-time; they cannot generate 512 whitespace tokens.

`adaptGemma4ToolGrammarForRenderedPrompt` only rewrites grammar for an already-open thought in the rendered prompt. A fresh `#3` turn is `NEW_TURN`; that path is inert here.

---

## Ruled out

| Hypothesis | Why not |
|---|---|
| Model cannot emit named `search_docs` | `#3c` unary on the exact prompt does |
| Policy / `structured_output_config` missing on stream | Built once in `parseConfigFromRequest`; stream-flag independent |
| Streamer fabricated `\n\t` | `finish_reason: length` at 512; token accounting matches generated ids |
| Server errors | `dogfood-server-26b.log` has none around these requests |
| Context overflow | 5234 prompt tokens succeeds in unary |
| Open-thought residual `AnyText` rewrite | Fresh turn; 7 skipped tokens fit tool begin, not thought opener |

---

## Cheapest confirmations (do not block the PR)

1. Raw ids with `skip_special=false` / verbose decode: expect a short begin-tag prefix, then `\n`/`\t` only, no `{`.
2. Same named streaming on a **short** prompt: if `{` appears immediately, the bug is length × unbounded whitespace, not a stream-only CB path.
3. Repeat `#3` several times: intermittent tool calls ⇒ greedy non-determinism on `{` vs `\n`.
4. Prefix cache off: rules out KV pollution from `#1`/`#2`.
5. Log the structural-tag JSON actually sent to GenAI (named Tag + JSONSchema, no `max_whitespace_cnt`).

---

## Fix direction (follow-up, not this note)

Do **not** paper over with prompt wording.

When GenAI exposes `JSONSchema(schema, max_whitespace_cnt)` (companion #4477 / 2026.4 RC):

- Pass `max_whitespace_cnt=2` on every Gemma4 tool JSONSchema (and ideally the same bound for other parsers that embed JSONSchema in tags).
- Keep whitespace inside JSON strings unrestricted; only bound *between* elements.

Until that API exists on the current pin, this stays a known follow-up: unary policy is the PR core; named+streaming+long-context can hit the historical whitespace trap.

---

## Pointers

| Path | Role |
|---|---|
| `src/llm/io_processing/generation_config_builder.hpp` | Gemma4 Tag + unbounded JSONSchema |
| `src/llm/apis/openai_api_handler.cpp` | `include_stop_str_in_output=true` when `stream` |
| `src/llm/servable.cpp` | shared parse/prepare; streamer after generation |
| `src/llm/visual_language_model/continuous_batching/servable.cpp` | same `add_request` for stream and unary |
| `src/llm/io_processing/gemma4/gemma4_tool_parser.hpp` | startTags require `{`/`(` |
| `src/llm/ovms_text_streamer.cpp` | skip-special + phase inject |
| Artifacts `gemma4-upstream-pr-20260916/` | SSE, unary JSON, server log, original bug note |
| `docs/gemmamonster/.../HANDOFF.md` | pin `fe818c04`, no whitespace companion |
