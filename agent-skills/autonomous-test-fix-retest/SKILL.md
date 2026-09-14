---
name: autonomous-test-fix-retest
description: Use when an agent owns a debugging, stabilization, acceptance, or CI-repair task where fixing one failure is likely to expose another and routine failures should not require repeated human handoffs.
---

# Autonomous Test-Fix-Retest

## Overview

Own the repair loop until the requested gate is genuinely green or a real decision boundary is reached.

**Core principle:** a newly exposed routine failure is the next unit of work, not a reason to hand the task back.

If skills named `systematic-debugging`, `test-driven-development`, or `verification-before-completion` are available, use them for their respective phases. They are accelerators, not installation dependencies; this skill remains usable without them.

## When to Use

Use for test-suite stabilization, CI repair, acceptance runs, runtime crash triage, flaky-test investigation, integration hardening, and similar work where failures appear sequentially.

Do not use when the user requested only diagnosis, review, or one narrowly bounded experiment.

## The Loop

1. Establish the exact baseline: branch/HEAD or artifact identity, environment, command, failing gate, logs/dumps.
2. Reproduce the current blocker and classify it before editing code.
3. Find a minimal reproducer and causal mechanism. Mark unsupported hypotheses explicitly.
4. Create or identify a RED regression that fails for the proven reason.
5. Apply the smallest fix that restores the violated invariant.
6. Build or compile the affected target. A source diff is not validation.
7. Run the RED reproducer to GREEN, then related tests, then the broader gate.
8. If the broader gate exposes another ordinary blocker, name it and repeat from step 2 without asking for permission.
9. Commit validated independent fixes in small units when repository policy allows; push checkpoints only when remote work is expected or authorized.
10. Stop only at a hard-stop condition or when the requested final gate has actually run and passed.

## Hard Stops

Return to the human only when at least one is true:

- continuing requires a destructive or non-fast-forward operation not already authorized;
- evidence leaves a material architecture/product-policy choice unresolved;
- the only apparent route is weakening acceptance with skips, exclusions, ignored errors, arbitrary retries, or relaxed assertions;
- a dependency/version/pin change is required and that choice is outside the task's authority;
- required credentials, hardware, symbols, source, artifacts, or permissions are unavailable;
- evidence points outside an explicitly protected scope and modifying it requires approval;
- the next action is unsafe, irreversible, or materially broadens scope.

Compile errors, new deterministic test failures, rebuilding, another crash dump, or discovering the next bug are **not** hard stops.

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

Never infer an unrun gate. `NOT RUN` is valid evidence; imaginary green is not.

## Completion Contract

State exact HEAD/artifact lineage when available, commands or gates actually executed, pass/skip/fail counts where relevant, remaining failures, protected-scope changes, packaging/deployment status, and exactly one terminal state:

```text
STATUS: ELIGIBLE_FOR_ACCEPTANCE
```

or

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
| “Full suite is expensive.” | Run it when required to discover the next blocker and before final acceptance. |
| “Skip this platform-only failure.” | Do not weaken the gate without explicit authority. |
| “I changed code; it looks right.” | Build and execute verification. |
| “The remaining failure is unrelated.” | If it blocks the requested gate, it remains owned unless scope says otherwise. |
