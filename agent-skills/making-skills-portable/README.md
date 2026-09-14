# making-skills-portable

A self-contained skill plus stdlib-only portability tool for auditing and packaging other agent skills.

## Install

```bash
python install.py
```

Shell/PowerShell alternatives are also bundled.

## Tool

```bash
python scripts/skill_portability.py audit <skill-dir>
python scripts/skill_portability.py refresh <skill-dir> --version 1.0.0
python scripts/skill_portability.py package <skill-dir> <output.zip> --version 1.0.0
```

`package` refreshes metadata, audits the resulting bundle, and writes a deterministic ZIP using normalized entry ordering, permissions, and timestamps.

## Verify this skill

```bash
python scripts/skill_portability.py audit .
python -m unittest discover tests -v
```

The package intentionally uses only Python's standard library.
