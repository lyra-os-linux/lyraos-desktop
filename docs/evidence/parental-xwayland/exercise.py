"""Disposable VM-only split-domain experiment; never install on a host."""
import bz2, hashlib, json, os, pathlib, re, shlex, shutil, stat, subprocess
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
worker=P('/usr/libexec/gdm/gdm-session-worker')
mutter=P('/usr/lib64/libmutter-16.so.0.0.0')
x11ready=P('/usr/lib/systemd/user/gnome-session-x11-services-ready.target')
helper=P('/usr/libexec/gdm/gdm-wayland-session')
native=P('/usr/libexec/gnome-session-binary')
ctl=P('/usr/libexec/gnome-session-ctl')
shell=P('/usr/bin/gnome-shell')
xwayland=P('/usr/bin/Xwayland')
xclient=P('/usr/bin/xprop')
xkbcomp=P('/usr/bin/xkbcomp')
entry=P('/usr/share/wayland-sessions/gnome.desktop')
application=P('/usr/share/applications/org.gnome.Shell.desktop')
atspi=[P('/usr/libexec/at-spi2/at-spi-bus-launcher'),P('/usr/libexec/at-spi2/at-spi2-registryd')]
launcher=P('/usr/libexec/lyra/trusted-shell-test')
dropin=P('/etc/systemd/user/org.gnome.Shell@wayland.service.d/99-lyra-trusted-test.conf')
profile=P('/etc/dconf/profile/lyra-supervised-test')
database=P('/etc/dconf/db/lyra-supervised-test')
debuglog=P('/tmp/lyra-trusted-shell-test.log')
keydir=P('/root/lyra-shell-test-db.d')
generated=[launcher,dropin,profile,database,debuglog,keydir/'00-policy',keydir/'locks/00-policy']
assert all(not p.exists() for p in generated)
for p in atspi:
    owner=subprocess.check_output(['rpm','-qf','--qf','%{NAME}',str(p)],text=True)
    assert owner=='at-spi2-core' and p.stat().st_uid==0,(str(p),owner)
