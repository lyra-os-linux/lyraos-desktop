import subprocess,pathlib,json,pwd,hashlib
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
records=[]
def run(name,argv):
 p=subprocess.run(argv,capture_output=True,text=True,timeout=30)
 row={'name':name,'argv':argv,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr};records.append(row);print(json.dumps(row),flush=True);return row
assert not pathlib.Path('/etc/rpm/macros.parental-build').exists()
assert run('enforce',['setenforce','1'])['rc']==0
try:
 assert pathlib.Path('/sys/fs/selinux/enforce').read_text().strip()=='1'
 r=run('permissive-domains',['seinfo','--permissive']);assert r['rc']==0 and 'lyra_parental_probe_t' not in r['stdout']
 prefix=['runuser','-u','parentaltest','--','runcon','system_u:system_r:lyra_parental_probe_t:s0','/opt/lyra-parental-probe/probe']
 uid=pwd.getpwnam('parentaltest').pw_uid
 cases=[('approved-probe',[],0),('approved-child',['/opt/lyra-parental-probe/approved'],0),('generic-system-binary',['/usr/bin/true'],126),('copy',['/home/parentaltest/copied-true'],126),('shell',['/usr/bin/bash','-c','true'],126),('interpreter',['/usr/bin/python3','-c','print(42)'],126),('elf-loader',['/usr/lib64/ld-linux-x86-64.so.2','/home/parentaltest/copied-true'],126),('anonymous-executable-memory',['--anon'],126),('executable-mapping',['--map','/home/parentaltest/copied-true'],126)]
 for name,args,expected in cases:
  r=run(name,prefix+args)
  assert r['rc']==expected and f'uid={uid} context=system_u:system_r:lyra_parental_probe_t:s0' in r['stdout'],r
 r=run('same-uid-outside-domain',['runuser','-u','parentaltest','--','/usr/bin/python3','-c','print("outside-domain-ok")']);assert r['rc']==0 and 'outside-domain-ok' in r['stdout']
 r=run('ordinary-account',['runuser','-u','ordinaryuser','--','/usr/bin/python3','-c','print("ordinary-ok")']);assert r['rc']==0 and 'ordinary-ok' in r['stdout']
 result={'kernel':subprocess.check_output(['uname','-r'],text=True).strip(),'enforcing_during_tests':True,'domain_permissive':False,'checks':records,'full_account_protection':False,'gnome_qualified':False,'policy_sha256':hashlib.sha256(pathlib.Path('/tmp/lyra-parental-probe.cil').read_bytes()).hexdigest()}
 pathlib.Path('/tmp/parental-selinux-result.json').write_text(json.dumps(result,indent=2)+'\n')
finally:
 # Boot fixture remains permissive for preparation; each accepted run enforces.
 subprocess.run(['setenforce','0'],check=True)
 pathlib.Path('/tmp/parental-selinux-progress.json').write_text(json.dumps(records,indent=2)+'\n')
