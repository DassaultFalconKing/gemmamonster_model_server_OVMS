# Qwen tool-call publication contract

Decision (2026-10-21): publish identity after completed-call validation.

The original disabled test was executed on `8cd25d6`. A registered
`string_int_tool` prefix emitted name/id at index 0. Its invalid numeric argument
then caused rejection. A subsequent valid `cd` emitted arguments at index 0 with
no new name. The retained `evidence/LIFECYCLE-RED.txt` records both assertions.
This is a parser identity defect independent of grammar or model behavior.

An OpenAI SSE consumer cannot retract an already published tool header. The Qwen
parser therefore buffers each native call until the low-level parser completes
the envelope (or bounded natural-STOP recovery), and registry/argument checks
accept it. Only then does it allocate a public index and queue two adjacent
events: name/id first, arguments second. Rejected calls publish neither event
and consume no index. Indices increase in accepted call order. IDs are unique
within the request, with collision detection; argument deltas keep the same
index and do not replace its name/id. Reset clears the queue and ID registry.

Compatibility cost: a tool name is no longer observable while its arguments
are incomplete. Successful normalized tool payloads and header-before-arguments
ordering remain the same. Consumers must reconstruct the event sequence rather
than assume a name arrives at the end of a particular decoder chunk. The legacy
streaming fixtures retain their payload expectations under that contract.

Ownership: this decision belongs to `Qwen3CoderToolParser`; no Qwen-specific
branch is added to generic `OutputParser`. Prompt delivery of queued events is
a separate streamer concern. STOP can recover only a completed `</function>`;
LENGTH must not manufacture a completion. This decision does not establish full
JSON Schema validation or correct constrained generation.
