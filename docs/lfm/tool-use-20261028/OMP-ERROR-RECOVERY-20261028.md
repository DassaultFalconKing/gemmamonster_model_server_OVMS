# LFM2.5 / OMP 18.12.6: error recovery and reasoning investigation

Evidence: `C:\gm\lfm-2026.4\error-recovery-20261028`.
Live server: loopback8137, PID24800, model `lfm25-8b-a1b-int4`, cleanup EXE
`d7ec623dbd82dae2f5e80f66c4446a7b650e086f3c7cc6da4806fa5aa68a4c3d`.
No model, server parser, generation builder, or global OMP config was changed.

## Findings

The actual OMP session matching the pasted transcript was found:
`C:\Users\testc\.omp\agent\sessions\-haha\2026-10-27T22-55-30-625Z_01a17f93-6d41-750a-8f21-09bb44055c2a.jsonl`.
It records native `bash -> read -> bash` calls, the real missing-pygame result,
and then an assistant `stop` with 334 output tokens. Its final text is a malformed
JSON-like fragment followed by `)]<|tool_call_end|>`, with no executable call.
This is not evidence of exhausting a 4096-token output budget.

The session used provider `openvino-server-ornith` with model
`lfm25-8b-a1b-int4`. The inspected `~/.omp/agent/models.yml` has overrides for
`ornith` and `gemma26`, but none for the exact LFM model ID. An Ornith-specific
override therefore does not configure LFM simply because they share a base URL.

## Live probes

All probes use real HTTP against the running model, temperature0.2/top_k80/
repetition_penalty1.05, max_tokens4096. No generated installation command ran.

| Probe | Observed outcome |
|---|---|
| Fresh analogous task | Native directory listing, then invented JSON-described action instead of a registered tool; chain failed before executing Python |
| Replay after real pygame error, reasoning retained | `stop`, 117 output tokens, zero calls, empty content |
| Same replay, reasoning omitted | `stop`, prose/JSON plan rather than executable calls |
| After-error `required` control | Native bash call, but requested `pip install pygame` despite system prohibition; protocol pass is not task acceptance |
| After-error native-envelope hint | Native bash call with the same prohibited install; prompt hint alone does not establish agent reliability |
| Request built by installed OMP using candidate overrides | HTTP/SSE completed, `stop`, 207 output tokens; JSON-like glob arguments in content, zero native calls |

Replay preserves the original user/assistant/tool messages before the failed
continuation. System instructions and three tool schemas are simplified;
this is not a byte-identical replay of OMP's original ~8K-token system/tools.
Fresh tool execution is restricted to a sandbox and a bounded command allowlist.

The same rendered prompt through `/v3/completions` produces malformed
`{"bash", "command": ...}` content. In chat mode Hybrid-C demotes that malformed
object into reasoning, explaining the empty visible answer. The native-hint
variant produces a proper native envelope. This supports a format/instruction
failure rather than a demonstrated Gemma-like tool transition inside thinking.

`response.raw.txt` and `omp-wire-live.sse` are raw HTTP/SSE artifacts. They have
already passed through server parsing. The attempted verbose/logprobs paths do
not expose a complete pre-parser token trace in this pinned LM binary: verbose
content is empty/partial and token logprobs are absent. Files named `*.unparsed.txt`
are `/completions` text and still pass through reasoning parsing; they must not
be cited as complete generated token streams. Exact native delimiter ordering
therefore remains NOT_VERIFIED.

## Documentation and OMP overrides

The [official model card](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B) specifies
explicit reasoning and Pythonic calls in native envelopes. Its recommended
sampling is temperature0.2/top_k80/repetition_penalty1.05. The
[checkpoint template](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B/blob/main/chat_template.jinja)
renders previous reasoning as a closed `<think>...</think>` block before native
calls, retains reasoning within the current user round, and removes older
reasoning unless preserve_thinking is requested. It does not advertise Gemma
protocol markers or a Gemma-specific mid-thought tool transition.

The current generic Liquid docs lead with LFM3; use their LFM2/LFM2.5 sections
and the exact checkpoint template, not LFM3's prefilled `<think>` or XML tools.
No documented LFM2.5 `reasoning_effort` or `enable_thinking` control was found.

Candidate: `omp-models.lfm25.yml` beside this report. It defines a separate
provider; start a fresh session with `openvino-lfm25/lfm25-8b-a1b-int4` after
merging the provider block into models.yml. It is not installed automatically.

* `reasoning: true`, `reasoningContentField: reasoning_content`, and
  `replayReasoningContent: true` preserve model metadata and current-round history.
* Disable unsupported effort/toggle wire parameters using
  `supportsReasoningParams: false`, `supportsReasoningEffort: false`,
  `omitReasoningEffort: true`; do not inherit Qwen/Gemma thinking switches.
* System role, `max_tokens`, native tool-choice support, grammar schema flavor,
  and official sampling are explicitly configured for this local OVMS endpoint.
* 32768 prompt / 4096 output is a bounded candidate working configuration,
  not acceptance of the checkpoint's advertised 128K context on this server.
* No blanket `tool_choice=required` override: it can force wrong actions and
  prevent final text. Force only a specific genuinely mandatory workflow step.

Installed OMP18.12.6 schema validation passed with zero unknown compat keys.
Its real request builder was inspected via onPayload without network execution:
all six wire checks passed (reasoning metadata, system role, history replay,
absence of effort/toggle fields, official sampling, output cap). That captured
request was then sent to the live endpoint; its remaining model failure is
recorded above. These overrides correct metadata/protocol configuration but
do not cure the model's unreliable auto tool selection.

References: [OMP18.12.6 models](https://github.com/can1357/oh-my-pi/blob/v18.12.6/docs/models.md),
[OMP18.12.6 compatibility](https://github.com/can1357/oh-my-pi/blob/v18.12.6/docs/provider-compat-reference.md).
Evidence scripts and raw requests/responses are retained under the evidence root.
