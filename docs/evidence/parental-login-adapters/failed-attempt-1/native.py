from bridge import *
from routes import *
import routes,configparser
import secrets,shutil,subprocess

assert run(['getenforce'])['stdout'].strip()=='Permissive'
assert not any(p.exists() for p in (DIRECTORY,MODULE,UNIT,CONFIG,ROLES,PROOFS))
assert not run(['loginctl','list-sessions','--no-legend'])['stdout'].strip()
assert all(show(uid)['MainPID']=='0' and not uid_processes(uid) for uid in (1000,1002,1003))
assert not any(Path('/var/lib/systemd/linger',n).exists() for n in ('installeduser','ordinaryuser','parentaltest'))
BASE.mkdir(mode=0o700,exist_ok=True)
for uid,name in ((1000,'installeduser'),(1002,'ordinaryuser'),(1003,'parentaltest')):drain(uid,name)
original=PAM.read_bytes();(BASE/'original-pam').write_bytes(original)
meta=dict(original_pam_sha256=hashlib.sha256(original).hexdigest(),original_pam_mode=PAM.stat().st_mode&0o777,
    vendor_sha256=hashlib.sha256(VENDOR.read_bytes()).hexdigest(),account_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('/etc/passwd','/etc/group')},
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (GUARD,WRITER,Path(__file__),BASE/'common.py',BASE/'helper.py',BASE/'state.py',BASE/'bridge.py',BASE/'withdrawal.py',BASE/'coordinator.py',BASE/'ordinary-coordinator.py',BASE/'manager_adapters.py',BASE/'cleanup.py',BASE/'restore-check.py')})
backup_login(meta)
meta['source_sha256'].update({p.name:digest(p) for p in (BASE/'login-adapters.py',BASE/'login-common.py',BASE/'routes.py',BASE/'ssh-ordinary-guard.c',BASE/'manager_adapters.py',BASE/'password-client.py',BASE/'manager-session.c',BASE/'lyra-login-state.cil',BASE/'lyra-registry-gdm.cil')})
save(meta);passed=False;error=None
pins=[]

def expect(code,action):
    try:action()
    except oc.GateError as e:assert e.code==code,(e.code,code)
    else:raise AssertionError('expected '+code)

def stop_target():
    stop(1002);run(['systemctl','stop','user-runtime-dir@1002.service']);drain(1002,'ordinaryuser')

