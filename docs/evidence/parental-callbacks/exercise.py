"""Disposable callback test. Requires probe.c at /root/ffi-probe.c and the prior
parental fixture. Never install or execute on a host. See README.md.
"""
import bz2, hashlib, json, os, pathlib, re, shlex, shutil, stat, subprocess
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
worker=P('/usr/libexec/gdm/gdm-session-worker')
helper=P('/usr/libexec/gdm/gdm-wayland-session')
native=P('/usr/libexec/gnome-session-binary')
ctl=P('/usr/libexec/gnome-session-ctl')
shell=P('/usr/bin/gnome-shell')
entry=P('/usr/share/wayland-sessions/gnome.desktop')
application=P('/usr/share/applications/org.gnome.Shell.desktop')
launcher=P('/usr/libexec/lyra/trusted-shell-test')
dropin=P('/etc/systemd/user/org.gnome.Shell@wayland.service.d/99-lyra-trusted-test.conf')
profile=P('/etc/dconf/profile/lyra-supervised-test')
database=P('/etc/dconf/db/lyra-supervised-test')
debuglog=P('/tmp/lyra-trusted-shell-test.log')
private_file=P('/tmp/lyra-ffi-private-test.bin')
keydir=P('/root/lyra-shell-test-db.d')
generated=[launcher,dropin,profile,database,debuglog,private_file,keydir/'00-policy',keydir/'locks/00-policy']
assert all(not p.exists() for p in generated)
original={p:(p.read_bytes(),stat.S_IMODE(p.stat().st_mode),os.getxattr(p,'security.selinux'))
          for p in [worker,helper,native,ctl,shell,entry,application]}
created_dirs=[]
loaded=False
audit_started=False
audit_disabled=False
records=[]
def run(args,timeout=180):
    r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    records.append(dict(argv=args,rc=r.returncode,stdout=r.stdout,stderr=r.stderr))
    P('/root/trusted-shell-progress.json').write_text(json.dumps(records,indent=2))
    assert r.returncode==0,records[-1]
    return r.stdout
def make_parent(path):
    missing=[]
    p=path.parent
    while not p.exists(): missing.append(p);p=p.parent
    for p in reversed(missing):p.mkdir();created_dirs.append(p)
def forms(text):
    text='\n'.join(line.split(';',1)[0] for line in text.splitlines())
    depth=0;start=0
    for i,char in enumerate(text):
        if char=='(':
            if depth==0:start=i
            depth+=1
        elif char==')':
            depth-=1
            if depth==0:yield text[start:i+1]
