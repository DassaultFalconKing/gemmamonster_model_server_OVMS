# Local execution checkpoint (2026-10-21)

- ACTIVE_STAGE: initial unmodified Bazel build / dependency audit
- BASE_SHA: ba6ec792c3121850fea167fa7d7e190b25fcdc76
- WORK_BRANCH: feature/qwenmonster-parser-invariants-20261021
- CURRENT_HEAD: 8cd25d63085637d112f616d62913e345a93d2233
- DEPENDENCY_LOCK: ../public-source-lock.json (unchanged)
- LAST_GREEN_TESTS: source-only preflight, all six sources; no compiled tests yet
- CURRENT_FAILURE: installed cohort Minja checkout advanced to after-lock commit;
  its installed GenAI build cannot yet be asserted to match the locked cohort.
- ROOT_CAUSE: checkout identity differs; build.ninja includes that checkout.
  The after-lock change is confined to a test Jinja fixture, but matching build
  provenance must still be established independently.
- NEXT_ACTION: retain initial Bazel result; establish locked Minja build input;
  execute lifecycle RED before implementation.
- REVERT_POINT: 8cd25d63085637d112f616d62913e345a93d2233
- EVIDENCE_PATH: local build logs under C:/gm/qwenmonster/evidence;
  PUBLIC-COHORT-SOURCE.json preserves initial mismatch, pinned JSON records repair.
- ACCEPTED: NO

Remote HEAD matched local checkout; comparative-refit ancestry was 0 behind / 7
ahead. A separate clean worktree was created. The stale PREC6 gitfile was left
untouched. Initial wrapper failed before Bazel because compiler environment setup
was reached with an unsuitable inherited PATH; prepending Python 3.12 permitted
Bazel to start. No product source has been changed at this checkpoint.
