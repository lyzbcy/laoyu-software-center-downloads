"""Public orchestration only. Candidate implementation remains in authenticated draft assets."""
import hashlib,json,os,pathlib,re,subprocess,urllib.request,urllib.error
REPO='lyzbcy/laoyu-software-center-downloads'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):return None

def metadata(suffix,token):
 request=urllib.request.Request('https://api.github.com/repos/'+REPO+suffix,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Cache-Control':'no-store'})
 with urllib.request.build_opener(NoRedirect).open(request,timeout=60) as response:return json.load(response)
def run(manifest,platform,token):
 if set(manifest)!=(set(['mode','tag','candidates','product'])|({'driver'} if 'driver' in manifest else set())) or manifest['mode'] not in ['import-only','public-product','native-build','installed-update'] or not re.fullmatch(r'center-candidate-\d{8}-[a-f0-9]{8}',manifest['tag']):raise ValueError('Invalid frozen suite')
 if platform not in ['win-x64','mac-arm64','mac-x64']:raise ValueError('Unsupported native host')
 if manifest['mode'] in ['native-build','installed-update'] and platform!='win-x64':raise ValueError('Native builder is Windows-only')
 entry=manifest['candidates'][platform]
 if set(entry)!=set(['version','sha256','size']) or not re.fullmatch(r'\d+\.\d+\.\d+',entry['version']) or not re.fullmatch(r'[a-f0-9]{64}',entry['sha256']) or type(entry['size']) is not int or not 0<entry['size']<1024**3:raise ValueError('Invalid original candidate fingerprint')
 product=manifest['product']
 driver=manifest.get('driver')
 if driver is not None:
  if manifest['mode']!='installed-update' or set(driver)!=set(['name','sha256','size']) or driver['name']!='center-installed-update-driver.zip' or not re.fullmatch(r'[a-f0-9]{64}',driver['sha256']) or type(driver['size']) is not int or not 0<driver['size']<1024*1024:raise ValueError('Invalid external installed driver')
 if manifest['mode']=='public-product':
  if set(product)!=set(['id','version','assets']) or product['id'] not in ['nettools','cleaner'] or not re.fullmatch(r'\d+\.\d+\.\d+',product['version']):raise ValueError('Invalid product')
  frozen=product['assets'][platform]
  if set(frozen)!=set(['sha256','size']) or not re.fullmatch(r'[a-f0-9]{64}',frozen['sha256']) or type(frozen['size']) is not int or not 0<frozen['size']<1024**3:raise ValueError('Invalid original product fingerprint')
 elif manifest['mode']=='installed-update':
  if set(product)!=set(['id','oldVersion','candidate']) or product['id']!='installed-center-update' or not re.fullmatch(r'\d+\.\d+\.\d+',product['oldVersion']) or type(product['candidate']) is not bool or tuple(map(int,product['oldVersion'].split('.')))>=tuple(map(int,entry['version'].split('.'))):raise ValueError('Invalid installed-center update proof')
 elif product is not None:raise ValueError('Import-only has no product claim')
 root=pathlib.Path(os.environ['RUNNER_TEMP']).resolve();downloads=root/'center-candidate-download';downloads.mkdir(mode=0o700,exist_ok=False)
 name=f"laoyu-software-center-{entry['version']}-{platform}.zip";target=downloads/name
 matches=[item for item in metadata('/releases?per_page=100',token) if item.get('tag_name')==manifest['tag'] and item.get('draft') is True]
 if len(matches)!=1:raise ValueError('Exact unpublished draft not uniquely visible to this job token')
 release=matches[0]
 if release.get('draft') is not True or release.get('tag_name')!=manifest['tag']:raise ValueError('Only the exact unpublished candidate draft is allowed')
 assets=[asset for asset in release['assets'] if asset['name']==name]
 if len(assets)!=1 or assets[0]['size']!=entry['size']:raise ValueError('Frozen candidate asset differs')
 asset=assets[0];request=urllib.request.Request('https://api.github.com/repos/'+REPO+'/releases/assets/'+str(asset['id']),headers={'Authorization':'Bearer '+token,'Accept':'application/octet-stream','Cache-Control':'no-store'})
 try:response=urllib.request.build_opener(NoRedirect).open(request,timeout=60)
 except urllib.error.HTTPError as error:
  if error.code not in [301,302,303,307,308]:raise
  url=error.headers.get('Location','');parsed=urllib.parse.urlparse(url)
  if parsed.scheme!='https' or parsed.hostname not in ['release-assets.githubusercontent.com','objects.githubusercontent.com'] or parsed.username or parsed.password:raise ValueError('Unexpected asset redirect')
  response=urllib.request.urlopen(urllib.request.Request(url),timeout=120)
 digest=hashlib.sha256();size=0
 with response,target.open('xb') as output:
  while True:
   chunk=response.read(1024*1024)
   if not chunk:break
   size+=len(chunk)
   if size>entry['size']:raise ValueError('Candidate exceeds frozen size')
   digest.update(chunk);output.write(chunk)
 if size!=entry['size'] or digest.hexdigest()!=entry['sha256']:raise ValueError('Candidate original bytes differ')
 bootstrap=root/'center-candidate-bootstrap';bootstrap.mkdir(mode=0o700)
 if platform.startswith('mac-'):subprocess.run(['/usr/bin/ditto','-x','-k',str(target),str(bootstrap)],check=True)
 else:
  ps=pathlib.Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
  quote=lambda value:"'"+str(value).replace("'","''")+"'"
  code="$ErrorActionPreference='Stop';$env:PSModulePath=(Join-Path $PSHOME 'Modules')+';'+[Environment]::GetEnvironmentVariable('PSModulePath','Machine');Expand-Archive -LiteralPath "+quote(target)+' -DestinationPath '+quote(bootstrap)
  import base64
  subprocess.run([str(ps),'-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(code.encode('utf-16le')).decode()],check=True)
 source=bootstrap/('捞鱼软件中心.app/Contents/Resources/app' if platform.startswith('mac-') else f"捞鱼软件中心-{entry['version']}-win-x64/resources/app")
 package=json.loads((source/'package.json').read_text(encoding='utf-8'))
 if package.get('name')!='laoyu-software-center' or package.get('version')!=entry['version']:raise ValueError('Bootstrap package identity differs')
 env=dict(os.environ,CI='true',RUNNER_TEMP=str(root),CENTER_CANDIDATE_ZIP=str(target),CENTER_CANDIDATE_SHA256=entry['sha256'],CENTER_CANDIDATE_SIZE=str(entry['size']))
 env.pop('GITHUB_TOKEN',None);env.pop('GH_TOKEN',None)
 if manifest['mode']=='import-only':
  # Deliberately poison inherited module search to exercise the fixed Windows child bootstrap.
  if platform=='win-x64':env['PSModulePath']=str(root/'missing-pwsh7-modules')
  code="require('./src/ci-candidate.cjs').importCandidate({centerVersion:require('./package.json').version,platform:process.platform,arch:process.arch}).then(value=>console.log(JSON.stringify({ok:true,gui:false,fingerprint:value.fingerprint}))).catch(error=>{console.error(error.message);process.exitCode=1})"
  subprocess.run(['node','-e',code],cwd=source,env=env,check=True)
 elif manifest['mode']=='native-build':
  # Bootstrap runtime is never claimed as a final version; rebuild from reviewed packaged resources.
  for key in ['CENTER_CANDIDATE_ZIP','CENTER_CANDIDATE_SHA256','CENTER_CANDIDATE_SIZE']:env.pop(key,None)
  subprocess.run(['pnpm','--ignore-workspace','install','--ignore-scripts','--frozen-lockfile'],cwd=source,env=env,check=True,shell=os.name=='nt')
  code="require('./scripts/ci-cleaner-product.cjs').build({platform:'win32',arch:'x64',centerVersion:require('./package.json').version}).catch(error=>{console.error(error.message);process.exitCode=1})"
  subprocess.run(['node','-e',code],cwd=source,env=env,check=True)
  import shutil
  destination=root/'center-built';destination.mkdir(mode=0o700)
  for file in (source/'release').iterdir():
   if file.is_file() and (file.suffix in ['.exe','.zip'] or file.name.startswith('SHA256SUMS-') or file.name=='launcher-update.json'):shutil.copy2(file,destination/file.name)
  expected=[destination/f"laoyu-software-center-{entry['version']}-win-x64.{extension}" for extension in ['exe','zip']]
  if any(not file.is_file() for file in expected):raise ValueError('Native final Windows package set incomplete')
  records=[{'name':file.name,'size':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()} for file in expected]
  (destination/'native-build-receipt.json').write_text(json.dumps({'protocol':1,'formal':False,'version':entry['version'],'bootstrap':entry,'assets':records},indent=2),encoding='utf-8')
 elif manifest['mode']=='installed-update':
  env.update({'GH_TOKEN':token,'E2E_OLD_VERSION':product['oldVersion'],'E2E_NEW_VERSION':entry['version'],'E2E_CANDIDATE_INPUT':str(product['candidate']).lower()})
  import shutil,zipfile,io
  proofSource=source
  if driver is not None:
   matches=[a for a in release['assets'] if a['name']==driver['name']]
   if len(matches)!=1 or matches[0]['size']!=driver['size'] or matches[0].get('digest')!='sha256:'+driver['sha256']:raise ValueError('External driver asset differs')
   request=urllib.request.Request('https://api.github.com/repos/'+REPO+'/releases/assets/'+str(matches[0]['id']),headers={'Authorization':'Bearer '+token,'Accept':'application/octet-stream'})
   try:response=urllib.request.build_opener(NoRedirect).open(request,timeout=60)
   except urllib.error.HTTPError as error:
    if error.code!=302:raise
    url=error.headers.get('Location','');parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in ['release-assets.githubusercontent.com','objects.githubusercontent.com'] or parsed.username or parsed.password:raise ValueError('Unexpected driver redirect')
    response=urllib.request.urlopen(urllib.request.Request(url),timeout=60)
   with response:raw=response.read(driver['size']+1)
   if len(raw)!=driver['size'] or hashlib.sha256(raw).hexdigest()!=driver['sha256']:raise ValueError('External driver original bytes differ')
   archive=zipfile.ZipFile(io.BytesIO(raw));expected={'scripts/ci-installed-update.cjs','scripts/ci-installed-diagnostics.cjs'}
   if set(archive.namelist())!=expected or len(archive.infolist())!=2 or any(item.file_size>1024*1024 or (item.external_attr>>16)&0o170000==0o120000 for item in archive.infolist()):raise ValueError('Unexpected external driver files')
   proofSource=root/'center-installed-proof-driver';shutil.copytree(source,proofSource);archive.extractall(proofSource)
   evidence=proofSource/'.ci-artifacts/windows-installed-update';evidence.mkdir(parents=True)
   (evidence/'external-driver-input.json').write_text(json.dumps({'externalDriver':driver,'sourceCandidate':entry,'draftTag':manifest['tag'],'installedReleaseBytesUnchanged':True,'scope':'External diagnostic-only driver; actual public immutable old/new installers and mandatory native shortcut/UI checks unchanged'},indent=2))
  try:subprocess.run(['node',str(proofSource/'scripts/ci-installed-update.cjs')],cwd=proofSource,env=env,check=True)
  finally:
   evidence=proofSource/'.ci-artifacts/windows-installed-update'
   if evidence.is_dir():shutil.copytree(evidence,root/'center-installed-update-evidence')
 else:
  prefix='NETTOOLS' if product['id']=='nettools' else 'CLEANER'
  env.update({prefix+'_VERSION':product['version'],prefix+'_SHA256':frozen['sha256'],prefix+'_SIZE':str(frozen['size']),'LAOYU_CI_GITHUB_TOKEN':token})
  subprocess.run(['node',str(source/'scripts'/('ci-'+product['id']+'-product.cjs'))],cwd=source,env=env,check=True)
 evidence=root/'center-public-receipt.json';evidence.write_text(json.dumps({'protocol':1,'ok':True,'mode':manifest['mode'],'candidate':entry,'platform':platform,'draftTag':manifest['tag'],'externalDriver':driver,'product':product,'gui':manifest['mode'] in ['public-product','installed-update']},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':
 run(json.loads(os.environ['FROZEN_MANIFEST']),os.environ['NATIVE_PLATFORM'],os.environ.pop('GITHUB_TOKEN'))
