"""Disposable real user-manager activation, including indirect execution negatives."""
import pathlib,subprocess,json,os,pwd,datetime
assert os.geteuid()==0
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
rows=[];created=[];context='lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
units={'approved':'/opt/lyra-parental-probe/probe','generic':'/usr/bin/true','shell':'/usr/bin/bash -c "exit 0"','python':'/usr/bin/python3 -c "print(42)"'}
def run(name,args,env=None):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30,env=env)
 r={'name':name,'argv':args,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr};rows.append(r);print(json.dumps(r),flush=True);return r
def call(user,*args):
 a=pwd.getpwnam(user);env=dict(os.environ,HOME=a.pw_dir,XDG_RUNTIME_DIR=f'/run/user/{a.pw_uid}',DBUS_SESSION_BUS_ADDRESS=f'unix:path=/run/user/{a.pw_uid}/bus')
 if user=='parentaltest':
  argv=['python3','/root/lyra-parental-pam-probe.py',user,'/opt/lyra-parental-probe/probe','/usr/bin/systemctl','--user',*args]
 else:argv=['runuser','-u',user,'--','/usr/bin/systemctl','--user',*args]
 return run(user+'-'+args[0]+'-'+args[-1],argv,env)
try:
 for name,command in units.items():
  p=pathlib.Path('/etc/systemd/user')/f'lyra-parental-{name}-fixture.service'
  assert not p.exists(),p
  p.write_text('[Unit]\nDescription=Disposable Lyra activation fixture\n[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart='+command+'\n');created.append(p)
  subprocess.run(['restorecon',str(p)],check=True)
 subprocess.run(['setenforce','1'],check=True)
 start=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
 for user,uid in [('parentaltest',1003),('ordinaryuser',1002)]:
  r=run(user+'-manager',['systemctl','start',f'user@{uid}.service']);assert r['rc']==0,r
  r=call(user,'show','systemd-tmpfiles-setup.service','-p','Result','-p','ExecMainStatus');assert r['rc']==0 and 'Result=success' in r['stdout'] and 'ExecMainStatus=0' in r['stdout'],r
  for name in units:
   unit=f'lyra-parental-{name}-fixture.service'
   r=call(user,'start',unit)
   allowed=user=='ordinaryuser' or name=='approved'
   assert (r['rc']==0)==allowed,r
   state=call(user,'show',unit,'-p','Result','-p','ExecMainStatus','-p','ActiveState')
   if allowed: assert 'Result=success' in state['stdout'] and 'ExecMainStatus=0' in state['stdout'],state
   else:assert 'ExecMainStatus=203' in state['stdout'],state
  r=run(user+'-journal',['journalctl','-u',f'user@{uid}.service','--since',start,'--no-pager'])
  if user=='parentaltest':assert 'uid=1003 context='+context in r['stdout'],r
  run(user+'-stop',['systemctl','stop',f'user@{uid}.service'])
finally:
 subprocess.run(['setenforce','0'],check=True)
 for uid in (1003,1002):subprocess.run(['systemctl','stop',f'user@{uid}.service'],timeout=45,check=False)
 for p in created:p.unlink()
 pathlib.Path('/root/parental-service-regression.json').write_text(json.dumps({'scope':'user-manager-only','full_account_protection':False,'checks':rows},indent=2)+'\n')
