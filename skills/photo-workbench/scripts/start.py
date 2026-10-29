"""Portable local workbench reference runtime; data is supplied by the Agent."""
import ctypes
import argparse,hashlib,json,mimetypes,os,secrets,shlex,subprocess,sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import feedback as fb
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'data';fb.PROJECT=ROOT;fb.BASE=DATA;TOKEN=secrets.token_urlsafe(32)
def read(name):return json.loads((DATA/name).read_text(encoding='utf-8'))
def profile():return json.loads((ROOT/'profile.json').read_text(encoding='utf-8'))
def catalogue():return read('catalog.json')
def tasks():
    rows=read('review_tasks.json')
    for r in rows:r['source_version']=fb.digest({k:v for k,v in r.items() if k!='source_version'})
    return rows
def state(r,s):
    if r.get('owner') in {'Agent','system'}:return 'agent'
    d=s['decisions'].get(r['id'])
    if not d or d.get('source_version')!=r['source_version'] or d.get('action')=='reopen':return 'pending'
    if d['action']=='deferred':return 'deferred'
    if d['action'] in {'accept','reject','keep_unknown','not_this_round'}:return 'done'
    receipt=s['receipts'].get(d.get('event_id'));return 'done' if receipt and receipt['result']=='applied' else 'waiting'
def safe_file(path):
    f=Path(path).resolve();roots=[ROOT]+[Path(x).resolve() for x in profile()['source_roots']]
    if not any(f==r or f.is_relative_to(r) for r in roots):raise ValueError('文件超出使用者确认的来源范围')
    if not f.exists():raise FileNotFoundError('文件当前不存在或存储端未连接')
    return f
def search(q='',page=1,ids=None):
    terms=shlex.split(q.casefold());rows=[p for p in catalogue() if (ids is None or p['id'] in ids) and all(t in ' '.join(str(p.get(k,'')) for k in ['name','description','theme','month','equipment']).casefold() for t in terms)];page=max(1,int(page));return dict(items=rows[(page-1)*30:page*30],total=len(rows),page=page)
def select_file(path):
    target=Path(path).resolve()
    if not target.is_file():raise FileNotFoundError('原文件不存在或当前无法访问')
    if os.name!='nt':raise OSError('此定位实现仅用于 Windows')
    shell=ctypes.WinDLL('shell32');ole=ctypes.WinDLL('ole32');ptr=ctypes.c_void_p()
    ole.CoInitialize.argtypes=[ctypes.c_void_p];ole.CoInitialize.restype=ctypes.c_long
    ole.CoTaskMemFree.argtypes=[ctypes.c_void_p];ole.CoUninitialize.argtypes=[]
    shell.SHParseDisplayName.argtypes=[ctypes.c_wchar_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p),ctypes.c_ulong,ctypes.c_void_p];shell.SHParseDisplayName.restype=ctypes.c_long
    shell.SHOpenFolderAndSelectItems.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_ulong];shell.SHOpenFolderAndSelectItems.restype=ctypes.c_long
    initialized=ole.CoInitialize(None)
    if initialized<0:raise OSError('无法初始化文件定位组件：'+hex(initialized&0xffffffff))
    try:
        result=shell.SHParseDisplayName(str(target),None,ctypes.byref(ptr),0,None)
        if result<0:raise OSError('无法定位此文件：'+hex(result&0xffffffff))
        # With cidl=0 the PIDL is the item, not a folder: the Shell opens its
        # parent and selects this exact file. HRESULT S_OK confirms acceptance.
        result=shell.SHOpenFolderAndSelectItems(ptr,0,None,0)
        if result!=0:raise OSError('资源管理器未完成文件定位：'+hex(result&0xffffffff))
        return dict(path=str(target),selected_file=True,shell_result='S_OK')
    finally:
        if ptr:ole.CoTaskMemFree(ptr)
        ole.CoUninitialize()

