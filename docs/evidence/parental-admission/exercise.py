import pathlib,subprocess,json
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
records=[]
def cmd(args):subprocess.run(args,check=True,timeout=90)
def test(name,user='parentaltest',expected=70,approved=False):
 program=['/opt/lyra-parental-probe/probe'] if approved else ['/usr/bin/python3','-c','print("PAYLOAD_EXECUTED")']
 p=subprocess.run(['python3','/root/lyra-parental-pam-probe.py',user,*program],capture_output=True,text=True,timeout=30)
 row={'name':name,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr};records.append(row);print(json.dumps(row),flush=True)
 assert p.returncode==expected,row
 if expected:assert 'PAYLOAD_EXECUTED' not in p.stdout,row
 if approved:assert 'uid=1003 context=lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0' in p.stdout,row
cmd(['setenforce','1'])
try:
 test('guard-approved',expected=0,approved=True)
 test('guard-python',expected=126)
 test('ordinary-healthy',user='ordinaryuser',expected=0)
 cmd(['semanage','login','-d','parentaltest'])
 try:
  test('missing-mapping-denied')
  test('ordinary-with-other-mapping-missing',user='ordinaryuser',expected=0)
 finally:cmd(['semanage','login','-a','-s','lyra_parental_u','-r','s0','parentaltest'])
 cmd(['setenforce','0'])
 try:test('global-permissive-denied')
 finally:cmd(['setenforce','1'])
 cmd(['semanage','permissive','-a','lyra_parental_probe_t'])
 try:test('domain-permissive-denied')
 finally:cmd(['semanage','permissive','-d','lyra_parental_probe_t'])
 cmd(['groupmod','-n','parentaltest-unavailable','parentaltest'])
 try:
  test('missing-registry-denied')
  test('missing-registry-ordinary-preserved',user='ordinaryuser',expected=0)
 finally:cmd(['groupmod','-n','parentaltest','parentaltest-unavailable'])
 module=pathlib.Path('/usr/lib64/security/pam_lyra_fixture_guard.so');backup=module.with_suffix('.so.disabled')
 module.rename(backup)
 try:test('missing-guard-module-denied')
 finally:backup.rename(module)
 test('recovery-approved',expected=0,approved=True)
 test('recovery-ordinary',user='ordinaryuser',expected=0)
finally:
 cmd(['setenforce','0'])
 pathlib.Path('/root/parental-admission-result.json').write_text(json.dumps({'kind':'dedicated-pam-session-fixture','full_account_protection':False,'checks':records},indent=2)+'\n')
