"""Recheck the collected signed OBS staging evidence; never mutate a VM."""
import hashlib,json,pathlib,shutil,subprocess,sys,tempfile
import xml.etree.ElementTree as ET
OUT=pathlib.Path(__file__).resolve().parent
BASE=OUT.parent/'parental-shortcuts'
def read(name):return json.loads((OUT/name).read_text())
package=OUT.parents[2]/'packaging/xdg-desktop-portal-gnome'
inputs=read('revised-source-manifest.json')
source=ET.parse(OUT/'source.xml').getroot()
receipt=read('receipt.json')
assert source.get('srcmd5')==receipt['srcmd5']=='077471ed2335bc96dcb5b43fef6e1334'
assert source.get('rev')==receipt['revision']=='2'
assert not receipt['release_promoted'] and not receipt['iso_qualified']
assert {e.get('name') for e in source}==set(inputs)
for name in ['xdg-desktop-portal-gnome.spec','xdg-desktop-portal-gnome.changes','globalshortcuts-success.patch']:
 data=(package/name).read_bytes()
 assert hashlib.sha256(data).hexdigest()==inputs[name]
 assert hashlib.md5(data).hexdigest()==source.find("entry[@name='"+name+"']").get('md5')
for name,digest in json.loads((package/'sources.json').read_text())['inputs'].items():assert inputs[name]==digest
expected=read('expected.json')
assert expected['signed'] is True
assert expected['rpm_sha256']=='9e7f6622e12cc8c343f772b5900d4ca7e4be01c9a20ef9477cf24373e55b1670'
repository=read('signed-repository.json');fingerprint='399218A6E088C4053F4533BE58097F767EDCA82E'
assert repository['metadata_signature']=='verified' and repository['signing_fingerprint']==fingerprint
assert {p['sha256'] for p in repository['packages']}=={expected['rpm_sha256'],'ba84d6486f3b5907c86e0a38e17d93e939e0dbb674cd3ea4754deac256f50a28'}
assert all(p['signature']=='verified' and receipt['srcmd5'] in p['disturl'] for p in repository['packages'])
assert any(p['filename']==expected['nevra']+'.rpm' for p in repository['packages'])
signatures=read('signature-checks.json');assert all(r['rc']==0 for r in signatures)
assert any(fingerprint in r['stdout'] for r in signatures if '--fingerprint' in r['argv'])
assert any(fingerprint in r['stderr'] and 'Good signature' in r['stderr'] for r in signatures if r['argv'][0]=='gpgv')
checks=[r for r in signatures if '--checksig' in r['argv']]
assert len(checks)==2 and all('signatures OK' in r['stdout'] and 'NOKEY' not in r['stdout'] for r in checks)
assert {pathlib.Path(r['argv'][-1]).name for r in checks}=={p['filename'] for p in repository['packages']}
inspection=read('inspection.json')
assert inspection['changed_payload_digests']==['/usr/libexec/xdg-desktop-portal-gnome']
assert inspection['dependency_delta']==dict(removed=[],added=[]) and inspection['scripts_equal']
assert inspection['--requires']['original']==inspection['--requires']['candidate']
transactions=read('transactions.json');assert all(r['rc']==0 for r in transactions)
name='xdg-desktop-portal-gnome';candidate='/root/portal-staging.rpm';lang='/root/portal-staging-lang.rpm'
for argv in [['rpm','-Uvh','--test',candidate,lang],['rpm','-Uvh',candidate,lang],['rpm','-e','--test',name],['rpm','-e',name],['rpm','-ivh',candidate,lang]]:
 assert sum(r['argv']==argv for r in transactions)==1,argv
