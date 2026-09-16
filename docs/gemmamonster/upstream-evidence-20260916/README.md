# Evidence: Gemma4 upstream PR test gates (2026-09-16)

Prep-only branch, never merge into the PR. Companion to:
- `upstream/gemma4-tool-calling` @ d582668e6 (code+provenance docs)
- `upstream/gemma4-tool-calling-split` @ 62676e2e4 (clean PR series)

Contents:
- `test-triage-handoff.md` — GREEN 6-target gate + 16 ovms_test failures triage,
  with bisect pointers and own-docs search requests for the fixer.
- `bug-streaming-named-degenerate.md` — streaming named tool_choice degenerate
  report (whitespace to length) with 3/3b/3c isolation proof.
- `dogfood-*.json/.txt` — raw live captures (26B-heretic, dist binary 3DFC2D11).
- `ovmstest-failing-blocks.txt` — trimmed failing blocks (16) from ovms_test.
- `gate-64-64-summary.txt`, `tested-head*.txt`, `exit-code*.txt` — gate receipts.
