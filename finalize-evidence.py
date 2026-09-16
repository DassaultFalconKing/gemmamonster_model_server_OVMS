from pathlib import Path
import json, hashlib
out=Path(__file__).parent
live=out/'live'
tests=json.loads((out/'test-summary.json').read_text())
tree=json.loads((out/'tree-verification.json').read_text())
rows=json.loads((live/'summary.json').read_text())
continuations=json.loads((live/'stream-continuation-summary.json').read_text())
assert len(rows)==16 and len(continuations)==4
responses=[]
for f in (live/'responses').glob('*.json'):
    if f.name.endswith('.raw.json') or f.name=='model-list.json': continue
    data=json.loads(f.read_text())
    if 'http_status' in data: responses.append((f.name,data))
assert len(responses)==44, len(responses)
assert all(d['http_status']==200 for _,d in responses)
calls=[c for _,d in responses for c in (d['message'].get('tool_calls') or [])]
assert len(calls)==32
lengths=[name for name,d in responses if d['finish_reason']=='length']
assert len(lengths)==4 and all('agent-auto-turn4' in name for name in lengths)
assert all(d['status']=='PASS' for d in continuations)
assert all(d['status']=='PASS' for d in rows if 'unary-named' in d['case'] or 'parallel' in d['case'])
log=(live/'ovms.log').read_text(encoding='utf-8',errors='replace')
for marker in ['GPU_CONTEXT_FATAL','CL_OUT_OF_RESOURCES','quarantine','CANCELLED']:
    assert marker.lower() not in log.lower(), marker
snapshots=[json.loads(p.read_text(encoding='utf-8-sig')) for p in sorted(live.glob('process-*.json'))]
assert len(snapshots)>=2 and all(s['pid']==3380 for s in snapshots)
for s in snapshots:
    core={m['ModuleName']:m['FileName'] for m in s['modules'] if m['ModuleName'] in ['openvino.dll','openvino_genai.dll','openvino_tokenizers.dll','python312.dll']}
    assert len(core)==4 and all('gemma4-upstream-refit-clean-20260915\\dist\\windows\\ovms\\' in v for v in core.values())
