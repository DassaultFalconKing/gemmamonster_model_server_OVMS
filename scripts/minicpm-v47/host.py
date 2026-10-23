"""Read instantaneous DXGI adapter budgets; never reserves memory."""
import ctypes as c
from ctypes import wintypes as w
import json
import uuid
import psutil


def guid(s):
    return (c.c_byte * 16).from_buffer_copy(uuid.UUID(s).bytes_le)


def method(obj, index, result, *types):
    table = c.cast(obj, c.POINTER(c.POINTER(c.c_void_p))).contents
    return c.WINFUNCTYPE(result, c.c_void_p, *types)(table[index])


def dxgi():
    factory = c.c_void_p()
    create = c.WinDLL('dxgi').CreateDXGIFactory1
    create.argtypes = [c.c_void_p,c.POINTER(c.c_void_p)]
    create.restype = c.c_long
    hr = create(guid('770aae78-f26f-4dba-a829-253c83d1b387'),c.byref(factory))
    if hr < 0: raise OSError(hr)
    adapter = c.c_void_p(); adapter3 = c.c_void_p()
    try:
        hr = method(factory,12,c.c_long,w.UINT,c.POINTER(c.c_void_p))(factory,0,c.byref(adapter))
        if hr < 0: raise OSError(hr)
        hr = method(adapter,0,c.c_long,c.c_void_p,c.POINTER(c.c_void_p))(adapter,guid('645967a4-1392-4310-a798-8053ce3e93fd'),c.byref(adapter3))
        if hr < 0: raise OSError(hr)
        class Info(c.Structure):
            _fields_=[(x,c.c_ulonglong) for x in ('Budget','CurrentUsage','AvailableForReservation','CurrentReservation')]
        result = {}
        for segment in (0,1):
            info=Info()
            hr=method(adapter3,14,c.c_long,w.UINT,c.c_int,c.POINTER(Info))(adapter3,0,segment,c.byref(info))
            if hr < 0: raise OSError(hr)
            result['local' if segment==0 else 'non_local']={name:getattr(info,name) for name,_ in info._fields_}
        result['scope']='Adapter index 0, calling-process usage only; not global WDDM usage. Budget is dynamic.'
        return result
    finally:
        for obj in (adapter3,adapter,factory):
            if obj.value: method(obj,2,w.ULONG)(obj)


if __name__ == '__main__':
    result={'ram':psutil.virtual_memory()._asdict(),'swap':psutil.swap_memory()._asdict(),'disk':psutil.disk_usage('C:/')._asdict()}
    try: result['dxgi']=dxgi()
    except Exception as e: result['dxgi_error']=str(e)
    print(json.dumps(result,indent=2))
