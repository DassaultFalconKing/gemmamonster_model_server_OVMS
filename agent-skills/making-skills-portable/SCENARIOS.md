# Validation scenarios

## A. Repo-bound installer

A skill's install docs require cloning its origin repository and copying a nested directory. Expected: identify `ORIGIN_REPOSITORY_REQUIRED`; rewrite installation so extracted local bytes are sufficient.

## B. Hidden sibling helper

`SKILL.md` invokes `../tools/probe.py`. Expected: bundle the helper under the skill, update relative references, then test from a detached directory.

## C. Hard companion skill

The skill says another skill is REQUIRED but distribution does not include it. Expected: internalize the necessary contract or make the companion optional when available.

## D. Machine path

Docs contain `C:\git\project\...` or `/home/alice/project/...`. Expected: parameterize or use skill-relative paths.

## E. False green packaging

Source audit passed, but ZIP omitted a referenced script. Expected: extracted shipped bytes fail audit; fix packaging and regenerate metadata.

## F. Recursive case

Apply `making-skills-portable` to itself. Expected: self-audit and tests pass without reading any file outside its directory.
