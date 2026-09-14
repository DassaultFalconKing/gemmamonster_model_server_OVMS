# Gemma4 Roundtrip Forensics Report

Generated: `2026-09-14T12:58:16.449256+00:00`
Endpoint: `http://127.0.0.1:18091/v3/chat/completions`
Model: `gemma4`
Overall: `PASS`

## Run summary

| Run | Result | Turn1 | Exact unary | Exact stream | Localization |
|---:|---|---|---|---|---|
| 1 | PASS | OK | OK | OK | none |

## Exact-path metrics

| Run | Phase | HTTP | Finish | Prompt tok | Completion tok | TTFB s | TTFT s | Total s | tok/s wall | tok/s after TTFT |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | turn1 | 200 | tool_calls | 185 | 137 | 6.4053 | n/a | 6.4055 | 21.3878 | n/a |
| 1 | turn2 unary | 200 | stop | 293 | 23 | 1.7133 | n/a | 1.7133 | 13.4240 | n/a |
| 1 | turn2 stream | 200 | stop | n/a | n/a | 0.1205 | 0.2232 | 1.2088 | n/a | n/a |

## Interpretation

### Run 1

Classification: `none`

Likely subsystems: `none`

Clean-history variants that recover: `clean-null, clean-empty`

## Evidence layout

Each run contains the exact turn1 request/response and, for each history variant, both unary and streaming turn2 exchanges. Raw SSE, event timing, response headers, request sizes, parsed responses, and summaries are retained next to each exchange.

`TTFT` is reported only for streaming, where a first meaningful delta can actually be observed. Unary requests report TTFB and total latency; no fake TTFT is synthesized.
