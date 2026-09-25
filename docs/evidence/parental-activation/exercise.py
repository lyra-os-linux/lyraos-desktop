import pathlib,subprocess,json,os,pwd,datetime,time,hashlib,uuid
assert os.geteuid()==0
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
rows=[];created=[];ctx='lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0';checks=[]
def run(name,args,env=None,timeout=15):
 try:
  p=subprocess.run(args,capture_output=True,text=True,env=env,timeout=timeout)
  r={'name':name,'argv':args,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 except subprocess.TimeoutExpired:r={'name':name,'argv':args,'rc':124,'stdout':'','stderr':'test timeout'}
 rows.append(r);print(json.dumps(r),flush=True);return r
def client(user,tool,args):
 a=pwd.getpwnam(user);env=dict(os.environ,HOME=a.pw_dir,XDG_RUNTIME_DIR=f'/run/user/{a.pw_uid}',DBUS_SESSION_BUS_ADDRESS=f'unix:path=/run/user/{a.pw_uid}/bus')
 if user=='parentaltest':prefix=['python3','/root/lyra-parental-pam-probe.py',user,'/opt/lyra-parental-probe/probe',('/opt/lyra-parental-probe/busctl' if tool=='busctl' else '/usr/bin/systemctl')]
 else:prefix=['runuser','-u',user,'--','/usr/bin/'+tool]
 return run(user+'-'+tool+'-'+args[-1],prefix+['--user',*args],env)
def record(name,passed):checks.append({'name':name,'passed':bool(passed)})
start=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
try:
 for name,exe in [('Approved','bus-service'),('Denied','unapproved-bus-service')]:
  p=pathlib.Path('/usr/share/dbus-1/services')/('org.lyra.Fixture.'+name+'.service');assert not p.exists(),p
  p.write_text('[D-BUS Service]\nName=org.lyra.Fixture.'+name+'\nExec=/opt/lyra-parental-probe/'+exe+' org.lyra.Fixture.'+name+'\n');created.append(p)
  subprocess.run(['restorecon',str(p)],check=True)
 assert hashlib.sha256(pathlib.Path('/opt/lyra-parental-probe/bus-service').read_bytes()).digest()==hashlib.sha256(pathlib.Path('/opt/lyra-parental-probe/unapproved-bus-service').read_bytes()).digest()
 subprocess.run(['setenforce','1'],check=True)
 for user,uid in [('parentaltest',1003),('ordinaryuser',1002)]:
  r=run(user+'-manager-start',['systemctl','start',f'user@{uid}.service']);record(user+'-manager',r['rc']==0)
  for name in ('Approved','Denied'):
   r=client(user,'busctl',['--timeout=5s','--','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','StartServiceByName','su','org.lyra.Fixture.'+name,'0'])
   record(user+'-dbus-'+name,(r['rc']==0)==(user=='ordinaryuser' or name=='Approved'))
  for name,argv,escape in [('approved',['/opt/lyra-parental-probe/probe'],False),('python',['/usr/bin/python3','-c','print(42)'],False),('context',['/opt/lyra-parental-probe/probe'],True)]:
   unit='lyra-transient-'+name+'-'+uuid.uuid4().hex+'.service'
   props=['3' if not escape else '4','Type','s','oneshot','RemainAfterExit','b','true','ExecStart','a(sasb)','1',argv[0],str(len(argv)),*argv,'false']
   if escape:props+=['SELinuxContext','s','unconfined_u:unconfined_r:unconfined_t:s0']
   r=client(user,'busctl',['--timeout=5s','--','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','StartTransientUnit','ssa(sv)a(sa(sv))',unit,'fail',*props,'0'])
   if r['rc']==0:
    for _ in range(20):
     state=client(user,'systemctl',['show',unit,'-p','ActiveState','-p','Result','-p','ExecMainStatus'])
     if 'ActiveState=activating' not in state['stdout']:break
     time.sleep(.1)
    success='ActiveState=active' in state['stdout'] and 'ExecMainStatus=0' in state['stdout']
    if name=='context':
     child=run(user+'-context-child',['journalctl','_SYSTEMD_USER_UNIT='+unit,'_UID='+str(uid),'--since',start,'--no-pager'])
     safe=(('ExecMainStatus=229' in state['stdout']) or (success and 'uid=1003 context='+ctx in child['stdout']))
     record(user+'-transient-'+name,safe if user=='parentaltest' else success)
    else:record(user+'-transient-'+name,success if (name=='approved' or user=='ordinaryuser') else 'ExecMainStatus=203' in state['stdout'])
   else:record(user+'-transient-'+name,name=='context' and 'Access denied' in r['stderr'])
  r=run(user+'-journal',['journalctl','-u',f'user@{uid}.service','--since',start,'--no-pager'])
  if user=='parentaltest':
   record('no-unknown-classes','Unknown class' not in r['stdout'])
   record('approved-service-confined','uid=1003 context='+ctx+' name=org.lyra.Fixture.Approved' in r['stdout'])
   record('unapproved-service-exec-denied',any('org.lyra.Fixture.Denied' in l and '203/EXEC' in l for l in r['stdout'].splitlines()))
  assert pathlib.Path('/sys/fs/selinux/enforce').read_text().strip()=='1'
  r=run(user+'-stop-enforcing',['systemctl','stop',f'user@{uid}.service'],timeout=12);record(user+'-stop-enforcing',r['rc']==0)
  r=run(user+'-stop-state',['systemctl','show',f'user@{uid}.service','-p','ActiveState','-p','MainPID'])
  record(user+'-inactive','ActiveState=inactive' in r['stdout'] and 'MainPID=0' in r['stdout'])
finally:
 subprocess.run(['setenforce','0'],check=True)
 for uid in (1003,1002):
  r=run('cleanup-'+str(uid),['systemctl','stop',f'user@{uid}.service'],timeout=12)
  if r['rc']==124:subprocess.run(['systemctl','kill','--signal=KILL',f'user@{uid}.service'],check=False)
 for p in created:p.unlink()
 pathlib.Path('/root/parental-activation-result.json').write_text(json.dumps({'checks':checks,'commands':rows,'full_account_protection':False},indent=2)+'\n')
print(json.dumps({'checks':checks},indent=2))
assert checks and all(c['passed'] for c in checks),checks