class Handler(BaseHTTPRequestHandler):
    def trusted(self):return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
    def send(self,value,status=200,kind='application/json; charset=utf-8'):
        body=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if not self.trusted():return self.send({'error':'Host invalid'},403)
        url=urlparse(self.path);q={k:v[0] for k,v in parse_qs(url.query).items()};s=fb.projection(DATA)
        try:
            if url.path=='/api/health':return self.send(dict(app='photo-workbench',version=1))
            if url.path=='/api/v2/summary':
                rows=tasks();counts={k:sum(state(r,s)==k for r in rows) for k in ['pending','waiting','done','deferred']};cats={r['category']:sum(x['category']==r['category'] and state(x,s)=='pending' for x in rows) for r in rows};intake=Path(profile()['source_roots'][0]);return self.send(dict(counts=counts,categories=cats,assets=len(catalogue()),projects=read('projects.json') if (DATA/'projects.json').exists() else [],intake_files=sum(p.is_file() for p in intake.rglob('*')) if intake.is_dir() else 0,intake_path=str(intake),revision=s['revision'],catalog_at=None,token=TOKEN))
            if url.path=='/api/library':return self.send(search(q.get('q',''),q.get('page',1)))
            if url.path=='/api/v2/collections':
                sections=profile()['collections'];section=q.get('section','');section=section if any(x['id']==section for x in sections) else sections[0]['id'];rows=[r for r in read('collections.json') if r['section']==section];page=max(1,int(q.get('page',1)));return self.send(dict(sections=sections,active_section=section,items=[{k:v for k,v in r.items() if k!='members'} for r in rows[(page-1)*24:page*24]],total=len(rows),page=page))
            if url.path=='/api/v2/album':
                album=next(r for r in read('collections.json') if r['id']==q.get('id'));result=search(q.get('q',''),q.get('page',1),album['members']);result['album']={k:v for k,v in album.items() if k!='members'};return self.send(result)
            if url.path=='/api/v2/queue':
                rows=[r for r in tasks() if state(r,s)==q.get('view','pending') and (not q.get('category') or r['category']==q['category'])];rows.sort(key=lambda r:(r.get('priority',50),r['id']));offset=max(0,int(q.get('offset',0)));chosen=rows[offset:offset+1]
                for r in chosen:r.update(photo_count=len(r['asset_ids']),photos=[p for p in catalogue() if p['id'] in r['asset_ids']][:12],decision=s['decisions'].get(r['id']))
                return self.send(dict(items=chosen,total=len(rows),offset=offset,revision=s['revision']))
            if url.path=='/api/v2/task':
                t=next(r for r in tasks() if r['id']==q.get('id'));start=max(0,int(q.get('page',0)))*24;photos=[p for p in catalogue() if p['id'] in t['asset_ids']];return self.send(dict(details=t.get('details',{}),paths=t['paths'],photos=photos[start:start+24],total=len(photos)))
            if url.path=='/api/v2/learning':return self.send(dict(revision=s['revision'],suggestions=[dict(x,receipt=s['receipts'].get(x['event_id'])) for x in s['suggestions']],rules=list(s['rules'].values())))
            if url.path=='/api/library-preview':
                photo=next(p for p in catalogue() if p['id']==q.get('id'));f=(ROOT/photo['preview']).resolve()
                if not f.is_relative_to(ROOT) or not f.is_file():raise ValueError('预览不可用')
                raw=f.read_bytes()
                if hashlib.sha256(raw).hexdigest()!=photo['preview_sha256']:raise ValueError('预览已改变，需重新生成')
                return self.send(raw,kind='image/jpeg')
            path=(ROOT/('index.html' if url.path=='/' else url.path.lstrip('/'))).resolve()
            if not path.is_relative_to(ROOT) or path==ROOT or path.parts[len(ROOT.parts)] not in {'assets','index.html'} or not path.is_file():return self.send({'error':'not found'},404)
            return self.send(path.read_bytes(),kind=mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
        except (OSError,ValueError,KeyError,StopIteration) as e:return self.send({'error':str(e) or '记录不存在'},400)
    def do_POST(self):
        if not self.trusted() or self.headers.get('X-Photo-Token')!=TOKEN or self.headers.get('Origin',f'http://127.0.0.1:{self.server.server_port}') not in {f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}:return self.send({'error':'Request denied'},403)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=1000000:raise ValueError('Request too large')
            d=json.loads(self.rfile.read(size))
            if self.path=='/api/v2/suggestion':event=fb.save_suggestion(d,DATA)
            elif self.path=='/api/v2/rule-adoption':
                if d.get('rule_id') not in fb.projection(DATA)['rules'] or type(d.get('adopt')) is not bool:raise ValueError('Invalid rule')
                event=fb.append('rule_adoption',dict(rule_id=d['rule_id'],adopt=d['adopt']),revision=d.get('revision'),base=DATA)
            elif self.path=='/api/v2/decision':
                t=next(r for r in tasks() if r['id']==d.get('task_id'))
                if d.get('source_version')!=t['source_version']:raise RuntimeError('审核资料已变化，刷新后再决定；草稿保留')
                if t.get('owner') in {'Agent','system'}:raise ValueError('此项由 Agent 继续处理')
                if d.get('action') not in t['choices']+['reopen']:raise ValueError('请选择本次决定')
                if d['action']=='needs_change' and not d.get('note','').strip():raise ValueError('请说明需要调整哪里')
                event=fb.append('decision',dict(task_id=t['id'],source_version=t['source_version'],action=d['action'],note=d.get('note',''),asset_ids=t['asset_ids'],person_names=d.get('person_names',[])),revision=d.get('revision'),base=DATA)
            elif self.path in {'/api/open','/api/locate'}:
                target=safe_file(d['path'])
                if self.path=='/api/locate' and not target.is_file():raise ValueError('具体照片不存在')
                if self.path=='/api/open' and not target.is_dir():raise ValueError('目录不存在')
                if os.name=='nt':
                    if target.is_file():select_file(target)
                    else:os.startfile(str(target))
                elif sys.platform=='darwin':subprocess.Popen(['open','-R',str(target)] if target.is_file() else ['open',str(target)])
                else:subprocess.Popen(['xdg-open',str(target.parent if target.is_file() else target)])
                return self.send(dict(ok=True,message='已定位文件' if os.name=='nt' or sys.platform=='darwin' else '已打开所在目录，请按照片文件名查看'))
            else:return self.send({'error':'Unknown action'},404)
            return self.send(dict(ok=True,event_id=event['id'],revision=event['seq']))
        except RuntimeError as e:return self.send({'error':str(e)},409)
        except (OSError,ValueError,KeyError,StopIteration) as e:return self.send({'error':str(e) or '记录不存在'},400)
    def log_message(self,*args):pass
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8932);a=p.parse_args();print('Open http://127.0.0.1:'+str(a.port));ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
