# Gemma4 tool-history / chat-template compatibility gap — 2026-09-19

Status: **CANONICAL DIAGNOSIS — NEWLY EXPOSED COMPATIBILITY GAP**

Scope: multi-turn assistant tool-call history crossing the OpenAI API representation into the Gemma4 chat-template domain.

This issue was exposed after the C5 reasoning -> tool handoff was restored. It is **not** currently classified as another lost parser fix.

---

## 1. Live symptom

A subsequent chat-completions turn fails before generation with:

```text
Mediapipe execution failed. MP status - INVALID_ARGUMENT:
CalculatorGraph::Run() failed:
Calculator::Process() for node "LLMExecutor" failed:
chat_template: tool_calls[].function.arguments must be a JSON object (mapping), not a string.
Deserialize arguments before passing to the template.
```

Observed sequence:

```text
turn 1:
user
 -> reasoning
 -> real tool call
 -> API tool_calls[].function.arguments serialized as JSON STRING

agent executes tool
 -> appends assistant tool-call message + tool result to history

turn 2:
history enters OVMS
 -> ChatHistory
 -> chat template
 -> strict template sees STRING arguments
 -> INVALID_ARGUMENT before generation
```

This is downstream of first-turn tool recognition. The repaired reasoning -> tool transition can therefore expose this defect by allowing the agent loop to reach the next request.

---

## 2. External vs internal representation

OpenAI-compatible wire representation:

```json
{
  "tool_calls": [{
    "function": {
      "name": "read_file",
      "arguments": "{\"path\":\"C:\\\\foo.txt\"}"
    }
  }]
}
```

Here `function.arguments` is a JSON-encoded **string**.

A strict Gemma4 template may instead require its template-domain value to be a JSON **object/mapping**:

```json
{
  "arguments": {
    "path": "C:\\foo.txt"
  }
}
```

These are two different contracts at two different boundaries.

Canonical rule:

```text
PUBLIC OPENAI API:
    function.arguments = JSON STRING

TEMPLATE INPUT:
    function.arguments = JSON OBJECT / MAPPING when required by template

PUBLIC RESPONSE:
    remains JSON STRING
```

Do not change the public OpenAI response contract merely to satisfy an internal Jinja template.

---

## 3. Current OVMS path

Current C5/C5fixed path:

```text
HTTP messages[]
    |
    v
OpenAIChatCompletionsHandler::parseMessages()
    |
    | tool_calls member
    v
rapidJsonValueToJsonContainer(member->value)
    |
    v
request.chatHistory
    |
    v
prepareInputRequest()
    |
    | req.input = request.chatHistory
    v
ChatTemplateProcessor
    |
    v
Gemma4 chat_template.jinja
```

### 3.1 `rapidJsonValueToJsonContainer`

A RapidJSON string remains a `JsonContainer` string.

Therefore:

```json
"arguments": "{\"x\":1}"
```

remains string-shaped inside `request.chatHistory`.

### 3.2 `ensureArgumentsInToolCalls`

Despite its broad name, this helper does **not** deserialize JSON arguments.

Its current historical behavior is only:

```text
if function.arguments is missing:
    add arguments = "{}"
```

and that default is also inserted as a string.

It does not perform:

```text
STRING JSON -> OBJECT
```

### 3.3 Ordering caveat

`parseMessages()` copies `tool_calls` into `request.chatHistory` before calling `ensureArgumentsInToolCalls(obj)`.

Therefore mutations performed by `ensureArgumentsInToolCalls` on the RapidJSON request object are not a reliable normalization mechanism for the already-copied `ChatHistory`.

---

## 4. Git archaeology verdict

Checked representative historical lineages:

- `fd0c86c77ce6812fd6c77d9c8ee16a7dd7cb973b` — PR3 runtime-proven parser/generation candidate;
- `b4b183d67a83aef9b35f83cacca864fdd6f1bc0c` — PR4 reviewed contracts;
- `7d00c5fe63c5f81e6c06972a974cd57fd7180326` — runtime-proven Google-template/session candidate;
- `f36d2d758264ac5f371c344c49e485f582b07b5a` — `fix/gemma4-google-template-session-state`;
- `7300995129f5686fe7ec6999905031399698745e` — final tool-calling review line;
- `5d995cfafdb2ec90578678aa15714dedebc843b8` — 2026.5 Gemma4 protocol-hardening;
- C5 `a671ddf9f10f31a8afda849b44400291c35148ea`.

Across these inspected lineages:

