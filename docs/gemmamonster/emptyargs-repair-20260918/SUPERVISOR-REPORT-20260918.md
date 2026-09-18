# Supervisor report — GEMMAMONSTER track to PR (2026-09-18)

## Where we stand

Live question that started the track is ANSWERED: bounded-whitespace repair alone
fixes the Sept-16 streaming degeneration (C2: 3/3 `tool_calls`, zero whitespace-only
chunks, same 5232-token fixture that used to degenerate). Parser hardening was not
required for that symptom. Proven on C2, repeated identically on C3/C4/C5.

The empty-args follow-up (`calculator{}`) is ATTRIBUTED, not fixed at runtime yet:
grammar forbids it (proven), parser passes it through (proven), schema ingestion is
verbatim (proven) — the `{}` escapes through the guided-enforcement path (GenAI mask
activation/application). F1→F5 repair program is mid-flight to close exactly that.

## Commit ledger (all pushed, local == remote verified at each step)

Main track `fix/gemma4-upstream-evidence-triage-20260917` (HEAD `41ac41f09`):
- C1 parser line: `d7e26e7d` test-helper lexemes, `2dc4e54c` escaped strings prod,
  `dd3845f` legacy reconciliation, `d554273a5` HTTP INVALID_ARGUMENT,
  `2ec9530df` post-call STOP-flush reconciliation. Audit pair `2489e342/b9f65b96`
  deliberately EXCLUDED from C3+ (revert net-zero, kept out of reviewer series).
- Matrix + strategy docs: `27cc20eea` (Build Reuse), `3b9e9f082` (C6 refresh rule),
  `9b429adf` (maintainer report), `ff5804b8a` (C6 preflight plan).
- Handoffs: C1 (`d10dc0e89`), C2 (`7562d4d70`), C3 (`1112ee2b9`), C4 (`5a20b9e96`),
  C5 (`71b769765`), F-repair (`41ac41f09`).

Candidate branches (all pushed): C2 `eebda599f`, C3 `526099c57`, C4 `29f5562fb`,
C5 `a671ddf9f`, coverage `71566af5`, GenAI `c4 881684e7` / `c5 15e8f897` /
`integration 045f4456`, F1 `06ca3508`, F5 `abe90176`, F3 `91a92a29`.

## Gate table (honest)

| Gate | Result | Note |
|---|---|---|
| C1 G3/G4 | 228/229 + 64/64 | 1 environmental (`opt-125m` absent on host) |
| C2/C3/C4/C5 live G5/G6 | 4× GREEN, identical | same 5232-token fixture |
| C3/C4 live-like | 5/6 + fail-closed | empty-noop pre-existing (C2 control identical) |
| GenAI 4/4 | PASS on G1, G2, X2, integration | |
| F1/F2/F5 C++ | 2/2, 6/6, 8/8 | +visitor arm + TokenIds qualify (test-only) |
| Python bindings | 4/4 model-free | stubs hand-updated (stubgen offline) |
| JS/TS | types added, 0 NEW tsc errors | 36 pre-existing env errors; no JS runtime test on host |
| F3 A/B 20 runs | 0/1/19 vs control 1/3/0 | dispatch-missing verdict, evidence-only |
| G2-strict dogfood | NOT_RUN | archived requests/expected are different fixture generations |
| C6 | NOT_STARTED | preflight planned, merge check CLEAN |

## Decisions already locked (challenge any)

1. One cold build per program (C2 GenAI, C6 final); everything else incremental.
2. Immutable runtime slots (`G2-X1`, `G2-X2`, `TOKEN-REPAIR-ACTIVE`); no shared-tree mutation.
3. C6: deps to fresh HEADs, server rebases ONLY on clean merge (check says clean: 4 CI commits, 1 disjoint file).
4. XGrammar path: X1 → `f6043f4` (C5) → HEAD `1de42473` (integration, done, 10/10).
5. Parser untouched for `{}` (valid JSON; enforcement layer owns it).

## Open questions for you

1. **F3 dispatch-missing**: my read is missing TokenizerInfo/plumbing at OVMS→GenAI boundary
   (F4 scope). If you see another candidate cause in `f3-ab-result.txt`, redirect before F4.
2. **G2-strict**: fixtures unrecoverable as strict pairs — accept spot-check GREEN as final,
   or fund a canonical dogfood-pack rebuild?
3. **opencode config**: I flagged `limit.context 262144` as OOM-risk (proven only to ~32K);
   not changed without your call. Same for thinking budget (512 burns on thought alone).
4. **Upstream PR shape**: atomic map drafted in matrix §19; F-repair adds F1/F2/F5 + whitespace.
   Confirm split before C6 rewrites history into reviewer series.
5. **JS runtime**: types only, never executed here. Accept as-is for PR, or require node harness?

Artifacts: `C:\git\artifacts\gemma4-frankenstein-20260917\{C1..C5}\` (identity.txt + raw logs/SSE).
Next physical step (no approval needed unless you redirect): F4 control-token protocol.
