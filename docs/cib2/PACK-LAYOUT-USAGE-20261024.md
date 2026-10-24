# CIB2 PGP-02: offline Pack V1 layout optimizer — input contract and handoff

Coordinator review hardening: numeric JSON integer costs/weights are checked against bounds *before* conversion to float; enormous integer inputs fail closed as `REJECTED`/exit 2 rather than throwing `OverflowError` or rounding into range. Regression: `tests/cib2/test_pack_layout_numeric_review.py`.

Coordinator review hardening: output files must end in `.json` and cannot replace the source profile. The layout validator checks offline-only acceptance/policy invariants and complete scoped identity fields as well as permutation/inverse correctness. This is structural validation, not authentication of caller-supplied provenance or proof of a captured runtime trace. Consumers still need an independently pinned source profile and exact native PackLayerSpec.

**Date:** 2026-10-24. **Status:** OFFLINE FOUNDATION IMPLEMENTED; NOT RUNTIME/PROFILE/PACK ACCEPTED.

**Scope:** `scripts/cib2/pack_layout.py`, focused tests and synthetic fixtures only. This
is PGP-02 dry-run scaffolding from
[PROFILE-GUIDED-EXPERT-PACKING-20261024.md](PROFILE-GUIDED-EXPERT-PACKING-20261024.md)
§4.2 and §8, compatible with the native Pack V1 placement API described in
[LAYER-EXPERT-PACK-IMPLEMENTATION-20261024.md](LAYER-EXPERT-PACK-IMPLEMENTATION-20261024.md)
P3/P5. It does not implement P3/P5 and does not read a pack file.

## 1. Decision and non-claims

The tool consumes one **derived, sanitized offline profile** and emits one complete
`placement[logical_expert_id] = physical_position` permutation for **one scoped compiled
layer**. That table is the only handoff:

```text
PackLayout::set_placement(placement)
build_pack(..., placement)        # native P3, not called here
```

It is deliberately **not** any of the following:

- an implementation, parser, or producer of `cib2.expert_trace.v2`;
- evidence that real traces, hotness, or routing data exist;
- a pack reader, pack writer, pack-file validator, or Pack V2 design;
- a payload/tensor transformer; all payload bytes and tensors remain unchanged;
- a resident-mode, prefetch, pinning, or router top-k change;
- a throughput or physical-I/O benefit claim;
- runtime, profile, or pack acceptance. Every output says `NO`.

Native full-payload byte parity and independent verification remain **NOT_RUN** until
native Pack V1 P3/P5 acceptance. Synthetic fixtures are labelled synthetic and can never
promote a profile, pack, or runtime.

## 2. Input: `cib2.pack_layout_profile.v1`

The file is bounded UTF-8 JSON (≤ 32 MiB, duplicate JSON keys rejected). All fields below
are required at their level; unknown fields are rejected, including payload, tensor,
weight, pack-byte, and resident-mode fields. The profile is a *derived small contract*,
not a raw trace.

```json
{
  "schema": "cib2.pack_layout_profile.v1",
  "kind": "cib2_pack_layout_profile",
  "complete": true,
  "synthetic": true,
  "provenance": {
    "checkpoint_sha": "64 lowercase hex",
    "export_sha": "64 lowercase hex",
    "compiled_layer_key": "sanitized identifier, 1..256 chars [A-Za-z0-9._:-]",
    "quant_profile_sha": "64 lowercase hex",
    "profile_key": "sanitized identifier, 1..128 chars [A-Za-z0-9._-]",
    "source": "synthetic | offline_trace_derived",
    "sanitized": true
  },
  "scope": {
    "model_key": "sanitized identifier, 1..128 chars [A-Za-z0-9._-]",
    "logical_layer_id": 0
  },
  "expert_count": 8,
  "experts": [
    {"logical_expert_id": 0, "miss_count": 10, "read_cost_us": 1.5}
  ],
  "coaccess": [
    {"expert_a": 0, "expert_b": 2, "weight": 10.0}
  ]
}
```

### 2.1 Strict validation

| Rule | Rejection |
| --- | --- |
| Exact schema and kind | Wrong or missing version fails closed |
| `complete` is exactly `true` | `false`, missing, or non-boolean fails closed |
| `synthetic` boolean matches `provenance.source` | Any mismatch is a provenance error |
| `sanitized` is exactly `true` | Unsanitized/private input fails closed |
| SHA fields are 64 lowercase hex | Placeholder, uppercase, short, or empty digest fails |
| `expert_count` is 1..16384 | Zero, negative, or over-bound fails |
| Expert IDs are integers in `0..expert_count-1` | Out-of-range or non-integer fails |
| Expert IDs are unique | Duplicate entry fails |
| `miss_count` is an integer in `0..2^53-1` | Negative, boolean, or non-integer fails |
| `read_cost_us` is finite and in `0..1e12` | Negative, `NaN`, or infinity fails |
| Coaccess endpoints are in range and differ | Self-pair or out-of-range fails |
| Pair weight is finite and in `0..1e18` | Negative or non-finite fails |
| Unordered coaccess pairs are unique | `(a,b)` twice, including reversed, fails |
| Unknown fields | Any level fails closed |

