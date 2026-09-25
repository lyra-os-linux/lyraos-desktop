import pathlib,subprocess,json,pwd
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
rows=[]
def run(name,args,timeout=40):
 try:
  p=subprocess.run(args,capture_output=True,text=True,timeout=timeout);r={'name':name,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 except subprocess.TimeoutExpired as e:
  r={'name':name,'timeout':True}
 rows.append(r);print(json.dumps(r),flush=True);return r
uids={u:pwd.getpwnam(u).pw_uid for u in ('parentaltest','ordinaryuser')}
# Only fixtures created for these tests; don't stop unrelated user managers.
for u,uid in uids.items():
 p=subprocess.run(['systemctl','is-active',f'user@{uid}.service'],capture_output=True,text=True)
 assert p.stdout.strip()=='inactive',(u,p.stdout)
subprocess.run(['setenforce','1'],check=True)
try:
 for u,uid in uids.items():
  run(u+'-start',['systemctl','start',f'user@{uid}.service'])
  run(u+'-state',['systemctl','show',f'user@{uid}.service','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus','-p','MainPID'])
  run(u+'-journal',['journalctl','-u',f'user@{uid}.service','-n','30','--no-pager'])
 run('process-contexts',['ps','-eo','uid,label,args'])
finally:
 subprocess.run(['setenforce','0'],check=True)
 for uid in uids.values():
  subprocess.run(['systemctl','stop',f'user@{uid}.service'],timeout=45,check=False)
 pathlib.Path('/root/parental-systemd-result.json').write_text(json.dumps({'enforcing_during_tests':True,'full_account_protection':False,'checks':rows},indent=2)+'\n')
