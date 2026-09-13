---
name: autonomous-test-fix-retest
description: Use when an agent owns a debugging, stabilization, acceptance, or CI-repair task where fixing one failure is likely to expose another and routine failures should not require repeated human handoffs.
---

# Autonomous Test-Fix-Retest

## Overview

Own the repair loop until the requested gate is genuinely green or a real decision boundary is reached.

**Core principle:** a newly exposed routine failure is the next unit of work, not a reason to hand the task back.

**REQUIRED BACKGROUND:** Use `systematic-debugging` for root-cause work, `test-driven-development` for fixes, and `verification-before-completion` before any success claim when those skills are available.

## When to Use

Use this skill for test-suite stabilization, CI repair, acceptance runs, runtime crash triage, flaky-test investigation, integration hardening, and similar work where failures appear sequentially.

Do not use it when the user requested only diagnosis, review, or one narrowly bounded experiment.

## The Loop

1. Establish the exact baseline: branch/HEAD, environment, command, failing gate, logs/dumps.
2. Reproduce the current blocker. Classify it before editing code.
3. Find a minimal reproducer and causal mechanism. Reject unsupported hypotheses explicitly.
4. Create or identify a RED regression that fails for the proven reason.
5. Apply the smallest fix that restores the violated invariant.
6. Build or compile the affected target. A source diff is not validation.
7. Run the RED reproducer to GREEN, then related tests, then the broader gate.
8. If the broader gate exposes another ordinary blocker, name it and repeat from step 2 without asking for permission.
9. Commit validated independent fixes in small units; push useful checkpoints when remote work is expected.
10. Stop only at a hard-stop condition or when the requested final gate has actually run and passed.

## Hard Stops

Return to the human only when at least one is true:

- continuing requires a destructive/non-fast-forward operation;
- evidence leaves a material architecture/product-policy choice unresolved;
- the only apparent route is weakening acceptance by adding skips, exclusions, ignored errors, arbitrary retries, or relaxed assertions;
- a dependency/version/pin change is required and that choice is outside the task's authority;
- required credentials, hardware, symbols, source, artifacts, or permissions are unavailable;
- the evidence points outside an explicitly protected scope and touching it requires approval;
- the next action is unsafe, irreversible, or materially broadens scope.

Compile errors, new deterministic test failures, another dump, rebuilding, or discovering the next bug are **not** hard stops.

## Evidence Contract

For each blocker record:

```text
ID:
SYMPTOM:
MINIMAL_REPRODUCER:
ROOT_CAUSE: PROVEN | NOT_PROVEN
RED:
FIX:
BUILD:
TARGETED_GREEN:
BROADER_GATE:
COMMIT:
```

Never infer an unrun gate. `NOT RUN` is a valid result; imaginary green is not.

## Completion Contract

A completion report must state exact HEAD/commit(s), commands or gates actually executed, pass/skip/fail counts where relevant, remaining failures, protected-scope changes, packaging/deployment status, and either:

```text
STATUS: ELIGIBLE_FOR_ACCEPTANCE
```

or:

```text
STATUS: HARD_STOP
STOP_REASON: <specific decision/resource boundary>
```

Do not report `fixed`, `green`, `ready`, or `eligible` unless the corresponding verification actually ran.

## Common Failure Modes

| Temptation | Required behavior |
|---|---|
| “I found another failure, reporting back.” | Reproduce it and continue the loop. |
| “The likely cause is obvious.” | Prove the causal chain first. |
| “The targeted test passes, so done.” | Run the next broader required gate. |
| “Full suite is expensive.” | Run it when needed to discover the next blocker and before final acceptance. |
| “Skip this Windows-only failure.” | Do not weaken the gate without explicit authority. |
| “I changed code; it looks right.” | Build and execute verification. |
| “The remaining failure is unrelated.” | If it blocks the requested gate, it is still part of the owned stabilization task unless scope says otherwise. |
