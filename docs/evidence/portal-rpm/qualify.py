"""Recheck the exact local RPM, real transactions and both collected sessions."""
import hashlib,json,pathlib,shutil,subprocess,sys,tempfile
OUT=pathlib.Path(__file__).resolve().parent
BASE=OUT.parent/'parental-shortcuts'
def read(name):return json.loads((OUT/name).read_text())
package=OUT.parents[2]/'packaging/xdg-desktop-portal-gnome'
inputs=read('inputs.json')
sources=json.loads((package/'sources.json').read_text())
for name in ['xdg-desktop-portal-gnome.spec','globalshortcuts-success.patch']:
 assert hashlib.sha256((package/name).read_bytes()).hexdigest()==inputs[name]
for name,digest in sources['inputs'].items():assert inputs[name]==digest
expected=read('expected.json');artifacts=read('artifacts.json')
assert expected['signed'] is False
assert expected['rpm_sha256']=='a4a5e1c0ebf5fa35b125e003190869f7c636c365b579d1109cacbf7ae1a43b30'
assert any(a['sha256']==expected['rpm_sha256'] and a['nevra']==expected['nevra'] for a in artifacts)
assert all(r['rc']==0 for r in read('build.json'))
inspection=read('inspection.json')
assert inspection['passed'] and inspection['release_order_validated']
assert inspection['changed_payload_digests']==['/usr/libexec/xdg-desktop-portal-gnome']
assert inspection['dependency_delta']==dict(removed=[],added=['libc.so.6(GLIBC_2.38)(64bit)'],installed_provider='glibc-2.40-160100.2.1.x86_64')
transactions=read('transactions.json')
assert all(r['rc']==0 for r in transactions)
original='/root/portal-original.rpm'
candidate=next(a['path'] for a in artifacts if a['sha256']==expected['rpm_sha256'])
for argv in [['rpm','-Uvh',candidate],['rpm','-e','--test','xdg-desktop-portal-gnome'],['rpm','-e','xdg-desktop-portal-gnome'],['rpm','-ivh',candidate]]:
 assert sum(r['argv']==argv for r in transactions)==1,argv
assert sum(r['argv']==['rpm','-Uvh','--oldpackage',original] for r in transactions)==2
assert transactions[-1]['stdout']=='48.0-160100.2.1'
assert any(r['argv']==['rpm','-K',original] and 'signatures OK' in r['stdout'] for r in transactions)
# Regenerate the tested fixture; its sole semantic change checks the installed
# RPM instead of copying an executable compiled outside the package manager.
with tempfile.TemporaryDirectory(prefix='lyra-rpm-qualify-') as directory:
 generated=pathlib.Path(directory)/'fixture'
 subprocess.run([sys.executable,str(OUT/'prepare-supervised.py'),str(BASE),str(generated)],check=True,capture_output=True)
 manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in generated.iterdir()}
 assert manifest==read('generated-sources.json')
 for file in (OUT/'supervised').iterdir():shutil.copy2(file,generated/file.name)
 subprocess.run([sys.executable,str(generated/'qualify.py'),'rpmFull1'],check=True,capture_output=True)
progress=read('supervised/progress-rpmFull1.json')
installed=[r for r in progress if r.get('fixture')=='installed-portal-rpm']
assert installed==[dict(fixture='installed-portal-rpm',**expected)]
assert 'Result=success\n' in read('supervised/rpmFull1-unit.json')['state']
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
summary=dict(passed=True,rpm_sha256=expected['rpm_sha256'],upgrade=True,fresh_install=True,rollback=True,ordinary=True,supervised_full=True,restored=True,published=False,iso_qualified=False)
print(json.dumps(summary,indent=2))
