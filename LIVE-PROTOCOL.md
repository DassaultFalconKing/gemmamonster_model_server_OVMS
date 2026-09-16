# Promotion follow-up: live tool-calling dogfood

Requested on 2026-09-16 after the six promotion semantic targets pass.

The requested source document is `C:/git/gemma4-upstream-refit-clean-20260915/acceptance/gemma4-u4-mtp-20260916/README.md`. Its old 2026.4 binary and experimental profile matrix are not current RC authority. This run uses its tool-calling and OpenCode compatibility workload concepts and its one-warmup/three-measured-repeat protocol, with the accepted 2026.5 binary and unchanged u4/b4096/seq4 profile.

The fixture is the immutable acceptance directory inside the promotion worktree. Tools perform actual directory listing and bounded text reads, resolve paths under that root, validate tool names and JSON arguments, and record tool results. No model-generated shell commands are executed. This is an API-driven local agent harness, not execution of the OpenCode application.

Each identical round uses temperature=0 and max_tokens=512:

- Named unary `read_file`, followed by tool-result replay and a grounded final answer.
- Required streaming `read_file`, preserving raw SSE and reconstructing calls by index, followed by streaming replay.
- Parallel same-name `read_file` calls for two explicitly named files, followed by replay of both results.
- Auto agent: list root, read binary provenance, list logs, then produce a grounded final answer within eight turns.

Validation includes HTTP status, tool identity and unique ids, schema and exact requested file paths, `finish_reason`, successful tool execution, replay continuation, final answer grounding, and bounded agent termination. A length finish, missing work, malformed arguments, or exhausted turn budget is FAIL. HTTP 200 alone is insufficient.

Artifacts are saved in `live/requests`, `live/responses`, `live/streams`, `live/tools`, and `live/ovms.log`. `summary.json` records per-case outcomes. Transport errors or GPU fatal/quarantine markers stop the run for inspection. Subsequent requests must not be used to treat an already quarantined executor as ready merely because `/models` responds.

No production source, operating parameters, original accepted evidence, or existing server process is changed by this harness. The fresh launcher refuses an occupied port and uses the accepted package setup and launch script, redirecting logs into this new evidence directory.
