import pathlib,subprocess,json,time,datetime
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
rows=[]
started=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
def run(a):
 import os,signal
 process=subprocess.Popen(a,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
 try:
  stdout,stderr=process.communicate(timeout=12 if '/usr/bin/xprop' in a else 60)
  rc=process.returncode
 except subprocess.TimeoutExpired:
  os.killpg(process.pid,signal.SIGKILL)
  stdout,stderr=process.communicate(timeout=5)
  rc=124;stderr+='\nfixture timeout (process group terminated)'
 p=subprocess.CompletedProcess(a,rc,stdout,stderr)
 rows.append({'argv':a,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr});print(json.dumps(rows[-1]),flush=True);return p
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

 manager=run(['runuser','-u','parentaltest','--','env','XDG_RUNTIME_DIR=/run/user/1003','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/bus','systemctl','--user','show-environment'])
 environment=dict(l.split('=',1) for l in manager.stdout.splitlines() if '=' in l)
 selected={k:environment.get(k) for k in ['DISPLAY','WAYLAND_DISPLAY','XAUTHORITY']}
 rows.append(dict(argv=['fixture','display-environment'],rc=manager.returncode,stdout=json.dumps(selected),stderr=manager.stderr))
 if selected['DISPLAY'] and selected['XAUTHORITY']:
  run(['runuser','-u','parentaltest','--','env','DISPLAY='+selected['DISPLAY'],'XAUTHORITY='+selected['XAUTHORITY'],'runcon','system_u:system_r:lyra_parental_probe_t:s0','/opt/lyra-parental-probe/probe','/usr/bin/xprop','-root'])
  import re
  logs=pathlib.Path('/tmp/lyra-trusted-shell-test.log').read_text(errors='replace')
  displays=re.findall(r'Using public X11 display ([^,]+), \(using ([^ ]+) for managed services\)',logs)
  if displays:
   public,managed=displays[-1]
   rows.append(dict(argv=['fixture','managed-display-diagnostic'],rc=0,stdout=json.dumps(dict(public=public,managed=managed)),stderr='Not qualification of the public desktop display'))
   client=['runuser','-u','parentaltest','--','env','DISPLAY='+managed,'XAUTHORITY='+selected['XAUTHORITY'],'runcon','system_u:system_r:lyra_parental_probe_t:s0','/opt/lyra-parental-probe/probe','/usr/bin/xprop','-root']
   run(client+['-f','LYRA_PARENTAL_PROBE','8s','-set','LYRA_PARENTAL_PROBE','restricted-client'])
   run(client+['LYRA_PARENTAL_PROBE'])
  run(['runuser','-u','parentaltest','--','env','XDG_RUNTIME_DIR=/run/user/1003','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/bus','systemctl','--user','list-jobs','--no-pager'])
  run(['runuser','-u','parentaltest','--','env','XDG_RUNTIME_DIR=/run/user/1003','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/bus','systemctl','--user','show','gnome-session-initialized.target','gnome-session-x11-services-ready.target','org.gnome.SettingsDaemon.XSettings.service','-p','ActiveState','-p','SubState','-p','Job'])
  time.sleep(3)
 else:
  rows.append(dict(argv=['fixture','x11-client-unavailable'],rc=1,stdout='',stderr='display variables missing'))
 run(['getenforce']);run(['loginctl','list-sessions']);run(['ps','-eo','uid,pid,label,args'])
 run(['runuser','-u','parentaltest','--','env','XDG_RUNTIME_DIR=/run/user/1003','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/bus','systemctl','--user','show','org.gnome.Shell@wayland.service','-p','ExecStart','-p','DropInPaths','-p','Restart','-p','Environment','-p','ActiveState','-p','SubState'])
 observed=[]
 keys={'DCONF_PROFILE','GSETTINGS_BACKEND','GNOME_SHELL_JS','GJS_PATH','GI_TYPELIB_PATH','LD_PRELOAD','LD_LIBRARY_PATH','NOTIFY_SOCKET','XDG_DATA_DIRS','GNOME_SHELL_SESSION_MODE','GSETTINGS_SCHEMA_DIR'}
 for proc in pathlib.Path('/proc').glob('[0-9]*'):
  try:
   if proc.stat().st_uid!=1003 or (proc/'comm').read_text().strip()!='gnome-shell':continue
   env=dict(item.split('=',1) for item in (proc/'environ').read_bytes().decode().split('\0') if '=' in item)
   observed.append({'pid':int(proc.name),'context':(proc/'attr/current').read_text().strip(),'environment':{k:v for k,v in env.items() if k in keys}})
  except (FileNotFoundError,ProcessLookupError):pass
 rows.append({'argv':['fixture','shell-processes'],'rc':0,'stdout':json.dumps(observed),'stderr':''})
 run(['journalctl','-b','-u','gdm','--no-pager','-n','90'])
 run(['journalctl','-b','--since',started,'--no-pager','-n','500']);run(['journalctl','-b','-k','--no-pager','--since',started,'-n','500'])
finally:
 run(['systemctl','stop','gdm']);run(['loginctl','terminate-user','parentaltest']);run(['systemctl','stop','user@1003.service']);run(['setenforce','0'])
 p.write_bytes(p.with_suffix('.conf.lyra-baseline').read_bytes());p.with_suffix('.conf.lyra-baseline').unlink()
 pam.unlink(missing_ok=True)
 run(['loginctl','terminate-user','ordinaryuser'])
print(json.dumps(rows,indent=2))
