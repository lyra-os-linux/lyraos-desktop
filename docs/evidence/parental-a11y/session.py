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
  run(['runuser','-u','parentaltest','--','env','DISPLAY='+selected['DISPLAY'],'XAUTHORITY='+selected['XAUTHORITY'],'runcon','system_u:system_r:lyra_parental_probe_t:s0','/opt/lyra-parental-probe/probe','/opt/lyra-parental-probe/xwindow-test'])
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
  run(['runuser','-u','parentaltest','--','env','XDG_RUNTIME_DIR=/run/user/1003','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/bus','systemctl','--user','show','gnome-session-initialized.target','gnome-session-x11-services-ready.target','org.gnome.SettingsDaemon.XSettings.service','-p','ActiveState','-p','SubState','-p','Job','-p','MainPID','-p','NRestarts','-p','ExecMainStatus'])
  # Observe the same compositor and native helper across an idle interval.
  first=run(['pgrep','-u','1003','-x','gnome-shell'])
  first_xsettings=run(['pgrep','-u','1003','-x','gsd-xsettings'])
  time.sleep(45)
  last=run(['pgrep','-u','1003','-x','gnome-shell'])
  last_xsettings=run(['pgrep','-u','1003','-x','gsd-xsettings'])
  stable=all(p.returncode==0 for p in [first,first_xsettings,last,last_xsettings]) and first.stdout==last.stdout and first_xsettings.stdout==last_xsettings.stdout and len(first.stdout.splitlines())==len(first_xsettings.stdout.splitlines())==1
  rows.append(dict(argv=['fixture','continuity-45s'],rc=0 if stable else 1,stdout=json.dumps(dict(shell_before=first.stdout,shell_after=last.stdout,xsettings_before=first_xsettings.stdout,xsettings_after=last_xsettings.stdout)),stderr='Short diagnostic interval, not prolonged stability qualification'))
  run(['runuser','-u','parentaltest','--','env','DISPLAY='+selected['DISPLAY'],'XAUTHORITY='+selected['XAUTHORITY'],'runcon','system_u:system_r:lyra_parental_probe_t:s0','/opt/lyra-parental-probe/probe','/usr/bin/xprop','-root','RESOURCE_MANAGER'])
 else:
  rows.append(dict(argv=['fixture','x11-client-unavailable'],rc=1,stdout='',stderr='display variables missing'))
 run(['runuser','-u','parentaltest','--','runcon','system_u:system_r:lyra_parental_probe_t:s0','/opt/lyra-parental-probe/probe','/usr/libexec/lyra/parental-services-probe'])
 # Fixed native GSettings/dconf operations use the real restricted session bus.
 base=['runuser','-u','parentaltest','--','env','HOME=/home/parentaltest','XDG_RUNTIME_DIR=/run/user/1003','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/bus','GSETTINGS_BACKEND=dconf']
 def settings(mode):
  profile='/etc/dconf/profile/lyra-supervised-raw-test' if mode=='raw-write' else '/etc/dconf/profile/lyra-supervised-test'
  return run(base+['DCONF_PROFILE='+profile,'runcon','system_u:system_r:lyra_parental_probe_t:s0','/opt/lyra-parental-probe/probe','/opt/lyra-parental-probe/settings-probe',mode])
 for mode in ['write','read','locked','raw-write','effective','system-write','data-not-code']:settings(mode)
 manager=base+['systemctl','--user']
 run(manager+['show','dconf.service','-p','MainPID','-p','NRestarts','-p','ActiveState','-p','SubState'])
 run(manager+['restart','dconf.service'])
 for mode in ['read','effective']:settings(mode)
 run(manager+['show','dconf.service','-p','MainPID','-p','NRestarts','-p','ActiveState','-p','SubState'])
 run(['ls','-lZ','/home/parentaltest/.config/dconf','/usr/libexec/dconf-service'])
 # Observe native settings propagation and X11-only AT-SPI discovery.
 run(base+['DCONF_PROFILE=/etc/dconf/profile/lyra-supervised-test','runcon','system_u:system_r:lyra_parental_probe_t:s0','/opt/lyra-parental-probe/probe','/opt/lyra-parental-probe/a11y-settings-probe'])
 run(manager+['show','org.gnome.SettingsDaemon.A11ySettings.service','-p','MainPID','-p','NRestarts','-p','ActiveState','-p','SubState'])
 if selected['DISPLAY'] and selected['XAUTHORITY']:
  run(['runuser','-u','parentaltest','--','env','DISPLAY='+selected['DISPLAY'],'XAUTHORITY='+selected['XAUTHORITY'],'runcon','system_u:system_r:lyra_parental_probe_t:s0','/opt/lyra-parental-probe/probe','/usr/bin/xprop','-root','AT_SPI_BUS'])
  xbase=['runuser','-u','parentaltest','--','env','-u','WAYLAND_DISPLAY','-u','AT_SPI_BUS_ADDRESS','-u','NO_AT_BRIDGE','HOME=/home/parentaltest','XDG_RUNTIME_DIR=/run/user/1003','DISPLAY='+selected['DISPLAY'],'XAUTHORITY='+selected['XAUTHORITY'],'GDK_BACKEND=x11','GSETTINGS_BACKEND=dconf','DCONF_PROFILE=/etc/dconf/profile/lyra-supervised-test']
  domain=['runcon','system_u:system_r:lyra_parental_probe_t:s0','/opt/lyra-parental-probe/probe']
  for extra in [['DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/bus'],['DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/no-session-bus-for-test']]:
   args=xbase+extra+domain+['/usr/etc/xdg/Xwayland-session.d/00-at-spi']
   if extra[0].endswith('/bus'):args+=['--invalid']
   run(args)
  appargs=xbase+['DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/bus']+domain+['/opt/lyra-parental-probe/accessible-app']
  # Pipes inherit the already-tested FIFO permissions; root log files do not.
  import selectors,os,signal
  app=subprocess.Popen(appargs,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  output={'stdout':bytearray(),'stderr':bytearray()}
  try:
   with selectors.DefaultSelector() as poll:
    poll.register(app.stdout,selectors.EVENT_READ,'stdout');poll.register(app.stderr,selectors.EVENT_READ,'stderr')
    deadline=time.monotonic()+10
    while b'accessible-window-ready' not in output['stdout'] and time.monotonic()<deadline and app.poll() is None:
     for key,_ in poll.select(0.1):
      data=os.read(key.fd,4096)
      if data:output[key.data].extend(data)
      else:poll.unregister(key.fileobj)
   ready=b'accessible-window-ready' in output['stdout']
   rows.append(dict(argv=['fixture','gtk-ready'],rc=0 if ready else 1,stdout=output['stdout'].decode(errors='replace'),stderr=output['stderr'].decode(errors='replace')))
   if ready:
    client=xbase+['DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/no-session-bus-for-test']+domain+['/opt/lyra-parental-probe/accessible-client']
    run(client)
    run(xbase+['DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/bus']+domain+['/usr/bin/xprop','-root','-remove','AT_SPI_BUS'])
    rows.append(dict(argv=['fixture','atspi-property-absent'],rc=0,stdout='The following fresh client must fail without either discovery path',stderr=''))
    run(client)
    run(xbase+['DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/bus']+domain+['/usr/etc/xdg/Xwayland-session.d/00-at-spi'])
    run(client)
   stdout,stderr=app.communicate(timeout=45)
   output['stdout'].extend(stdout);output['stderr'].extend(stderr)
  finally:
   if app.poll() is None:
    os.killpg(app.pid,signal.SIGKILL);app.wait(timeout=5)
  rows.append(dict(argv=appargs,rc=app.returncode,stdout=output['stdout'].decode(errors='replace'),stderr=output['stderr'].decode(errors='replace')))
 run(['getenforce']);run(['loginctl','list-sessions']);run(['ps','-eo','uid,pid,label,args'])
 run(['runuser','-u','parentaltest','--','env','XDG_RUNTIME_DIR=/run/user/1003','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/bus','systemctl','--user','--failed','--no-pager'])
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
 run(['journalctl','-b','-u','gdm','--no-pager','--since',started,'--grep','Register|register|session|Session','-n','120'])
 run(['journalctl','-b','--since',started,'--no-pager','--grep','XSettings|xsettings|[Rr]egister.*session','-n','100'])
 run(['journalctl','-b','--since',started,'--no-pager','-n','500']);run(['journalctl','-b','-k','--no-pager','--since',started,'-n','500'])
finally:
 run(['systemctl','stop','gdm']);run(['loginctl','terminate-user','parentaltest']);run(['systemctl','stop','user@1003.service']);run(['setenforce','0'])
 p.write_bytes(p.with_suffix('.conf.lyra-baseline').read_bytes());p.with_suffix('.conf.lyra-baseline').unlink()
 pam.unlink(missing_ok=True)
 run(['loginctl','terminate-user','ordinaryuser'])
print(json.dumps(rows,indent=2))
