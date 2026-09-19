# Tool-history template normalization fix proposal — 2026-09-19

Status: **IMPLEMENTATION PROPOSAL — SUPPORTED BY LIVE 2x2 EVIDENCE**

Depends on:

- `TOOL-HISTORY-TEMPLATE-COMPAT-20260919.md`
- H-series contracts in `CONTRACT-REGISTRY.md`

This proposal addresses exactly one reproduced compatibility defect:

```text
OpenAI assistant history:
    tool_calls[].function.arguments = JSON STRING

strict Gemma4 template:
    requires arguments = OBJECT/MAPPING
```

The executed 2x2 proves that `function.arguments` representation is the deciding axis and `tool.content` is not.

---

## 1. Desired behavior

Preserve the public API contract:

```text
HTTP request/response domain:
    function.arguments = JSON STRING
```

Normalize only the copy entering the chat-template domain:

```text
template domain:
    function.arguments = OBJECT/MAPPING
```

Do not modify:

- output parsing;
- Gemma4 reasoning parser;
- Gemma4 tool parser;
- generation policy;
- `tool.content`;
- public OpenAI response serialization.

---

## 2. Preferred implementation seam

Current code in `OpenAIApiHandler::extractInputRequest()`:

```cpp
req.input = request.chatHistory;
auto& chatHistory = std::get<ov::genai::ChatHistory>(req.input);

auto toolsResult = parseToolsToJsonContainer();
...
```

Insert normalization immediately after the copy and before the request reaches chat-template application:

```cpp
req.input = request.chatHistory;
auto& chatHistory = std::get<ov::genai::ChatHistory>(req.input);

auto status = normalizeToolCallArgumentsForTemplate(chatHistory);
if (!status.ok()) {
    return status;
}
```

This keeps:

```text
request.chatHistory
    = OpenAI-shaped history

req.input ChatHistory copy
    = template-shaped history
```

That separation is intentional.

---

## 3. Proposed helper contract

Suggested helper:

```cpp
absl::Status normalizeToolCallArgumentsForTemplate(
    ov::genai::ChatHistory& chatHistory);
```

Location options:

Preferred:

`src/llm/apis/openai_api_handler.cpp/.hpp`

because this is an API-domain -> generation/template-domain adaptation.

Do not place it in Gemma4 parser code.

---

## 4. Per-tool-call normalization

For every assistant message with `tool_calls`:

### Case A — arguments already object

```text
OBJECT
    -> keep unchanged
```

This makes the operation idempotent.

### Case B — arguments string containing JSON object

Example:

```json
"{\"path\":\"C:\\\\foo.txt\",\"recursive\":true}"
```

Parse once using the existing JSON machinery.

Require parsed root to be object.

Replace only the template-bound copy with:

```json
{
  "path": "C:\\foo.txt",
  "recursive": true
}
```

### Case C — missing arguments

Preserve current API policy, but the value passed to the template must become an empty object:

```json
{}
```

not the string:

```json
"{}"
```

### Case D — invalid JSON string

Example:

```text
"{bad json"
```

Return clear request-level:

```text
INVALID_ARGUMENT
```

Do not allow the malformed value to reach Jinja and fail as a Mediapipe graph error.

### Case E — valid JSON but non-object root

Reject:

```json
[1,2]
"foo"
42
true
null
```

The template/tool-call contract requires a mapping.

---

## 5. Reuse existing JSON machinery

OVMS already uses:

```cpp
ov::genai::JsonContainer::from_json_string(...)
```

for other request fields.

Prefer reusing established JSON parsing/conversion rather than introducing another parser.

However, validate the parsed root is object/mapping before installing it into `function.arguments`.

No double parse:

```text
OBJECT -> OBJECT
STRING -> parse once -> OBJECT
```

---

## 6. Why not normalize in response serialization

Wrong seam:

```text
ToolCallDelta.arguments
    -> response as OBJECT
```

This would violate OpenAI compatibility.

Public response must remain:

```json
"arguments": "{\"x\":1}"
```

not:

```json
"arguments": {
  "x": 1
}
```

---

## 7. Why not patch only the model template

A model-template patch such as `from_json` could solve one template instance, but it would leave OVMS dependent on each model author accepting OpenAI wire representation directly.

The server already owns the transition:

```text
OpenAI API representation
    ->
internal template representation
```

Therefore server-side normalization is the more stable compatibility layer.

A permissive template may remain compatible with the normalized object.

A strict template requires it.

---

## 8. Why not normalize `tool.content`

Executed 2x2:

```text
args STRING + content STRING -> 400
args STRING + content OBJECT -> 400

args OBJECT + content STRING -> 200
args OBJECT + content OBJECT -> 200
```

Therefore `tool.content` is not part of the reproduced defect.

Do not expand patch scope to it.

The old Sept-15 `str.get` failure is currently historical/non-reproduced evidence.

---

## 9. Minimal touched files

Expected primary production scope:

```text
src/llm/apis/openai_api_handler.hpp
src/llm/apis/openai_api_handler.cpp
```

Potentially only `.cpp` if the helper remains file-local.

Avoid changes to:

```text
openai_completions response serialization
Gemma4 parsers
OutputParser
OVMSTextStreamer
Gemma4GenerationConfigBuilder
XGrammar/GenAI
```

---

## 10. Acceptance without building ovms_test

For the C5fixed live lane, prefer cached incremental `//src:ovms` build.

Do not build `ovms_test` merely for this compatibility patch.

Do not clear Bazel cache.

Full clean/test acceptance remains a C6-B pre-PR concern unless a focused compile/runtime failure makes it necessary earlier.

### Required live replay

Rerun exact 2x2.

Expected after fix:

```text
args STRING + content STRING -> 200
args STRING + content OBJECT -> 200
args OBJECT + content STRING -> 200
args OBJECT + content OBJECT -> 200
```

Then:

```text
reasoning
 -> tool A
 -> result A
 -> reasoning
 -> tool B
 -> result B
 -> final answer
```

The standard OpenAI replay form must work:

```text
assistant.tool_calls[].function.arguments = STRING
```

---

## 11. Fail-closed expectations

Malformed history must fail before graph execution.

Preferred error shape:

```text
INVALID_ARGUMENT:
tool_calls[].function.arguments must contain a JSON object
```

Avoid:

```text
Mediapipe execution failed
CalculatorGraph::Run failed
LLMExecutor failed
chat_template raised
```

The adapter owns this type boundary and should diagnose it there.

---

## 12. Proposed implementation verdict

Minimal fix:

```text
one normalization helper
+
one call in extractInputRequest() after ChatHistory copy
+
no public API change
+
no parser/generation change
```

This directly matches the live evidence and has a small blast radius.

If the exact `JsonContainer` mutation API makes post-copy traversal awkward, acceptable fallback is to construct the copied template-bound `ChatHistory` from normalized tool-call objects during input preparation. The architectural rule remains unchanged: normalize the template copy, not the public OpenAI contract.
