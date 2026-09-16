# Gemma4 streaming named whitespace regression diagnosis

Date: 2026-09-16
Author: Codex

## Summary

The reported whitespace degeneration is not caused by `Gemma4ToolParser` and is
not an SSE serialization artifact. The streaming response serializes whitespace
because continuous batching streaming already returns whitespace token ids from
`GenerationHandle::read()`.

The precise failing transition is:

`OpenVINO GenAI continuous batching structured-output generation + incremental
read()` diverges from the same request consumed with `read_all()`.

In the reproduced case, unary `read_all()` returns a valid hard-named
`search_docs` tool call, while streaming `read()` returns `\n\t` whitespace until
`max_new_tokens` is exhausted and the request finishes with `length`.

## Evidence From OVMS Code

### The Gemma4 hard named grammar is built before streaming is relevant

`Gemma4GenerationConfigBuilder` treats a named `tool_choice` as a hard tool
policy:

- `buildToolTags()` filters to the named tool only.
- `buildRequiredToolGrammar()` builds `TagsWithSeparator` with
  `at_least_one = true`.
- `parseConfigFromRequest()` installs that required grammar for both
  `required` and named hard choices.

Relevant code:

- `src/llm/io_processing/generation_config_builder.hpp`
  - `buildToolTags()`: named choice filtering
  - `buildRequiredToolGrammar()`: required tool grammar
  - `parseConfigFromRequest()`: hard choice installs required grammar

`stream` is not consumed by this builder.

### The generation config is created once, before unary/streaming response split

`GenAiServable::parseRequest()` creates the API handler, initializes the output
parser, builds the `GenerationConfigBuilder`, and extracts a single
`InputRequest`.

Relevant code:

- `src/llm/servable.cpp`
  - `GenAiServable::parseRequest()`
- `src/llm/apis/openai_api_handler.cpp`
  - `OpenAIApiHandler::extractInputRequest()`

At this point, the generation config and structured-output grammar have already
been constructed.

### Gemma4 rendered-prompt grammar adaptation also happens before the split

`GenAiServable::prepareInputs()` applies Gemma4 rendered-prompt grammar
adaptation before any unary or streaming result handling:

- `adaptGemma4ToolGrammarForRenderedPrompt(req.generationConfig, req.promptText)`
- followed by structured-output validation

Relevant code:

- `src/llm/servable.cpp`
  - `GenAiServable::prepareInputs()`
- `src/llm/io_processing/gemma4/rendered_prompt_state.cpp`
  - `adaptGemma4ToolGrammarForRenderedPrompt()`

This makes a request-layer or parser-layer `stream` discrepancy unlikely.

### Continuous batching is where unary and streaming diverge

For continuous batching, OVMS adds the request to GenAI with only:

- `inputIds`
- `generationConfig`

Relevant code:

- `src/llm/language_model/continuous_batching/servable.cpp`
  - `ContinuousBatchingServable::addRequestToPipeline()`

The OVMS `OVMSTextStreamer` is not passed into the CB pipeline. OVMS receives
generated ids from GenAI and parses/serializes them afterward.

Unary path:

- `ContinuousBatchingServable::readCompleteExecutionResults()`
- calls `generationHandle->read_all()`

Streaming path:

- `ContinuousBatchingServable::readPartialExecutionResults()`
- calls `generationHandle->read()`

Relevant code:

- `src/llm/language_model/continuous_batching/servable.cpp`
  - `readCompleteExecutionResults()`
  - `readPartialExecutionResults()`

### OVMS parsing happens after ids are already returned

Unary response preparation writes the complete generated id vector through
`OVMSTextStreamer`:

- `GenAiServable::prepareCompleteResponse()`
- `executionContext->textStreamer->write(output.generated_ids)`

Streaming response preparation writes each partial generated id vector through
the same parser/streamer bridge:

- `GenAiServable::preparePartialResponse()`
- `executionContext->textStreamer->write(generationOutput.generated_ids)`

Relevant code:

- `src/llm/servable.cpp`
  - `prepareCompleteResponse()`
  - `preparePartialResponse()`

Therefore the whitespace observed in SSE was already generated upstream of
OVMS parsing and serialization.

## Root-Cause Classification

The root transition is not:

- OpenAI request parsing
- Gemma4 named tool filtering
- Gemma4 hard grammar construction
- rendered prompt adaptation
- `Gemma4ToolParser`
- SSE serialization hiding a real call

The root transition is:

- GenAI continuous batching `read()` behavior under Gemma4 hard named
  structured-output grammar

More specifically, the likely defect is that the GenAI continuous batching
incremental read path does not apply or advance structured-output constraints
equivalently to the final `read_all()` path, allowing a whitespace loop to run
to `max_new_tokens` instead of forcing the named tool tag.

## Recommended Next Instrumentation

Add temporary DEBUG or TRACE logging around:

1. `GenAiServable::prepareInputs()`
   - prompt token count
   - decoded prompt suffix
   - whether `structured_output_config` is present
   - compact fingerprint of `structural_tags_config`

2. `ContinuousBatchingServable::readCompleteExecutionResults()`
   - `read_all()` output count
   - generated id count
   - decoded generated text with `skip_special_tokens=false`
   - finish reason

3. `ContinuousBatchingServable::readPartialExecutionResults()`
   - per-iteration `read()` output count
   - generated id count
   - decoded generated text with `skip_special_tokens=false`
   - finish reason
   - `generationHandle` status and `can_read()`

If the structured-output fingerprint is identical for unary and streaming, this
becomes a GenAI continuous batching incremental-read bug rather than an OVMS
request/build/parser bug.

## Suggested Follow-Up Experiment

Run the same named streaming request with a temporary diagnostic patch that
decodes every partial `generationOutput.generated_ids` before OVMS parsing. If
the decoded ids are already `\n\t` repeats, OVMS parser and SSE layers are
exonerated. If the decoded ids contain a valid `<|tool_call>call:search_docs`
sequence before parser output, then the investigation should move back into
`OVMSTextStreamer`/`OutputParser`.

Based on the supplied capture, the first outcome is expected.
