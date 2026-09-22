import pathlib,subprocess,json,os,pwd,datetime,uuid
assert os.geteuid()==0
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
rows=[];checks=[];paths=[]
def run(name,args,env=None):
 p=subprocess.run(args,capture_output=True,text=True,env=env,timeout=20)
 r={'name':name,'argv':args,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr};rows.append(r);print(json.dumps(r),flush=True);return r
def call(user,program,args):
 a=pwd.getpwnam(user);env=dict(os.environ,HOME=a.pw_dir,XDG_RUNTIME_DIR=f'/run/user/{a.pw_uid}',DBUS_SESSION_BUS_ADDRESS=f'unix:path=/run/user/{a.pw_uid}/bus')
 prefix=(['python3','/root/lyra-parental-pam-probe.py',user,'/opt/lyra-parental-probe/probe',program] if user=='parentaltest' else ['runuser','-u',user,'--',program])
 return run(user+'-'+program.split('/')[-1],prefix+args,env)
start=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
subprocess.run(['setenforce','1'],check=True)
try:
 for user,uid in [('parentaltest',1003),('ordinaryuser',1002)]:
  assert run(user+'-manager',['systemctl','start',f'user@{uid}.service'])['rc']==0
  directory=pathlib.Path(f'/run/user/{uid}/systemd/user');unitnames={}
  for name,command in [('approved','/opt/lyra-parental-probe/probe'),('python','/usr/bin/python3 -c "print(42)"'),('context','/opt/lyra-parental-probe/probe\nSELinuxContext=unconfined_u:unconfined_r:unconfined_t:s0')]:
   unit='lyra-written-'+name+'-'+uuid.uuid4().hex+'.service';unitnames[name]=unit;path=directory/unit;paths.append(path)
   r=call(user,'/opt/lyra-parental-probe/unit-writer',[str(directory),unit,command]);assert r['rc']==0,r
   assert path.stat().st_uid==uid
   if user=='parentaltest':assert 'uid=1003 context=lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0' in r['stdout'],r
   assert path.read_text()=='[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart='+command+'\n'
  r=call(user,'/usr/bin/systemctl',['--user','daemon-reload'])
  if user=='ordinaryuser':assert r['rc']==0,r
  else:assert r['rc']!=0 and 'Access denied' in r['stderr'],r
  checks.append({'name':user+'-reload-policy','passed':True})
  r=call(user,'/usr/bin/systemctl',['--user','start','systemd-tmpfiles-setup.service']);assert r['rc']==0,r
  for name,unit in unitnames.items():
   r=call(user,'/usr/bin/systemctl',['--user','start',unit])
   if user=='ordinaryuser':assert r['rc']==0,r
   else:assert r['rc']!=0,r
   checks.append({'name':user+'-'+name,'passed':True})
  journal=run(user+'-journal',['journalctl','-u',f'user@{uid}.service','--since',start,'--no-pager'])
  if user=='parentaltest':
   checks.append({'name':'written-unit-mediation','passed':('tcontext=lyra_parental_u:object_r:user_tmp_t:s0 tclass=service permissive=0' in journal['stdout'])})
  assert pathlib.Path('/sys/fs/selinux/enforce').read_text().strip()=='1'
  r=run(user+'-stop',['systemctl','stop',f'user@{uid}.service']);assert r['rc']==0,r
finally:
 subprocess.run(['setenforce','0'],check=True)
 for uid in (1003,1002):subprocess.run(['systemctl','stop',f'user@{uid}.service'],timeout=20,check=False)
 for p in paths:
  if p.exists():p.unlink()
 pathlib.Path('/root/parental-written-unit-result.json').write_text(json.dumps({'full_account_protection':False,'checks':checks,'commands':rows},indent=2)+'\n')
assert checks and all(c['passed'] for c in checks),checks
