'use strict';
// Fixed public acceptance wiring only; product implementation is never overlaid.
const fs=require('node:fs'),fsp=fs.promises,path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),cp=require('node:child_process'),assert=require('node:assert/strict');
const REF='e315098a00a33e6d8a4642ac51d093ebc0e7e61d';
const CENTER={version:'0.8.12',name:'laoyu-software-center-0.8.12-win-x64.zip',size:106252582,sha256:'a270c417b2d5d802e873627a3bae1150c81d3c012e3ad518efc1f8f9c3e7a417',repo:'lyzbcy/laoyu-software-center-downloads'};
const CLEANER={version:'2.0.0',name:'laoyu-disk-cleaner-2.0.0-win-x64.zip',size:157456167,sha256:'f7cc129546f6a0360c83bd1942739c1bcc6ab113213b5dd60707bc42391a106e',repo:'lyzbcy/laoyu-disk-cleaner-downloads'};
const PINS={'cleaner-owned-desktop-runner.ps1':'dae9552b0530faedc0fd677f89417f9a928dcc6c29b9b2288ebea99f542cd3c0','cleaner-owned-desktop.cs':'c96440acff37314d43e88c53ca8eb6c89fdb491a7f3f6e65165f4159da0ad097','cleaner-restricted-probe.ps1':'a286a8de83877539ab49c8984def2b3f3accaa7c0d80965c1e513a463131dcb3','cleaner-restricted-probe.cs':'5ad724517206c16661c6eff911f7b63cb81705f8837efab91bd395794790027e'};
const digest=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
function verifyBytes(bytes,entry){assert(bytes.length===entry.size&&digest(bytes)===entry.sha256,'FROZEN_ORIGINAL_BYTES_DIFFER');}
function replaceExact(source,from,to,count=1){assert.equal(source.split(from).length-1,count,'PINNED_SELECTOR_SHAPE');return source.split(from).join(to);}
function stageRunner(bytes){
 assert.equal(digest(bytes),PINS['cleaner-owned-desktop-runner.ps1'],'PINNED_RUNNER_SOURCE');let s=bytes.toString('utf8');
 s=replaceExact(s,'[switch]$FullSuite)','[switch]$FullSuite, [switch]$CenterCleanerSuite)');
 s=replaceExact(s,'bool fullSuite)','bool fullSuite,bool centerCleanerSuite)',2);
 s=replaceExact(s,'fullSuite?"cleaner-owned-suite.cjs":"cleaner-owned-desktop-probe.cjs"','centerCleanerSuite?"center-cleaner-controller.cjs":fullSuite?"cleaner-owned-suite.cjs":"cleaner-owned-desktop-probe.cjs"',2);
 s=replaceExact(s,'TargetFileAccess(token,node,project,fullSuite)','TargetFileAccess(token,node,project,fullSuite,centerCleanerSuite)');
 s=replaceExact(s,'Diagnostic["scope"]=fullSuite?','Diagnostic["scope"]=centerCleanerSuite?"frozen center to formal cleaner original-byte ordinary-profile chain":fullSuite?');
 s=replaceExact(s,'fullSuite?900000u:360000u','centerCleanerSuite?3600000u:fullSuite?900000u:360000u');
 s=replaceExact(s,'$grantOutput, [bool]$FullSuite)','$grantOutput, [bool]$FullSuite, [bool]$CenterCleanerSuite)');
 return Buffer.from(s);
}
function assertIdentity(i,env,home){
 const nonce=env.CLEANER_CI_DESKTOP_NONCE;assert.match(nonce||'',/^[0-9a-f]{32}$/);const groups=i.groups.filter(g=>(((g.attributes>>>0)&0xc0000000)>>>0)===0xc0000000);assert.equal(groups.length,1);assert.equal(groups[0].sid,env.CLEANER_CI_EXPECTED_LOGON_SID);assert((groups[0].attributes&4)!==0&&(groups[0].attributes&16)===0);
 assert.equal(i.user,env.CLEANER_CI_EXPECTED_SID);assert.equal(i.owner,i.user);assert.equal(i.integrity,'S-1-16-8192');assert.equal(i.adminMember,false);assert.equal(i.elevated,false);assert.equal(i.session,Number(env.CLEANER_CI_PARENT_SESSION));assert(i.session>0);assert.equal(i.windowStation,'WinSta0');assert.equal(i.desktop,'LaoyuCleaner_'+nonce);assert.equal(i.profile,env.CLEANER_CI_OS_PROFILE);assert.equal(home,i.profile);
}
function ps(args){return cp.execFileSync(path.join(process.env.SystemRoot,'System32/WindowsPowerShell/v1.0/powershell.exe'),['-NoProfile','-NonInteractive',...args],{encoding:'utf8',timeout:300000,windowsHide:true});}
function expand(file,dest){const q=s=>"'"+s.replaceAll("'","''")+"'";const script="$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';$env:PSModulePath=(Join-Path $PSHOME 'Modules')+';'+[Environment]::GetEnvironmentVariable('PSModulePath','Machine');Expand-Archive -LiteralPath "+q(file)+' -DestinationPath '+q(dest);ps(['-EncodedCommand',Buffer.from(script,'utf16le').toString('base64')]);}
async function download(entry,file){
 let url=`https://github.com/${entry.repo}/releases/download/v${entry.version}/${entry.name}`,response;
 for(let i=0;i<6;i++){const u=new URL(url);assert(u.protocol==='https:'&&['github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'].includes(u.hostname)&&!u.username&&!u.password,'PUBLIC_ASSET_REDIRECT');response=await fetch(url,{redirect:'manual',headers:{'User-Agent':'laoyu-center-ordinary-proof'}});if([301,302,303,307,308].includes(response.status)){url=new URL(response.headers.get('location'),url).href;continue;}break;}
 assert(response.ok&&response.body,'PUBLIC_ASSET_HTTP');const handle=await fsp.open(file,'wx');let size=0,hash=crypto.createHash('sha256');try{for await(const chunk of response.body){size+=chunk.length;assert(size<=entry.size,'PUBLIC_ASSET_OVERSIZE');hash.update(chunk);await handle.writeFile(chunk);}}finally{await handle.close();}assert(size===entry.size&&hash.digest('hex')===entry.sha256,'PUBLIC_ASSET_FINGERPRINT');
}
async function prepare(){
 assert(process.platform==='win32'&&process.env.GITHUB_ACTIONS==='true'&&process.env.CI==='true');const workspace=fs.realpathSync(process.env.GITHUB_WORKSPACE),root=path.join(workspace,'ordinary-env');assert.equal(fs.realpathSync(root),root);
 for(const [name,sha]of Object.entries(PINS))assert.equal(digest(await fsp.readFile(path.join(root,'scripts',name))),sha,'PINNED_ENVIRONMENT_SOURCE');
 const input=path.join(root,'center-input');await fsp.mkdir(input);await download(CENTER,path.join(input,CENTER.name));await download(CLEANER,path.join(input,CLEANER.name));
 expand(path.join(input,CLEANER.name),path.join(root,'candidate'));const production=await require(path.join(root,'scripts/candidate-bootstrap.cjs')).copyProduction(path.join(root,'candidate/resources/app'),root);
 await fsp.mkdir(path.join(root,'verification/core'),{recursive:true});await fsp.writeFile(path.join(root,'verification/core/center-bridge-preparation.json'),JSON.stringify({environmentRef:REF,environmentPins:PINS,center:CENTER,cleaner:CLEANER,productionCopy:production,scope:'original cleaner modules copied only into independent ordinary-env; original center ZIP remains immutable'},null,2));
 await fsp.writeFile(path.join(root,'scripts/center-owned-desktop-runner.ps1'),stageRunner(await fsp.readFile(path.join(root,'scripts/cleaner-owned-desktop-runner.ps1'))),{flag:'wx'});
 for(const name of ['bridge.cjs','controller.cjs'])await fsp.copyFile(path.join(__dirname,name),path.join(root,'scripts',name==='controller.cjs'?'center-cleaner-controller.cjs':'center-cleaner-bridge.cjs'),fs.constants.COPYFILE_EXCL);
 console.log('CENTER_ORDINARY_BRIDGE_PREPARED; no product started');
}
async function collectEvidence(temp,dest){
 await fsp.mkdir(dest,{recursive:true});
 for(const name of await fsp.readdir(temp)){if(!name.startsWith('center-laoyu-disk-cleaner-'))continue;const root=path.join(temp,name);await fsp.cp(root,path.join(dest,name),{recursive:true,errorOnExist:true,force:false,filter:async(file)=>{const stat=await fsp.lstat(file);assert(!stat.isSymbolicLink(),'EVIDENCE_LINK_REJECTED');return stat.isDirectory()||/\.(json|jsonl|png|log)$/.test(file);}});}
}
module.exports={REF,CENTER,CLEANER,PINS,digest,verifyBytes,stageRunner,assertIdentity,ps,expand,prepare,collectEvidence};
if(require.main===module){if(process.argv[2]!=='prepare')throw Error('FIXED_PREPARE_MODE');prepare().catch(()=>{console.error('CENTER_BRIDGE_PREPARATION_FAILED');process.exitCode=1;});}
