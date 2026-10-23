"""One reversible working-set trim of selected desktop apps; never stops a process."""
import argparse
import ctypes as c
import json
from pathlib import Path
import time
import psutil


GROUPS={
    'desktop':{'Cursor.exe','ChatGPT.exe','Discord.exe','Signal.exe','msedge.exe','msedgewebview2.exe','handy.exe','TextInputHost.exe'},
    'secondary':{'NordVPN.exe','explorer.exe','PhoneExperienceHost.exe','PowerToys.Peek.UI.exe','Microsoft.CmdPal.UI.exe','WidgetBoard.exe'},
}


def reclaim(group,apply):
    kernel=c.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[c.c_uint32,c.c_int,c.c_uint32];kernel.OpenProcess.restype=c.c_void_p
    kernel.K32EmptyWorkingSet.argtypes=[c.c_void_p];kernel.K32EmptyWorkingSet.restype=c.c_int
    kernel.CloseHandle.argtypes=[c.c_void_p]
    result=dict(before=psutil.virtual_memory()._asdict(),group=group,apply=apply,processes=[])
    for process in psutil.process_iter(['pid','name','create_time','memory_info']):
        if process.info['name'] not in GROUPS[group]:continue
        row=dict(pid=process.pid,name=process.info['name'],birth=process.info['create_time'],rss_before=process.info['memory_info'].rss)
        if apply:
            handle=kernel.OpenProcess(0x1000|0x100,False,process.pid)
            if handle:
                try:
                    row['success']=bool(kernel.K32EmptyWorkingSet(handle))
                    if not row['success']:row['error']=c.get_last_error()
                finally:kernel.CloseHandle(handle)
            else:row['error']=c.get_last_error()
        try:row['rss_after']=process.memory_info().rss
        except psutil.Error:pass
        result['processes'].append(row)
    if apply:time.sleep(2)
    result['after']=psutil.virtual_memory()._asdict()
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--group',choices=GROUPS,required=True);p.add_argument('--apply',action='store_true')
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(reclaim(args.group,args.apply),indent=2),encoding='utf-8')
