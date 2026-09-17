# C6 SUPER-UPSTREAM — preflight plan (docs only, 2026-09-18)

candidate_id: C6-super-upstream
status: PREFLIGHT-PLANNED (no builds yet; C5 server left running per instruction)

## Re-resolve results (2026-09-18)

- GenAI upstream master: `3abf349be` — NO movement since C4. G2 base is current.
- XGrammar HEAD: `1de42473` (test-only #847 on top of `38b97c0`).
  C5 pin `f6043f4` -> HEAD delta: `e571161` (build), `38b97c0` (perf #900 with
  INTENTIONAL converter behavior changes), `1de42473` (tests only).
- OVMS upstream master: `16ca1ac6` (only 4 commits past our merge-base `204d3bf3`:
  all CI/infra — connectivity, libsonic removal, MP checks reorder, archive change).
  Merge check `merge-tree(base, C5-OVMS a671ddf9, upstream/main)`:
  ONE overlapping file (WORKSPACE: upstream absl git->http_archive vs our slot paths),
  disjoint hunks, zero conflict markers -> CLEAN per C6 refresh rule.
  Evidence: artifacts/gemma4-frankenstein-20260917/c6-mergecheck.txt

## Preflight construction plan (when ordered)

1. GenAI: `c5` branch + XGrammar pin `f6043f4` -> `1de42473`, targeted _deps
   invalidation, incremental rebuild, 4/4, new slot G2-X3. RED here = XGrammar HEAD.
2. OVMS server: rebase C5 source onto `upstream/main 16ca1ac6` (clean per check above).
   If rebase turns dirty in practice: STOP, record blocker, server stays per refresh rule.
3. OVMS increment against G2-X3, full gates (compile, 4/4 GenAI, focused 229, 64,
   long unary, long stream 3/3, dogfood spot, audits).
4. Only when preflight GREEN: C6-FINAL (empty roots, no disk cache, reboot, clean caches).

## RETAIN/ADAPT/DROP ledger (preliminary; finalized at construction)

- O1 parser repairs (2dc4e54c, d7e26e7d): RETAIN (upstream untouched this area).
- Whitespace call-site (a3a7004bd): RETAIN (upstream untouched).
- GenAI whitespace commits: RETAIN on fresh base (re-verify 4/4).
- XGrammar 9aa840b6->1de42473: ADAPT (pin move; upstream #900 behavior changes get gates).
- Nothing qualifies for DROP_UPSTREAMED yet (no upstream equivalent of max_whitespace_cnt found).
