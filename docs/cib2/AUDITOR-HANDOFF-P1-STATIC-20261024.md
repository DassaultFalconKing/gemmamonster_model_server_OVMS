# Auditor handoff: static P0 file identity and P1 name co-occurrence

Subject of this review is the tip of `feature/cib2-p1-static-eligibility-20261024`.
Parent is `279f4097f9340cd9044c92ee43e67b0b24ab54d2`.
This branch was not pushed onto the cloud research branches
`feature/cib2-offload-family-map-20261024`,
`feature/cib2-pgp00-20261024`, or
`feature/cib2-pgp02-20261024`.

Runtime acceptance: **NO**. Compiled expert kind: **UNKNOWN**.
Full tickets CIB2-P0 and CIB2-P1 stay open.

## What to read

| Item | Path |
| --- | --- |
| Checker | `scripts/cib2/static_nine_slice.py` |
| Synthetic tests | `tests/cib2/test_static_nine_slice.py` |
| Ornith report | `docs/cib2/P1-STATIC-ORNITH-20261024.md` and `.json` |
| Gemma26 worker report | `docs/cib2/evidence/20261024-p1-static/CIB2-P1-GEMMA-STATIC.md` |
| P0 file-identity receipt | `docs/cib2/evidence/20261024-p1-static/CIB2-P0-RECEIPT.md` |

The evidence files are copies of the local orchestration reports from 2026-10-24. They are not a build receipt and not a loaded-module list.

## Claims already checked by the coordinator

1. `python -m unittest tests.cib2.test_static_nine_slice` — 5 tests, PASS, before this commit. The tests are synthetic and do not open a weights BIN.
2. Ornith `openvino_language_model.xml`: 15765 layer elements, 120 matched routed Const slots, 40 blocks. Only `down/weight`, `down/scale`, and `down/zp` (40 each). `blocks_with_all_nine` is 0. Block 0 weight ordinal 379, layer id 344, offset 309329201, size 134217728. BIN was not opened.
3. Both Gemma26 language XMLs have 10687 layer elements and 4450 Const layers. The Ornith name rule `.mlp.experts.` matches 0 Consts, so the worker's protocol count is 0. An independent recount of `mlp.{gate,up,down}_proj` weight, scale, and zero-point found 30 of each slot and all nine together on blocks 0 through 29. `experts.down_proj` weight, scale, and zero-point are also 30. That recount is static naming, not eligibility.
4. Six binaries were rehashed independently and matched the receipt: `openvino.dll` `829c4642e287…`, `openvino_genai.dll` `5a2904f2564e…`, `openvino_intel_gpu_plugin.dll` `b90b57aecb9d…`, `openvino_tokenizers.dll` `e96e02744f4c…`, `ovms.exe` `f472d619097b…`, `ovms_test.exe` `3ac79a92468f…`. `stable-status.txt` was not found under `semantic-refit-2026.4-src`. `source_build_association` stays **UNVERIFIED**. `loaded_modules` stays **NOT_RUN**.

## Do not accept

- Do not mark either model `ELIGIBLE` or `GEMM3_SWIGLU` from these names.
- Do not treat the six hash matches as proof that the binaries were built from `eb76a74f7aa39573d452d95443e189b1f5f4d9e8`.
- Do not open a pack, start OVMS, or enable Path B from this branch.
- Gemma's `mlp.*_proj` names are a different static pattern from Ornith's `.mlp.experts.down_proj`. The checker does not currently count the Gemma pattern. That gap is intentional in this commit.

## Sessions

- P0 receipt: OpenCode `ses_e94a563f7ffeV5n0t1F2Z4lAl9`, exit 0.
- Gemma scan: OpenCode `ses_e94a55ef5ffedNzm9RD4lo4Qcu`, exit 0.
- Ornith checker: coordinator, no provider session.
