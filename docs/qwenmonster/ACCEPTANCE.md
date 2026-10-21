# Qwenmonster M1 verification

Status: **NOT RUN** (source-only GitHub work).

## Bazel gates

On a checkout containing the Qwen tokenizer test assets and the correct OVMS toolchain:

```bash
bazel test //src:qwenmonster_output_parser_test --test_output=errors
bazel test //src:gemma4_output_parser_test --test_output=errors
bazel test //src:output_parser_core_test --test_output=errors
```

Optional focused test filter:
```bash
bazel test //src:qwenmonster_output_parser_test --test_filter='Qwen3CoderOutputParserTest.Qwenmonster*' --test_output=errors
```

Check compilation and actual assertions rather than treating successful Bazel analysis as a PASS.

## Live gates
1. Deploy the branch binary in an **isolated test instance**, not the working C6 service.
2. Record full unary and SSE JSON for 1 call, 2 calls, zero-argument call, quoted function and parameter names.
3. For every `tool_calls[index]`: exactly one stable `id` + `name`, followed by valid JSON arguments and correct order.
4. Exercise STOP on complete `</function>`, truncation inside a value, and backend LENGTH/timeout/cancellation. Confirm incomplete arguments never become executable.
5. Run Gemma4 control on its pinned profile without changing templates or server flags.
6. Run 20 tool-result continuation cycles, then longer multi-agent acceptance in R5.

## Milestone evidence
- Build output: MISSING
- Focused unit run: MISSING
- Full existing Qwen suite: MISSING
- Gemma regression run: MISSING
- Qwen live unary/SSE traces: MISSING
- Cross-request contamination run: MISSING

M1 is not accepted until all relevant gates are evidenced.
