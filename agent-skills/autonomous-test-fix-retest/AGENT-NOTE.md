# Note to agents

If you were given this note because you keep returning after every newly exposed test failure, install and use the portable skill `autonomous-test-fix-retest`.

Remote source:

`https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS`

Branch:

`skills/autonomous-test-fix-retest`

Skill directory:

`agent-skills/autonomous-test-fix-retest/`

Preferred cross-runtime destination:

`~/.agents/skills/autonomous-test-fix-retest/`

After installation, read `SKILL.md` before continuing any debugging/stabilization task with sequential blockers.

The important behavioral contract is simple: an ordinary new failure is the next unit of work, not a handoff point. Continue test → root cause → RED → minimal fix → build → retest → broader gate until the requested gate passes or a documented hard-stop condition genuinely requires a human decision.

Do not weaken acceptance by inventing skips, exclusions, ignored failures, or unrun green gates.
