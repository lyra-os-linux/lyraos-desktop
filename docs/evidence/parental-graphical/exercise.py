import pathlib,subprocess,json,os,datetime,time
assert os.geteuid()==0
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
rows=[];created=[];checks=[];ctx='lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
def run(name,args,env=None):
 p=subprocess.run(args,capture_output=True,text=True,env=env,timeout=20)
 r={'name':name,'argv':args,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr};rows.append(r);print(json.dumps(r),flush=True);return r
def call(*args):
 env=dict(os.environ,HOME='/home/parentaltest',XDG_RUNTIME_DIR='/run/user/1003',DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1003/bus')
 return run('restricted-'+args[0],['python3','/root/lyra-parental-pam-probe.py','parentaltest','/opt/lyra-parental-probe/probe','/usr/bin/systemctl','--user',*args],env)
def create(path,text):
 p=pathlib.Path(path);assert not p.exists(),p;p.write_text(text);created.append(p);subprocess.run(['restorecon',str(p)],check=True)
start=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
try:
 create('/etc/systemd/user/lyra-graphical-fixture.target','[Unit]\nDescription=Disposable graphical dependency fixture\nRequires=graphical-session.target\nWants=xdg-desktop-autostart.target\nAfter=graphical-session.target\n')
 for name,command,extra in [('approved','/opt/lyra-parental-probe/probe',''),('conditional','/opt/lyra-parental-probe/probe','OnlyShowIn=GNOME;\n'),('hidden','/opt/lyra-parental-probe/probe','OnlyShowIn=KDE;\n'),('python','/usr/bin/python3 -c "print(42)"',''),('indirect','/opt/lyra-parental-probe/probe /usr/bin/python3 -c "print(42)"','')]:
  create('/etc/xdg/autostart/lyra-graphical-'+name+'.desktop','[Desktop Entry]\nType=Application\nName=Lyra '+name+' fixture\nExec='+command+'\n'+extra)
 subprocess.run(['setenforce','1'],check=True)
 assert run('manager-start',['systemctl','start','user@1003.service'])['rc']==0
 assert call('set-environment','XDG_CURRENT_DESKTOP=GNOME')['rc']==0
 generated={str(p):p.read_text() for p in pathlib.Path('/run/user/1003/systemd').glob('generator*/*lyra*') if p.is_file()}
 rows.append({'name':'generated-units','files':generated})
 assert len(generated)==4,generated
 assert call('start','lyra-graphical-fixture.target')['rc']==0
 time.sleep(.4)
 units={}
 for path,content in generated.items():
  for name in ['approved','conditional','hidden','indirect']:
   if 'SourcePath=/etc/xdg/autostart/lyra-graphical-'+name+'.desktop' in content:units[name]=pathlib.Path(path).name
 assert set(units)=={'approved','conditional','hidden','indirect'},units
 for name,unit in units.items():
  r=run(name+'-child',['journalctl','_SYSTEMD_USER_UNIT='+unit,'_UID=1003','--since',start,'--no-pager'])
  if name in ['approved','conditional']:passed='uid=1003 context='+ctx in r['stdout']
  elif name=='hidden':passed='uid=1003 context=' not in r['stdout']
  else:passed='exec_errno=13' in r['stdout'] and 'uid=1003 context='+ctx in r['stdout']
  checks.append({'name':name,'passed':passed})
 r=run('session-journal',['journalctl','-u','user@1003.service','--since',start,'--no-pager'])
 checks.append({'name':'hidden-condition-skipped','passed':any(units['hidden'] in l and ('skipped' in l.lower() or 'condition' in l.lower()) for l in r['stdout'].splitlines())})
 assert pathlib.Path('/sys/fs/selinux/enforce').read_text().strip()=='1'
 assert run('manager-stop-enforcing',['systemctl','stop','user@1003.service'])['rc']==0
finally:
 subprocess.run(['setenforce','0'],check=True)
 subprocess.run(['systemctl','stop','user@1003.service'],timeout=20,check=False)
 for p in created:p.unlink()
 pathlib.Path('/root/parental-graphical-result.json').write_text(json.dumps({'full_gnome_session':False,'checks':checks,'commands':rows},indent=2)+'\n')
assert checks and all(c['passed'] for c in checks),checks
