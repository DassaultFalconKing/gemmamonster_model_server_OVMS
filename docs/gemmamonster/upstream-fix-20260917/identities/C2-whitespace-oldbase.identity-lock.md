# C2 WHITESPACE-OLDBASE — immutable identity lock

Status: `IMMUTABLE_RESEARCH_CHECKPOINT`
Date locked: 2026-09-17
Purpose: freeze the exact C2 source/dependency/binary identity that produced the recorded live whitespace result, and require byte-for-byte reuse of the G1/X1 dependency identity by C3.

This file is an identity record, not a claim that every C2 promotion gate was executed.

## 1. Candidate identity

```text
candidate_id=C2-whitespace-oldbase
candidate_branch=test/gemma4-c2-whitespace-oldbase-20260917
ovms_head=eebda599f
ovms_upstream_base=d582668e6405e5d4cffbf050e9ee7303f7b94ef0
ov_genai_head=e00eada6f4cce794ac3b3f6053cdb0c9dc569e68
ov_genai_upstream_base=fe818c0467feb17b87c5adfb3f7e28dd70b76e99
xgrammar_sha=9aa840b6d16abf094f3e8e2ac9c10465b77656c9
xgrammar_previous_stock_pin=v0.1.31
openvino_source_identity=4977f92a
openvino_tokenizers_identity=b40486a0
```

OVMS composition:

```text
O0 d582668
+ O2 whitespace call-site repair
+ candidate-specific dependency wiring
```

No C1 parser-repair delta is part of this identity.

## 2. Required Windows dependency wiring

The successful C2 build established that repointing `windows_genai` alone is insufficient because headers from `windows_openvino` can shadow the G1 GenAI headers.

For this identity both repositories resolved to the same G1 runtime slot:

```text
windows_genai   -> C:\opt\openvino_g1\runtime
windows_openvino -> C:\opt\openvino_g1\runtime
```

C3 must preserve this dependency identity relationship. Do not combine G1 libraries with older GenAI headers from another OpenVINO runtime root.

## 3. Binary fingerprints

```text
ovms.exe SHA256
C96E7819AFDCFE04CC3A2D423E17C94BBC2E5EAFCC28C8FE7FF4EE333C22740A

openvino_genai.dll SHA256
92AB145C8CF238E1F37CF84C2F72F93D3D978E9B7F7CFC726208D3B9FCF35AED

openvino_genai.lib SHA256
5AA71A0C49857C96E634783643DBAFD4EFC1D856E40F8701822C601260F0A77F
```

Recorded runtime version strings:

```text
OpenVINO 2026.5.0-23084-4977f92a234
GenAI    2026.5.0.0-3447-e00eada6f4c
```

Recorded package:

```text
C:\git\gemmamonster-C2\dist\windows\ovms.zip
149 MB / 37 files
```

Recorded artifact root:

```text
C:\git\artifacts\gemma4-frankenstein-20260917\C2-whitespace-oldbase\
```

Machine-local paths are historical evidence locations only. The hashes and source SHAs above are the portable identity authority.

## 4. Recorded gates / result

Executed and recorded:

```text
build=PASS
G1 StructuredOutputJSONSchema=4/4 PASS
G5 named unary=PASS
G6 named streaming=PASS 3/3
G13 host-state/reboot/cache hygiene=recorded GREEN for live gate
```

Recorded live behavior:

```text
unary:
  finish_reason=tool_calls
  tool=search_docs
  arguments={"query":"dead-letter prefix handling"}
  completion_tokens=22

streaming:
  runs=3/3
  tool_calls observed=True
  finish_reason=tool_calls
  whitespace_only_chunks=0
  completion_tokens=22-23
```

Not closed on this frozen C2 checkpoint:

```text
G2 focused OVMS whitespace-bound test
G4 full 64-case semantic suite on exact C2
G7 dogfood replay
G8 formal promotion diff-audit closure
```

Therefore the locked conclusion is deliberately narrow:

```text
C2_RESEARCH_QUESTION=PASS
C2_FULL_PROMOTION=NOT_CLAIMED
```

## 5. Freeze contract

After this lock is written:

- do not rebuild C2 merely to obtain more historical evidence;
- do not overwrite the recorded G1/X1 runtime slot in place;
- do not mutate C2 and continue calling the result C2;
- do not substitute a newly rebuilt `e00eada6` binary and assume binary identity equivalence;
- do not reopen the old baseline solely for another A/B run;
- preserve existing raw C2 artifacts/logs read-only where practical.

Allowed operations:

- copy the frozen G1/X1 runtime to an immutable slot;
- hash-verify copied artifacts against this lock;
- read/archive existing evidence;
- use the exact dependency identity as an input to C3.

If the physical runtime is copied to the planned canonical slot:

```text
C:\git\gemma4-runtimes\G1-X1\
```

then `openvino_genai.dll` and `openvino_genai.lib` must match the SHA256 values above before C3 uses it. Copying is not a new candidate; rebuilding is.

## 6. C3 inheritance contract

C3 is allowed to change the OVMS parser/validation side only.

Required invariant from C2 -> C3:

```text
GenAI source identity:  e00eada6f4cce794ac3b3f6053cdb0c9dc569e68
XGrammar identity:      9aa840b6d16abf094f3e8e2ac9c10465b77656c9
openvino_genai.dll:     92AB145C8CF238E1F37CF84C2F72F93D3D978E9B7F7CFC726208D3B9FCF35AED
openvino_genai.lib:     5AA71A0C49857C96E634783643DBAFD4EFC1D856E40F8701822C601260F0A77F
```

C3 may produce a different `ovms.exe` hash because OVMS source changes are the point of C3.

Before C3 live acceptance, its handoff must state whether the frozen G1/X1 artifacts matched this identity lock. A mismatch means the candidate is not the intended C3 composition and must not be compared against C2 as a single-axis transition.

## 7. Authority

For C2 dependency/binary identity, this file supersedes mutable prose descriptions elsewhere if they conflict.

For test scope and promotion requirements, `FRANKENSTEIN-TEST-MATRIX.md` remains the authority.

For operational continuation, use `handoffs/C2-whitespace-oldbase.md`, which explicitly points forward to C3 without reopening C2.
