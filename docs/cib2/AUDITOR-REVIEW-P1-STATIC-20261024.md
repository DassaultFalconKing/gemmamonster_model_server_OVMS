# CIB2-P1 independent static-auditor review (2026-10-24)

**Subject:** local worker branch `feature/cib2-p1-static-eligibility-20261024`,
original commit `608c9c555a62cad5076ef2dfa8283ffda8439ae2`,
direct parent `279f4097f9340cd9044c92ee43e67b0b24ab54d2`.

**Decision:** ACCEPT the local findings as *static name observations* with code
hardening in this separate audit branch. Do **NOT** close CIB2-P0 or CIB2-P1.
`compiled_kind=UNKNOWN`, `source_build_association=UNVERIFIED`,
`loaded_modules=NOT_RUN`, `runtime_acceptance=NO`. No GPU/model or Pack V1
work performed by this review. Worker source branch is unchanged.

## Independently reviewed evidence

- Git commit is one direct child of the supplied coordinator base and changes
  only `docs/cib2`, `scripts/cib2`, `tests/cib2`.
- Ornith JSON internal recount: 120 records, 40 block IDs 0..39 with exactly
  3 entries each (`down/weight`, `down/scale`, `down/zp`), no duplicate
  `layer_id` among recorded matches, no null offset/size in those records.
  Nine-name co-occurrence: 0/40. This is an **internal audit of committed JSON**,
  not independent rereading of the operator's original XML or any BIN.
- Gemma26 report gives 0 matches for the strict Ornith
  `.mlp.experts.` name rule, but *separately reported* 30/30 blocks with
  nine `mlp.{gate,up,down}_proj` names. This alternative recount was performed
  by the local worker and is not independently reproducible with
  `static_nine_slice.py` as written. The `mlp.*` names and separate
  `experts.down_proj` / `ListUnpack` records must not be equated with
  nine native per-expert Pack V1 tensors or compiled GEMM3_SWIGLU.
- P0 receipt: six SHA-256 values match a prior on-disk identity receipt.
  The source root contains no observed `stable-status.txt`, but that path
  is not a Bazel execution/output tree, so absence does **not** prove lack
  of a build stamp elsewhere. No loaded-module list or build action receipt.

## Code-review findings and fixes in this QA branch

1. **P1-F1 (medium, incorrect static counts):** the original
   `classify_routed_const` matches `gate_proj`/`up_proj`/`down_proj`
   as arbitrary substrings in scale/zp names. A false name such as
   `fake_down_proj/scale` could contribute to `blocks_with_all_nine`.
   Fix: anchored projection-segment regex and adversarial regression fixtures.
2. **P1-F2 (high, output clobber):** `--markdown` lacked an extension
   restriction and could write into an unrelated `.bin` file outside the
   source XML directory, since the containment guard only protects the
   source tree. Fix: require `.md`, prevalidate both output paths before
   writing either, retain source-directory protection.
3. **P1-F3 (low, metadata exposure):** CLI Markdown used the absolute
   operator-local source XML path. Fix: use only the source basename in
   newly generated Markdown. Historical source receipts are not rewritten
   or silently redacted.
4. **P1-F4 (evidence limitation, not a scanner defect):** reports contain
   no exact XML SHA-256 or compiled-layer/weights-path proof. Future host
   P1 capture should bind XML SHA, export/checkpoint/quant keys, layer IDs,
   compiled expert kind, nine native slices and usable weights path to
   a verified source/build/module tuple. Keep this OUT of the static-only
   acceptance claim.

## Independent regression coverage

Added five tests in `tests/cib2/test_static_nine_slice.py` to the
worker's five existing synthetic tests: false-positive projection names,
falsely complete blocks, attempted foreign BIN overwrite, validation
before partial JSON write, and source-path sanitization.

**Code authored and reviewed in cloud; full host/Windows suite NOT_RUN in this
session.** Run the focused ten tests and full `tests/cib2` in the local
operator worktree, record exact counts, then independently compare a refreshed
read-only XML scan against these historical JSON records.

## Next gates

1. Integrate this branch only after focused and full host regression PASS,
   without resetting the original worker's branch. Keep a separate audit PR.
2. CIB2-P0: source-build identity and loaded module paths/hashes from the
   exact isolated 2026.4 RC1 process; six file hashes alone are insufficient.
3. CIB2-P1: compiled `MOECompressed` kind / `GEMM3_SWIGLU` gate,
   effective `weights_path`, offload ratio and exact native nine-slice
   `PackLayerSpec`. The observed XML names are hypotheses, not a substitute.
4. Only then permit native lease RED, safe Pack V1 and Path A GPU parity;
   leave Path B OFF.
