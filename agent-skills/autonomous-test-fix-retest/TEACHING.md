# Teaching agents to use autonomous-test-fix-retest

When assigning a multi-failure debugging task, state the final gate, protected scope, forbidden shortcuts, and remote policy. Then instruct the agent once to load `autonomous-test-fix-retest`.

Recommended task fields:

```text
FINAL_GATE: <actual command/test/gate>
PROTECTED_SCOPE: <paths/components requiring proof or approval>
FORBIDDEN_SHORTCUTS: <skips/exclusions/ignored failures/destructive Git/etc.>
REMOTE_POLICY: <whether validated checkpoints may be pushed>
```

If the agent returns after a routine newly exposed blocker, point it to the Hard Stops section. Do not replace the skill with “keep going no matter what”; architecture, policy, authorization, dependency and safety boundaries remain real stops.

Use `TESTS.md` as pressure scenarios when revising the skill.
