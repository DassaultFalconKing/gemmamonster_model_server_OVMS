# R1 runner hardening: implementation contract

Base/revert point: `8ad9410de45a2f16e8fe7bc9e560f0c11387d7aa`.
ACCEPTED: NO. No native matcher or installed-cohort acceptance is implied.

1. Cause: the prepared runner accepts any 28 unique row names with 4 OPEN statuses;
   it does not assert SUMMARY, and timeout cleanup has unbounded waits. This can
   accept the wrong selected set or prevent a durable final status.
2. Files: scripts/qwenmonster/r1_gate.py, scripts/qwenmonster/r1_runner.py,
   scripts/qwenmonster/tests/test_r1_runner.py, and a new private preparation
   revision of run.py plus its sealed inputs. Preserve the prior manifest/tree.
3. Implementation: validate an explicit 28-name contract, expected row semantics
   and a single exact SUMMARY. Bound taskkill and the subsequent owned-process
   wait. Record cleanup uncertainty and fail closed; never kill unrelated PIDs.
   Require one exact companion SUMMARY and one observation per lazy mode; do
   not accept duplicate-mode or substring-only success. Skip PID-based cleanup
   when the retained process handle already reports exit, leaving descendant
   cleanup explicitly unconfirmed. Bind the actually executing runner/helper hashes to the sealed preparation,
   rather than checking only copies stored in the preparation directory.
4. Expected effect: substituted/missing/extra/duplicate rows, inconsistent counts
   and semantic fields cannot produce an OPEN gate success; a cleanup timeout
   yields durable failure/uncertainty rather than a stuck runner.
5. Tests: RED/GREEN against the actual runner orchestration with synthetic native
   output and fake owned-process handles. Positive OPEN control, adversarial row
   substitution, invalid/missing/duplicate SUMMARY, semantic mismatch and bounded
   cleanup tests. These tests run no compiler, matcher, model or real taskkill.
6. Provenance: current prepared runner, external R1 review and independent local
   confirmation. Portable validation and cleanup design are independent.

## Measured implementation checkpoint

- Baseline runner: RED, 8 failures plus an escaped cleanup-timeout exception;
  the latter is recorded as an explicit test failure in the retained RED run.
- Corrected runner: 18/18 offline tests PASS, including separately observed
  RED/GREEN for executing identity, relative external paths, duplicate lazy mode,
  substring-only companion success, manifest drift and already-exited cleanup.
- Explicit 28-name/semantic contract matches the prepared native matrix source.
- Original preparation preserved. New revision sealed separately; dry-run
  preflight PASS. Four inherited grammar defects still have OPEN status.
- Native configure/build/matcher, real Windows tree termination, new inference
  and installed-cohort changes: NOT RUN by these offline tests.
- External code review identified cleanup-scope and companion-output gaps;
  local RED/GREEN confirmed and corrected them. Initial manifest identity stays
  in a failed final result while a separate field records any observed drift.
- Malformed manifest structure can still fail closed with a Python traceback;
  this is not a complete manifest-schema validator. Windows environment handling
  and real process-tree termination were not changed into a new subsystem.
- Full acceptance remains NO.

Run portable offline tests from the repository root:

```powershell
rtk proxy python -m unittest discover -s scripts/qwenmonster/tests -p test_r1_runner.py -v
```

Check an explicitly prepared input package without invoking a compiler:

```powershell
rtk proxy python scripts/qwenmonster/r1_runner.py --preparation-root <prepared-root>
```

The package must seal logical run.py (identical to r1_runner.py), r1_gate.py,
native sources/headers, tools and runtime identities. Runtime Python home and
Python path are explicit input-manifest fields; no machine path map is embedded
in repository code. Actual native execution additionally requires the separate
resource-slot flag and the project's serialized resource checks.