assert sum(r['argv']==['rpm','-Uvh','--oldpackage','/root/portal-original.rpm'] for r in transactions)==2
assert sum(r['argv']==['rpm','-e',name+'-lang'] for r in transactions)==2
assert set(transactions[-1]['stdout'].splitlines())==set(read('baseline.json')['keys'])
assert transactions[-1]['argv']==['rpm','-qa','gpg-pubkey']
assert any(r['argv']==['rpm','-q','--qf','%{VERSION}-%{RELEASE}',name] and r['stdout']=='48.0-160100.2.1' for r in transactions[-5:])
for mode in ['original','candidate']:
 rows=read('resolver-'+mode+'.json');assert all(r['rc']==0 for r in rows)
 dry=[r for r in rows if '--dry-run' in r['argv']];assert len(dry)==5
 summaries=[ET.fromstring(r['stdout']).find('.//install-summary') for r in dry]
 for i,summary in enumerate(summaries):
  no_change=i<2 or (mode=='candidate' and i==2)
  assert summary.get('packages-to-change')==('0' if no_change else '1')
  selections=summary.findall('.//solvable')
  if no_change:assert not selections
  else:
   kind='to-reinstall' if mode=='candidate' else 'to-upgrade'
   assert summary.find(kind+'/solvable') is not None
   assert all(s.get('name')==name and s.get('repository')=='portal-staging-test' and s.get('edition')=='48.0-160100.2.1.lyra1.160101.1' for s in selections)
 if mode=='original':
  assert 'current vendor' in dry[0]['stdout'] and 'lower priority' in dry[0]['stdout']
  assert 'current vendor' in dry[1]['stdout']
 assert read('resolver-'+mode+'.restored.json')==dict(restored=True,keys_restored=True)
# Regenerate the tested fixture; its sole semantic change checks the installed
# RPM instead of copying an executable compiled outside the package manager.
with tempfile.TemporaryDirectory(prefix='lyra-rpm-qualify-') as directory:
 generated=pathlib.Path(directory)/'fixture'
 subprocess.run([sys.executable,str(OUT.parent/'portal-rpm/prepare-supervised.py'),str(BASE),str(generated)],check=True,capture_output=True)
 manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in generated.iterdir()}
 assert manifest==read('generated-sources.json')
 for file in (OUT/'supervised').iterdir():shutil.copy2(file,generated/file.name)
 subprocess.run([sys.executable,str(generated/'qualify.py'),'signedFull1'],check=True,capture_output=True)
progress=read('supervised/progress-signedFull1.json')
installed=[r for r in progress if r.get('fixture')=='installed-portal-rpm']
assert installed==[dict(fixture='installed-portal-rpm',**expected)]
assert 'Result=success\n' in read('supervised/signedFull1-unit.json')['state']
rows=read('ordinary.json')
probes=[r for r in rows if '/usr/local/libexec/portal-rpm-shortcuts-probe' in r['argv'] and 'runuser' in r['argv']]
assert [r['argv'][-1] for r in probes]==['cancel','activate']
for r in probes:
 assert r['rc']==0 and 'shortcuts-probe-passed=1' in r['stdout']
 assert 'context=unconfined_u:unconfined_r:unconfined_t:s0-s0:c0.c1023 enforcing=1' in r['stdout']
assert 'cancel-left-no-bindings=1' in probes[0]['stdout']
for token in ['BindShortcuts-response=0','foreign-ListShortcuts-denied=1','foreign-BindShortcuts-denied=1','shortcut-signal=Activated','shortcut-signal=Deactivated','closed-session-no-signals=1']:
 assert token in probes[1]['stdout'],token
unit=read('ordinary-unit.json')
assert 'Result=success\n' in unit['state']
assert unit['keys']==['shortcuts-cancel','shortcuts-bind','shortcuts-activate','shortcuts-released']
assert not (OUT/'ordinary-stderr.log').read_text()
assert read('ordinary-restored.json')['restored'] and read('ordinary-restored.json')['home_restored']
assert read('verified-final.json')['passed']
summary=dict(passed=True,rpm_sha256=expected['rpm_sha256'],signed_staging=True,upgrade=True,fresh_install=True,rollback=True,ordinary=True,supervised_full=True,restored=True,solver_characterized=True,automatic_vendor_migration=False,release_promoted=False,iso_qualified=False)
print(json.dumps(summary,indent=2))
