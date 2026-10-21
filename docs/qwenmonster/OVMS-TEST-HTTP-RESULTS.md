# Full ovms_test / QWM HTTP gate — 2026-10-21

**QWM request unit gate: PASS. ACCEPTED: NO.**

Tested product commit `e0772d161a81ed3420082af2bf68ab46d342e904`;
all subsequent repository changes in this execution are workflow/evidence docs.
The exact core source lock is unchanged and all six source checks pass.

| Gate | Result |
|---|---|
| Full `//src:ovms_test` build | PASS, exit0 |
| QWM-01 request schema profile + Hermes isolation | 2/2 PASS; the intake test covers 12 table cases |
| Related tool-request controls | 11/11 PASS |
| Qwen parser in full executable | 69/69 PASS |
| Gemma parser in full executable | 67/70, exactly the three previously retained failures |
| Actual loaded core DLL identities | GenAI/OpenVINO/Tokenizers hashes match staged inputs |
| HTTP400 transport / live model / agent loops | NOT RUN |

Each run first verified its exact enabled GTest listing, then executed the same
filter and checked a new XML file's timestamp, names, counts and statuses plus
process exit code. Zero-test or excess-test selection is a failure. The parser
control invocation exited1 for the retained Gemma failures; it is not all-green.
Raw XML/logs and exact local command lines are retained privately, with hashes
in `evidence/ovms-test-http-20261021/RESULTS.json`.

## Root causes and smallest environment repairs

1. Missing BoringSSL/curl/OpenCV installations prevented dependency analysis.
   Restored recipe-selected BoringSSL-SwiftPM0.32.1, curl Windows8.22.0_2 and
   official OpenCV4.14.0; verified upstream digests and local files. The official
   OpenCV DLL differs from the historical release DLL, so no old binary acceptance
   is inherited. The vc17 layout alias references unchanged official vc16 files.
2. Repository rules found a different `python3`; the old embedded Python lacked
   development headers/import library. A private CPython3.12.10 development
   package was verified against NuGet catalog SHA512. Both interpreter entry
   points, repository/action variables and actual stdlib/include locations were
   checked. No global PATH or core runtime replacement was performed.
3. Bazel7.4.1's default Windows symlink mode created a directory junction for a
   generated Protobuf file. Reproduced C1083/WinError267, verified file-symlink
   capability, enabled startup `--windows_enable_symlinks`, removed only one
   validated invalid derived junction, and rebuilt. The same header is now a
   file symlink and the object compiles. No generated header was fabricated.
4. Prepared only the needed tokenizer fixture from official
   `facebook/opt-125m@27dcfa74d334bc871f3234de431e71c6eeba5dd6` with the pinned local conversion runtime.
   Three token-ID probes (including Unicode) match the reference tokenizer.
   No inference model weights were downloaded or executed.

No product C++ or dependency source patch was needed. Accepted C6 source/install
and published core lock remain intact. No candidate #802 library was deployed.

## Workflow rules

`AGENTS.md` section8 now covers full-vs-focused target scope, pinned dependency
restoration and junctions, full Python development inputs, native argument
arrays, isolated incremental output, bounded jobs, fixture cwd/provenance,
exact GTest-set checks, fresh XML authority, retained baseline failures, actual
loaded-module provenance and the distinction between unit/API/live gates.
An independent read-only OpenCode review identified filter-loss and stale-XML
risks; the rules and private execution guards were tightened and used here.

Next: a separate real HTTP400 transport probe, then remaining grammar/cohort
integration and canonical target-model/live acceptance. Source and parser units
alone do not close these gates.
