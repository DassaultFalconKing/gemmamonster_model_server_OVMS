"""Bounded passive process memory observations. Never infer, restart or kill."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time


def utc():
    return datetime.now(timezone.utc).isoformat()


def validate_snapshot(value, expected_created):
    if value['created_before'] != expected_created or value['created_after'] != expected_created:
        raise ValueError('Target process identity changed')
    for key in ('total_bytes','available_bytes','rss_bytes','private_bytes'):
        metric=value[key]
        if key=='private_bytes' and metric is None:
            continue
        if type(metric) is not int or metric<0:
            raise ValueError('Invalid memory metric: '+key)
    if value['total_bytes']==0:
        raise ValueError('Total memory must be positive')
    if value['available_bytes']>value['total_bytes']:
        raise ValueError('Available memory exceeds total')


def collect(output, reader, *, pid, expected_created, samples=6, interval=10,
            phase='idle', stop_below_bytes=None, sleep=time.sleep):
    if type(pid) is not int or pid<=0:
        raise ValueError('PID must be positive')
    if not math.isfinite(expected_created) or expected_created<=0:
        raise ValueError('Expected creation time must be finite and positive')
    if type(samples) is not int or not 1<=samples<=1000:
        raise ValueError('Sample count must be between1 and1000')
    if not math.isfinite(interval) or interval<0 or (samples-1)*interval>300:
        raise ValueError('Sampling duration must be bounded by300 seconds')
    if stop_below_bytes is not None and (type(stop_below_bytes) is not int or stop_below_bytes<0):
        raise ValueError('Headroom limit must be nonnegative bytes')
    values=[]
    status='COMPLETE'
    started=time.monotonic()
    with Path(output).open('x',encoding='utf-8') as stream:
        def emit(record):
            stream.write(json.dumps(record,ensure_ascii=True)+'\n')
            stream.flush()
        emit({'kind':'header','utc':utc(),'sampler_pid':os.getpid(),'target_pid':pid,
              'expected_created':expected_created,'requested':samples,'interval_s':interval,
              'phase':phase,'stop_below_bytes':stop_below_bytes,'accepted':False})
        try:
            for index in range(samples):
                value=reader(pid,expected_created)
                validate_snapshot(value,expected_created)
                record={key:value[key] for key in ('created_before','created_after','total_bytes',
                        'available_bytes','rss_bytes','private_bytes')}
                record.update(kind='sample',index=index,utc=utc(),elapsed_s=time.monotonic()-started,
                              backend_version=value.get('backend_version'))
                values.append(record)
                emit(record)
                if stop_below_bytes is not None and record['available_bytes']<stop_below_bytes:
                    status='RESOURCE_LIMIT'
                    break
                if index+1<samples and interval:
                    sleep(interval)
        except Exception as error:
            status='FAILED'
            emit({'kind':'error','utc':utc(),'error_type':type(error).__name__,'message':str(error)})
        private_delta=None
        if values and values[0]['private_bytes'] is not None and values[-1]['private_bytes'] is not None:
            private_delta=values[-1]['private_bytes']-values[0]['private_bytes']
        result={'kind':'summary','utc':utc(),'status':status,'requested':samples,'collected':len(values),
                'exit_code':{'COMPLETE':0,'RESOURCE_LIMIT':2,'FAILED':1}[status],
                'min_available_bytes':min(v['available_bytes'] for v in values) if values else None,
                'rss_delta_bytes':values[-1]['rss_bytes']-values[0]['rss_bytes'] if values else None,
                'private_delta_bytes':private_delta,'leak_status':'NOT_DETERMINED','accepted':False}
        emit(result)
    return result


def read_psutil(pid,expected_created):
    import psutil
    process=psutil.Process(pid)
    before=process.create_time()
    if before!=expected_created:
        raise ValueError('Target process identity changed before metric read')
    memory=process.memory_info()
    system=psutil.virtual_memory()
    after=psutil.Process(pid).create_time()
    return {'created_before':before,'created_after':after,
            'total_bytes':system.total,'available_bytes':system.available,
            'rss_bytes':memory.rss,'private_bytes':getattr(memory,'private',None),
            'backend_version':psutil.__version__}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--expected-created',type=float,required=True,help='Exact psutil create_time Unix timestamp')
    parser.add_argument('--output',type=Path,required=True,help='New private JSONL path; never overwritten')
    parser.add_argument('--samples',type=int,default=6)
    parser.add_argument('--interval',type=float,default=10)
    parser.add_argument('--phase',default='idle')
    parser.add_argument('--stop-below-mib',type=int)
    args=parser.parse_args()
    try:
        result=collect(args.output,read_psutil,pid=args.pid,expected_created=args.expected_created,
                       samples=args.samples,interval=args.interval,phase=args.phase,
                       stop_below_bytes=args.stop_below_mib*1048576 if args.stop_below_mib is not None else None)
    except (ValueError,OSError) as error:
        print(json.dumps({'status':'FAILED','error_type':type(error).__name__,'message':str(error)}))
        return 1
    print(json.dumps(result))
    return result['exit_code']


if __name__=='__main__':
    raise SystemExit(main())
