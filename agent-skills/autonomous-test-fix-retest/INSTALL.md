# Installation

This directory is self-contained. Do not clone an origin repository merely to install it.

## Cross-platform

```bash
python install.py
python install.py "$HOME/.claude/skills"
```

## POSIX shell

```bash
sh install.sh
sh install.sh "$HOME/.claude/skills"
```

## PowerShell

```powershell
.\install.ps1
# or
.\install.ps1 -TargetRoot "$HOME/.claude/skills"
```

The default target root is `~/.agents/skills`, giving the installed directory:

`~/.agents/skills/autonomous-test-fix-retest/`

If a runtime uses another native skill root, pass that root explicitly. Start a fresh agent session when the runtime only discovers skills at session initialization.
