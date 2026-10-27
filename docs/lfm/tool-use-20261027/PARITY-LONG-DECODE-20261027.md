# Parity + Long Decode — Hybrid-C — 2026-10-27

EXE pin `d9663aa6…`, KvPrecision=u4, port 18147, sequential GPU.

## Decode (SSE client-observed median, ×3)
| Model | input | max_tokens | decode med | TTFT med |
|-------|-------|------------|------------|----------|
| lfm25-8b-a1b-int4 | short | 128 | 59.30 | 0.143 |
| lfm25-8b-a1b-int4 | long | 128 | 52.58 | 0.866 |
| lfm25-8b-a1b-int4 | short | **512** | **55.61** | 0.148 |
| lfm25-8b-a1b-int4 | long | **512** | **53.26** | 0.874 |
| lfm2-24b-a2b-int4 | short | 128 | 38.54 | 0.246 |
| lfm2-24b-a2b-int4 | long | 128 | 35.63 | 1.747 |
| lfm2-24b-a2b-int4 | short | **512** | **37.79** | 0.238 |
| lfm2-24b-a2b-int4 | long | **512** | **34.79** | 1.726 |

Long-decode headline (max_tokens=512): LFM2.5 ≈ **55.6 / 53.3** tok/s (short/long input); LFM2-24B ≈ **37.8 / 34.8** tok/s.

## Parity suite (same harness, both models)
| Model | tool-probe | agent det (1× unary+sse) | ordinary JSON false-demotion |
|-------|------------|--------------------------|------------------------------|
| lfm25-8b-a1b-int4 | **8/8** | **2/2 PASS** | **PASS** |
| lfm2-24b-a2b-int4 | **8/8** | **2/2 PASS** | **PASS** |

Evidence: `parity-long-decode-20261027\{lfm25,lfm2-24b}\` + `SUMMARY.json`.
