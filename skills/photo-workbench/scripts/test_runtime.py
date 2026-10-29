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
  self.value=dict(purpose='synthetic collection',source_roots=[str(self.folder/'incoming')],stages=['incoming','editing','archived'],review_kinds=['selection'],update_trigger='manual_message',collections=[dict(id='themes',title='Synthetic themes',description='User-confirmed test grouping')],confirmed_by_user=True)
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
   body=dict(revision=0,scope='workflow',text='Synthetic feedback preserved verbatim.')
   self.assertEqual(call('/api/v2/suggestion',body,state['token'])[0],200);self.assertEqual(call('/api/v2/suggestion',body,state['token'])[0],409);self.assertEqual(call('/api/v2/suggestion',body)[0],403)
   self.assertEqual(call('/api/v2/learning')[1]['suggestions'][0]['text'],body['text']);ctx=runtime.fb.context(app/'data');self.assertEqual(ctx['pending_feedback'][0]['payload']['text'],body['text']);self.assertFalse(ctx['active_rules'])
  finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
