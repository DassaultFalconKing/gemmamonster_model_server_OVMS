# Gemma4 structured-output whitespace bound — live verification report

Date: 2026-09-17. Author: DassaultFalconKing (GEMMAMONSTER track).
Scope: does the bounded-whitespace repair fix the reported live degeneration
(streaming named `tool_choice` emitting whitespace to `max_tokens` instead of
a tool call) without any parser changes? Answer: **yes**, within the recorded C2 research checkpoint described below.

## 1. Failing behavior (baseline, 2026-09-16)

Binary: stock `openvino.genai` base `fe818c04` (XGrammar `v0.1.31`), OVMS PR base.
Request: `POST /v3/chat/completions`, `temperature: 0.0`, `max_tokens: 512`,
tools `get_weather` / `search_docs` / `calculator`, named
`tool_choice: {"type":"function","function":{"name":"search_docs"}}`,
single user message ~5234 prompt tokens (long runbook context).

- unary (`stream: false`): `finish_reason: tool_calls`,
  `search_docs{"query":"dead-letter prefix handling"}`, 23 completion tokens.
- streaming (`stream: true`): ~100 tokens of newline/tab spam,
  `finish_reason: length`, zero `tool_calls`.

## 2. Repair under test (single axis, no parser changes)

- GenAI: `DassaultFalconKing/openvino.genai @ e00eada6f4cce794ac3b3f6053cdb0c9dc569e68`
  (`StructuredOutputConfig::JSONSchema` gains optional `max_whitespace_cnt`,
  serialized at schema-format level; XGrammar pinned to
  `9aa840b6d16abf094f3e8e2ac9c10465b77656c9`).
  Base: upstream `fe818c0467feb17b87c5adfb3f7e28dd70b76e99`.
  C++ contract tests 4/4 PASS
  (`LegacySerializationDoesNotSetWhitespaceBound`,
  `BoundIsSerializedAtSchemaFormatLevel`, `ZeroBoundIsNotTreatedAsUnset`,
  `EqualityIncludesWhitespacePolicy`).
- OVMS: PR base `d582668e6405e5d4cffbf050e9ee7303f7b94ef0` + whitespace call-site only
  (`JSONSchema(schema, 2)`); parser/validation untouched. Recorded C2 OVMS head:
  `eebda599f`.
- Runtime: `--version` reports OpenVINO `2026.5.0-23084-4977f92a234`,
  GenAI `2026.5.0.0-3447-e00eada6f4c`.

Full binary fingerprints for the frozen checkpoint:

```text
ovms.exe SHA256
C96E7819AFDCFE04CC3A2D423E17C94BBC2E5EAFCC28C8FE7FF4EE333C22740A

openvino_genai.dll SHA256
92AB145C8CF238E1F37CF84C2F72F93D3D978E9B7F7CFC726208D3B9FCF35AED

openvino_genai.lib SHA256
5AA71A0C49857C96E634783643DBAFD4EFC1D856E40F8701822C601260F0A77F
```

Identity authority:
`docs/gemmamonster/upstream-fix-20260917/identities/C2-whitespace-oldbase.identity-lock.md`.

## 3. Live result (2026-09-17, fresh reboot, isolated caches)

Reconstructed fixture calibrated to prompt=5232 tokens (original paragraph text
was not archived; tools/choice/params/temperature identical; fixture request
SHA256 recorded in the raw artifact set as `117525BB…D70AA1`).

- unary: `finish_reason: tool_calls`,
  `search_docs{"query":"dead-letter prefix handling"}`, 22 completion tokens.
- streaming, 3/3 runs: `tool_calls` observed in-stream, `finish_reason:
  tool_calls`, zero whitespace-only chunks, 22–23 completion tokens.
- Server healthy throughout; no GPU errors; no OOM.

Raw evidence retained in the C2 artifact root includes the canonical requests,
unary response, 3× raw SSE streams, build/test logs, and reusable gate script.
The C2 handoff records the artifact location and exact candidate identity.

## 4. Frozen checkpoint status

C2 is now frozen as an immutable research checkpoint.

Recorded PASS evidence:

- build PASS;
- GenAI whitespace contract tests 4/4 PASS;
- G5 named unary PASS;
- G6 named streaming PASS 3/3;
- fresh-reboot / isolated-cache host state recorded GREEN for the live gate.

Not claimed on this frozen checkpoint:

- full C2 promotion through every matrix gate;
- upstream-master GenAI compatibility;
- XGrammar-main compatibility;
- performance improvement.

No additional old-baseline or rebuilt-C2 reruns are planned. The exact G1/X1 binary identity above is preserved for byte-for-byte inheritance into C3.

## 5. What this proves / does not prove

Proves: on the recorded C2 identity, the bounded-whitespace repair produces correct streaming named tool calls without parser hardening, while the previously recorded baseline exhibited whitespace degeneration for the corresponding long-context scenario.

Does not prove: upstream-master compatibility (C4), XGrammar-main compatibility
(C5), complete matrix promotion of C2, or performance deltas.

## 6. Next

1. Construct C3 by adding the accepted parser-repair delta while reusing the frozen C2 G1/X1 artifacts byte-for-byte.
2. Verify the C3 GenAI DLL/LIB hashes against the C2 identity lock before C3 gates.
3. After C3, replay the whitespace contract + implementation on GenAI master `438e061` (C4).
4. Then move only XGrammar to `f6043f4` (C5).
5. Finish with the retained-delta ledger and clean reviewer-facing `SUPER-UPSTREAM` series (C6).
