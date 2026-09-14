# FREEZE (c48366fe) vs WS candidate (17064400): code delta that matters

Range: `c48366fee` (freeze/gemmamonster-2026.4-known-good, 2026-09-09) ..
`17064400` (fix/gemma4-whitespace-loop-20260914). 31 files under src/llm/.
Direction below: frozen -> WS. (Counts, not substance, omitted.)

## 1. Tool-call grammar construction (generation_config_builder.hpp)

- WS adds the whitespace bound: `JSONSchema(schema, 2)` (frozen: no bound).
- `buildAutoToolGrammar` split into `buildTriggeredToolGrammar(tags, ptc, atLeastOne)`;
  `auto` keeps `at_least_one=false`; sole-tag duplication workaround removed as
  superseded (pinned GenAI/xgrammar v0.1.31 repeats one alternative).
- Mandatory (required/named) grammar reshaped with the same thought-union
  (tools-only vs thought-then-tools); comments updated.
- Net: same TriggeredTags wire shape for auto; WS additionally bounds
  insignificant whitespace inside tool JSON.

## 2. Gemma4 tool parser (gemma4_tool_parser.cpp, +278/-)

Frozen already HAD bare-`call:` recovery and preamble routing; WS hardens it:
- Registry-gated streaming hold: a nameless `call:` prefix is held only while it
  can still become an allowed tool name (prefix match against tool registry);
  otherwise the scan advances instead of holding forever.
- Split-boundary holdback: trailing partial `<|tool_call>` start tags and
  line-start `call:` fragments are held across streamer chunks (DELAY_N_TOKENS
  splits like `call`+`:`), not emitted as prose prematurely.
- Anchored-vs-bare tracking (`currentCallBare`, `currentCallStartPos`): a bare
  line-start `call:` that turns out invalid (bad name, end-tag before args)
  REWINDS and re-emits as content instead of being dropped; chained calls after
  framing stay anchored (drop on invalid). Frozen dropped refused calls silently.
- Numeric arguments: strict `isValidJsonNumber` (rejects `1.`, `1e`), lossless
  lexical preservation via RapidJSON RawValue when the normalized form matches.
- parseChunk loop reworked with progress guard (no infinite re-entry when a
  terminal flush arrives in ToolCallEnded with an empty call).

## 3. OutputParser orchestration (output_parser.cpp, +82)

- `pendingDelta` holdback for bare-recovery tool calls (emit next chunk).
- Implicit-reasoning detection fixed for tags with trailing whitespace
  (`<|channel>thought\n` vs rtrimmed prompt).
- `toolStartTerminatesReasoning`: a complete native tool opener while reasoning
  owns the stream hands over to the tool parser, preserving the reasoning prefix
  as a delta; partial openers are held, not leaked into reasoning.
- CONTENT phase routes through the owning tool parser when
  `ownsToolCallBoundaries` (generic content parser can't own Gemma4 boundaries).

## 4. Reasoning parser (gemma4_reasoning_parser.*)

- Frozen: subclass of Qwen3ReasoningParser with token skipping.
- WS: standalone BaseOutputParser impl; strips the `<|channel>thought\n` opener
  exactly once at phase entry (handles post-tool continuation where the prompt
  already placed the opener, so generation starts inside reasoning).

## 5. Streamer + terminal diagnostics (ovms_text_streamer.cpp, servable.cpp)

- Phase-aware decode-mode reconciliation at reasoning/tool handoffs.
- `m_generated_tokens` counter; `end(finish_reason)` overload threading the
  ACTUAL terminal reason (STOP/LENGTH/TOOL_CALL) into the final flush instead
  of always STOP; state reset (tokens cache, counters).
- `pendingToolFrameDiagnostic()` WARN on terminal incomplete frames:
  `Incomplete tool frame: parser_phase=... finish_reason=LENGTH ...` — this is
  the LENGTH diagnostic our deep-dive wished for.
- `finishTextStreamer` helper preserves legacy `end()` behavior for non-OVMS
  streamers.

## 6. Prompt-aware grammar + history adaptation

- `adaptGemma4HardToolGrammarForRenderedPrompt`: when the rendered prompt ends
  in an OPEN thought channel, the hard (required/named) Union grammar is
  rewritten to TriggeredTags (at_least_one=true), then re-validated; failure is
  a 400-class error, not a silent fallback.
- `removeResponseFromToolDefinition` behind new cap
  `supportsResponseFieldInToolDefinition` (upstream 2026.5 gem): strip OpenAI
  `function.response` before rendering for templates that reject it.
- Tool-content mapping split clarified (Google-style `part.get(...)` templates
  must keep tool content a string).
- `toolStartTerminatesReasoning` flag added to OutputParsingConfig with docs.

## 7. API surface (openai_*)

- `reasoning_effort` / `reasoning_strength` / `enable_thinking` plumbed through
  chat-template kwargs (both endpoints). Frozen had none of this.

## 8. Dependencies (NOT code, but decides what the binary is)

- Frozen pins: OV source `61afcb26`, GenAI `5f7f1278`, GenAI **rc1** package,
  OpenCV 4.14.0. WS/RC2 line: OV `227c3375`, GenAI `7ea25468` + rc2-based
  rebuilds. Different GenAI generations across the comparison.

## Why this matters for our open questions

- `<call:...>` archaeology: the tolerant lineage lives HERE (bare-call recovery,
  preamble routing, rewind-to-prose). RC2 audit showed src/llm identical to
  9a162626; the freeze tree explains where the dialect tolerance came from.
  No `<call:...>` handling exists anywhere (still NOT a protocol form).
- Whitespace loop: frozen has NO bound — if the frozen binary loops the same
  way, the bound is confirmed as the fix; if not, the loop needs the newer
  GenAI/template context to trigger.
- GPU death: none of the above touches GPU allocation paths; a frozen-binary
  churn run isolates "old parser+old GenAI rc1" vs "new parser+new GenAI".
- The frozen tree's own contract tests do NOT build in this env as-is
  (stale `//src:windows` select keys); Dev binary build only. One-line BUILD
  fix (duplicate visibility) applied in the disposable worktree, branches untouched.
