import pathlib,subprocess,json,time,datetime
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
rows=[]
started=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
def run(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=60);rows.append({'argv':a,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr});print(json.dumps(rows),flush=True);return p
p=pathlib.Path('/etc/gdm/custom.conf');pam=pathlib.Path('/etc/pam.d/gdm-autologin')
assert not pam.exists()
try:
 run(['systemctl','stop','gdm'])
 run(['loginctl','terminate-user','ordinaryuser'])
 pam.write_text(pathlib.Path('/usr/lib/pam.d/gdm-autologin').read_text()+'\nsession [success=1 default=ignore] pam_succeed_if.so quiet gid ne 1004\nsession required pam_lyra_fixture_guard.so\n')
 run(['restorecon',str(pam)])
 p.with_suffix('.conf.lyra-baseline').write_bytes(p.read_bytes())
 p.write_text(p.read_text().replace('[daemon]', '[daemon]\nAutomaticLoginEnable=True\nAutomaticLogin=parentaltest'))
 p.write_text(p.read_text().replace('[debug]', '[debug]\nEnable=true'))
 run(['setenforce','1']);run(['systemctl','start','gdm']);time.sleep(15)
 run(['loginctl','list-sessions']);run(['ps','-eo','uid,pid,label,args'])
 run(['runuser','-u','parentaltest','--','env','XDG_RUNTIME_DIR=/run/user/1003','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/bus','systemctl','--user','show','org.gnome.Shell@wayland.service','-p','ExecStart','-p','DropInPaths','-p','Restart','-p','Environment'])
 observed=[]
 keys={'DCONF_PROFILE','GSETTINGS_BACKEND','GNOME_SHELL_JS','GJS_PATH','GI_TYPELIB_PATH','LD_PRELOAD','LD_LIBRARY_PATH','XDG_DATA_DIRS','GNOME_SHELL_SESSION_MODE','GSETTINGS_SCHEMA_DIR'}
 for proc in pathlib.Path('/proc').glob('[0-9]*'):
  try:
   if proc.stat().st_uid!=1003 or (proc/'comm').read_text().strip()!='gnome-shell':continue
   env=dict(item.split('=',1) for item in (proc/'environ').read_bytes().decode().split('\0') if '=' in item)
   observed.append({'pid':int(proc.name),'context':(proc/'attr/current').read_text().strip(),'environment':{k:v for k,v in env.items() if k in keys}})
  except (FileNotFoundError,ProcessLookupError):pass
 rows.append({'argv':['fixture','shell-processes'],'rc':0,'stdout':json.dumps(observed),'stderr':''})
 run(['journalctl','-b','-u','gdm','--no-pager','-n','90'])
 run(['journalctl','-b','--since',started,'--no-pager']);run(['journalctl','-b','-k','--no-pager','--since',started])
finally:
 run(['systemctl','stop','gdm']);run(['loginctl','terminate-user','parentaltest']);run(['systemctl','stop','user@1003.service']);run(['setenforce','0'])
 p.write_bytes(p.with_suffix('.conf.lyra-baseline').read_bytes());p.with_suffix('.conf.lyra-baseline').unlink()
 pam.unlink(missing_ok=True)
 run(['loginctl','terminate-user','ordinaryuser'])
print(json.dumps(rows,indent=2))
