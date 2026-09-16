# Agent Handoff / Push Protocol

Status: `MANDATORY / APPLIES_TO_FRANKENSTEIN_MATRIX`
Date: 2026-09-17

This protocol is mandatory for every agent/operator executing the Gemma4 Frankenstein candidate matrix (`C0` through `C6`) or any heavy build/test/repair stage feeding it.

## 1. Core rule

Every meaningful stage ends with a **written handoff committed and pushed to the remote branch immediately**.

Do not leave authoritative state only in:

- terminal scrollback;
- local worktree notes;
- an unpushed commit;
- an artifact directory without a remote pointer;
- chat prose that is not reflected in the repository.

The next agent/reviewer must be able to reconstruct the exact state from the remote repository without access to the previous process.

## 2. When a handoff is mandatory

Write, commit, and push a handoff immediately after any of the following:

1. a candidate build finishes, succeeds, fails, or is cancelled;
2. a focused or full test gate completes;
3. live GPU acceptance completes or fails;
4. a reboot/cache-clean boundary is reached before switching candidates;
5. a candidate is promoted, rejected, quarantined, or superseded;
6. a dependency identity changes (OVMS / GenAI / XGrammar / OpenVINO pins);
7. an unexpected regression is classified or a new blocker is found;
8. work must stop before the planned next gate;
9. a repair branch becomes the new resume point;
10. before handing execution to another agent/operator.

For long-running builds, do not fabricate progress handoffs while compilation is still running. Either let the build finish, or explicitly cancel it and record the attempt as incomplete/non-evidence.

## 3. Required handoff contents

Every handoff must record at minimum:

```text
candidate_id
status
repository
branch
local_head
remote_head_before_push
remote_head_after_push
upstream_base
ovms_head
ov_genai_head
xgrammar_sha_or_tag
openvino_pin
openvino_tokenizers_pin
host_state
reboot_state
cache_state
build_state
build_command
test_state
test_commands
passed_gates
failed_gates
non_evidence_runs
artifact_root
binary_sha256
known_blockers
next_exact_action
resume_point
```

If a field does not apply, write `n/a`; do not silently omit identity-critical fields.

## 4. Build/test truthfulness

The handoff must distinguish clearly between:

- `PASS` — command completed successfully and evidence exists;
- `FAIL` — command completed and failed;
- `BLOCKED` — could not execute because of an identified prerequisite;
- `RUNNING` — only allowed while the same agent continues execution; not a final handoff state;
- `CANCELLED_NON_EVIDENCE` — explicitly cancelled heavy operation;
- `DIRTY_HOST_NON_EVIDENCE` — result invalidated by overlapping runtimes/builds, stale GPU/runtime state, missing reboot/cache hygiene, or unknown binary identity;
- `NOT_RUN` — no execution evidence exists.

Never turn an inferred result, old candidate result, clean compilation, or source inspection into `PASS` for a gate that was not actually executed on the recorded candidate identity.

## 5. Immediate push rule

After writing the handoff:

1. commit source/test changes first when they are part of the stage;
2. update the handoff so it references the resulting exact commit SHA(s);
3. commit the handoff;
4. push the branch immediately;
5. fetch/re-resolve the remote branch;
6. verify `remote HEAD == expected pushed HEAD`;
7. record the verified remote HEAD in the final handoff state.

An unpushed handoff is not authoritative.

Do not start the next heavy operation until the previous stage's source state and handoff are remotely recoverable, except for a trivial read-only inspection that cannot mutate or consume the host runtime state.

## 6. Remote-first resume rule

A new agent/session must resume from remote truth, not from a remembered local state:

1. fetch the relevant branch;
2. resolve its exact remote HEAD;
3. read the latest handoff(s);
4. compare the local worktree with the recorded remote HEAD;
5. verify candidate/dependency identity;
6. only then continue execution.

If local and remote state diverge, stop promotion work and reconcile the divergence first. Do not guess which side is authoritative.

## 7. Handoff placement

Use candidate-local handoffs where possible:

```text
docs/gemmamonster/upstream-fix-20260917/handoffs/
  C1-parser-only.md
  C2-whitespace-oldbase.md
  C3-frankenstein-old.md
  C4-frankenstein-newgenai.md
  C5-frankenstein-newxgrammar.md
  C6-super-upstream.md
```

A candidate handoff is updated in place as that candidate advances. Preserve exact test/artifact references rather than replacing historical failures with only the final GREEN state.

For cross-cutting repair work, maintain the existing live `HANDOFF.md` and link the candidate-specific handoff.

## 8. Heavy-operation boundary integration

The handoff protocol is coupled to the host-state protocol in `FRANKENSTEIN-TEST-MATRIX.md`.

Before moving to the next heavy operation, the handoff must state:

- whether the previous prototype/runtime has been stopped;
- whether the previous compilation completed or was cancelled;
- whether reboot is required before the next GPU run;
- whether candidate-local GPU/OpenVINO/GenAI/XGrammar caches were cleaned or isolated;
- whether the host is acceptable for promotion evidence.

If any of these are unknown, mark the host state `DIRTY_HOST_NON_EVIDENCE` and do not use subsequent live results for promotion until the reboot/cache protocol is satisfied.

## 9. Promotion requirement

No candidate `C1` through `C6` may be promoted unless:

- its current handoff exists in the repository;
- the handoff references the exact candidate identities and evidence;
- all claimed gates are supported by logs/artifacts;
- the handoff commit is pushed;
- the pushed remote HEAD has been verified;
- the next exact action / resume point is unambiguous.

For `C6 SUPER-UPSTREAM`, the final handoff must additionally contain the retained-delta ledger, PR split/order, clean-build identity, reboot/cache hygiene state, and all final gate results.

The goal is simple: at every boundary, another agent can continue from GitHub alone without reconstructing state from folklore.