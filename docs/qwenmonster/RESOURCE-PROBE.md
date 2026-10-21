# OVMS resource observation

Status: implemented; 10/10 focused offline tests and 3 passive idle samples PASS.
Combined runner/resource regression: 28/28 PASS. ACCEPTED:NO.

1. Cause: existing-server probes observed available RAM falling below 1 GiB,
   while RSS and private bytes moved differently. This does not establish a leak.
2. Files: scripts/qwenmonster/resource_probe.py and
   scripts/qwenmonster/tests/test_resource_probe.py; compact evidence/status docs.
3. Implementation: bounded passive JSONL sampling for one explicit PID and
   expected process creation time. Check identity before/after each sample;
   collect system total/available, process RSS and Windows private bytes. Missing
   private bytes remain unknown. Exclusive output creation, flushed rows and a
   final summary/error prevent stale-output success. No HTTP, model requests,
   process termination, environment dump or process discovery.
4. Expected effect: reproducible idle/before/after evidence and an optional
   stop-on-low-headroom result, without attributing system pressure to OVMS.
5. Test: offline identity-reuse/mid-sample change, error persistence, unknown
   metric, existing output protection, invalid bounds and low-resource stopping;
   then a short passive sample of the existing verified process. Idle evidence
   cannot close load/soak/concurrency or leak acceptance.
6. Provenance: actual external-gates-20261021 memory receipts and the resource
   characterization step of NEXT-STEPS-20261021.md. Independent implementation.

## Use

The CLI uses psutil from the selected interpreter; offline tests use injected
readers. Choose a new private output file outside the repository:

```powershell
rtk proxy python scripts/qwenmonster/resource_probe.py --pid <pid> --expected-created '<exact-created-unix>' --output <new-private-jsonl> --samples 6 --interval 10 --phase idle
```

Keep the creation timestamp quoted in PowerShell: unquoted numeric arguments
can be rounded before Python receives them. The first local CLI attempt rejected
that mismatch without recording process metrics; the corrected quoted invocation
passed. The exact identity check was retained.

Samples are limited to 1000 and scheduled waits to 300 seconds. An optional
`--stop-below-mib` ends the observer with RESOURCE_LIMIT/exit 2; it does not stop
OVMS or authorize other work. Missing/error/incomplete observations are not
COMPLETE. Existing output files are never overwritten.

## Measured scope

Three idle samples of the same running OVMS process completed. Available memory
was about 4154-4163MiB, RSS 714.59MiB and private bytes 16436.7MiB. RSS/private deltas
were 0 over this short interval. This establishes working observation, not leak,
load, soak or concurrency acceptance. No model request, restart, process kill or
compiler was executed. Raw JSONL remains private; compact hashes/outcomes are in
`evidence/resource-probe-20261021/RESULTS.json`.
