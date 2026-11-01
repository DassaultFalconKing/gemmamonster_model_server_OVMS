# WTTP research harness (not production)

This directory contains a Russian-project architectural prototype documented in [WTTP_CONCEPT_AND_TEST_PROTOCOL.md](WTTP_CONCEPT_AND_TEST_PROTOCOL.md).

| File | Role |
|---|---|
| `wttp_token_fixture.py` | Generate/replay synthetic token-ID sequences from `tokenizer.json` |
| `test_wttp_token_fixture.py` | Runnable Python `unittest` suite |
| `synthetic_tokenizer.json` | Explicitly artificial miniature tokenizer for CI/offline demo |
| `synthetic_token_streams.json` | 12 reproducible synthetic ID sequences from the artificial tokenizer |
| `synthetic_replay_results.json` | Replay output; no tool ever executed |
| `WTTP_CONCEPT_AND_TEST_PROTOCOL.md` | Architecture, Retainer boundary, evidence limits and acceptance tests |

Run:

```bash
python -m unittest -v test_wttp_token_fixture.py
python wttp_token_fixture.py generate synthetic_tokenizer.json --family lfm25 -o synthetic_token_streams.json
python wttp_token_fixture.py replay synthetic_token_streams.json -o synthetic_replay_results.json
```

For real tokenizer files, `pip install tokenizers huggingface_hub` then run `generate LiquidAI/LFM2.5-8B-A1B --family lfm25` (no model weights downloaded). The tokenizer SHA is checked during replay.

Never label these outputs as live model traces, model quality metrics or validated GPU behavior. Do not execute candidate tools from this harness.