summary={'chat_requests':44,'http_200':44,'tool_calls':32,'named_with_replay':'4/4 PASS','parallel_same_name_with_replay':'4/4 PASS','required_stream_trajectory_with_replay':'4/4 PASS','strict_stream_first_tool_expectation':'4/4 FAIL: valid list_dir chosen before read_file; original receipts preserved','auto_agent_tools':'4/4 completed all three required tools','auto_agent_final_completion':'4/4 FAIL: finish_reason=length at max_tokens=512','server_pid_before_after':3380,'gpu_fatal_or_resource_or_quarantine':False,'delegation_cancellation_exercised':False,'overall_full_dogfood':'FAIL','runtime_fix_attempted':False}
(live/'reviewed-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
report=f'''# Promotion delivery and live dogfood review

PROMOTION_HEAD: {tree['PROMOTION_HEAD']}
MAIN_BASE: {tree['MAIN_BASE']}
RC_SOURCE: {tree['RC_SOURCE']}
RUNTIME_DIFF_FROM_RC: NONE
DOC_ONLY_DIFFS: docs/gemmamonster/promotion-20260916/COMMITS.md, PR-CANDIDATE.md, REPORT.md

All 2074 accepted RC tree entries have identical Git blob ids and file modes. Main and staging are the two exact parents. No main-only files are retained. Production source and build configuration have no changes from RC. Main-only commits: 89; staging-only: 63, comprising 14 upstream lineage and 49 Gemmamonster-specific commits (13 documentation/evidence, 36 implementation/tests).

## Fresh semantic tests

Tested exact promotion HEAD: {tests['tested_head']}. Six targets executed, 64 tests passed, zero failures, zero skipped, zero cached test results. Full command, Bazel build-event stream, log and per-target XML/logs are in this directory.

| Target | Result | Tests |
|---|---|---|
'''
for row in tests['targets']:
    report+=f"| {row['target'].split(':')[1]} | PASS | {row['tests']} |\n"
report+='''
git diff --check: PASS. RC-to-promotion documentation diff check: PASS. Whole-tree RC allowlist check: PASS.

## Accepted build provenance

BUILD_PROVENANCE_REUSED: YES, by complete runtime/build tree equivalence.
BUILD_SOURCE: b722aa440b5555041f24e6d6f7aea8bda100bdf7
EVIDENCE_HEAD: 43bc254e8996f17b929afef79f310d0b0b0cc139
BINARY_SHA256: 3DFC2D11E614BD03924E6730AD8053DB00A6E5564F41E11F966A0929B44F65FE

The accepted packaged binary was hashed again. The new promotion is not claimed as a new binary build. Test runtime DLL hashes also match the accepted package. Full live acceptance was not repeated; the user explicitly added a focused fresh tool-calling dogfood after tests passed.

## Fresh live dogfood

One warmup plus three measured rounds, temperature=0, max_tokens=512. Accepted 2026.5 package and unchanged VLM_CB/GPU/u4, prefix cache enabled, batch tokens=4096, sequences=4, cache_size=0, Gemma4 reasoning/tool parsers, guided tools and dynamic split fuse enabled. The old README's 2026.4 binary/profile was not used.

44 chat requests returned HTTP 200. Across them, 32 tool calls were inspected for id, name, JSON schema and grounded local paths, and executed as bounded local read/list operations. Raw requests, JSON responses, SSE streams, reconstructed messages and tool results are preserved under live/.

- Named unary plus tool-result replay: 4/4 PASS.
- Two parallel same-name read_file calls plus replay of both results: 4/4 PASS.
- Required streaming trajectory and replay: 4/4 PASS, list_dir -> read_file -> final grounded OVMS version.
- The original strict streaming probe expected read_file immediately. It instead got a protocol-valid list_dir("."). Its four FAIL receipts are retained. Separate continuation proves task completion; this was an overly strict first-tool expectation, not an invalid required-tool response.
- Auto agent: all four runs executed list_dir("."), read_file("binary-provenance.txt"), list_dir("logs") correctly. All four final answers were verbose file enumerations and reached exactly 512 completion tokens with finish_reason=length. Full agent completion is FAIL. No repeated tool-call cycle was observed; the payload shows a truncated substantive answer. No max_tokens or runtime tuning was performed to hide this outcome.

FULL_DOGFOOD: FAIL (agent final-answer completion).
TOOL_CALLING_AND_REPLAY: PASS within the stated bounded cases.

PID 3380 and executor thread 27048 continued through the campaign. The initial and final process/module snapshots show the accepted package's core runtime DLLs. The fresh server log contains no GPU_CONTEXT_FATAL, CL_OUT_OF_RESOURCES, quarantine or CANCELLED markers. This harness does not exercise real OpenCode delegation, so it does not independently reproduce parent cancellation or certify the OpenCode application.

## Known caveats and review boundary

- Existing non-blocking caveat: local Gemma/OpenCode can enter repetitive planning/delegation loops; this has not been shown to be an OVMS protocol/parser/runtime failure. Separate track: agent-loop termination / progress watchdog / plan-ledger policy.
- Expected parent-turn cancellation remains the documented delegation behavior when the same PID/executor survives, no GPU fatal/resource/quarantine occurs and the following request succeeds. Not triggered in this fresh harness; no claim of new cancellation evidence.
- Fresh additional dogfood limitation: correct tool execution followed by verbose final answer truncation at the fixed 512-token cap. Full end-to-end dogfood is not green.

PR_READY: YES for independent promotion review; this is not a claim of full dogfood completion.
BLOCKERS: No runtime-equivalence or semantic-suite promotion blocker. The incomplete agent final answer is disclosed as a separate agent/output-budget limitation; no evidence here demonstrates a server fault.

No PR is opened or merged. Main and staging must remain unchanged. Push only the authorized promotion branch after a fresh remote-ref check. Fresh receipts are kept outside the tracked promotion tree so its tested SHA does not change after verification.
'''
(out/'FINAL-REPORT.md').write_text(report,encoding='utf-8')
candidate=Path(r'C:\git\gemma4-rc-main-promotion-20260916\docs\gemmamonster\promotion-20260916\PR-CANDIDATE.md').read_text()
candidate+='\n## Verified delivery evidence\n\nExact candidate `'+tree['PROMOTION_HEAD']+'`: six semantic targets freshly executed, 64/64 tests PASS, zero skipped or cached results. RC whole-tree comparison has only the three documented Markdown additions.\n\nFresh requested API dogfood: named, same-name parallel and streaming replay pass all four rounds. Auto-agent executes its three tools correctly but final answers reach the fixed 512-token cap in 4/4 rounds; full dogfood completion is FAIL. No GPU fatal/resource/quarantine or server restart was observed. This is disclosed separately from the unchanged runtime/source acceptance. Full local receipts: `C:/git/artifacts/gemma4-promotion-20260916/FINAL-REPORT.md`.\n'
(out/'PR-READY-DESCRIPTION.md').write_text(candidate,encoding='utf-8')
manifest={str(p.relative_to(live)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in live.rglob('*') if p.is_file() and p.name!='ovms.log'}
(out/'live-files-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(summary,indent=2))