```text
tool_calls copied to ChatHistory:
    YES

string arguments deserialized before template:
    NO

ensureArgumentsInToolCalls performs deserialization:
    NO
```

Therefore there is no evidence that a previous OVMS-side string -> mapping adapter existed and was later lost.

Canonical classification:

**NEWLY EXPOSED COMPATIBILITY GAP**

not:

**CONFIRMED LOST FIX**

---

## 5. Historical live proof: string arguments used to survive two turns

Old runtime-proven evidence exists for exact source:

`7d00c5fe63c5f81e6c06972a974cd57fd7180326`

Evidence path:

`ab-evidence/live-reallyfinal/required-session-gemma4-reallyfinal-required/`

### Turn 1 response

`request1-response.json` contains:

```json
"function": {
  "name": "inspect_repository_state",
  "arguments": "{...}"
}
```

The arguments are a string.

### Turn 2 request

`request2-input.json` sends that assistant tool call back in history with the same string-shaped arguments, followed by the tool result.

### Turn 2 result

`summary.json` records:

```text
request1.http = 200
request2.http = 200
request2.tool = publish_review_evidence
exact_sha_pass = true
verdict = PASS
```

The second request successfully generated another tool call.

### Source check

Exact `7d00c5fe` source still has no string -> mapping adapter in the OpenAI handler / ChatHistory path.

Therefore the historical two-turn success cannot be attributed to a hidden OVMS deserializer.

Strong interpretation:

> the older model/template/runtime combination tolerated the OpenAI string representation, while the newer strict template rejects it.

This also explains why the gap can surface without a corresponding OVMS source regression.

---

## 6. Host-side current-template evidence

Local host inspection reports that the newer model template `gemma4-26-heretic-google-current/chat_template.jinja` has, near the same assistant/tool-call rendering section:

- rendering of `reasoning` / `reasoning_content` into the thinking channel;
- a guard requiring `function['arguments'] is mapping`;
- an explicit exception when arguments are still a string.

This yields the exact live error above.

The project's older model/template path was reported to contain a softer branch in the equivalent area rather than the hard exception.

This host-side template observation should be preserved with the eventual runtime evidence bundle, including exact template SHA256.

---

## 7. Separate Sept-15 `str has no attribute get` observation

A previous probe reportedly showed that an object-shaped payload could fail elsewhere with:

```text
'str' has no attribute 'get'
```

Do not assume that this proves object-shaped `function.arguments` is invalid.

There are at least two independently typed template fields:

```text
assistant.tool_calls[].function.arguments
tool-message content
```

A template can correctly require arguments as mapping while separately mishandling object-shaped tool content as a sequence and then calling `.get()` on iterated dictionary keys.

Therefore this older error must be localized by A/B, not used to reject arguments normalization globally.

---

## 8. Recommended repair seam

Preferred architecture:

```text
OpenAI HTTP representation
arguments = STRING
        |
        v
request.chatHistory
arguments = STRING
        |
        | copy for generation/template domain
        v
req.input = request.chatHistory
        |
        | TEMPLATE-BOUNDARY NORMALIZATION
        v
arguments = OBJECT
        |
        v
ChatTemplateProcessor / Jinja
```

The adapter should normalize the **copy destined for template rendering**, not mutate the public/API representation globally.

Preferred locality is after:

```cpp
req.input = request.chatHistory;
auto& chatHistory = std::get<ov::genai::ChatHistory>(req.input);
```

and before template application.

Do not modify:

- Gemma4 tool parser;
- reasoning parser;
- public response serializer;
- generation grammar merely to solve this type mismatch.

---

## 9. Normalization contract

For every assistant history tool call:

```text
arguments is valid JSON STRING whose root is OBJECT
    -> deserialize once
    -> OBJECT

arguments already OBJECT
    -> leave unchanged

arguments missing
    -> canonical empty OBJECT if API policy permits

arguments null
    -> explicit policy required; do not silently invent non-empty args

arguments invalid JSON STRING
    -> INVALID_ARGUMENT at request boundary

arguments JSON STRING whose root is ARRAY / scalar
    -> INVALID_ARGUMENT
```

The operation must be idempotent:

```text
STRING(object-json) -> OBJECT
OBJECT              -> OBJECT
```

It must never double-decode an already structured object.

---

## 10. Required live A/B before promotion

Cross both independent representation axes:

| assistant `function.arguments` | tool-message `content` | Purpose |
|---|---|---|
| STRING | STRING | canonical OpenAI roundtrip |
| OBJECT | STRING | strict-template assistant history |
| STRING | OBJECT | isolate tool-content typing bug |
| OBJECT | OBJECT | fully structured template input |

