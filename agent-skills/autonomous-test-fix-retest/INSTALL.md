# Installing the portable skill

The portable unit is the directory:

`agent-skills/autonomous-test-fix-retest/`

## Recommended cross-runtime install

Clone or update the remote branch, then copy the directory to:

`~/.agents/skills/autonomous-test-fix-retest/`

The installed directory must contain `SKILL.md` at its root.

Example:

```bash
git clone --depth 1 --branch skills/autonomous-test-fix-retest \
  https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS.git /tmp/gemmamonster-skills
mkdir -p ~/.agents/skills
rm -rf ~/.agents/skills/autonomous-test-fix-retest
cp -R /tmp/gemmamonster-skills/agent-skills/autonomous-test-fix-retest ~/.agents/skills/
```

On runtimes with a different native skill directory, copy or symlink the same folder there. Claude Code commonly uses `~/.claude/skills/`; Codex, Gemini CLI, and Copilot CLI can use the cross-runtime `~/.agents/skills/` location.

Restart or start a fresh agent session if the runtime discovers skills only at session initialization.

## Verify installation

Ask the agent to list/read its available skill named:

`autonomous-test-fix-retest`

Then give it a stabilization task with sequential failures and verify that it continues after the first ordinary blocker instead of handing the task back prematurely.
