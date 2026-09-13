# Teaching agents to use autonomous-test-fix-retest

This skill is for agents that repeatedly stop after exposing the next ordinary blocker in a stabilization or acceptance task.

## Human-side instruction

When assigning a multi-failure debugging task, add one short requirement near the top of the prompt:

> Before starting, load and follow the `autonomous-test-fix-retest` skill. Own sequential routine failures until the requested gate is green or a documented hard stop requires a human decision.

Do not paste the whole workflow into every prompt. The point of the skill is to make the reusable behavior discoverable and consistent.

## First-time training pattern

1. Install the skill in the agent runtime.
2. Start a fresh session if skills are discovered only at startup.
3. Give the agent a task with a clearly stated final gate, protected scopes, and forbidden shortcuts.
4. Explicitly name the skill once in that first task.
5. Inspect whether the agent continues after the first newly exposed ordinary failure.
6. If it stops prematurely, point it back to the skill's Hard Stops section rather than rewriting the whole task.

## Good task framing

State these inputs:

```text
FINAL_GATE: <the actual command/test/gate that must pass>
PROTECTED_SCOPE: <paths/components that require proof or approval>
FORBIDDEN_SHORTCUTS: <new skips/exclusions, ignored failures, force-push, packaging, etc.>
REMOTE_POLICY: <whether/when validated checkpoints should be pushed>
```

Then say:

> Use `autonomous-test-fix-retest`. A new deterministic failure discovered while pursuing FINAL_GATE is the next unit of work, not a handoff point.

## What not to do

Do not tell the agent to “keep going no matter what.” The skill deliberately distinguishes routine repair work from architecture, policy, authorization, destructive Git, dependency-pin, and safety boundaries.

Do not accept reports that replace unrun gates with inference. `NOT RUN` is evidence; guessed green is fiction.

## Teaching by correction

If an agent returns too early, the correction should be short:

> This is not a hard stop under `autonomous-test-fix-retest`. Continue from the newly exposed blocker through reproduce → root cause → RED → minimal fix → build → retest → broader gate.

If the agent reaches a genuine hard stop, require exact evidence and the smallest concrete human decision needed to resume.

## Periodic verification

Use the pressure scenarios in `TESTS.md` when changing the skill. The observed baseline failure that motivated the skill was premature handoff after a newly exposed ordinary blocker during Windows acceptance stabilization.
