"""Native global-shortcut flow as the ordinary disposable GDM account."""
import hashlib,json,os,pathlib,shlex,shutil,subprocess,sys,threading,time
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
assert P('/sys/block/vda/serial').read_text().strip()=='lyra-virtualization-'
assert not P('/root/lyra-xwayland-recovery/active.json').exists()
backup=P('/root/portal-ordinary-backup');active=backup/'active'
config=P('/etc/gdm/custom.conf');home=P('/home/ordinaryuser')
probe=P('/usr/local/libexec/portal-rpm-shortcuts-probe')
desktop=P('/usr/share/applications/org.lyra.ShortcutsFixture.desktop')
rows=[]
def run(args,check=True):
 p=subprocess.run(args,capture_output=True,text=True,timeout=60)
 rows.append(dict(argv=args,rc=p.returncode,stdout=p.stdout,stderr=p.stderr))
 P('/root/portal-ordinary.json').write_text(json.dumps(rows,indent=2))
 if check:assert p.returncode==0,rows[-1]
 return p.stdout

def recover():
 if not active.exists():return
 subprocess.run(['setenforce','0'],check=True)
 subprocess.run(['systemctl','stop','gdm','user@1002.service'],check=True)
 subprocess.run(['loginctl','terminate-user','ordinaryuser'],capture_output=True)
 shutil.copy2(backup/'custom.conf',config)
 assert home.is_dir() and not home.is_symlink()
 shutil.rmtree(home)
 subprocess.run(['tar','--xattrs','--selinux','--acls','-xpf',str(backup/'home.tar'),'-C','/home'],check=True)
 subprocess.run(['tar','--xattrs','--selinux','--acls','--compare','-f',str(backup/'home.tar'),'-C','/home'],check=True)
 deadline=time.monotonic()+15
 while P('/run/user/1002').exists() and time.monotonic()<deadline:time.sleep(.2)
 assert not P('/run/user/1002').exists()
 for file in [probe,desktop]:file.unlink(missing_ok=True)
 subprocess.run(['rpm','-V','gdm','gnome-control-center','xdg-desktop-portal-gnome'],check=True)
 active.unlink()
 P('/root/portal-ordinary-restored.json').write_text(json.dumps(dict(restored=True,home_restored=True,config_sha256=hashlib.sha256(config.read_bytes()).hexdigest())))
if len(sys.argv)>1 and sys.argv[1]=='recover':recover();raise SystemExit
assert not active.exists() and not probe.exists() and not desktop.exists()
assert P('/sys/fs/selinux/enforce').read_text().strip()=='0'
for unit in ['gdm','user@1002.service','user@1003.service']:
 assert run(['systemctl','is-active',unit],False).strip()=='inactive'
expected=json.loads(P('/root/portal-rpm-expected.json').read_text())
assert run(['rpm','-q','xdg-desktop-portal-gnome']).strip()==expected['nevra']
assert run(['rpm','-V','xdg-desktop-portal-gnome'])==''
assert hashlib.sha256(P('/usr/libexec/xdg-desktop-portal-gnome').read_bytes()).hexdigest()==expected['binary_sha256']
backup.mkdir(exist_ok=True,mode=0o700)
shutil.copy2(config,backup/'custom.conf')
run(['tar','--xattrs','--selinux','--acls','-cpf',str(backup/'home.tar'),'-C','/home','ordinaryuser'])
active.touch();os.sync()
try:
 # Use the same public-API probe, changing only the disposable UID and domain.
 source=P('/root/shortcuts-probe.c').read_text().replace('1003','1002').replace(':lyra_parental_probe_t:',':unconfined_t:')
 P('/root/ordinary-shortcuts-probe.c').write_text(source)
 run(['gcc','-std=c17','-Wall','-Wextra','-Werror','-O2','/root/ordinary-shortcuts-probe.c','-lselinux','-o',str(probe)]+shlex.split(run(['pkg-config','--cflags','--libs','gio-2.0'])))
 desktop.write_text('[Desktop Entry]\nType=Application\nName=Lyra Shortcuts Fixture\nExec='+str(probe)+' activate\nNoDisplay=true\n')
 run(['restorecon',str(probe),str(desktop)])
 config.write_text(config.read_text().replace('[daemon]','[daemon]\nAutomaticLoginEnable=True\nAutomaticLogin=ordinaryuser'))
 run(['setenforce','1']);run(['systemctl','start','gdm']);time.sleep(18)
 base=['runuser','-u','ordinaryuser','--','env','HOME=/home/ordinaryuser','XDG_RUNTIME_DIR=/run/user/1002','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1002/bus']
 run(base+['systemctl','--user','show-environment'])
 # GNOME opens its overview after login; dismiss it before testing dialog keys.
 run(base+['gdbus','call','--session','--dest','org.gnome.Shell','--object-path','/org/gnome/Shell','--method','org.freedesktop.DBus.Properties.Set','org.gnome.Shell','OverviewActive','<false>'])
 time.sleep(1)
 for mode in ['cancel','activate']:
  args=base+['runcon','unconfined_u:unconfined_r:unconfined_t:s0-s0:c0.c1023',str(probe),mode]
  app=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  lines=[]
  def capture():
   for line in app.stdout:
    lines.append(line)
    if line.startswith('phase='):P('/root/input-phase.json').write_text(json.dumps(dict(phase=line.strip().split('=',1)[1])))
  reader=threading.Thread(target=capture);reader.start()
  try:app.wait(timeout=85)
  finally:
   if app.poll() is None:app.kill();app.wait()
   reader.join(timeout=5)
  row=dict(argv=args,rc=app.returncode,stdout=''.join(lines),stderr=app.stderr.read());rows.append(row)
  P('/root/portal-ordinary.json').write_text(json.dumps(rows,indent=2))
  assert row['rc']==0 and 'shortcuts-probe-passed=1' in row['stdout'],row
  P('/root/input-phase.json').write_text('{}')
 run(base+['systemctl','--user','show','xdg-desktop-portal-gnome.service','-p','ActiveState','-p','MainPID','-p','NRestarts'])
 run(['rpm','-V','gdm','gnome-control-center','xdg-desktop-portal-gnome'])
finally:recover()
print('Ordinary account global-shortcut checks passed; restored')