run(['systemctl','stop','gdm'])
try:
    for p in generated:make_parent(p)
    run(['gcc','-std=gnu17','-Wall','-Wextra','-Werror','-O2',
         '-Wl,-z,relro,-z,now','/root/trusted-shell.c','-lselinux','-o',str(launcher)]
        +shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','gio-2.0'],text=True)))
    launcher.chmod(0o755)
    profile.write_text('user-db:user\nsystem-db:lyra-supervised-test\n')
    (keydir/'00-policy').write_text("[org/gnome/shell]\nallow-extension-installation=false\ndevelopment-tools=false\ndisable-user-extensions=true\n")
    (keydir/'locks/00-policy').write_text('/org/gnome/shell/allow-extension-installation\n/org/gnome/shell/development-tools\n/org/gnome/shell/disable-user-extensions\n')
    run(['dconf','compile',str(database),str(keydir)])
    debuglog.touch();os.chown(debuglog,1003,1004);debuglog.chmod(0o600)
    run(['chcon','-t','user_tmp_t',str(debuglog)])
    dropin.write_text('[Unit]\nStartLimitIntervalSec=60\nStartLimitBurst=1\n[Service]\nRestart=no\nExecStart=\nExecStart=/usr/libexec/lyra/trusted-shell-test\n'
                     'StandardOutput=append:/tmp/lyra-trusted-shell-test.log\nStandardError=inherit\n'
                     'Environment=GNOME_SHELL_JS=/home/parentaltest/untrusted-js GSETTINGS_BACKEND=memory DCONF_PROFILE=/home/parentaltest/untrusted-profile\n')
    run(['restorecon',str(profile),str(database),str(dropin)])
    policy='''
(type lyra_parental_shell_t)
(typeattributeset domain (lyra_parental_shell_t))
(roletype lyra_parental_r lyra_parental_shell_t)
(roletype system_r lyra_parental_shell_t)
(type lyra_parental_shell_entry_t)
(typeattributeset file_type (lyra_parental_shell_entry_t))
(typeattributeset exec_type (lyra_parental_shell_entry_t))
(type lyra_parental_shell_payload_t)
(typeattributeset file_type (lyra_parental_shell_payload_t))
(typeattributeset exec_type (lyra_parental_shell_payload_t))
(allow lyra_parental_probe_t lyra_parental_shell_entry_t (file (execute)))
(allow lyra_parental_probe_t lyra_parental_shell_t (process (transition signal sigkill sigstop)))
(typetransition lyra_parental_probe_t lyra_parental_shell_entry_t process lyra_parental_shell_t)
(allow lyra_parental_shell_t lyra_parental_shell_entry_t (file (entrypoint execute)))
(allow lyra_parental_shell_t lyra_parental_shell_payload_t (file (execute execute_no_trans)))
(allow lyra_parental_shell_t lib_t (file (execute)))
(allow lyra_parental_shell_t ld_so_t (file (execute)))
(allow lyra_parental_shell_t self (process (execmem)))
(allow lyra_parental_shell_t lib_t (dir (read open)))
; Mutter enumerates DRM devices through sysfs/udev and opens the virtual GPU.
(allow lyra_parental_shell_t sysfs_t (dir (read open)))
(allow lyra_parental_shell_t udev_var_run_t (dir (read open)))
(allow lyra_parental_shell_t device_t (dir (read open)))
(allow lyra_parental_shell_t dri_device_t (chr_file (read write open getattr ioctl map)))
; libinput receives udev device events and reads the seat's input devices.
(allow lyra_parental_shell_t self (netlink_kobject_uevent_socket (create bind read getattr getopt setopt)))
(allow lyra_parental_shell_t event_device_t (chr_file (read write open getattr ioctl)))
(allow lyra_parental_shell_t systemd_logind_sessions_t (dir (read open)))
(allow lyra_parental_shell_t systemd_logind_var_run_t (dir (read open)))
(allow lyra_parental_shell_t system_dbusd_var_run_t (sock_file (write)))
(allow lyra_parental_shell_t system_dbusd_t (unix_stream_socket (connectto)))
(allow lyra_parental_shell_t system_dbusd_t (dbus (send_msg)))
(allow system_dbusd_t lyra_parental_shell_t (dbus (send_msg)))
(allow lyra_parental_shell_t systemd_logind_t (dbus (send_msg)))
(allow systemd_logind_t lyra_parental_shell_t (dbus (send_msg)))
(allow lyra_parental_probe_t lyra_parental_shell_t (dir (search getattr)))
(allow lyra_parental_probe_t lyra_parental_shell_t (file (read open getattr)))
(type lyra_parental_shell_memory_t)
(typeattributeset file_type (lyra_parental_shell_memory_t))
; Executable memory files belong to the trusted desktop, never to the account domain.
(typetransition lyra_parental_shell_t tmpfs_t file lyra_parental_shell_memory_t)
(allow lyra_parental_shell_t lyra_parental_shell_memory_t (file (create read open getattr map write append setattr unlink execute)))
(allow lyra_parental_shell_t lyra_parental_probe_t (dbus (send_msg acquire_svc)))
(allow lyra_parental_shell_t lyra_parental_probe_t (unix_stream_socket (connectto)))
(allow lyra_parental_probe_t lyra_parental_shell_t (dbus (send_msg)))
(allow lyra_parental_probe_t tty_device_t (chr_file (read write)))
(allow lyra_parental_probe_t devlog_t (sock_file (write)))
(allow lyra_parental_probe_t system_dbusd_var_run_t (sock_file (write)))
(allow lyra_parental_probe_t system_dbusd_t (unix_stream_socket (connectto)))
(allow lyra_parental_probe_t system_dbusd_t (dbus (send_msg)))
(allow system_dbusd_t lyra_parental_probe_t (dbus (send_msg)))
(allow lyra_parental_probe_t xdm_t (dbus (send_msg)))
(allow xdm_t lyra_parental_probe_t (dbus (send_msg)))
(allow lyra_parental_probe_t systemd_logind_t (dbus (send_msg)))
(allow systemd_logind_t lyra_parental_probe_t (dbus (send_msg)))
(allow lyra_parental_probe_t xdm_unit_file_t (service (start status)))
(allow lyra_parental_probe_t config_home_t (dir (open read watch)))
(allow lyra_parental_probe_t root_t (dir (watch)))
(allow lyra_parental_probe_t etc_t (dir (watch)))
(type lyra_parental_gnome_session_exec_t)
(typeattributeset file_type (lyra_parental_gnome_session_exec_t))
(typeattributeset exec_type (lyra_parental_gnome_session_exec_t))
(allow lyra_parental_probe_t lyra_parental_gnome_session_exec_t (file (execute execute_no_trans)))
(type lyra_parental_gdm_launcher_exec_t)
(typeattributeset file_type (lyra_parental_gdm_launcher_exec_t))
(typeattributeset exec_type (lyra_parental_gdm_launcher_exec_t))
(allow xdm_t lyra_parental_gdm_launcher_exec_t (file (getattr open read map execute)))
(allow lyra_parental_probe_t lyra_parental_gdm_launcher_exec_t (file (entrypoint execute execute_no_trans)))
'''
    # Share only the current experiment's discovery/runtime permissions.
    # Do not copy execution, service-management or system-management grants.
    base=bz2.decompress(P('/etc/selinux/targeted/active/modules/400/lyra-parental-probe/cil').read_bytes()).decode()
    for form in forms(base):
        if not re.match(r'^\(allow\s+lyra_parental_probe_t\s',form):continue
        if re.search(r'\bexecute\b|\bexecute_no_trans\b|\bentrypoint\b|\(\s*(?:service|system)\s',form):continue
        policy+='\n'+re.sub(r'^(\(allow\s+)lyra_parental_probe_t\b',r'\1lyra_parental_shell_t',form)
    policy_path=P('/root/lyra-trusted-shell-test.cil');policy_path.write_text(policy)
    run(['semodule','-i',str(policy_path)]);loaded=True
    for path,kind in [(helper,'lyra_parental_gdm_launcher_exec_t'),(native,'lyra_parental_gnome_session_exec_t'),
                      (ctl,'lyra_parental_gnome_session_exec_t'),(shell,'lyra_parental_shell_payload_t'),
                      (launcher,'lyra_parental_shell_entry_t')]:
        run(['chcon','-t',kind,str(path)])
    entry.write_text(entry.read_text().replace('\nExec=/usr/bin/gnome-session\n','\nExec=/usr/libexec/gnome-session-binary\n'))
    assert '\nExec=/usr/bin/gnome-shell\n' in application.read_text()
    application.write_text(application.read_text().replace('\nExec=/usr/bin/gnome-shell\n','\nExec='+str(launcher)+'\n'))
    shutil.copyfile('/root/gdm-official-build/daemon/gdm-session-worker',worker)
    run(['restorecon',str(worker)])
    run(['setenforce','1'])
    cases=[([],0),(['/opt/lyra-parental-probe/approved'],0),
           (['/usr/bin/true'],126),(['/home/parentaltest/copied-true'],126),
           (['/usr/bin/bash','-c','true'],126),(['/usr/bin/python3','-c','print(42)'],126),
           (['/usr/lib64/ld-linux-x86-64.so.2','/home/parentaltest/copied-true'],126),
           (['--anon'],126),(['--map','/home/parentaltest/copied-true'],126),
           ([str(launcher),'--invalid'],126),([str(shell),'--version'],126)]
    for args,expected in cases:
        cmd=['runuser','-u','parentaltest','--','runcon','system_u:system_r:lyra_parental_probe_t:s0',
             '/opt/lyra-parental-probe/probe']+args
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
        records.append(dict(argv=cmd,rc=r.returncode,stdout=r.stdout,stderr=r.stderr))
        assert r.returncode==expected and 'uid=1003 context=system_u:system_r:lyra_parental_probe_t:s0' in r.stdout,records[-1]
    run(['runuser','-u','ordinaryuser','--','python3','-c','print("ordinary-account-ok")'])
    run(['python3','/root/trusted-shell-config-faults.py'])
    run(['setenforce','0'])
    audit_started=subprocess.run(['systemctl','is-active','--quiet','auditd']).returncode!=0
    if audit_started:run(['systemctl','start','auditd'])
    audit_log=P('/var/log/audit/audit.log')
    audit_offset=audit_log.stat().st_size
    import datetime
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    run(['gcc','-Wall','-Wextra','-Werror','-O2','/root/ffi-probe.c','-lffi','-lselinux','-o',str(launcher)])
    run(['chcon','-t','lyra_parental_shell_entry_t',str(launcher)])
    run(['setenforce','1'])
    prefix=['runuser','-u','parentaltest','--','runcon','system_u:system_r:lyra_parental_probe_t:s0','/opt/lyra-parental-probe/probe']
    for name,cmd in [('ordinary',['runuser','-u','ordinaryuser','--',str(launcher)]),('shell-domain',prefix+[str(launcher)])]:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
        records.append(dict(name=name,argv=cmd,rc=r.returncode,stdout=r.stdout,stderr=r.stderr))
    assert records[-1]['rc']==0 and 'callback result=42' in records[-1]['stdout'],records[-1]
    private_file.write_bytes(b'callback-fixture');os.chown(private_file,1003,1004);private_file.chmod(0o600)
    run(['chcon','-t','lyra_parental_shell_memory_t',str(private_file)])
    run(['chcon','-t','lyra_parental_probe_exec_t',str(launcher)])
    for name,cmd,expected in [
      ('restricted-callback-still-denied',prefix+[str(launcher)],126),
      ('restricted-private-executable-map-denied',prefix+['--map',str(private_file)],126),
      ('restricted-private-write-denied',prefix+[str(launcher),'--write',str(private_file)],126),
      ('same-uid-outside-domain-can-write',['runuser','-u','parentaltest','--',str(launcher),'--write',str(private_file)],0)]:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
        records.append(dict(name=name,argv=cmd,rc=r.returncode,stdout=r.stdout,stderr=r.stderr))
        assert r.returncode==expected,records[-1]
    import time
    time.sleep(1)
    P('/root/ffi-probe-audit.log').write_bytes(audit_log.read_bytes()[audit_offset:])
    kernel=run(['journalctl','-b','-k','--since',stamp,'--no-pager'])
    P('/root/ffi-probe-kernel.log').write_text(kernel)
    P('/root/ffi-probe-result.json').write_text(json.dumps(records,indent=2))

finally:
    if audit_started:subprocess.run(['systemctl','stop','auditd'],check=True)
    subprocess.run(['systemctl','stop','gdm'],check=True)
    subprocess.run(['loginctl','terminate-user','parentaltest'],capture_output=True)
    subprocess.run(['systemctl','stop','user@1003.service'],check=True)
    subprocess.run(['setenforce','0'],check=True)
    if debuglog.exists():
        P('/root/trusted-shell-stderr.log').write_bytes(debuglog.read_bytes())
    for path,(data,mode,label) in original.items():
        if path.read_bytes()!=data:path.write_bytes(data)
        path.chmod(mode);os.setxattr(path,'security.selinux',label)
        assert path.read_bytes()==data and os.getxattr(path,'security.selinux')==label
    for path in reversed(generated):path.unlink(missing_ok=True)
    for directory in reversed(created_dirs):directory.rmdir()
    if loaded:subprocess.run(['semodule','-r','lyra-trusted-shell-test'],check=True)
    if audit_disabled:subprocess.run(['semodule','-B'],check=True)
print(json.dumps({'restored':True,'official_worker_sha256':hashlib.sha256(worker.read_bytes()).hexdigest(),'commands':records},indent=2))
