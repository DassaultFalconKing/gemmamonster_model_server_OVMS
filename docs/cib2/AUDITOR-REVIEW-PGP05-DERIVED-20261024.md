# CIB2 PGP Wave-01: independent post-Cursor auditor delta (2026-10-24)

**Base:** `feature/cib2-pgp-wave01-cursor-integration-20261024`
at `be50ed1c25fe45bd1cac7c255a9ddb838b2d7a22` (Draft PR #27).
**Audit scope:** only `scripts/cib2/benchmark_screen.py`,
`tests/cib2/test_benchmark_screen.py` and related `docs/cib2`.
The source branch and unrelated P1 Static PR #26 remain unchanged.

**Review judgement:** Cursor's 174/174 Python 3.14.6 host test receipt is
accepted as an *operator-reported* host result at that source lineage.
This separate QA branch fixes downstream arithmetic cases outside the
174-test corpus; its modified suite requires an independent host run.
No GPU, OVMS, weights, Pack V1 or native acceptance is implied.

## Audit delta

- **PGP05-F1, MEDIUM:** individual `tokens / wall_seconds` may be finite,
  but `statistics.median` for four finite ~1e308 values can return
  positive infinity because it averages the two middle values.
  New post-aggregate finite check rejects it as `ScreenError`.
- **PGP05-F2, MEDIUM:** the A1-vs-A0 percentage difference can overflow to
  infinity with finite, schema-valid medians (e.g. A0 ~1e-16 TPS,
  A1 ~1e308 TPS). New derived-delta finite check rejects it.
- **PGP05-F3, LOW:** streaming `json.dump(..., sys.stdout, allow_nan=False)`
  can print a partial object before rejecting a nonfinite value.
  Serialize completely with `json.dumps` before writing to stdout.
  Every rejection remains structured, exit code 2, and never promotes.
- **PGP05-F4, programme consistency (no code restriction):** receipt schema
  compares the exact scenario across arms; it must not arbitrarily reject
  r10/r30/r50 historical offload cohorts merely because a proposed
  four-point benchmark protocol names r0/r20/r40/r75. Similarly,
  `slots=1/2/4` are the intended C1/C2/C4 campaign cells, but making
  them exclusive at the generic receipt-parser level needs a separately
  versioned execution protocol. This review adds no new enums.

## Regression plan

Four added tests cover even-size median overflow, finite TPS/percent delta
overflow, CLI structured rejection without partial stdout, and preservation
of legacy ratio scenarios as offline-only. Original 174/174 evidence is not
relabelled as passing these tests. Expected full suite count after adding
four tests: **178**, only if the operator reruns it and confirms.

```powershell
py -3 -m unittest discover -s tests/cib2 -p test_benchmark_screen.py -v
py -3 -m unittest discover -s tests/cib2 -p "test_*.py" -v
py -3 -m py_compile scripts/cib2/benchmark_screen.py
git diff --check
```

## Remaining integration path

- PR #27 consolidates cloud PGP #24/#25 and Cursor host hardenings.
- PR #26 independently hardens the P1 static-name checker and requires
  the operator's focused/full host regression before CIB2 integration.
- This PR is a *delta QA* on PR #27 and must not silently reset or
  replace its worktree or claim prior tests covered the patch.
- P0 source/build/module identity and P1 compiled eligibility remain open.
  P2 lease RED, native P3/P5 Pack V1 and GPU live parity remain NOT_RUN.
- Keep Path A the default and Path B OFF.
