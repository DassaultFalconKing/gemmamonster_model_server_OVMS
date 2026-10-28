# STATE — Qwen3.8 MTP Arc 140V experiment

## Native versus OVMS status (2026-10-28 follow-up)

- **Native GenAI**: load/generation PASS; bounded NAT timing sweep completed (30 measured rows). Original u4/DQ128 greedy equivalence FAIL. See `NATIVE-FOLLOWUP.md`.
- **Native RCA P0–P6 + P6b**: complete; see `RCA-MATRIX.md`. u4 fails with either DQ; default u8/f16 pairs pass on the short prompt. u4/BY_TOKEN unsupported; u8/BY_TOKEN fails later. Isolated source-matched trace reproduces P0 and proves a raw target-logit argmax flip before sampling, with identical internal input IDs. KV/GDN/kernel-level cause remains unresolved.
- **OVMS HTTP stages 3–4** below: NOT_RUN; VLM draft gate still blocks deployment. Native results do not change these statuses.
- **Production MTP**: HOLD. No OVMS source patch until the divergence mechanism is established.

## Stage 0 identity (2026-10-28)

| Item | Value |
|------|-------|
| User worktree (untouched) | `C:\git\gemmamonster-lfm-2026.4` @ `review/lfm25-design-c-semantic-refit-20261027` `1b87c2b64` |
| origin/main (Stage 0) | `f5970325764c7bc839d66f92e486941416737caa` |
| Tag `gemmamonster-2026.4-rc4` (peeled) | `362b1d293b0461fa6b8772f1cf34d075c7ee23e4` |
| Experiment worktree | `C:\git\gemmamonster-qwen38-mtp-20261028` |
| Experiment branch | `experiment/qwen38-mtp-arc140v-20261028` @ RC4 (docs untracked until commit) |
| Experiment port | `18138` |
| GPU servers | **all stopped** at handoff |

## Progress

- [x] Stage 0 worktree
- [x] Stage 1 official model + MTP files + SHA locks
- [x] Stage 2 capability probes → **BLOCKED_CAPABILITY** (see `HANDOFF.md` / `failures.md`)
- [ ] Stage 3 benchmarks — NOT_RUN
- [ ] Stage 4 correctness — NOT_RUN
- [ ] Stage 5-6 report + experimental push — handoff doc ready; no push yet

## Blocker

RC4 `VLM_CB` + `draft_models_path` (MTP via `.`) rejected as Fast Draft. Full package cannot use `LM_CB`. LM-only staging still pulls vision IR from GenAI.

**Handoff:** `docs/experiments/qwen38-mtp-20261028/HANDOFF.md`
