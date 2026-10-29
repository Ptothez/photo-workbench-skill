"""Synthetic, retained installation/runtime fixtures. No real photos or accounts."""
import importlib.util,json,threading,unittest,uuid,os,tempfile
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import bootstrap
import start as runtime
class Portable(unittest.TestCase):
 def setUp(self):
  self.folder=Path(os.environ.get('PHOTO_WORKBENCH_TEST_ROOT',str(Path(tempfile.gettempdir())/'photo-workbench-tests')))/uuid.uuid4().hex;self.folder.mkdir(parents=True);self.profile=self.folder/'profile.json'
  self.value=dict(purpose='synthetic collection',source_roots=[str(self.folder/'incoming')],stages=['incoming','editing','archived'],review_kinds=['selection'],update_trigger='manual_message',collections=[dict(id='my-collection',title='Synthetic themes',description='User-confirmed test grouping')],confirmed_by_user=True)
  self.profile.write_text(json.dumps(self.value),encoding='utf-8')
 def test_requires_user_confirmation_and_preserves_existing_directory(self):
  self.value['confirmed_by_user']=False;self.profile.write_text(json.dumps(self.value),encoding='utf-8')
  with self.assertRaises(ValueError):bootstrap.create(self.profile,self.folder/'app')
  self.assertFalse((self.folder/'app').exists());self.value['confirmed_by_user']=True;self.profile.write_text(json.dumps(self.value),encoding='utf-8');bootstrap.create(self.profile,self.folder/'app')
  with self.assertRaises(FileExistsError):bootstrap.create(self.profile,self.folder/'app')
 def test_real_http_save_restart_projection_and_conflict(self):
  app=bootstrap.create(self.profile,self.folder/'app');runtime.ROOT=app;runtime.DATA=app/'data';runtime.fb.PROJECT=app;runtime.fb.BASE=app/'data';server=ThreadingHTTPServer(('127.0.0.1',0),runtime.Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url='http://127.0.0.1:'+str(server.server_port)
  def call(path,data=None,token=None):
   r=Request(url+path,data=None if data is None else json.dumps(data).encode(),headers={'X-Photo-Token':token} if token else {})
   try:
    with urlopen(r,timeout=10) as response:return response.status,json.load(response)
   except HTTPError as response:return response.code,json.load(response)
  try:
   code,state=call('/api/v2/summary');self.assertEqual(code,200);self.assertEqual(state['assets'],0)
   self.assertEqual(call('/api/v2/collections?section=themes')[1]['active_section'],'my-collection')
   (app/'data/catalog.json').write_text(json.dumps([dict(id='one',name='flower'),dict(id='two',name='flower')]),encoding='utf-8')
   self.assertEqual([p['id'] for p in runtime.search('flower',ids=['two'])['items']],['two'])
   rows=[dict(id=lane,category='test',title=lane,owner='user',review_lane=lane,asset_ids=[],paths=[],choices=['keep_unknown']) for lane in ['pending','info','optional','clues']]
   (app/'data/review_tasks.json').write_text(json.dumps(rows),encoding='utf-8')
   summary=call('/api/v2/summary')[1];self.assertTrue(all(summary['counts'][k]==1 for k in ['pending','info','optional','clues']))
   version=runtime.tasks()[0]['source_version']
   for _ in range(2):self.assertEqual(call('/api/v2/queue?view=pending')[1]['total'],1)
   self.assertEqual(runtime.tasks()[0]['source_version'],version)
   task=call('/api/v2/queue?view=info')[1]['items'][0]
   self.assertEqual(call('/api/v2/decision',dict(revision=0,task_id='info',source_version=task['source_version'],action='keep_unknown'),state['token'])[0],200)
   counts=call('/api/v2/summary')[1]['counts'];self.assertEqual(counts['info'],0);self.assertEqual(counts['done'],1);self.assertEqual(counts['optional'],1);self.assertEqual(counts['clues'],1)
   body=dict(revision=1,scope='workflow',text='Synthetic feedback preserved verbatim.')
   self.assertEqual(call('/api/v2/suggestion',body,state['token'])[0],200);self.assertEqual(call('/api/v2/suggestion',body,state['token'])[0],409);self.assertEqual(call('/api/v2/suggestion',body)[0],403)
   self.assertEqual(call('/api/v2/learning')[1]['suggestions'][0]['text'],body['text']);ctx=runtime.fb.context(app/'data');self.assertTrue(any(x['payload'].get('text')==body['text'] for x in ctx['pending_feedback']));self.assertFalse(ctx['active_rules'])
  finally:server.shutdown();server.server_close();thread.join()
 def test_optional_desktop_and_port_validation(self):
  self.value.update(desktop_windows=True,port=18934);self.profile.write_text(json.dumps(self.value),encoding='utf-8')
  app=bootstrap.create(self.profile,self.folder/'native')
  self.assertTrue((app/'app/windows/PhotographyWorkbench.cs').is_file());self.assertEqual((app/'desktop-port.txt').read_text(),'18934');self.assertIn('--port 18934',(app/'README.md').read_text(encoding='utf-8'))
  self.value['port']=0;self.profile.write_text(json.dumps(self.value),encoding='utf-8')
  with self.assertRaises(ValueError):bootstrap.create(self.profile,self.folder/'invalid')
  self.assertFalse((self.folder/'invalid').exists())
 def test_cached_reads_reload_changed_content(self):
  from read_cache import read_json
  f=self.folder/'cached.json';f.write_text('[1]',encoding='utf-8');self.assertEqual(read_json(f),[1]);f.write_text('[1,2]',encoding='utf-8');self.assertEqual(read_json(f),[1,2])
if __name__=='__main__':unittest.main()
