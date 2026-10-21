"""Default is read-only plan/preflight. Execution needs explicit resource-slot flag."""
import argparse, hashlib, json, os, pathlib, subprocess, sys, time
from datetime import datetime, timezone
sys.dont_write_bytecode=True
from r1_gate import validate_matrix_log, validate_original_log, terminate_owned_process
ROOT=pathlib.Path(__file__).resolve().parent
def utc(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data): p.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
def absolute_input_path(value):
    if not isinstance(value,str) or not value or not pathlib.Path(value).is_absolute():
        raise RuntimeError('Expected an absolute external input path')
    return pathlib.Path(value)

def preflight():
    data=json.loads((ROOT/'INPUTS.json').read_text(encoding='utf-8'))
    for item in data['files']:
        p=ROOT/item['path']
        if not p.is_file() or p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:
            raise RuntimeError('Sealed input changed/missing: '+str(p))
    sealed={item['path']:item['sha256'] for item in data['files']}
    for name,actual in [('run.py',pathlib.Path(__file__)),
                        ('r1_gate.py',pathlib.Path(validate_matrix_log.__code__.co_filename))]:
        if not actual.is_file() or sealed.get(name)!=sha(actual):
            raise RuntimeError('Executing runner/helper is not the sealed input: '+name)
    # XGrammar CMake globs source files; reject additions as well as changed files.
    expected={x['path'] for x in data['files']
              if x['path'].startswith(('snapshot/','native/'))}
    actual={p.relative_to(ROOT).as_posix() for folder in ['snapshot','native']
            for p in (ROOT/folder).rglob('*') if p.is_file()}
    if actual!=expected:
        raise RuntimeError('Sealed source inventory changed: '+str(sorted(actual^expected)))
    for item in data['external_runtime_files']+data['external_tools']:
        p=absolute_input_path(item['path'])
        if not p.is_file() or sha(p)!=item['sha256']:
            raise RuntimeError('External runtime changed/missing: '+str(p))
    for key in ('runtime_root','runtime_python_home','runtime_python_path'):
        if not absolute_input_path(data.get(key)).is_dir():
            raise RuntimeError('Missing explicit runtime directory: '+key)
    return data
def commands():
    inputs=json.loads((ROOT/'INPUTS.json').read_text(encoding='utf-8'))
    def tool(name):
        matches=[item['path'] for item in inputs['external_tools']
                 if pathlib.Path(item['path']).name.lower()==name]
        if len(matches)!=1: raise RuntimeError('Missing or ambiguous tool: '+name)
        return matches[0]
    cmake=tool('cmake.exe')
    native=ROOT/'native'; build=ROOT/'build'
    wrapper=['rtk','proxy','cmd','/d','/c',str(ROOT/'native-env.cmd')]
    configure=[cmake,'-S',str(native),'-B',str(build),'-G','Ninja',
      '-DCMAKE_BUILD_TYPE=Release',
      '-DCMAKE_MAKE_PROGRAM='+tool('ninja.exe'),
      '-DXGRAMMAR_SOURCE_DIR='+str(ROOT/'snapshot/xgrammar'),
      '-DRUNTIME_HEADERS_DIR='+str(ROOT/'snapshot/runtime-headers')]
    buildcmd=[cmake,'--build',str(build),'--target','r1_guard_matrix','r1_original_checks','--parallel','2']
    return [
      ('configure',wrapper+configure,180),('build',wrapper+buildcmd,1200),
      ('matrix',['rtk','proxy',str(build/'r1_guard_matrix.exe')],120),
      ('original',['rtk','proxy',str(build/'r1_original_checks.exe'),str(ROOT/'snapshot/tokenizer')],120)]
def stage(out,name,argv,timeout,env):
    log=out/(name+'.log'); receipt=out/(name+'.json')
    data={'stage':name,'started_utc':utc(),'command':argv,'cwd':str(ROOT),
      'runner_pid':os.getpid(),'status':'STARTING','timeout_seconds':timeout,
      'input_manifest_sha256':sha(ROOT/'INPUTS.json')}
    write(receipt,data)
    started=time.monotonic()
    with log.open('wb') as stream:
        try:
            proc=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
            data.update(worker_pid=proc.pid,status='RUNNING'); write(receipt,data)
            try: data['exit_code']=proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                data.update(terminate_owned_process(proc, stream))
        except OSError as exc:
            data.update(exit_code=None,launch_error=str(exc))
    data.update(finished_utc=utc(),elapsed_seconds=round(time.monotonic()-started,3),
      status='CLEANUP_UNCONFIRMED' if data.get('cleanup_error') else 'PROCESS_FINISHED',
      log_sha256=sha(log),log_bytes=log.stat().st_size)
    write(receipt,data)
    return data,log.read_text(encoding='utf-8',errors='replace')
