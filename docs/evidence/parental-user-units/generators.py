import pathlib,subprocess,os,json,pwd,datetime
assert os.geteuid()==0
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
rows=[];created=[]
def run(name,args,env=None):
 p=subprocess.run(args,capture_output=True,text=True,env=env,timeout=20)
 r={'name':name,'argv':args,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr};rows.append(r);print(json.dumps(r),flush=True);return r
start=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
try:
 for path,text in [('/usr/lib/environment.d/90-lyra-fixture.conf','LYRA_GENERATOR_FIXTURE=present\n'),('/etc/xdg/autostart/lyra-approved-fixture.desktop','[Desktop Entry]\nType=Application\nName=Lyra approved fixture\nExec=/opt/lyra-parental-probe/probe\n'),('/etc/xdg/autostart/lyra-generator-fixture.desktop','[Desktop Entry]\nType=Application\nName=Lyra fixture\nExec=/usr/bin/python3 -c "print(42)"\n')]:
  p=pathlib.Path(path);assert p.parent.is_dir() and not p.exists(),p
  p.write_text(text);created.append(p);subprocess.run(['restorecon',str(p)],check=True)
 run('labels',['ls','-ldZ','/usr/lib/environment.d','/etc/xdg/autostart'])
 subprocess.run(['setenforce','1'],check=True)
 assert run('manager-start',['systemctl','start','user@1003.service'])['rc']==0
 env=dict(os.environ,HOME='/home/parentaltest',XDG_RUNTIME_DIR='/run/user/1003',DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1003/bus')
 r=run('environment',['python3','/root/lyra-parental-pam-probe.py','parentaltest','/opt/lyra-parental-probe/probe','/usr/bin/systemctl','--user','show-environment'],env)
 assert r['rc']==0 and 'LYRA_GENERATOR_FIXTURE=present' in r['stdout'],r
 r=run('environment-generator-direct',['python3','/root/lyra-parental-pam-probe.py','parentaltest','/opt/lyra-parental-probe/probe','/usr/lib/systemd/user-environment-generators/30-systemd-environment-d-generator'],env)
 assert r['rc']==0 and 'LYRA_GENERATOR_FIXTURE=present' in r['stdout'],r
 r=run('flatpak-script-negative',['python3','/root/lyra-parental-pam-probe.py','parentaltest','/opt/lyra-parental-probe/probe','/usr/lib/systemd/user-environment-generators/60-flatpak'],env)
 assert r['rc']==126 and 'exec_errno=13' in r['stdout'],r
 generated={str(p):p.read_text() for p in pathlib.Path('/run/user/1003/systemd').glob('generator*/*lyra*') if p.is_file()}
 rows.append({'name':'generated-units','files':generated})
 assert len(generated)==1 and 'ExecStart=:/opt/lyra-parental-probe/probe' in next(iter(generated.values())),generated
 run('journal',['journalctl','-u','user@1003.service','--since',start,'--no-pager'])
 run('kernel',['journalctl','-k','-n','50','--no-pager'])
 assert pathlib.Path('/sys/fs/selinux/enforce').read_text().strip()=='1'
 assert run('manager-stop-enforcing',['systemctl','stop','user@1003.service'])['rc']==0
finally:
 subprocess.run(['setenforce','0'],check=True)
 subprocess.run(['systemctl','stop','user@1003.service'],timeout=20,check=False)
 for p in created:p.unlink()
 pathlib.Path('/root/parental-generators-result.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
