"""Thread-safe, version-keyed cache for immutable read projections, not media."""
import json, threading
from pathlib import Path

_lock=threading.RLock()
_cache={}

def read_json(path):
    path=Path(path).resolve()
    with _lock:
        before=path.stat();key=(before.st_mtime_ns,before.st_size)
        cached=_cache.get(path)
        if cached and cached[0]==key:return cached[1]
        raw=path.read_bytes();after=path.stat()
        if (after.st_mtime_ns,after.st_size)!=key:raise RuntimeError('读取时清单发生变化，请重新读取')
        value=json.loads(raw)
        _cache[path]=(key,value)
        return value