For each case include:

- assistant reasoning/reasoning_content where applicable;
- one real tool call;
- tool result;
- second assistant turn.

Then run full sequences:

```text
tool A -> result -> reasoning -> final answer

tool A -> result -> reasoning -> tool B

reasoning -> tool A -> result -> reasoning -> tool B -> final
```

Acceptance requires that the second request reaches generation instead of failing in chat-template rendering.

---

## 11. Error ownership and fail-fast behavior

After repair:

```text
invalid arguments string
    -> HTTP/API INVALID_ARGUMENT with clear request error
```

Preferred.

Not:

```text
Mediapipe execution failed
CalculatorGraph::Run failed
chat_template raised deep inside LLMExecutor
```

The type contract should fail at the OpenAI/template boundary before graph execution.

---

## 12. Relationship to the mid-thought repair

The two issues are independent layers.

### Recovered C5 defect

```text
raw <|tool_call> emitted inside open reasoning
    -> parser previously lost phase transition
```

Classification:

**CONFIRMED LOST PARSER CONTRACT**

### Current history/template defect

```text
valid first-turn tool call succeeds
    -> assistant tool call returns in history
    -> strict template rejects string arguments
```

Classification:

**NEWLY EXPOSED COMPATIBILITY GAP**

The first repair can expose the second because the agent now survives long enough to perform a real second turn.

Do not collapse them into one root cause.

---

## 13. Forward-port contract

Add a permanent cross-layer contract:

**H01 — assistant tool-call history roundtrip**

```text
OVMS response:
    function.arguments = OpenAI JSON STRING

client returns the assistant message unchanged
    +
tool result

OVMS internal template input:
    function.arguments normalized to template-required OBJECT

second generation:
    succeeds
```

This must be verified for both:

- old/permissive templates;
- new/strict Gemma4 templates.

A parser/tool-calling implementation is not agentically complete if the first call succeeds but its own valid OpenAI response cannot be replayed into the next turn.


---

## 14. Executed 2x2 representation matrix — 2026-09-19

The ambiguity around `function.arguments` versus tool-message `content` has now been resolved by live A/B.

Observed matrix:

| assistant `function.arguments` | tool-message `content` | Result |
|---|---|---|
| STRING | STRING | **HTTP 400 — arguments mapping error** |
| STRING | OBJECT | **HTTP 400 — arguments mapping error** |
| OBJECT | STRING | **HTTP 200 — stop** |
| OBJECT | OBJECT | **HTTP 200 — stop** |

### Experimental conclusion

The outcome is controlled by exactly one axis:

```text
function.arguments
```

The `tool.content` representation does not change the current result.

Therefore:

```text
arguments STRING
    -> FAIL

arguments OBJECT/MAPPING
    -> PASS
```

This is now executed evidence, not inference.

### Sept-15 `str has no attribute get` disposition

The older `'str' has no attribute 'get'` observation did not reproduce in any current 2x2 cell.

In particular:

```text
arguments OBJECT
tool.content OBJECT
    -> HTTP 200
```

Therefore that older failure is not part of the current compatibility defect.

Canonical status:

```text
Sept-15 str.get:
    HISTORICAL / NON-REPRODUCED ON CURRENT STACK
    NOT A BLOCKER FOR ARGUMENTS NORMALIZATION
```

Do not use it as evidence against the string -> mapping repair.

---

## 15. Confirmed repair requirement

The template boundary must normalize assistant tool-call arguments before rendering.

Confirmed contract:

```text
OpenAI/API history:
    function.arguments = JSON STRING

template-bound history:
    function.arguments = OBJECT/MAPPING
```

The live 2x2 proves that this conversion is necessary and sufficient for the reproduced failure.

The repair must preserve:

```text
public API output:
    STRING

internal template input:
    OBJECT
```

---

## 16. Promotion acceptance

After the repair, rerun the exact same 2x2.

Required result:

| assistant `function.arguments` | tool-message `content` | Expected after normalization |
|---|---|---|
| STRING | STRING | **200** |
| STRING | OBJECT | **200** |
| OBJECT | STRING | **200** |
| OBJECT | OBJECT | **200** |

Additional live acceptance:

```text
reasoning
 -> tool A
 -> tool result
 -> reasoning
 -> tool B
 -> tool result
 -> final answer
```

No template error may occur when the assistant tool-call history is replayed in standard OpenAI string form.
