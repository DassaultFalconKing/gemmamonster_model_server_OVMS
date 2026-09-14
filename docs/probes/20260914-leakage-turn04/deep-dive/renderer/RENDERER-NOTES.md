# Renderer-only probe notes (no generation; openvino_genai 2026.3.1 Tokenizer)

Source requests: docs/probes/20260914-leakage-turn04/sweep-long-context/turn-03 (last
success) and turn-04 (LENGTH_WITH_EMPTY_OUTPUT). Exact messages+tools, unchanged.

## Saved per case (turn-03-success/, turn-04-length-empty/)

- messages.json, tools.json (exact copies from probe requests)
- rendered_prompt.txt (apply_chat_template, add_generation_prompt=True)
- tail_repr.txt (repr of last 1500 chars)
- last128_ids.json (encoded token IDs, last 128)
- last128_decode.txt, final_suffix_repr.txt

Shared: original_chat_template.jinja, tokenizer_chat_template.jinja
(IDENTICAL, 23073 chars), meta.json. Driver: render.py (rerunnable, offline).

## Final suffix (item 4)

Both prompts end after the last `<tool_response|>` with exactly:
'<|channel>thought\n<channel|>'
i.e. the thinking-suppression stub: thought channel opened AND closed, empty.
No open reasoning marker at the generation point.

## Renderer-vs-server token-count discrepancy (observed, unexplained)

| case | exchanges | renderer tokens | server prompt_tokens | delta |
|---|---|---|---|---|
| test-4 echo | 0 | 82 | 82 | 0 |
| turn-01 | 0 | 338 | 338 | 0 |
| turn-02 | 1 | 374 | 371 | 3 |
| turn-03 | 2 | 410 | 404 | 6 |
| turn-04 | 3 | 446 | 437 | 9 |

Delta = exactly 3 tokens per assistant+tool exchange, zero otherwise.
Tested and RULED OUT (turn-02 variants vs server 371):
- tool content as parsed mapping instead of string -> 370 (wrong shape+count)
- assistant arguments as parsed mapping -> 375
- encode add_special_tokens True/False -> identical (446/446)
Remaining hypotheses: server-bundle (GenAI 2026.4 RC2) minja/tokenizer counting
difference vs pip 2026.3.1 (e.g. per-exchange whitespace/special handling), or
VLMPerfMetrics num_input_tokens excluding 3 tokens per tool round-trip.
Rendered TEXT follows the committed chat_template.jinja deterministically; the
suffix finding is unaffected.