There is no lenient mode. A supplied malformed, incomplete, duplicate, out-of-range,
non-finite, unsanitized, or provenance-mismatched profile **never** silently becomes
identity: the CLI reports `REJECTED` and exits 2.

### 2.2 Sparse and unseen experts

`experts` may be a subset of `expert_count`. Missing IDs are **unseen** and have no
observed evidence. Present entries with `miss_count * read_cost_us == 0` have no usable
cost evidence. Neither group receives invented hotness; they sort after positively
evidenced experts by ascending logical ID.

### 2.3 Key isolation

The five provenance keys remain separate and are copied verbatim into output `scope`:
`checkpoint_sha`, `export_sha`, `compiled_layer_key`, `quant_profile_sha`, `profile_key`.
No key is concatenated with, derived from, or substituted for another. Source-profile
identity is the SHA-256 of the **exact supplied profile bytes**, not a filename and not a
claim about the model checkpoint.

## 3. Strategies

### 3.1 `identity`

`placement = [0, 1, ..., expert_count-1]`. Profile evidence is not applied. This is the
baseline candidate and the fallback destination.

### 3.2 `frequency`

Observed score:

```text
score(e) = miss_count(e) * read_cost_us(e)
```

Order is descending score, then ascending `logical_expert_id` (deterministic ties). The
seed is recorded but is not used by frequency ordering. Positive-score experts come
first; zero-cost and unseen experts follow by ascending ID. If no expert has a positive
score, the result is explicit identity fallback with reason
`no_observed_frequency_evidence`.

This uses only observed miss/read-cost evidence. It does not infer hotness from a model
name, static XML, router architecture, or an assumed “20% hot” set.

### 3.3 `coaccess`

Input is the bounded set of supplied positive-weight pairs. The deterministic greedy
order:

1. choose the remaining expert with the highest total incident pair weight as cluster
   anchor; ties use `SHA256(seed:logical_expert_id)` then logical ID;
2. repeatedly append the unplaced expert with the highest connection weight to the placed
   set, with the same seeded tie-break;
3. after all edge-bearing clusters are consumed, append isolated experts by the seeded
   tie-break;
4. for small profiles only (≤ 256 experts, ≤ 5000 pairs, ≤ 4 passes), run deterministic
   adjacent-swap local refinement;
5. compare the resulting offline objective with identity:

```text
objective(order) = Σ weight(a,b) * |position(a) - position(b)|
```

If the candidate is not strictly better than identity, identity is retained with reason
`coaccess_no_offline_improvement`. This is an offline candidate-layout objective only;
it is not a read, cache, or decode-benefit result. The pair set and weights are bounded
(≤ 200,000 pairs).

If there are no positive-weight pairs, the result is explicit identity fallback with
reason `no_coaccess_evidence`.

## 4. Fallback versus fail-closed

| Situation | Behavior |
| --- | --- |
| No `--profile`, explicit `--expert-count N` | Identity placement; `fallback.reason = no_profile_supplied` |
| No `--profile`, no expert count | Exit 2; a full permutation cannot be fabricated |
| Profiles disagree with `--expert-count` | Exit 2 |
| Valid frequency profile, no positive evidence | Identity; `no_observed_frequency_evidence` |
| Valid coaccess profile, no positive pairs | Identity; `no_coaccess_evidence` |
| Coaccess candidate not better than identity | Identity; `coaccess_no_offline_improvement` |
| Supplied profile malformed/incomplete/unsafe | Exit 2, `REJECTED`; **no output file** |
| Missing/unreadable profile path | Exit 2 |
| Profile path ends in `.bin` | Exit 2 before reading; BIN inputs are refused |

## 5. Output: `cib2.pack_layout.v1`

