---
name: worklog
description: Use when multiple agents, sessions, worktrees, or context resets must continue engineering work without losing provenance, decisions, evidence, open hypotheses, or exact Git state.
---

# Worklog

## Principle

Repository state is the authority, not chat memory. Preserve engineering continuity as immutable per-session records plus a compact derived `agent-worklog/CURRENT.md`.

## Start

Before consequential work:

1. Read `agent-worklog/CURRENT.md`.
2. Read the newest relevant files under `agent-worklog/sessions/`.
3. Re-resolve branch, HEAD, parent/base refs, and worktree status. Never trust a recorded SHA merely because it was once true.
4. Create a new session record from `agent-worklog/SESSION-TEMPLATE.md`. Never rewrite another agent's session record.

## Checkpoint

Record only externally useful engineering state, never private chain-of-thought:

- exact task and branch/base/HEAD;
- authorities and inherited decisions;
- commands/actions actually performed;
- files changed and resulting commit SHAs;
- tests with command plus PASS/FAIL/NOT_RUN;
- findings and negative evidence;
- decisions made and why;
- unresolved questions and next safe actions.

Use `PROVEN`, `DERIVED`, `INFERRED`, or `UNKNOWN` when evidence strength matters.

## Handoff

At session end:

1. Re-resolve HEAD and status.
2. Finish the session record. Do not claim unrun tests or acceptance.
3. Update `CURRENT.md` only with facts that remain current and include provenance to a session, commit, report, or artifact.
4. Keep historical failures and superseded hypotheses in session logs; `CURRENT.md` should contain only the current operational picture.

## Parallel Agents

Each agent writes a different session file. Agents do not append concurrently to one ledger. If two agents reach conflicting conclusions, preserve both records and mark the conflict in `CURRENT.md` until evidence resolves it.

## Commands

Interpret these names semantically even if the host has no slash-command implementation:

- `/worklog-start`: rehydrate state and open a session record.
- `/worklog-checkpoint`: append evidence/results to the current session.
- `/worklog-handoff`: close the session and refresh `CURRENT.md`.
- `/worklog-rehydrate`: read current state, relevant sessions, and re-resolve Git before continuing.

## Fail Closed

Never convert `UNKNOWN` into a guess. Never transfer runtime PASS from one SHA/package to another. Never use `CURRENT.md` to erase contradictory historical evidence.