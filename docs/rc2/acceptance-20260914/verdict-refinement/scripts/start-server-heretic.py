import os, json, time, subprocess, urllib.request, hashlib
from pathlib import Path

RC2_EXE = Path(r'C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914\ovms\ovms.exe')
EVID = Path(r'C:\Users\testc\AppData\Local\Temp\opencode\rc2-roundtrip-forensics\server-heretic')
EVID.mkdir(parents=True, exist_ok=True)
MODEL = 'C:/llm/models/OpenVINO/Wondernutts/gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov'

h = hashlib.sha256(RC2_EXE.read_bytes()).hexdigest()
assert h.lower() == "11d74fd958d1cd2570682fa13562c1bfcf0973dabbf79a0378a8d0cdc886a4fb".lower(), "hash mismatch!"
print("SHA OK")

# Mirror of the proven wondernutts-test smoke graph (GPU VLM_CB), model name gemma4
graph_text = '''# RC2 heretic run 2026-09-14: parity with wondernutts-test smoke (GPU, VLM_CB).
# OVMS_GRAPH_QUEUE_MAX_SIZE: AUTO
    input_stream: "HTTP_REQUEST_PAYLOAD:input"
    output_stream: "HTTP_RESPONSE_PAYLOAD:output"
    node: {
    name: "LLMExecutor"
    calculator: "HttpLLMCalculator"
    input_stream: "LOOPBACK:loopback"
    input_stream: "HTTP_REQUEST_PAYLOAD:input"
    input_side_packet: "LLM_NODE_RESOURCES:llm"
    input_side_packet: "LLM_NODE_EXECUTION_CONTEXTS:llm_ctx"
    output_stream: "LOOPBACK:loopback"
    output_stream: "HTTP_RESPONSE_PAYLOAD:output"
    input_stream_info: {
        tag_index: 'LOOPBACK:0',
        back_edge: true
    }
    node_options: {
        [type.googleapis.com / mediapipe.LLMCalculatorOptions]: {
            max_num_seqs:256,
            device: "GPU",
            models_path: "%s",
            enable_prefix_caching: true,
            cache_size: 0,
            pipeline_type: VLM_CB,
        }
    }
    input_stream_handler {
        input_stream_handler: "SyncSetInputStreamHandler",
        options {
        [mediapipe.SyncSetInputStreamHandlerOptions.ext] {
            sync_set {
            tag_index: "LOOPBACK:0"
            }
        }
        }
    }
    }
''' % MODEL
graph = EVID/'gemma4-graph.pbtxt'; graph.write_text(graph_text)
config = EVID/'config.json'
config.write_text(json.dumps({'model_config_list':[],'mediapipe_config_list':[{'name':'gemma4','graph_path':str(graph)}]}))

REST=18091; GRPC=18092
runtime = RC2_EXE.parent
env = os.environ.copy()
for key in ('PYTHONHOME','PYTHONPATH','OVMS_DIR','ESPEAK_DATA_PATH'):
    env.pop(key,None)
env['PATH']=os.environ['SystemRoot']+r'\System32;'+os.environ['SystemRoot']
out=open(EVID/'server.stdout.log','wb'); err=open(EVID/'server.stderr.log','wb')
cmdline=f'call setupvars.bat && ovms.exe --config_path {config} --rest_port {REST} --port {GRPC}'
p=subprocess.Popen(['cmd.exe','/d','/c',cmdline],cwd=str(runtime),env=env,stdout=out,stderr=err)
print(f"PID: {p.pid}")
try:
    ready=False
    for i in range(600):
        if p.poll() is not None:
            print(f"EXITED {p.poll()}"); break
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{REST}/v3/models',timeout=2) as r:
                body=r.read()
                try: ready=any(m.get('id')=='gemma4' for m in json.loads(body).get('data',[]))
                except Exception: ready=False
                if ready:
                    print(f"READY after ~{i}s"); break
        except Exception:
            if i%30==0: print(f"WAITING {i}",flush=True)
        time.sleep(1)
    print(f"READY={ready}")
    (EVID/'ready.json').write_text(json.dumps({"ready":ready,"pid":p.pid,"model":MODEL}))
finally:
    print(f"EVID: {EVID}")
