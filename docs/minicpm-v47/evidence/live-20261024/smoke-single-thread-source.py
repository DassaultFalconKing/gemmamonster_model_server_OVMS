"""Candidate GPU text smoke, NOT validated until inference succeeds.

Supervisor kills only its own child on timeout or memory pressure. No CPU fallback.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import psutil


def write(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2),encoding='utf-8')


def child(args):
    import openvino_genai as genai
    result={'device':'GPU','max_new_tokens':32,'do_sample':False,'phase':'constructing','compile_threads':args.compile_threads}
    write(args.output,result)
    try:
        start=time.perf_counter()
        properties={'COMPILATION_NUM_THREADS':args.compile_threads} if args.compile_threads else {}
        pipe=genai.VLMPipeline(str(args.model),'GPU',**properties)
        result['pipeline_construct_seconds']=time.perf_counter()-start
        result['phase']='generating'
        write(args.output,result)
        result['note']='Constructor combines graph reading and compilation; not a separate compile timing.'
        config=genai.GenerationConfig(max_new_tokens=32,do_sample=False)
        prompt='Answer in one sentence: what is a compiler?'
        start=time.perf_counter()
        response=pipe.generate(prompt,config)
        result.update(prompt=prompt,output=str(response),wall_seconds=time.perf_counter()-start,status='REQUIRES_CONTENT_REVIEW',phase='finished')
    except Exception:
        result.update(status='FAIL',exception=traceback.format_exc())
    write(args.output,result)


def supervisor(args):
    required=sum(x.stat().st_size for x in args.model.glob('*.bin'))+int(args.admission_reserve_gib*1024**3)
    available=psutil.virtual_memory().available
    if available<required:
        write(args.output,dict(status='BLOCKED',reason='Memory admission gate',required_bytes=required,available_bytes=available,admission_reserve_gib=args.admission_reserve_gib))
        return 2
    others=[]
    # Windows venv redirectors can leave a python.exe ancestor for this very
    # command. It is our launcher, not a competing model worker.
    own_ancestors={p.pid for p in psutil.Process().parents()}
    for p in psutil.process_iter(['pid','name']):
        name=(p.info['name'] or '').lower()
        if p.info['pid']!=os.getpid() and p.info['pid'] not in own_ancestors and (name.startswith('python') or name in ('ovms.exe','model_server.exe','llama-server.exe','benchmark_app.exe')):
            others.append(p.info)
    if others:
        write(args.output,dict(status='BLOCKED',reason='Another potential inference process',processes=others))
        return 2
    command=[sys.executable,__file__,'--child','--model',str(args.model),'--output',str(args.output)]
    if args.compile_threads:command.extend(['--compile-threads',str(args.compile_threads)])
    samples=[]; start=time.monotonic(); reason=None
    owned={}
    with args.output.with_suffix('.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                ram=psutil.virtual_memory().available
                try:
                    root=psutil.Process(process.pid)
                    members=[root]+root.children(recursive=True)
                    rss=0;private=0;details=[]
                    for member in members:
                        try:
                            owned[member.pid]=member.create_time()
                            info=member.memory_info()
                            rss+=info.rss;private+=getattr(info,'private',0)
                            details.append(dict(pid=member.pid,rss=info.rss,private=getattr(info,'private',0)))
                        except psutil.NoSuchProcess:pass
                except psutil.NoSuchProcess: break
                samples.append(dict(seconds=time.monotonic()-start,available_ram=ram,rss=rss,private=private,processes=details))
                if ram<3*1024**3: reason='Memory pressure floor 3 GiB';break
                if time.monotonic()-start>args.timeout: reason='Timeout';break
                time.sleep(0.5)
        finally:
            if process.poll() is None:
                # Kill observed descendants as well as the Windows venv redirector.
                # PID plus creation time protects against unrelated PID reuse.
                for pid,birth in reversed(list(owned.items())):
                    try:
                        member=psutil.Process(pid)
                        if member.create_time()==birth:member.kill()
                    except psutil.NoSuchProcess:pass
            if process.poll() is None: process.kill()
            code=process.wait(timeout=15)
    write(args.output.with_suffix('.monitor.json'),dict(returncode=code,stop_reason=reason,samples=samples,admission_reserve_gib=args.admission_reserve_gib,required_bytes=required,available_at_start=available))
    if reason or not args.output.exists():
        previous=json.loads(args.output.read_text()) if args.output.exists() else {}
        write(args.output,dict(status='BLOCKED' if reason else 'FAIL',reason=reason or 'Child exited without result',returncode=code,last_child_state=previous))
    if reason:return 2
    if args.output.exists() and json.loads(args.output.read_text())['status']=='FAIL':return 1
    return code


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--timeout',type=int,default=600);p.add_argument('--child',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--admission-reserve-gib',type=float,default=3.0,help='Static admission margin; live free-RAM stop remains 3 GiB regardless')
    p.add_argument('--compile-threads',type=int,help='Optional GPU compilation thread cap')
    a=p.parse_args()
    if a.admission_reserve_gib<0:p.error('admission reserve must be nonnegative')
    if a.compile_threads is not None and a.compile_threads<1:p.error('compile threads must be positive')
    if a.child: child(a)
    else: sys.exit(supervisor(a))
