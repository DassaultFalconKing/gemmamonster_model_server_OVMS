# CIB2 PGP-05: offline benchmark evidence screen (2026-10-24)

**Status:** standalone source and synthetic tests. **Runtime/pack/GPU acceptance: NO.**

This is an independent read-only reviewer for the four-arm experiment defined in the
current [PGP programme](PROFILE-GUIDED-EXPERT-PACKING-20261024.md).
It does not run benchmarks, load OpenVINO/OVMS, read models, access GPU/NVMe, or
authorize production mode promotion.

## Arms

| Arm | Layout | Resident | Variable compared with A0 |
| --- | --- | --- | --- |
| A0 | identity | usm_device | canonical control |
| A1 | optimized | usm_device | placement only |
| B0 | identity | usm_host | resident mode only |
| B1 | optimized | usm_host | both changes |

One input file describes one scenario: same exact source, model, quant,
OpenVINO GenAI, OVMS binary, Intel GPU plugin, tokenizer, driver, device, prompt
family, context length, cache state, phase, concurrency, and OTD ratio.
C1/C2/C4 and other contexts/cold-warm states need separate matching files.

## Usage

```powershell
py -3 -m unittest discover -s tests/cib2 -p test_benchmark_screen.py -v
py -3 scripts/cib2/benchmark_screen.py --input C:/gm/private/pgp05-benchmark-receipt.json
```

Exit 0 emits an offline review JSON to stdout; exit 2 emits a structured
`REJECTED` error on stderr. The tool never writes a file.
The input must be sanitized UTF-8 JSON of at most 4 MiB with exact
`schema = cib2.pgp05_screen.v1`. Duplicate keys, unknown fields,
nonfinite numbers, schema drift, incomplete cohorts and sample mismatches
fail closed.

## Input contract

Top-level keys exactly: `schema`, `synthetic` (boolean), `arms` (2-4 arm records).

Every arm has exactly `id`, `layout`, `resident_mode`,
`profile_sha`, `pack_manifest_sha`, `cohort`, `scenario`,
`gates`, `warmups`, `samples`.

- SHA256 cohort fields: `checkpoint_sha`, `export_sha`, `tokenizer_sha`,
  `quant_profile_sha`, `ovms_build_sha`, `genai_build_sha`,
  `gpu_plugin_sha` (64 lowercase hex). Plus `model_key`,
  `driver_version`, `sdk_version`, `device_key`.
- Scenario: `workload_key`, `context_tokens`, `slots`,
  `offload_ratio`, `phase`, `cache_state`, `prompt_family`.
  Phase is prefill/decode/draft/verify/mixed; cache is cold/warm.
- Gates are booleans `source_build_verified`, `compiled_eligible`,
  `native_pack_verified`, `gpu_logits_parity`, `agentic_parity`,
  `lease_integrity`, `no_gpu_reset`, `no_swap_storm`,
  `trace_complete`. An untrue gate blocks review; a claimed true gate
  does NOT establish independent provenance.
- At least one warmup and at least **three** measured samples per arm.
  Sample indices start at zero, are contiguous, and counts match across
  arms. Each sample has `index`, `accepted_target_tokens`,
  `wall_seconds`, `ttft_ms`, `tpot_p95_ms`, `tpot_p99_ms`,
  `startup_ms`, `unique_memory_bytes`, `physical_io`.
- `profile_sha` is null for identity arms and a 64-hex digest for
  optimized arms. A1 and B1 must use the same optimized profile digest.
- Same-layout arms must share `pack_manifest_sha` (A0≡B0 identity pack,
  A1≡B1 optimized pack) so resident-mode contrasts are not confounded.
- The pack manifest digest is a claim, **not** full Pack V1 verification;
  native payload parity and immutable generation checks are independent.

`physical_io` has two supported forms:

```json
{"status":"NOT_EXPOSED","reason":"counter_unavailable"}
```

```json
{"status":"EXPOSED","source":"device_counter","device_read_bytes":40960}
```

Only a device counter may claim physical bytes. The value may include
unrelated drive activity and is not proof of per-pack NVMe attribution.
Any unavailable counter makes the arm's aggregate physical
bytes/accepted-token **null**, never zero or guessed from logical
`read()` bytes.

## Output contract and non-claims

The output `cib2.pgp05_review.v1` contains source-file SHA256,
per-arm median accepted target tokens/wall-second, median TTFT,
median within-sample TPOT p95/p99, median startup, max unique resident
bytes, optional device bytes/accepted token, and A1/B0/B1 percentage
deltas vs A0.

**Do not mistake a median of reported within-run p95 values for pooled
p95 over all tokens.** Nor does device-counter read bandwidth constitute
exact physical bytes read from an individual Pack V1 file.

- `BLOCKED`: any false gate, synthetic fixture or incomplete four-arm matrix.
- `OFFLINE_REVIEW_ONLY`: full claimed evidence structurally comparable,
  but not authenticated and not approved.
- `runtime_acceptance` always `NO`.
- `promotion_authorized` always `false`.

No raw prompts, trace payloads, sensitive paths or serial numbers belong
in these JSON receipts.

## Integration gate

A future **operator-host runner** must produce real immutable receipts
from independently verified OpenVINO 2026.4 RC1 source/build/module
identity and actual A0/A1/B0/B1 model/kernel/agentic control tests.
That runner is not implemented here. Path A remains default and Path B OFF.