def reset_case():
    assert show(1002)['MainPID']=='0' and not uid_processes(1002)
    for n in ('.deny-1002','.withdrawal-1002.json'):(PROOFS/n).unlink(missing_ok=True)
    fd=os.open(PROOFS,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    write_rows(PROOFS,'1002',[ordinary])

try:
    run(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(GUARD),'-o',str(MODULE),'-lpam','-lselinux']);MODULE.chmod(0o755);run(['restorecon',str(MODULE)])
    DIRECTORY.mkdir(mode=0o700);ROLES.mkdir(mode=0o700);PROOFS.mkdir(mode=0o700)
    for uid in (1000,1002,1003):
        fd=os.open(PROOFS/f'.gate-{uid}.lock',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.fsync(fd);os.close(fd)
    fd=os.open(PROOFS,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    generation=secrets.token_hex(16);protected=dict(state='active',**IDENTITY,generation=generation)
    ordinary=dict(state='ordinary',user='ordinaryuser',uid=1002,gid=1003,group='ordinaryuser',generation=secrets.token_hex(16))
    peer=dict(state='ordinary',user='installeduser',uid=1000,gid=1001,group='installeduser',generation=secrets.token_hex(16))
    writer.RegistryStore(DIRECTORY).seed([protected]);run(['restorecon','-R',str(DIRECTORY)])
    write_rows(ROLES,'role-index',[protected,ordinary,peer])
    for row in (ordinary,peer):write_rows(PROOFS,str(row['uid']),[row])
    install_pam(generation);run(['setenforce','1'])
    # Install account-stage SSH gate plus the unchanged session-stage check.
    run(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(BASE/'ssh-ordinary-guard.c'),'-o',str(SSH_MODULE),'-lpam','-lselinux'])
    run(['restorecon',str(SSH_MODULE)])
    vendor=Path('/usr/lib/pam.d/sshd').read_text()
    ssh_pam=Path('/etc/pam.d/sshd')
    ssh_pam.write_text('#%PAM-1.0\naccount requisite pam_lyra_ordinary_ssh_fixture.so\n'+vendor.removeprefix('#%PAM-1.0\n')+'\nsession required pam_lyra_ordinary_ssh_fixture.so\n');ssh_pam.chmod(0o644);run(['restorecon',str(ssh_pam)])
    gdm_pam=Path('/etc/pam.d/gdm-password');gdm_pam.write_text(Path('/usr/lib/pam.d/gdm-password').read_text()+'\nsession required pam_lyra_withdrawal_fixture.so\n');gdm_pam.chmod(0o644);run(['restorecon',str(gdm_pam)])
    run(['semodule','-i',str(BASE/'lyra-login-state.cil')]);run(['semodule','-i',str(BASE/'lyra-registry-gdm.cil')])
    for directory in (DIRECTORY,ROLES,PROOFS):run(['chcon','-R','-t','lyra_login_state_t',str(directory)])
    # Existing test accounts only: temporary authentication secrets, restored.
    passwords={name:secrets.token_hex(24) for name in ('ordinaryuser','installeduser')}
    p=subprocess.run(['chpasswd'],input=''.join(n+':'+v+'\n' for n,v in passwords.items()),capture_output=True,text=True)
    assert p.returncode==0
    PRIVATE.mkdir(mode=0o700);KEYS.mkdir(mode=0o755)
    run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(PRIVATE/'client-key')]);run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(HOSTKEY)])
    for user in passwords:(KEYS/user).write_text((PRIVATE/'client-key.pub').read_text());(KEYS/user).chmod(0o644)
    host_public=HOSTKEY.with_suffix('.pub').read_text().split();(PRIVATE/'known_hosts').write_text('127.0.0.1 '+' '.join(host_public[:2])+'\n')
    SSH_CONFIG.write_text(f"Port 22\nListenAddress 127.0.0.1\nHostKey {HOSTKEY}\nPidFile {PRIVATE}/sshd.pid\nAuthorizedKeysFile {KEYS}/%u\nUsePAM yes\nPubkeyAuthentication yes\nPasswordAuthentication yes\nKbdInteractiveAuthentication no\nPermitRootLogin no\nStrictModes yes\nAllowUsers ordinaryuser installeduser\nAllowTcpForwarding yes\nPerSourcePenalties no\nSubsystem sftp internal-sftp\nLogLevel VERBOSE\n");SSH_CONFIG.chmod(0o600)
    run(['restorecon','-R',str(KEYS),str(HOSTKEY),str(HOSTKEY.with_suffix('.pub')),str(SSH_CONFIG)])
    run(['/usr/sbin/sshd','-t','-f',str(SSH_CONFIG)])
    effective=run(['/usr/sbin/sshd','-T','-f',str(SSH_CONFIG)])['stdout'];assert 'usepam yes\n' in effective and 'persourcepenalties no\n' in effective
    run(['systemd-run','--unit='+SSH_UNIT,'--property=KillMode=control-group','/usr/sbin/sshd','-D','-e','-f',str(SSH_CONFIG)])
    routes.invocation=run(['systemctl','show',SSH_UNIT,'-p','InvocationID','--value'])['stdout'].strip()
    ssh_pid=run(['systemctl','show',SSH_UNIT,'-p','MainPID','--value'])['stdout'].strip()
    assert int(ssh_pid)>0
    time.sleep(.3)
    # GDM diagnostic worker and bounded ELF payload; no GNOME compositor.
    run(['gcc','-Wall','-Wextra','-Werror','-O2',str(BASE/'manager-session.c'),'-o',str(SESSION)]);run(['chcon','-t','lyra_parental_probe_exec_t',str(SESSION)])
    shutil.copy2(PATCHED,WORKER);run(['restorecon',str(WORKER)]);run(['chcon','-t','lyra_manager_launcher_exec_t',str(HELPER)])
    for path in (Path('/usr/share/wayland-sessions/gnome.desktop'),Path('/usr/share/wayland-sessions/gnome-wayland.desktop')):
        path.write_text('[Desktop Entry]\nName=Login fixture\nExec='+str(SESSION)+'\nTryExec='+str(SESSION)+'\nType=Application\nDesktopNames=LYRA\nX-GDM-SessionRegisters=false\n')
    conf=configparser.ConfigParser(interpolation=None);conf.read(CONF)
    if not conf.has_section('daemon'):conf.add_section('daemon')
    if not conf.has_section('debug'):conf.add_section('debug')
    conf.set('daemon','AutomaticLoginEnable','False');conf.set('daemon','TimedLoginEnable','False');conf.set('debug','Enable','true')
    with CONF.open('w') as f:conf.write(f)
    run(['systemctl','reset-failed','gdm.service'],check=False);run(['systemctl','start','gdm.service'])
    gdm_pid=run(['systemctl','show','gdm.service','-p','MainPID','--value'])['stdout'].strip()
    assert int(gdm_pid)>0
    for uid in (1000,1002):
        run(['systemctl','start',f'user@{uid}.service']);assert context(uid).startswith('unconfined_u:unconfined_r:unconfined_t:')
        record(checks,f'baseline-ordinary-{uid}',unit=show(uid),context=context(uid))
    peer_pid=show(1000)['MainPID'];old_pid=show(1002)['MainPID'];peer_proof=(PROOFS/'1000').read_bytes()
    remote('ordinaryuser',True,'baseline-target-ssh');remote('installeduser',True,'baseline-peer-ssh')
    start_echo();target_tunnel,target_port=tunnel('ordinaryuser',True,'baseline-target-no-shell-tunnel');peer_tunnel,peer_port=tunnel('installeduser',True,'baseline-peer-no-shell-tunnel')
    target_command=persistent_command('ordinaryuser');peer_command=persistent_command('installeduser');mux_process,control=mux()
    worker=gdm_login('ordinaryuser',passwords['ordinaryuser'],True,'baseline-target-gdm-password')
    pins.append(os.pidfd_open(worker))
    inventory=account_scope_processes(1002)
    assert any(x['uids']==(0,)*4 and x['comm'] in ('sshd-session','sshd-auth') for x in inventory),inventory
    for row in inventory:pins.append(os.pidfd_open(row['pid']))
    record(checks,'target-admitted-roots-and-payloads-inventoried',processes=inventory,gdm_worker_pid=worker,pidfds=len(pins))
    storage=make();operation=secrets.token_hex(16);plan=storage.plan(1002,operation);storage.begin(plan,lambda p:True)
    # New negative files receive the same fixture-only read label.
    run(['chcon','-R','-t','lyra_login_state_t',str(PROOFS)])
    target=oc.Target(1002,operation,plan.proof_hash)
    spec=importlib.util.spec_from_file_location('manager_adapters',BASE/'manager_adapters.py');ma=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ma;spec.loader.exec_module(ma)
    spec=importlib.util.spec_from_file_location('login_adapters',BASE/'login-adapters.py');la=importlib.util.module_from_spec(spec);sys.modules[spec.name]=la;spec.loader.exec_module(la)
    expected={p:p.read_bytes() for p in (PAM,MODULE,ssh_pam,SSH_MODULE,SSH_CONFIG,gdm_pam,CONF,WORKER)}
    def unchanged(paths):return all(protected_bytes(p,expected[p]) for p in paths)
    def verify_identity(i):
        a=pwd.getpwnam(i.user);g=grp.getgrnam(i.group)
        return (a.pw_uid,a.pw_gid,g.gr_gid)==(i.uid,i.gid,i.gid)
    classification=ma.Classification(storage,ma.Identity('ordinaryuser',1002,1003,'ordinaryuser'),verify_identity,lambda:unchanged((PAM,MODULE)) and run(['getenforce'])['stdout'].strip()=='Enforcing')
    def no_pinned_processes():return all(select.select([p],[],[],0)[0] for p in pins)
    observe=lambda uid:observed_empty(uid) and no_pinned_processes()
    ssh=la.LoginRoute('sshd',classification,lambda:unchanged((ssh_pam,SSH_MODULE,SSH_CONFIG)) and run(['systemctl','show',SSH_UNIT,'-p','MainPID','--value'])['stdout'].strip()==ssh_pid,lambda args:run(args,check=False),observe,lambda t:False)
    gdm=la.LoginRoute('gdm-password',classification,lambda:unchanged((gdm_pam,CONF,WORKER)) and run(['systemctl','show','gdm.service','-p','MainPID','--value'])['stdout'].strip()==gdm_pid,lambda args:run(args,check=False),observe,lambda t:True)
    assert ssh.inhibited(target) and gdm.inhibited(target) and not ssh.quiescent(target)
    assert exchange(target_port) and target_command.poll() is None and session_processes(1002)
    mux_command(control,True,'old-multiplex-survives-admission-withdrawal')
    record(checks,'withdrawal-alone-keeps-existing-ssh-and-gdm',target_processes=account_scope_processes(1002))
    expect('Denied',lambda:ssh.revoke(target));assert exchange(target_port) and session_processes(1002)
    record(checks,'denied-login-revocation-has-no-session-effect')
    ssh.authorize_revocation=lambda t:True
    ssh_pam.write_bytes(expected[ssh_pam]+b'\n');expect('UnverifiedAdmission',lambda:ssh.revoke(target));assert exchange(target_port)
    ssh_pam.write_bytes(expected[ssh_pam]);run(['restorecon',str(ssh_pam)])
    record(checks,'changed-ssh-stack-prevents-revocation')
    assert ssh.revoke(target) and ssh.quiescent(target) and gdm.quiescent(target)
    for child in (target_tunnel,target_command,mux_process):child.wait(timeout=10);assert child.returncode!=0
    assert not exchange(target_port) and not session_processes(1002) and not account_scope_processes(1002) and no_pinned_processes()
    assert peer_tunnel.poll() is None and exchange(peer_port) and peer_command.poll() is None
    assert run(['systemctl','show',SSH_UNIT,'-p','MainPID','--value'])['stdout'].strip()==ssh_pid
    assert run(['systemctl','show','gdm.service','-p','MainPID','--value'])['stdout'].strip()==gdm_pid
    record(checks,'native-target-ssh-and-gdm-revoked-peer-and-daemons-preserved',target_processes=account_scope_processes(1002),pidfds_exited=len(pins),gdm_worker_exited=True,ssh_listener_pid=ssh_pid,gdm_pid=gdm_pid,peer_forwarded=True)
    before=state();assert gdm.revoke(target) and state()==before
    record(checks,'gdm-idempotent-revoke-retains-negative-authority')
    remote('ordinaryuser',False,'new-target-ssh-denied');sftp_denied();tunnel('ordinaryuser',False,'new-target-no-shell-tunnel-denied')
    mux_command(control,False,'old-multiplex-cannot-create-new-channel')
    remote('installeduser',True,'peer-new-ssh-preserved')
    gdm_login('ordinaryuser',passwords['ordinaryuser'],False,'new-target-gdm-password-denied')
    CONF.write_bytes(expected[CONF]+b'\n');expect('UnverifiedAdmission',lambda:gdm.inhibited(target));CONF.write_bytes(expected[CONF])
    record(checks,'changed-gdm-config-cannot-claim-inhibition')
    gate=oc.OrdinaryCoordinator(storage,WithdrawalError,{'classification':classification,'user-manager':ma.UserManager(classification,lambda args:run(args,check=False),observe,lambda t:True),'gdm':gdm,'ssh':ssh})
    expect('UnsupportedProducer',lambda:gate.resume_and_check(1002,operation,lambda p,r:True,revoke=True))
    record(checks,'four-real-adapters-still-refuse-uncovered-producers')
    gdm_login('installeduser',passwords['installeduser'],True,'peer-fresh-gdm-password-preserved')
    assert peer_tunnel.poll() is None and exchange(peer_port) and peer_command.poll() is None and (PROOFS/'1000').read_bytes()==peer_proof
    record(checks,'peer-ssh-survives-target-revocation-and-gdm-login')
    passed=True
except BaseException as e:error=str(e);raise
finally:
    for child in children:
        if child.poll() is None:child.terminate()
        child.wait(timeout=10)
    if routes.echo:routes.echo.shutdown();routes.echo.server_close()
    for p in pins:os.close(p)
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=150)
    row=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,
        full_account_protection=False,whole_classification_qualified=False,all_producer_quiescence=False,real_nss_mutations_tested=False,
        production_adapters_qualified=False,monotonic_revision_qualified=False,power_loss_tested=False,full_gnome_session_tested=False,official_gdm_worker_qualified=False,all_gdm_routes_qualified=False,pending_authentication_tested=False)
    (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({'passed':row['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}))
    assert cleanup.returncode==0,cleanup.stderr
