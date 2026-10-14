"""Upload only fixed native candidate binaries; never replace a release asset."""
import hashlib,json,os,pathlib,re,urllib.request
REPO='lyzbcy/laoyu-software-center-downloads'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args):return None
def publish(root,token):
 receipt=json.loads((root/'native-build-receipt.json').read_text(encoding='utf-8'));version=receipt['version']
 if receipt.get('protocol')!=1 or receipt.get('formal') is not False or not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Invalid native receipt')
 records=receipt['assets'];expected={f'laoyu-software-center-{version}-win-x64.exe',f'laoyu-software-center-{version}-win-x64.zip'}
 if {item['name'] for item in records}!=expected or len(records)!=2:raise ValueError('Unexpected native output set')
 for record in records:
  file=root/record['name'];actual=file.read_bytes()
  if file.is_symlink() or len(actual)!=record['size'] or hashlib.sha256(actual).hexdigest()!=record['sha256']:raise ValueError('Native output changed')
 tag='center-native-20261014-'+receipt['bootstrap']['sha256'][:8]
 if not re.fullmatch(r'center-native-20261014-[a-f0-9]{8}',tag):raise ValueError('Invalid native draft identity')
 def call(suffix,data=None,content='application/json',upload=False):
  url=('https://uploads.github.com/repos/' if upload else 'https://api.github.com/repos/')+REPO+suffix
  request=urllib.request.Request(url,data=data,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Content-Type':content})
  with urllib.request.build_opener(NoRedirect).open(request,timeout=300) as response:return json.load(response)
 matches=[r for r in call('/releases?per_page=100') if r.get('tag_name')==tag]
 if matches:
  if len(matches)!=1 or matches[0].get('draft') is not True:raise ValueError('Native target is not an unpublished unique draft')
  release=matches[0]
 else:release=call('/releases',json.dumps({'tag_name':tag,'name':'Unpublished native center '+version,'body':'Exact native candidate binaries for acceptance. Not a formal release and does not update latest.','draft':True,'prerelease':True,'make_latest':'false'}).encode())
 files=[root/name for name in sorted(expected)]+[root/f'SHA256SUMS-{version}.txt',root/'native-build-receipt.json']
 published=[]
 for file in files:
  data=file.read_bytes();sha=hashlib.sha256(data).hexdigest();existing=[a for a in release.get('assets',[]) if a['name']==file.name]
  if existing:
   if len(existing)!=1 or existing[0]['size']!=len(data) or existing[0].get('digest')!='sha256:'+sha:raise ValueError('Existing candidate asset differs; never replace it')
   asset=existing[0]
  else:asset=call('/releases/'+str(release['id'])+'/assets?name='+file.name,data,'application/octet-stream',upload=True)
  if asset['size']!=len(data) or asset.get('digest')!='sha256:'+sha:raise ValueError('Uploaded native asset fingerprint differs')
  published.append({key:asset[key] for key in ['id','name','size','digest']})
 (root/'native-draft-upload.json').write_text(json.dumps({'protocol':1,'draft':True,'tag':tag,'releaseId':release['id'],'assets':published},indent=2),encoding='utf-8')
 print('NATIVE_CANDIDATE_DRAFT '+tag)
if __name__=='__main__':publish(pathlib.Path(os.environ['RUNNER_TEMP']).resolve()/'center-built',os.environ.pop('GITHUB_TOKEN'))
