# Tool protocol fit

Verdict: BLOCKED for retainer acceptance. Native template rendering/tokenization was measured; native C++ parser RED/GREEN, matcher, streaming, live tool decision and continuation were NOT_RUN. Per mission, inference did not pass, so the requested post-inference acceptance remains gated. This is preliminary static/tokenizer work only.

6 native template cases render and tokenize: default/disabled thinking, empty arguments, multiple calls, tool response, reasoning. JSON-string arguments case fails with AttributeError; the template expects an object and iterates items. OVMS already has a dry-run capability probe (`src/llm/io_processing/chat_template/probe.cpp`) and `chat_template_adapter::funcArgsToObjectHistory` in input_processors/chat_template_adapter.cpp. Verify that adaptation fires for this exact template before proposing an adapter.

Native grammar is `<tool_call>\n<function=NAME>\n<parameter=ARG>\nVALUE\n</parameter>... </function>\n</tool_call>`. Empty arguments produce no parameter tags; multiple calls are separated by a newline. Native tool role becomes a user turn containing `<tool_response>`. Default generation prefix opens `<think>`; enable_thinking=false writes an empty closed thought. Reasoning content can be reconstructed from reasoning_content or embedded think tags.
The frozen `ChatTemplateAnalyzer::analyze` (src/llm/io_processing/chat_template/analyzer.cpp) selects qwen3coder plus qwen3 reasoning from these markers. Qwen3CoderToolParser constants match the textual tags. `Qwen3CoderGenerationConfigBuilder` uses QwenXMLParametersFormat and closes open reasoning before tool grammar; this is a plausible retainer candidate, not an acceptance result. MiniCPM5 parser uses different attribute tags and is not a substitute.

Generation config EOS: 248044 and 248046; BOS 248045. Special-token boundaries must remain visible where parser policy requires them. Function/parameter headers are multiple tokens, so token/stream splits can occur inside names. Full rendered strings and IDs are in evidence/protocol.json.

| Marker | Actual tokenizer IDs |
|---|---|
| `<think>` | `[248068]` |
| `</think>` | `[248069]` |
| `<tool_call>` | `[248058]` |
| `</tool_call>` | `[248059]` |
| `<function=ping>` | `[27, 1628, 28, 9694, 29]` |
| `<parameter=value>` | `[27, 15704, 44984, 29]` |
| `<|im_end|>` | `[248046]` |
| `<|im_start|>` | `[248045]` |
| `<tool_response>` | `[248066]` |

Required native RED/GREEN gates: empty args, schema invalid/unknown function, duplicate/missing parameters, multi-call order, every delimiter split, default/disabled reasoning, STOP/LENGTH truncation, tool-result continuation and guided/unguided policy. None was executed on the frozen production binary. No Gemma4, Qwen3Coder or LFM source was changed.
