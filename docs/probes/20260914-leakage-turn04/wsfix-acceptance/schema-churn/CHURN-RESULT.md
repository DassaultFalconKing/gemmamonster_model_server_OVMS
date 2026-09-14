# Schema-churn result (pre-reboot, candidate AF921BB2, PID 16656, no restart)

## Summary (§7)

```
TOTAL_REQUESTS=100 attempted (31 served HTTP200, 1 in-flight death, 68 refused)
UNIQUE_SCHEMAS=100 attempted fingerprints / 31 served distinct
HARD_FAIL_AT=032 (mid-tool_032, required, t=0, 4-8-prop schema, hung 22562ms)
CL_OUT_OF_RESOURCES=YES (llm_executor error, then process death, no recovery)

RSS_START=245MB (WS, mostly-paged, weak signal)
RSS_PEAK=587MB
PRIVATE_START=16776MB / PEAK=16256MB / END=n/a (dead)
FREE_RAM_START=6270548KB / LOWEST=5567240KB / END=26019364KB (post-death)

GPU_SHARED_START=16460.7MB / PEAK=16559MB (+~100MB drift over 30 served) / END=1382MB (dead)
GPU_SHARED explains the kill zone: model holds ~15.3GB of a ~17.5GB committed pool.

POST_CHURN_SIMPLE_GRAMMAR=NOT_RUN (process dead; relaunch forbidden pre-reboot)
PLAIN_NO_TOOLS_AFTER_FAILURE=NOT_RUN (same reason)
TOOLS_NONE_AFTER_FAILURE=NOT_RUN
GRAMMAR_AFTER_FAILURE=NOT_RUN
```

Driver defects on record: `Send-MixedAlias` undefined at call time → requests
101-120 (mix/named block) NEVER SENT. Run delivered 100 attempts (001-100):
31 served, all canonical tool_calls, 0 soft anomalies. Named-choice defect from
the old driver did NOT occur here (all named choices used present tools).

## What happened

- Reqs 001-031: HTTP200, canonical tool_calls, flat latency 1.3-2.1s, no growth.
- Req 032: hung 22.5s, transport failure mid-inference; executor threw
  CL_OUT_OF_RESOURCES at 20:44:30; process never served again.
- Reqs 033-100: connection refused (dead). GPU shared 16559→1382 (unloaded).
- Death window (500+500 saved as death-window-500-500.log): 2 CL_OUT_OF_RESOURCES
  lines, zero grammar/xgrammar/schema/matcher/FSM/mask lines — server logs no
  grammar internals. 16656 served ~69 requests before churn (plain+agentic+
  killer+60×soak) + 31 churn = ~100 lifetime.

## Interpretation (§8)

- `60 identical PASS` then death 31 into distinct schemas → heterogeneous
  structural-grammar churn is the PRIME SUSPECT (direction CONFIRMED vs the
  homogeneous-soak null). Prior death (23620) also struck in a heterogeneous
  phase after 70 mixed requests.
- NOT excluded: pure lifetime-count (~70 vs ~100 at deaths differs, weakens it
  but does not kill it); crash-poisoned pool as co-factor (fresh instances died
  on 1st grammar inference twice — needs reboot baseline to separate).
- Sudden death with flat latency → allocation failure, not gradual pressure
  (modulo weak +2MB/req shared drift, LOW confidence).
- Post-OOR triage impossible (dead process, no relaunch pre-reboot) →
  executor-dead vs grammar-poisoned vs context-poisoned UNRESOLVED from this run;
  reboot-baseline + same workload decides it.
- Whitespace-loop fix and CL_OUT_OF_RESOURCES are SEPARATE issues (no merge):
  loop never appeared on candidate in ~200 generations; OOM is the blocker.
- Previous findings unchanged: CONFIRMED (loop mechanism, adapter attribution,
  audit), this run adds the churn-death datapoint, SUPERSEDES nothing.

## Next (post-reboot, binary A)

Same 120-churn + 20-echo protocol on clean pool. If A survives → B rejected,
repair done. If A dies the same way → suspect GenAI structured-output lifetime
(grammar objects, compiled-schema cache, logits-mask buffers under heterogeneous
load) — profile the allocation boundary, not the parser.