```json
{
  "schema": "cib2.pack_layout.v1",
  "kind": "cib2_pack_layout",
  "status": "OK",
  "offline_only": true,
  "runtime_acceptance": "NO",
  "profile_acceptance": "NO",
  "pack_acceptance": "NO",
  "strategy_requested": "coaccess",
  "strategy_effective": "coaccess",
  "seed": 0,
  "seed_used_for": "coaccess tie-break only",
  "expert_count": 8,
  "scope": {
    "model_key": "…",
    "logical_layer_id": 0,
    "checkpoint_sha": "…",
    "export_sha": "…",
    "compiled_layer_key": "…",
    "quant_profile_sha": "…",
    "profile_key": "…"
  },
  "source_profile": {
    "supplied": true,
    "schema": "cib2.pack_layout_profile.v1",
    "sha256": "…",
    "synthetic": true,
    "complete": true,
    "provenance_source": "synthetic",
    "expert_evidence_entries": 8,
    "coaccess_pairs": 3
  },
  "fallback": {"used": false, "reason": null, "identity_used": false},
  "placement": [1, 2, 0, 3, 4],
  "order": [2, 0, 1, 3, 4],
  "placement_contract": "placement[logical_expert_id] = physical_position; order[physical_position] = logical_expert_id; both are full permutations",
  "validation": {
    "permutation": true,
    "logical_ids_preserved": true,
    "inverse_consistent": true,
    "physical_positions_complete": true
  },
  "objective": {},
  "policy": {
    "pack_format": "V1_PLACEMENT_TABLE_ONLY",
    "payload_bytes": "UNCHANGED",
    "tensors": "UNTOUCHED",
    "pack_v2": false,
    "resident_mode": "UNCHANGED",
    "prefetch": "OFF",
    "pinning": "OFF",
    "router_top_k": "UNCHANGED"
  },
  "handoff": {
    "api": "PackLayout::set_placement",
    "build_api": "build_pack(..., placement)",
    "native_full_payload_parity": "NOT_RUN"
  },
  "non_claims": ["…"],
  "warnings": ["…"]
}
```

`placement[logical] = physical` and `order[physical] = logical` must both be complete
permutations and exact inverses. They are not always equal arrays — only `placement` is
the handoff vector for `PackLayout::set_placement`. The tool re-validates inverse
parity before writing. Output is written atomically (temporary file plus replace); on
rejection no output is produced.
Source paths are not echoed into output; only the source profile SHA and sanitized keys
are reported.

## 6. CLI

```powershell
python scripts/cib2/pack_layout.py `
  --profile tests/cib2/fixtures/pack_layout/coaccess_cluster.json `
  --output layout.json `
  --strategy coaccess `
  --seed 0
```

```text
--profile JSON     cib2.pack_layout_profile.v1 (optional only for explicit identity)
--output JSON      required; written only on success
--strategy         identity | frequency | coaccess
--seed N           optional nonnegative coaccess tie-break seed, default 0
--expert-count N   only without --profile; required for a full identity fallback
```

Exit codes: `0` success (pending coordinator review), `2` rejected input/argument/output
error. Errors are JSON on stderr with `status: REJECTED`, `offline_only: true`, and
`runtime_acceptance: NO`.

## 7. Tests and fixtures

`tests/cib2/test_pack_layout.py` covers deterministic frequency ties, seeded coaccess
determinism, inverse/permutation exactness, tamper rejection, key isolation, sparse and
unseen experts, malformed/incomplete/duplicate/range/non-finite/provenance rejection,
synthetic coaccess versus identity objective, identity fallback, CLI success/failure, and
BIN refusal.

Fixtures in `tests/cib2/fixtures/pack_layout/` are small synthetic JSON profiles:

| Fixture | Purpose |
| --- | --- |
| `identity_empty.json` | Valid complete profile with no evidence |
| `frequency_ties.json` | Deterministic score ties and zero-cost experts |
| `coaccess_cluster.json` | Synthetic coaccess clusters; offline objective improvement |
| `sparse_unseen.json` | Sparse entries with unseen experts |
| `incomplete_marker.json` | Rejected incomplete profile |
| `provenance_mismatch.json` | Rejected synthetic/source mismatch |
| `nonfinite_cost.json` | Rejected non-finite read cost |

All valid fixtures declare `synthetic: true`, and outputs carry the synthetic warning.

## 8. Remaining gates (explicitly NOT_RUN)

- Native Pack V1 P3 build/read/checksum parity with a nonidentity placement.
- Native Pack V1 P5 independent full-pack verifier and bitflip/truncation cases.
- Actual complete provenance-pinned trace capture; no real trace exists here.
- Full-payload byte parity for every expert after native repacking.
- Identity/frequency/coaccess A/B on the exact same model/quant/kernel/hardware.
- Any physical-I/O, latency, throughput, memory, or accepted-token claim.
- Runtime/profile/pack acceptance.

Until those gates pass, this tool only produces a deterministic offline candidate table
for `PackLayout::set_placement`.
