# XGrammar cache hardening: A/B verdict (2026-09-14, post-reboot)

```
SOURCE_HEAD=52a32a8d3 (test/genai cache-off) on product branch, incl 4be7330b8 (cache instrumentation)
GENAI_HEAD=7ea25468 + bounded-whitespace patch + diagnostics patch (+cache-off patch for B)
XGRAMMAR_HEAD=9aa840b6 (both builds; submodules pinned, see whitespace-dependencies.json)

REBOOT_BASELINE=2026-09-14 21:05 boot; Free 17.9GB/33GB; GPU shared 1248MB;
  driver 32.0.101.8991; zero ovms.exe. (post-reboot-baseline/ in temp)

A_UNLIMITED=Build A pkg (ovms.exe AF921BB2 + genai CF762217): init limit=-1 size=0;
  same-fp reuse 86ms->0ms/0B-growth (cache reuse PROVEN);
  distinct fp +170-430KB each (growth PROVEN)
A_CACHE_GROWTH=+170-430KB per unique grammar (CPU-side counter)

B_CACHE_OFF=Build B pkg (same ovms.exe + genai 10A331D5, ctor cache_enabled=false):
  every compile before=0/after=0, ~80ms flat; B1 smoke 4/4 canonical; B2 32/32 clean
B_HOMOGENEOUS=32/32 canonical (t1 sweep)
B_HETEROGENEOUS=DIED at req 25 (24 served distinct, all canonical, 0 soft anomalies;
  req025 hung 27.5s -> CL_OUT_OF_RESOURCES (oneDNN ocl errcode -5) -> process death;
  fatal compile's [XGrammarCache] line ABSENT = died mid-compile)
B_POST_CHURN=NOT_RUN (dead; relaunch forbidden pre-conclusion)

C_CACHE_256M=NOT BUILT (skipped per protocol: B red)
C_CACHE_PEAK=n/a
C_HETEROGENEOUS=n/a
C_POST_CHURN=n/a

TTFT_UNLIMITED=repeat-grammar ~0ms post-warm (cache hit); first-unique ~86ms
TTFT_CACHE_OFF=~80ms EVERY grammar request (no reuse; median ~81, p95 ~94 over ~60 samples)
TTFT_CACHE_256M=n/a (would match unlimited on hits by construction)

WHITESPACE_FIX=INTACT (loop never observed on any build this session; no parser changes)
AGENTIC_REGRESSION=none on B before churn (B1 canonical incl. required/named)

ROOT_CAUSE_VERDICT=CACHE_ROOT_CAUSE REJECTED. Cache-off died FASTER (24 served)
  than unlimited (31 served) in the same regime. Cache accumulation is not the
  killer. Leading hypothesis (STRONGLY_SUPPORTED): transient per-compile GPU
  allocation vs a nearly-full pool (model holds ~15.3GB of ~17.5GB committed).
  Homogeneous load compiles once and reuses -> immortal; heterogeneous load pays
  a fresh transient spike per unique grammar -> eventually one spike doesn't fit
  (fragmentation luck), CL_OUT_OF_RESOURCES mid-compile, executor/process death.
  Supporting: flat compile latency (~80ms) and flat RSS to the very end (sudden,
  not gradual); zero grammar internals in server logs; no host-side growth signal.
RELEASE_CANDIDATE=NONE from this matrix. A 256MiB cap cannot fix transient
  compile bursts (it bounds stored entries; B proved zero stored entries still die).
```

## Addendum 2026-09-14 late: stock RC2 churn (dirty pool, pre-reboot commit A)

STOCK_RC2_CHURN=same 120-churn vs stock binary 11d74fd9 (genai 9d1639af):
  24 served distinct, all canonical; req 025 hung 18s -> CL_OUT_OF_RESOURCES
  (oneDNN ocl errcode -5) -> process death. Req 025 schema trivial (4 props).
  Same kill point as Build B (24 served, req 025). Evidence: deep-dive/churn-stock/.
STOCK_LOOP_EVENTS=3x whitespace-loop (req 012/016/021, length+empty, HTTP200),
  process SURVIVED all three and continued.

REBUILT_GENAI_CORRELATION: SUPERSEDED (stock dies identically in the same pool era;
  earlier 100% correlation was pool-state confounding, not a binary difference).
WHITESPACE_LOOP_CAUSES_GPU_DEATH: DISPROVED (loop events are survivable soft events).
DISTINCT_GRAMMAR_CHURN_CORRELATION: STRENGTHENED (deaths at 31 / 24 / 24 distinct
  served across three binaries; homogeneous reuse immortal everywhere).
PER_COMPILE_ACCUMULATION: OPEN / HIGH-CONFIDENCE HYPOTHESIS (mechanism detail —
  real leak vs USM fragmentation vs compiler artifacts vs plugin state — unobserved).
DIRTY_POOL_CONFOUND: OPEN (fresh-instance first-inference deaths unexplained).
NEXT_DISCRIMINATOR: CLEAN_REBOOT_STOCK_120_CHURN (commit B, separate experiment).
  Dies ~20-35 -> accumulation CONFIRMED. Passes 120/120 -> dirty-state-necessary,
  per-compile theory WEAKENED.

Note: this commit (A) is dirty-pool evidence by construction. Do NOT merge its
conclusion with the post-reboot discriminator (commit B).

## Classification ledger

- Persistent-unlimited-cache as OOM root cause: REJECTED (HIGH — B discriminates).
- Transient-compile-burst vs full pool: STRONGLY_SUPPORTED (HIGH on contrast, MEDIUM on mechanism — allocator internals unobserved).
- Whitespace-loop fix efficacy: CONFIRMED (unchanged).
- `<call:...>`/schema-validation/template theories: unchanged (NOT_REPRODUCED / no evidence).
- Pool-poisoning co-factor: OPEN (fresh-instance first-inference deaths pre-reboot unexplained by compile bursts alone; needs clean-pool rerun).

## What was built (binaries/DLLs)

- Build A genai DLL `CF762217` (instrumented, unlimited): package
  `.../4be7330b8-cache-instrumented-A-unlimited-20260914T213000Z/ovms`
- Build B genai DLL `10A331D5` (instrumented, cache-off): package
  `.../4be7330b8-cache-B-off-20260914T220000Z/ovms`
- ovms.exe `AF921BB2` reused for both (no GenAI ABI change from instrumentation).
- Protected modules unchanged (openvino `def53dd3`, tokenizers `ef29a1d5`).

## Recommended next (not executed)

1. Reboot baseline, rerun heterogeneous churn on Build B: if it still dies ~25,
   pool-poisoning is out and transient-burst is CONFIRMED.
2. Profile the allocation boundary: per-compile transient GPU high-water mark
   (GrammarCompiler/FSM/mask builders), then either cap transient (compile on
   CPU + upload?), serialize compilations, or reserve headroom (smaller model
   footprint / larger shared pool).
3. Keep [XGrammarCache] instrumentation in the tree regardless — it is pure
   observation and already paid for itself twice.
4. Do NOT downgrade XGrammar; do NOT touch parser recovery.

Evidence: buildA-test/, buildB-test/ (B1/B2/B3-churn with per-request results,
server TRACE windows incl. [XGrammarCache] lines, death window), C:\g54r2\*.log,
whitespace-dependencies.json. Live state: NO ovms running (Build B PID 12168 dead).