subprocess.run(['rpm','-V','at-spi2-core'],check=True)
assert subprocess.check_output(['rpm','-qf','--qf','%{NAME}',str(xwayland)],text=True)=='xwayland'
assert xwayland.stat().st_uid==0
subprocess.run(['rpm','-V','xwayland'],check=True)
assert subprocess.check_output(['rpm','-qf','--qf','%{NAME}',str(xclient)],text=True)=='xprop'
subprocess.run(['rpm','-V','xprop'],check=True)
assert subprocess.check_output(['rpm','-qf','--qf','%{NAME}',str(xkbcomp)],text=True)=='xkbcomp'
subprocess.run(['rpm','-V','xkbcomp'],check=True)
assert mutter.is_file() and not mutter.is_symlink()
subprocess.run(['rpm','-V','mutter'],check=True)
import fixture_recovery
backup = fixture_recovery.snapshot(
    [worker,helper,native,ctl,shell,entry,application,xwayland,xclient,xkbcomp,mutter,x11ready]+atspi+[P('/etc/gdm/custom.conf')],
    generated+[P('/etc/pam.d/gdm-autologin'),P('/etc/gdm/custom.conf.lyra-baseline')])
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
; Dedicated non-executable files for Mutter's XWayland lock files.
(type lyra_parental_atspi_exec_t)
(typeattributeset file_type (lyra_parental_atspi_exec_t))
(typeattributeset exec_type (lyra_parental_atspi_exec_t))
(allow lyra_parental_probe_t lyra_parental_atspi_exec_t (file (execute execute_no_trans)))
(type lyra_parental_x11_lock_t)
(typeattributeset file_type (lyra_parental_x11_lock_t))
(typetransition lyra_parental_shell_t tmp_t file lyra_parental_x11_lock_t)
(allow lyra_parental_shell_t tmp_t (dir (write add_name remove_name)))
(allow lyra_parental_shell_t lyra_parental_x11_lock_t (file (create read open getattr write unlink setattr)))
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
    policy+='''
; XWayland is a separate trusted native server, entered only by the Shell.
(type lyra_parental_xwayland_t)
(typeattributeset domain (lyra_parental_xwayland_t))
(roletype lyra_parental_r lyra_parental_xwayland_t)
(roletype system_r lyra_parental_xwayland_t)
(type lyra_parental_xwayland_exec_t)
(typeattributeset file_type (lyra_parental_xwayland_exec_t))
(typeattributeset exec_type (lyra_parental_xwayland_exec_t))
(typetransition lyra_parental_shell_t lyra_parental_xwayland_exec_t process lyra_parental_xwayland_t)
(allow lyra_parental_shell_t lyra_parental_xwayland_exec_t (file (execute)))
(allow lyra_parental_shell_t lyra_parental_xwayland_t (process (transition signal sigkill sigstop)))
(allow lyra_parental_xwayland_t lyra_parental_xwayland_exec_t (file (entrypoint execute)))
(allow lyra_parental_xwayland_t lyra_parental_shell_t (process (sigchld)))
; Dynamic libraries may be mapped, but not used as an executable loader.
(allow lyra_parental_xwayland_t file_type (dir (search getattr read open)))
(allow lyra_parental_xwayland_t file_type (lnk_file (read getattr)))
(allow lyra_parental_xwayland_t file_type (file (read open getattr map)))
(allow lyra_parental_xwayland_t lib_t (file (execute)))
(allow lyra_parental_xwayland_t ld_so_t (file (execute)))
; Inherit compositor channels, no generic outbound network permission.
(allow lyra_parental_xwayland_t lyra_parental_shell_t (fd (use)))
(allow lyra_parental_xwayland_t lyra_parental_shell_t (unix_stream_socket (read write getattr getopt setopt accept)))
(allow lyra_parental_xwayland_t lyra_parental_shell_t (fifo_file (read write getattr ioctl)))
(allow lyra_parental_xwayland_t lyra_parental_probe_t (fd (use)))
(allow lyra_parental_xwayland_t lyra_parental_probe_t (fifo_file (read write getattr ioctl)))
(allow lyra_parental_xwayland_t self (unix_stream_socket (create read write bind listen accept connect getattr getopt setopt shutdown)))
(allow lyra_parental_xwayland_t self (unix_dgram_socket (create read write bind connect getattr getopt setopt shutdown)))
(allow lyra_parental_xwayland_t self (process (getattr)))
(allow lyra_parental_xwayland_t dri_device_t (chr_file (read write open getattr ioctl map)))
(allow lyra_parental_xwayland_t null_device_t (chr_file (read write open getattr)))
(allow lyra_parental_xwayland_t urandom_device_t (chr_file (read open getattr)))
(type lyra_parental_xwayland_data_t)
(typeattributeset file_type (lyra_parental_xwayland_data_t))
(typetransition lyra_parental_xwayland_t tmpfs_t file lyra_parental_xwayland_data_t)
(allow lyra_parental_xwayland_t lyra_parental_xwayland_data_t (file (create read write open getattr map append setattr unlink)))
'''
    policy+='''
(type lyra_parental_xclient_exec_t)
(typeattributeset file_type (lyra_parental_xclient_exec_t))
(typeattributeset exec_type (lyra_parental_xclient_exec_t))
(allow lyra_parental_probe_t lyra_parental_xclient_exec_t (file (execute execute_no_trans)))
; Mutter owns the on-demand X11 listen socket before XWayland is started.
(allow lyra_parental_probe_t lyra_parental_shell_t (unix_stream_socket (connectto)))
'''
    policy+='''
; Fixed native keymap compiler, not a shell or general executable domain.
(type lyra_parental_xkb_t)
(typeattributeset domain (lyra_parental_xkb_t))
(roletype lyra_parental_r lyra_parental_xkb_t)
(roletype system_r lyra_parental_xkb_t)
(type lyra_parental_xkb_exec_t)
(typeattributeset file_type (lyra_parental_xkb_exec_t))
(typeattributeset exec_type (lyra_parental_xkb_exec_t))
(typetransition lyra_parental_xwayland_t lyra_parental_xkb_exec_t process lyra_parental_xkb_t)
(allow lyra_parental_xwayland_t lyra_parental_xkb_exec_t (file (execute)))
(allow lyra_parental_xwayland_t lyra_parental_xkb_t (process (transition signal)))
(allow lyra_parental_xkb_t lyra_parental_xkb_exec_t (file (entrypoint execute)))
(allow lyra_parental_xkb_t lyra_parental_xwayland_t (process (sigchld)))
(allow lyra_parental_xkb_t file_type (dir (search getattr read open)))
(allow lyra_parental_xkb_t file_type (lnk_file (read getattr)))
(allow lyra_parental_xkb_t file_type (file (read open getattr map)))
(allow lyra_parental_xkb_t lib_t (file (execute)))
(allow lyra_parental_xkb_t ld_so_t (file (execute)))
(allow lyra_parental_xkb_t lyra_parental_xwayland_t (fd (use)))
(allow lyra_parental_xkb_t lyra_parental_xwayland_t (fifo_file (read write getattr ioctl)))
(allow lyra_parental_xkb_t lyra_parental_shell_t (fd (use)))
(allow lyra_parental_xkb_t lyra_parental_probe_t (fd (use)))
(type lyra_parental_keymap_t)
(typeattributeset file_type (lyra_parental_keymap_t))
(typetransition lyra_parental_xkb_t user_tmp_t file lyra_parental_keymap_t)
(allow lyra_parental_xwayland_t user_tmp_t (dir (write add_name remove_name)))
(allow lyra_parental_xkb_t user_tmp_t (dir (write add_name remove_name)))
(allow lyra_parental_xkb_t lyra_parental_keymap_t (file (create write open getattr read setattr unlink)))
(allow lyra_parental_xwayland_t lyra_parental_keymap_t (file (read open getattr unlink)))
; Dedicated diagnostic log instead of write access to arbitrary account files.
(type lyra_parental_session_log_t)
(typeattributeset file_type (lyra_parental_session_log_t))
(allow lyra_parental_probe_t lyra_parental_session_log_t (file (write append)))
(allow lyra_parental_shell_t lyra_parental_session_log_t (file (write append)))
(allow lyra_parental_xwayland_t lyra_parental_session_log_t (file (write append)))
(allow lyra_parental_xkb_t lyra_parental_session_log_t (file (write append)))
'''
    policy+='''
; The sanitized NOTIFY_SOCKET names only the current user manager endpoint.
(allow lyra_parental_shell_t lyra_parental_probe_t (unix_dgram_socket (sendto)))
; Shell may notify readiness through exactly this packaged user target.
(type lyra_parental_x11_ready_unit_t)
(typeattributeset file_type (lyra_parental_x11_ready_unit_t))
(allow lyra_parental_shell_t lyra_parental_x11_ready_unit_t (service (start status)))
; The user manager must be able to inspect and stop its native X11 child.
(allow lyra_parental_probe_t lyra_parental_xwayland_t (dir (search getattr)))
(allow lyra_parental_probe_t lyra_parental_xwayland_t (file (read open getattr)))
(allow lyra_parental_probe_t lyra_parental_xwayland_t (process (signal sigkill sigstop)))
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
    run(['chcon','-t','lyra_parental_session_log_t',str(debuglog)])
    shutil.copyfile('/root/xwayland-build/hw/xwayland/Xwayland',xwayland)
    shutil.copyfile('/root/mutter-build/src/libmutter-16.so.0.0.0',mutter)
    for path,kind in [(helper,'lyra_parental_gdm_launcher_exec_t'),(native,'lyra_parental_gnome_session_exec_t'),
                      (ctl,'lyra_parental_gnome_session_exec_t'),(shell,'lyra_parental_shell_payload_t'),
                      (launcher,'lyra_parental_shell_entry_t')]:
        run(['chcon','-t',kind,str(path)])
    run(['chcon','-t','lyra_parental_xwayland_exec_t',str(xwayland)])
    run(['chcon','-t','lyra_parental_xclient_exec_t',str(xclient)])
    run(['chcon','-t','lyra_parental_xkb_exec_t',str(xkbcomp)])
    run(['chcon','-t','lyra_parental_x11_ready_unit_t',str(x11ready)])
    for path in atspi:run(['chcon','-t','lyra_parental_atspi_exec_t',str(path)])
    entry.write_text(entry.read_text().replace('\nExec=/usr/bin/gnome-session\n','\nExec=/usr/libexec/gnome-session-binary\n'))
    assert '\nExec=/usr/bin/gnome-shell\n' in application.read_text()
    application.write_text(application.read_text().replace('\nExec=/usr/bin/gnome-shell\n','\nExec='+str(launcher)+'\n'))
    shutil.copyfile('/root/gdm-official-build/daemon/gdm-session-worker',worker)
    run(['restorecon',str(worker)])
    run(['systemctl','start','auditd'])
    run(['auditctl','-b','8192'])
    import audit_capture
    audit_before = audit_capture.status()
    import time
    audit_since = time.time()
    run(['setenforce','1'])
    cases=[([],0),(['/opt/lyra-parental-probe/approved'],0),
           (['/usr/bin/true'],126),(['/home/parentaltest/copied-true'],126),
           (['/usr/bin/bash','-c','true'],126),(['/usr/bin/python3','-c','print(42)'],126),
           (['/usr/lib64/ld-linux-x86-64.so.2','/home/parentaltest/copied-true'],126),
           (['--anon'],126),(['--map','/home/parentaltest/copied-true'],126),
           ([str(xwayland),'-version'],126),([str(xkbcomp),'-version'],126),([str(launcher),'--invalid'],126),([str(shell),'--version'],126)]
    for args,expected in cases:
        cmd=['runuser','-u','parentaltest','--','runcon','system_u:system_r:lyra_parental_probe_t:s0',
             '/opt/lyra-parental-probe/probe']+args
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
        records.append(dict(argv=cmd,rc=r.returncode,stdout=r.stdout,stderr=r.stderr))
        assert r.returncode==expected and 'uid=1003 context=system_u:system_r:lyra_parental_probe_t:s0' in r.stdout,records[-1]
    run(['runuser','-u','ordinaryuser','--','python3','-c','print("ordinary-account-ok")'])
    run(['python3','/root/trusted-shell-config-faults.py'])
    # Instrumented entrypoints are confined test programs, never product launchers.
    run(['gcc','-std=gnu17','-Wall','-Wextra','-Werror','-O2','/root/xwayland-fd-probe.c','-lselinux','-o','/root/xwayland-fd-probe'])
    saved_launcher=launcher.read_bytes()
    saved_xwayland=xwayland.read_bytes()
    try:
        shutil.copyfile('/root/xwayland-fd-probe',launcher)
        shutil.copyfile('/root/xwayland-fd-probe',xwayland)
        for mode in ['rw','sealed-rw','sealed-ro']:
            run(['runuser','-u','parentaltest','--','runcon','system_u:system_r:lyra_parental_probe_t:s0','/opt/lyra-parental-probe/probe',str(launcher),mode],timeout=15)
    finally:
        launcher.write_bytes(saved_launcher)
        xwayland.write_bytes(saved_xwayland)
    run(['setenforce','0'])
    import datetime
    audit_stamp=datetime.datetime.now().strftime('%H:%M:%S')
    with P('/root/trusted-shell-session.json').open('w') as log:
        subprocess.run(['python3','/root/restricted-xwayland-session.py'],check=True,stdout=log,timeout=150)
    import time
    time.sleep(1)
    P('/root/trusted-shell-audit.json').write_text(json.dumps(audit_capture.collect(audit_since, audit_before),indent=2))
finally:
    fixture_recovery.recover()

print(json.dumps({'wayland_only_diagnostic':False,'restored':True,'official_worker_sha256':hashlib.sha256(worker.read_bytes()).hexdigest(),'commands':records},indent=2))
