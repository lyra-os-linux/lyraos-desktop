import pathlib,subprocess,json
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
rows=[]
def cmd(a):subprocess.run(a,check=True,timeout=60,capture_output=True,text=True)
def test(name,uid,allowed):
 unit=f'user@{uid}.service'
 cmd(['systemctl','stop',unit]);subprocess.run(['systemctl','reset-failed',unit],capture_output=True)
 p=subprocess.run(['systemctl','start',unit],capture_output=True,text=True,timeout=20)
 s=subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','-p','MainPID','-p','ExecMainStatus'],text=True)
 row={'name':name,'uid':uid,'rc':p.returncode,'state':s,'stderr':p.stderr};rows.append(row);print(json.dumps(row),flush=True)
 try:
  if allowed:assert p.returncode==0 and 'ActiveState=active' in s,row
  else:assert p.returncode!=0 and 'MainPID=0' in s and 'ExecMainStatus=224' in s,row
 finally:cmd(['systemctl','stop',unit])
cmd(['setenforce','1'])
try:
 test('healthy-supervised',1003,True);test('healthy-ordinary',1002,True)
 cmd(['semanage','login','-d','parentaltest'])
 try:test('mapping-missing-supervised',1003,False);test('mapping-missing-ordinary',1002,True)
 finally:cmd(['semanage','login','-a','-s','lyra_parental_u','-r','s0','parentaltest'])
 p=pathlib.Path('/usr/lib64/security/pam_lyra_fixture_guard.so');backup=p.with_suffix('.so.disabled');p.rename(backup)
 try:test('guard-missing-supervised',1003,False);test('guard-missing-ordinary',1002,True)
 finally:backup.rename(p)
 cmd(['groupmod','-n','parentaltest-unavailable','parentaltest'])
 try:test('group-inconsistent-supervised',1003,False);test('group-inconsistent-ordinary',1002,True)
 finally:cmd(['groupmod','-n','parentaltest','parentaltest-unavailable'])
 cmd(['setenforce','0'])
 try:test('permissive-supervised',1003,False);test('permissive-ordinary',1002,True)
 finally:cmd(['setenforce','1'])
 test('recovery-supervised',1003,True);test('recovery-ordinary',1002,True)
finally:
 cmd(['setenforce','0'])
 for uid in [1003,1002]:subprocess.run(['systemctl','stop',f'user@{uid}.service'],timeout=45,check=False)
 pathlib.Path('/root/parental-real-admission.json').write_text(json.dumps({'scope':'systemd-user-only','full_account_protection':False,'checks':rows},indent=2)+'\n')
