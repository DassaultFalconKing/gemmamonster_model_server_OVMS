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
    result={'device':'GPU','max_new_tokens':32,'do_sample':False}
    try:
        start=time.perf_counter()
        pipe=genai.VLMPipeline(str(args.model),'GPU')
        result['pipeline_construct_seconds']=time.perf_counter()-start
        result['note']='Constructor combines graph reading and compilation; not a separate compile timing.'
        config=genai.GenerationConfig(max_new_tokens=32,do_sample=False)
        prompt='Answer in one sentence: what is a compiler?'
        start=time.perf_counter()
        response=pipe.generate(prompt,config)
        result.update(prompt=prompt,output=str(response),wall_seconds=time.perf_counter()-start,status='REQUIRES_CONTENT_REVIEW')
    except Exception:
        result.update(status='FAIL',exception=traceback.format_exc())
    write(args.output,result)


def supervisor(args):
    required=sum(x.stat().st_size for x in args.model.glob('*.bin'))+3*1024**3
    available=psutil.virtual_memory().available
    if available<required:
        write(args.output,dict(status='BLOCKED',reason='Memory admission gate',required_bytes=required,available_bytes=available))
        return 2
    others=[]
    for p in psutil.process_iter(['pid','name']):
        name=(p.info['name'] or '').lower()
        if p.info['pid']!=os.getpid() and (name.startswith('python') or name in ('ovms.exe','model_server.exe','llama-server.exe','benchmark_app.exe')):
            others.append(p.info)
    if others:
        write(args.output,dict(status='BLOCKED',reason='Another potential inference process',processes=others))
        return 2
    command=[sys.executable,__file__,'--child','--model',str(args.model),'--output',str(args.output)]
    samples=[]; start=time.monotonic(); reason=None
    with args.output.with_suffix('.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                ram=psutil.virtual_memory().available
                try: rss=psutil.Process(process.pid).memory_info().rss
                except psutil.NoSuchProcess: break
                samples.append(dict(seconds=time.monotonic()-start,available_ram=ram,rss=rss))
                if ram<3*1024**3: reason='Memory pressure floor 3 GiB';break
                if time.monotonic()-start>args.timeout: reason='Timeout';break
                time.sleep(0.5)
        finally:
            if process.poll() is None: process.kill()
            code=process.wait(timeout=15)
    write(args.output.with_suffix('.monitor.json'),dict(returncode=code,stop_reason=reason,samples=samples))
    if reason or not args.output.exists():
        write(args.output,dict(status='BLOCKED' if reason else 'FAIL',reason=reason or 'Child exited without result',returncode=code))
    return 2 if reason else code


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--timeout',type=int,default=600);p.add_argument('--child',action='store_true',help=argparse.SUPPRESS)
    a=p.parse_args()
    if a.child: child(a)
    else: sys.exit(supervisor(a))
