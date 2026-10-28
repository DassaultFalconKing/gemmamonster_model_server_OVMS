import hashlib,json
from pathlib import Path
root=Path(__file__).parent
result=json.loads((root/'RESULT.json').read_text())
assert result['status']=='PASS' and len(result['measured'])==3
provenance=json.loads((root/'provenance.json').read_text(encoding='utf-8-sig'))
for module in provenance['modules']:
    module['on_disk_sha256']=hashlib.sha256(Path(module['FileName']).read_bytes()).hexdigest()
model=Path('C:/llm/models/tvall43-Qwen3.6-35B-A3B-heretic-int4-ov')
identity=[]
for p in sorted(model.iterdir()):
    if p.is_file():
        item={'name':p.name,'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}
        if p.suffix!='.bin':item['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        identity.append(item)
provenance['model_files']=identity
provenance['weight_hash_scope']='weights size/mtime only; full weight hashing not performed'
(root/'provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
text=['# Qwen3.6 heretic speed test, 2026-10-28','',
'Existing server on127.0.0.1:8137, PID8040. No restart/configuration change.',
'Model: tvall43-Qwen3.6-35B-A3B-heretic-int4-ov; API qwen36-35b-a3b-heretic-int4.',
'Intel Core Ultra7 258V / Arc140V, driver32.0.101.9150; RC4 py_off, VLM_CB/GPU, offload20, KV u4, 2slots, batch4096, cache_size0, interval256, prefix cache ON.',
'Method: existing speed-20261024/run_ab.py request/timing implementation; C12 live-long-prompt; 2warmups excluded, 3measured runs, temperature0, enable_thinking=false, seed unset. Input1788/output256 tokens per run.',
'','| Run | Decode tok/s estimate | TTFT s | Wall s |','|---|---:|---:|---:|']
for i,row in enumerate(result['measured'],1):text.append(f"| {i} | {row['decode_tok_s_estimate']:.3f} | {row['ttft_s']:.3f} | {row['wall_s']:.3f} |")
text+=['',f"Median decode: {result['median_decode_tok_s']:.3f} tok/s; median TTFT: {result['median_ttft_s']:.3f}s.",
'Decode=(usage.completion_tokens-1)/(last-first nonempty SSE delta). Client-observed estimate, not internal token timestamps. TTFT includes prefill/queue/transport; pure prefill throughput NOT_AVAILABLE.',
'All five requests, responses and per-run metrics are retained. Model-specific results only; no transfer to baseline/Fast/Ornith or different runtime settings. No agentic/tool acceptance claim.',
'provenance.json records actual process command, loaded-module paths/on-disk hashes and model metadata. Full weight hashes NOT_RUN. Server left unchanged and running.']
(root/'RESULT.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
print('\n'.join(text[7:]))
