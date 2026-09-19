# Worklog pressure scenarios

These scenarios define the behavior the skill must enforce.

## Scenario 1: New agent after context loss

Given only the repository and a vague instruction such as “continue RC2”, the agent must not infer the active source or build state from memory. It must read `agent-worklog/CURRENT.md`, relevant session logs, then re-resolve Git refs before acting.

Failure pattern the skill is intended to prevent: continuing from a stale SHA or an obsolete integration branch because an earlier chat called it “current”.

## Scenario 2: Two agents in parallel

Agent A investigates RC1 build provenance while Agent B reviews Gemma4 parser lineage. They must write separate session records. Neither may overwrite the other’s findings. Conflicts are surfaced in `CURRENT.md` with provenance instead of being silently reconciled.

Failure pattern: one shared mutable log where the second agent destroys or ambiguously edits the first agent’s evidence.

## Scenario 3: Runtime evidence does not transfer

A source commit passes unit contracts while another package built from a related lineage passes live Arc 140V runtime acceptance. The worklog must preserve these as separate facts and must not label a new candidate accepted until that exact package is tested.

Failure pattern: “same code family, therefore PASS”.

## Scenario 4: Historical hypothesis is disproved

An agent records a suspected parser defect. A later raw trace proves the model never emitted a tool marker. The later session records the contrary evidence and `CURRENT.md` is updated, but the older session remains immutable.

Failure pattern: rewriting history so future agents cannot see why the investigation changed direction.

## Verification status

The project already contains examples of stale-state, mixed-provenance, and cross-SHA acceptance confusion that motivate these scenarios. A dedicated automated/subagent RED→GREEN replay has NOT been executed in this chat environment; do not claim the skill itself is behaviorally verified until such a replay is run.