# PackV2 fast seal / verify operator manual

Status: **EXPERIMENTAL; offline-only; runtime_acceptance=NO; no production promotion**. Source TZ: `docs/cib2/TZ-SEAL-FAST-20261024.md` at commit `50bd3849c`.

## Drop-in commands

```powershell
python scripts/cib2/packv2_pipeline.py seal --plans-dir .\plans --native-packs .\pack-build --output-root .\generations
python scripts/cib2/packv2_pipeline.py verify --generation-dir .\generations\generation-<SHA>
python scripts/cib2/packv2_pipeline.py plans --bundle .\profile-bundle.json --output-dir .\plans --strategy frequency
```

`seal` defaults to `--post-seal-verify=fast`, `--materialize=copy`, `--fsync=dir`, `--workers=min(8,cpu_count)`, `--progress=auto`. An explicit `verify` defaults to `--mode=full` and must be used as the **release gate**. `--post-seal-verify=none` is strictly development-only.

Existing `generation-<digest>/manifest.v2.json`, `active.v2.json`, `OTDPACK1` and `cib2.pack_generation.v2` keys remain byte-compatible. No Resident Pack blobs are introduced into the native generation inventory.

## Flags

| Command | Flag | Default | Meaning |
|---|---|---|---|
| seal | `--post-seal-verify fast\|full\|none` | fast | Check after materialization; fast is structural only |
| seal | `--materialize copy\|hardlink` | copy | Copy & hash in one full-file pass, or zero-copy hardlink & hash |
| seal | `--hardlink-policy require-readonly\|chmod-readonly\|allow-shared` | require-readonly | Require immutable-looking source, change source permissions, or explicitly accept shared-writable inode |
| seal | `--fsync dir\|each\|none` | dir | Directory metadata sync (POSIX), per-file sync, or no explicit sync |
| both | `--workers N` | min(8,cpu_count) | 1=serial, at most 64 threads; reduce if SSD/antivirus saturates |
| both | `--progress auto\|tty\|jsonl\|off` | auto | TTY progress or stderr JSONL on CI; stdout remains one JSON object |
| both | `--log-file PATH` | disabled | Append UTF-8 JSONL events |
| both | `--metrics-file PATH` | `receipts/<op>-<run-id>.json` | Final OK/REJECTED metrics, located outside generation directory |
| verify | `--mode full\|fast` | full | Full SHA256 + each expert record FNV, versus header/geometry/placement only |

Example for agents:

```powershell
python scripts/cib2/packv2_pipeline.py seal --plans-dir .\plans --native-packs .\pack-build --output-root .\generations `
  --workers 4 --progress jsonl --log-file .\logs\seal.jsonl --metrics-file .\logs\seal-metrics.json
python scripts/cib2/packv2_pipeline.py verify --generation-dir .\generations\generation-<SHA> --mode full `
  --workers 4 --progress jsonl --log-file .\logs\verify.jsonl
```

## Critical integrity limitation

`fast` validates header checksum, canonical sizes, native layout, exact placement, checksums table presence, file size, generation manifest digest and strict file inventory. Copy mode computes SHA256 of **source bytes during materialization**. `fast` DOES NOT verify the per-expert FNV payload checksums or rehash the output payload. It cannot reject an arbitrary pre-existing payload corruption that leaves metadata unchanged. This is a consequence of the TZ fast target and not an acceptable release integrity check. A `full` verification always reads the records and checks their per-record FNV plus manifest SHA256, in one sequential file pass (at potentially high Python FNV cost).

Do not treat `VERIFIED_OFFLINE` from `fast` as full payload attestation: read additive `verification_mode` and `payload_integrity_checked`, and require `true` for release. Neither verification mode authorizes `runtime_acceptance=YES` or promotion.

For idempotent re-seal, an existing generation undergoes **full verification**, even if `--post-seal-verify=fast`; existing artifacts are never blindly trusted. This intentionally makes the second seal slower than a new copy. When source digest receipts from the native C++ packer become available, this decision can be reconsidered with a proven trusted producer contract.

## Hardlink safety

Hardlinks share data/inode. `require-readonly` checks the source file write bits before creating the link; it does **not** create cryptographic immutability. Administrators or ACLs can still modify a read-only file. `chmod-readonly` changes the source's mode *permanently* before publishing. `allow-shared` is an explicitly risky opt-in; events report a warning if source is writable. `copy` is the safe default. Same-volume requirement applies. Python `os.link()` is supported on Windows, `os.chmod()` there only controls the read-only flag. See Python 3.12 OS documentation.

`--fsync=dir` follows the TZ defaults; Windows has no portable directory fsync so it relies on flushed and closed file handles plus atomic rename. For stronger crash-durability use `--fsync=each`; none of these options replace payload verification.

## Machine receipts, timing and progress

`stdout`: one final JSON result with legacy `status`, `generation`, `pack_count`, `runtime_acceptance` and new verification attributes. `stderr`: JSONL in non-interactive mode, TTY bar in console, or silent on `--progress=off`. Metrics JSON includes run UUID, pack count, workers, bytes processed, per-phase times, speed, status, and mode. `bytes_read` counts logical Python stream consumption, not physical NVMe reads (Windows cache may satisfy reads). For `fast` verification, progress shows inspected *files* by their declared byte sizes, not claimed bytes physically read.

No progress/metrics/log file should ever be written **inside** `generation-*`, as strict inventory forbids extra files. Receipts live alongside generations under `output-root/receipts/`.

## Relationship with Resident Pack

Existing OTDPACK1 native reader, `--moe_experts_pack_dir`, `.residency` priorities and `active.v2.json` remain authoritative. Static by-design resident constants are managed by OpenVINO compiled model/IR separately from routed expert LRU. Draft PR #32 adds only an offline Resident Pack prototype; **its runtime reader has not been integrated**. Do not insert `resident.pack` into `generation-*`, change native decoder ABI, or make this fast-seal branch a prerequisite for the model to load. Future dual-generation publication requires an explicitly versioned manifest and an independently accepted Resident Pack reader.

## Offline chain

`family_map.py` → trace/profile (`trace_profile.py`) → layout (`pack_layout.py`) → plans (`packv2_pipeline.py plans` or identity plan smoke) → native GPU `--build_moe_experts_pack` → native pack verifier → fast `seal` → explicit full `verify` → attributed OVMS serve. Identity smoke plans do not prove live profile acceptance.

## Acceptance gates

1. Existing `tests/cib2/test_packv2_pipeline.py` plus new `test_packv2_fast.py` pass under Python 3.12 on Windows.
2. Same bytes + manifest digest on 1 vs 4 or 8 workers, exact `OTDPACK1` hashes; full-verify corruption and placement-negative cases reject; no stray temp directory or active-pointer update.
3. r20 reader full GPU acceptance remains separate. `runtime_acceptance=NO` until model gates, N2/UMA and 30-minute soak.
4. Real Arc 140V NVMe full 15.6 GiB/40 benchmark for `copy` target <= 8 min and hardlink <= 30s; **not measured in this implementation session**.
5. No merged production changes to PR #10, #29 or C6.
