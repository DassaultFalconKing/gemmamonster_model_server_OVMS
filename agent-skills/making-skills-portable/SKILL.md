---
name: making-skills-portable
description: Use when an agent skill works only inside its origin repository, depends on machine-specific paths or companion skills, lacks a standalone installer or integrity metadata, or needs to be distributed as a self-contained reproducible bundle.
---

# Making Skills Portable

## Overview

Turn a repo-bound skill into a directory that can be copied, audited, installed, tested, and packaged without its origin repository.

**Portability invariant:** after extraction, the skill's required behavior must depend only on files inside its directory plus capabilities explicitly provided by the host runtime.

## Procedure

1. **Inventory the real unit.** Read `SKILL.md` and every file/path it requires. Separate required payload from examples, provenance, caches, build output, and origin-repo convenience files.
2. **Prove the current portability failure.** Run `scripts/skill_portability.py audit <skill-dir>` and add a regression for any failure the generic audit cannot express.
3. **Remove hard bindings.** Replace machine paths and origin-repo installation steps with relative paths, arguments, environment variables, or files bundled inside the skill.
4. **Internalize required helpers.** If the skill requires a script/template/reference to function, ship it under the skill directory. Companion skills may be optional accelerators, never undisclosed hard dependencies.
5. **Add a standalone surface.** Provide `README.md`, `INSTALL.md`, `install.py`, `install.sh`, and `install.ps1`. Make `install.py` the extraction-safe default because executable mode bits are not preserved by every ZIP extractor. Default to `~/.agents/skills`; allow an explicit target root for runtimes such as `~/.claude/skills`.
6. **Preserve provenance without requiring it.** Put source repo/commit/history in a reference file if useful. The skill must still work when that source is unreachable.
7. **Add integrity metadata.** Generate `MANIFEST.json` and `SHA256SUMS` with the bundled tool. Do not hand-edit generated metadata.
8. **Test detached.** Copy or extract the directory outside the source checkout, run its self-tests/audit there, and verify no sibling repo files are consulted.
9. **Package reproducibly.** Use the bundled `package` command. It creates a sorted, timestamp-normalized ZIP and excludes transient VCS/cache files.
10. **Re-audit after every packaging change.** Portable means the shipped bytes pass, not that the source tree looked portable earlier.

## Commands

```bash
python scripts/skill_portability.py audit ./my-skill
python scripts/skill_portability.py refresh ./my-skill --version 1.0.0
python scripts/skill_portability.py package ./my-skill ./dist/my-skill-1.0.0.zip --version 1.0.0
```

## Portability Boundaries

A skill may require runtime capabilities explicitly named in its purpose, such as Git, a browser, or Python. It must not silently require a particular clone path, repository sibling, user home layout, branch name, private connector, or another skill just to understand its core procedure.

## Common Mistakes

| Mistake | Correction |
|---|---|
| “Portable” means “documented git clone command.” | Make the directory itself the distribution unit. |
| Source URL appears in install steps. | Move provenance to reference material; install from local bytes. |
| Helper script stays elsewhere in the repo. | Bundle it under `scripts/`. |
| Required companion skill is absent. | Internalize the necessary rule or make the companion explicitly optional. |
| ZIP was made manually. | Generate manifest/checksums and use deterministic packaging. |
| Audit passes only in the source checkout. | Verify from a detached copy/extraction. |
