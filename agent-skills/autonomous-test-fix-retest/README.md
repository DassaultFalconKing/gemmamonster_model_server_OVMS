# autonomous-test-fix-retest portable bundle

A self-contained agent skill for sequential debugging/stabilization work. The directory is the distribution unit: copy it anywhere, install it into a supported skill root, and no origin repository is required.

## Install

Cross-runtime default after copying or extracting the directory:

```bash
python install.py
```

POSIX shell alternative: `sh install.sh`.

PowerShell:

```powershell
.\install.ps1
```

Both default to the cross-runtime skill root (`~/.agents/skills`) and accept an explicit destination root.

## Verify

```bash
python scripts/selfcheck.py
python -m unittest discover tests -v
```

## Use without installation

Any agent that can read local files can consume `SKILL.md` directly. Installation is only for runtime discovery.

## Bundle contract

- No origin repository is required after extraction.
- No absolute machine path is required.
- Optional companion skills are never hard dependencies.
- `MANIFEST.json` describes the bundle.
- `SHA256SUMS` verifies all stable payload files except itself.
