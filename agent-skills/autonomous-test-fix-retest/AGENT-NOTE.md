# Note to agents

Load `SKILL.md` before a stabilization/debugging task with sequential blockers.

The behavioral contract is simple: an ordinary new failure is the next unit of work, not a handoff point. Continue reproduce → root cause → RED → minimal fix → build → retest → broader gate until the requested gate passes or a documented hard-stop condition genuinely requires a human decision.

Do not weaken acceptance by inventing skips, exclusions, ignored failures, or unrun green gates.
