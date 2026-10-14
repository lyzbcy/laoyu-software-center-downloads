import hashlib,importlib.util,io,json,pathlib,tempfile,unittest,unittest.mock
SCRIPT=pathlib.Path(__file__).parents[1]/'.github/scripts/center-publish-native-draft.py'
spec=importlib.util.spec_from_file_location('native_draft',SCRIPT);subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)
class NativeDraftTests(unittest.TestCase):
 def fixture(self,root):
  records=[]
  for extension in ['exe','zip']:
   file=root/f'laoyu-software-center-0.8.12-win-x64.{extension}';file.write_bytes(b'owned-'+extension.encode());records.append({'name':file.name,'size':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
  (root/'SHA256SUMS-0.8.12.txt').write_text('owned immutable sums')
  (root/'native-build-receipt.json').write_text(json.dumps({'protocol':1,'formal':False,'version':'0.8.12','bootstrap':{'sha256':'a'*64},'assets':records}))
 def test_fixed_outputs_upload_and_identical_retry_never_replace(self):
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory);self.fixture(root);assets=[];calls=[]
   class Opener:
    def open(inner,request,timeout):
     calls.append(request);url=request.full_url
     if request.get_method()=='GET':value=[{'id':7,'tag_name':'center-native-20261014-aaaaaaaa','draft':True,'assets':assets}]
     elif url.startswith('https://uploads.github.com/repos/lyzbcy/laoyu-software-center-downloads/releases/7/assets?name='):
      data=request.data;value={'id':len(assets)+1,'name':url.split('?name=')[1],'size':len(data),'digest':'sha256:'+hashlib.sha256(data).hexdigest()};assets.append(value)
     else:raise AssertionError('Unexpected publication endpoint '+url)
     return io.BytesIO(json.dumps(value).encode())
   with unittest.mock.patch.object(subject.urllib.request,'build_opener',return_value=Opener()):subject.publish(root,'owned-test-token');subject.publish(root,'owned-test-token')
   self.assertEqual(len(assets),4);self.assertEqual(sum(request.get_method()=='POST' for request in calls),4);self.assertTrue(all(request.get_method() in ['GET','POST'] for request in calls))
 def test_changed_native_bytes_cannot_contact_publication_api(self):
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory);self.fixture(root);(root/'laoyu-software-center-0.8.12-win-x64.exe').write_bytes(b'changed')
   with unittest.mock.patch.object(subject.urllib.request,'build_opener',side_effect=AssertionError('Network forbidden')):
    with self.assertRaisesRegex(ValueError,'changed'):subject.publish(root,'owned-test-token')
 def test_existing_different_asset_is_never_replaced(self):
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory);self.fixture(root);calls=[]
   class Opener:
    def open(inner,request,timeout):
     calls.append(request);return io.BytesIO(json.dumps([{'id':7,'tag_name':'center-native-20261014-aaaaaaaa','draft':True,'assets':[{'name':'laoyu-software-center-0.8.12-win-x64.exe','size':1,'digest':'sha256:'+'b'*64}]}]).encode())
   with unittest.mock.patch.object(subject.urllib.request,'build_opener',return_value=Opener()):
    with self.assertRaisesRegex(ValueError,'never replace'):subject.publish(root,'owned-test-token')
   self.assertEqual(len(calls),1);self.assertEqual(calls[0].get_method(),'GET')
if __name__=='__main__':unittest.main()