def main():
    global ROOT
    parser=argparse.ArgumentParser()
    parser.add_argument('--preparation-root',type=pathlib.Path,default=ROOT)
    parser.add_argument('--execute-resource-slot',action='store_true',
      help='Use only after root explicitly authorizes this CPU build/probe resource slot')
    args=parser.parse_args(); ROOT=args.preparation_root.resolve(); inputs=preflight(); cmds=commands()
    initial_manifest_sha256=sha(ROOT/'INPUTS.json')
    plan={'status':'READY','execution':'NOT RUN','accepted':False,
      'candidate_sha':inputs['candidate_sha'],'manifest_sha256':initial_manifest_sha256,
      'commands':[{'stage':n,'argv':a,'timeout_seconds':t} for n,a,t in cmds],
      'scope':'CPU static XGrammar + 2 native executables, jobs2; no install/model/server/HTTP',
      'estimate':'Fresh static XGrammar and two harness translation units; several minutes possible, no measured ETA'}
    if not args.execute_resource_slot:
        print(json.dumps(plan,indent=2)); return 0
    out=ROOT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out.mkdir(parents=True,exist_ok=False); write(out/'PLAN.json',plan)
    env={k.upper():v for k,v in os.environ.items()}
    runtime=pathlib.Path(inputs['runtime_root'])
    paths=[runtime/'bin/intel64/Release']
    paths += [p for p in (runtime/'3rdparty/tbb').rglob('*') if p.is_dir() and p.name in ('bin','vc14')]
    env['PATH']=';'.join(map(str,paths))+';'+inputs['runtime_python_home']+';'+env.get('PATH','')
    env['OPENVINO_TOKENIZERS_PATH_GENAI']=str(runtime/'bin/intel64/Release/openvino_tokenizers.dll')
    env['PYTHONHOME']=inputs['runtime_python_home']; env['PYTHONPATH']=inputs['runtime_python_path']
    results=[]; failed=False
    for name,argv,timeout in cmds:
        data,log=stage(out,name,argv,timeout,env)
        expected_exit=2 if name=='matrix' else 0
        good=data.get('exit_code')==expected_exit and not data.get('timed_out')
        if name=='matrix':
            gate=validate_matrix_log(log,data.get('exit_code'))
            good=good and gate['valid']
            data['matrix_validation']=gate
            data['semantic_status']=gate['status']
        if name=='original':
            good=good and validate_original_log(log,data.get('exit_code'))
        data['gate_status']='OPEN' if good and name=='matrix' else ('PASS' if good else 'FAIL')
        write(out/(name+'.json'),data); results.append(data)
        if not good: failed=True; break
    artifacts=[]
    for p in [ROOT/'build/r1_guard_matrix.exe',ROOT/'build/r1_original_checks.exe',
              ROOT/'build/xgrammar/xgrammar.lib',ROOT/'build/CMakeCache.txt',ROOT/'build/build.ninja']:
        if p.is_file(): artifacts.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
    # Revalidate inputs after execution to catch drift during the run.
    try: preflight()
    except Exception as exc: failed=True; results.append({'postflight_error':str(exc)})
    final={'status':'FAILED' if failed else 'OPEN_EXPECTED_FAILURES','accepted':False,
      'candidate_sha':inputs['candidate_sha'],'manifest_sha256':initial_manifest_sha256,
      'observed_final_manifest_sha256':sha(ROOT/'INPUTS.json') if (ROOT/'INPUTS.json').is_file() else None,
      'results':results,'artifacts':artifacts,'runtime_integrated':False,
      'limitation':'Unit tokenizer matcher evidence only; #650 and canonical model mask/live acceptance remain separate'}
    write(out/'RESULTS.json',final); print(json.dumps({'status':final['status'],'evidence':str(out),'accepted':False}))
    return 1 if failed else 2
if __name__=='__main__': sys.exit(main())
