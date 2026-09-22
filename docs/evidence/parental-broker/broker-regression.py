import pathlib,subprocess,json,os,pwd,datetime,hashlib
assert os.geteuid()==0
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
rows=[];context='lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
def run(name,argv,env=None):
 p=subprocess.run(argv,capture_output=True,text=True,timeout=20,env=env)
 r={'name':name,'argv':argv,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr};rows.append(r);print(json.dumps(r),flush=True);return r
def client(user,restricted):
 a=pwd.getpwnam(user);env=dict(os.environ,HOME=a.pw_dir,XDG_RUNTIME_DIR=f'/run/user/{a.pw_uid}',DBUS_SESSION_BUS_ADDRESS=f'unix:path=/run/user/{a.pw_uid}/bus')
 if restricted:args=['python3','/root/lyra-parental-pam-probe.py',user,'/opt/lyra-parental-probe/probe','/opt/lyra-parental-probe/busctl']
 else:args=['runuser','-u',user,'--','/usr/bin/busctl']
 return run(user+('-confined-bus' if restricted else '-outside-domain-bus'),args+['--timeout=5s','--user','list'],env)
start=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
subprocess.run(['setenforce','1'],check=True)
try:
 for u,uid in [('parentaltest',1003),('ordinaryuser',1002)]:
  r=run(u+'-start',['systemctl','start',f'user@{uid}.service']);assert r['rc']==0,r
 r=client('parentaltest',True);assert r['rc']==0 and 'org.freedesktop.systemd1' in r['stdout'] and 'uid=1003 context='+context in r['stdout'],r
 r=client('parentaltest',False);assert r['rc']!=0,r
 r=client('parentaltest',True);assert r['rc']==0 and 'org.freedesktop.systemd1' in r['stdout'],r
 r=client('ordinaryuser',False);assert r['rc']==0 and 'org.freedesktop.systemd1' in r['stdout'],r
 r=run('process-contexts',['ps','-eo','uid,label,args'])
 broker=[l for l in r['stdout'].splitlines() if l.split()[0]=='1003' and ('dbus-broker' in l or '/usr/lib/systemd/systemd --user' in l)]
 assert len(broker)==3 and all(context in l for l in broker),broker
 r=run('security-query-permissions',['sesearch','-A','-s','lyra_parental_probe_t','-c','security'])
 assert 'compute_av' in r['stdout'] and 'compute_create' in r['stdout'] and all(x not in r['stdout'] for x in ['setenforce','load_policy','setbool']),r
 r=run('session-journal',['journalctl','-u','user@1003.service','--since',start,'--no-pager'])
 assert 'Unknown class' not in r['stdout'],r
 assert 'scontext=system_u:system_r:unconfined_service_t:s0' in r['stdout'] and 'tclass=dbus permissive=0' in r['stdout'],r
finally:
 subprocess.run(['setenforce','0'],check=True)
 try:
  for uid in (1003,1002):
   r=run('stop-'+str(uid),['systemctl','stop',f'user@{uid}.service']);assert r['rc']==0,r
 finally:
  pathlib.Path('/root/parental-broker-result.json').write_text(json.dumps({'enforcing_during_tests':True,'full_account_protection':False,'policy_sha256':hashlib.sha256(pathlib.Path('/tmp/lyra-parental-probe.cil').read_bytes()).hexdigest(),'checks':rows},indent=2)+'\n')
