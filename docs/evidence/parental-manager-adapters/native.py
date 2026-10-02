from bridge import *
from state import *
import secrets,shutil,subprocess
checks=[]
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
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (GUARD,WRITER,Path(__file__),BASE/'common.py',BASE/'helper.py',BASE/'state.py',BASE/'bridge.py',BASE/'withdrawal.py',BASE/'coordinator.py',BASE/'ordinary-coordinator.py',BASE/'adapters.py',BASE/'cleanup.py',BASE/'restore-check.py')})
save(meta);passed=False;error=None

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
    for uid in (1000,1002):
        run(['systemctl','start',f'user@{uid}.service']);assert context(uid).startswith('unconfined_u:unconfined_r:unconfined_t:')
        record(checks,f'baseline-ordinary-{uid}',unit=show(uid),context=context(uid))
    peer_pid=show(1000)['MainPID'];old_pid=show(1002)['MainPID'];peer_proof=(PROOFS/'1000').read_bytes()
    storage=make();operation=secrets.token_hex(16);plan=storage.plan(1002,operation)
    storage.begin(plan,lambda p:True)
    target=oc.Target(1002,operation,plan.proof_hash)
    import adapters,grp,stat
    expected_pam=PAM.read_bytes();expected_module=MODULE.read_bytes()
    def verify_identity(i):
        a=pwd.getpwnam(i.user);g=grp.getgrnam(i.group)
        return (a.pw_uid,a.pw_gid,g.gr_gid)==(i.uid,i.gid,i.gid)
    def protected_bytes(path,expected):
        s=path.lstat()
        return stat.S_ISREG(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022 and s.st_nlink==1 and path.read_bytes()==expected
    def installation():
        return protected_bytes(PAM,expected_pam) and protected_bytes(MODULE,expected_module) and run(['getenforce'])['stdout'].strip()=='Enforcing'
    classification=adapters.Classification(storage,adapters.Identity('ordinaryuser',1002,1003,'ordinaryuser'),verify_identity,installation)
    manager=adapters.UserManager(classification,lambda args:run(args,check=False),lambda uid:show(uid)['MainPID']=='0' and run(['systemctl','show',f'user-runtime-dir@{uid}.service','-p','ActiveState','--value'])['stdout'].strip()=='inactive' and not uid_processes(uid) and run(['loginctl','show-user',str(uid)],check=False)['rc']!=0,lambda t:False)
    assert classification.inhibited(target) and not manager.quiescent(target)
    record(checks,'withdrawn-classification-old-manager-observed',target_pid=old_pid,peer_pid=peer_pid)
    expect('Denied',lambda:manager.revoke(target));assert show(1002)['MainPID']==old_pid
    record(checks,'revocation-denied-preserves-old-manager')
    manager.authorize_revocation=lambda t:True
    expect('Conflict',lambda:manager.revoke(oc.Target(1002,secrets.token_hex(16),target.proof_hash)))
    assert show(1002)['MainPID']==old_pid
    record(checks,'wrong-operation-no-revocation')
    PAM.write_bytes(expected_pam+b'\n');expect('UnverifiedAdmission',lambda:manager.revoke(target));assert show(1002)['MainPID']==old_pid
    PAM.write_bytes(expected_pam);run(['restorecon',str(PAM)])
    record(checks,'changed-pam-no-revocation')
    assert manager.revoke(target) and manager.quiescent(target)
    drain(1002,'ordinaryuser')
    assert show(1000)['MainPID']==peer_pid and (PROOFS/'1000').read_bytes()==peer_proof
    record(checks,'real-manager-revoked-peer-preserved',target_unit=show(1002),target_processes=uid_processes(1002),peer_pid=peer_pid)
    deny_attempt(checks,'revoked-target-native-readmission-denied')
    before=state();assert manager.revoke(target) and state()==before and show(1000)['MainPID']==peer_pid
    record(checks,'real-revocation-idempotent-negative-authority-preserved')
    g=oc.OrdinaryCoordinator(storage,WithdrawalError,{'classification':classification,'user-manager':manager})
    expect('UnsupportedProducer',lambda:g.resume_and_check(1002,operation,lambda p,r:True,revoke=True))
    record(checks,'two-real-adapters-do-not-satisfy-all-producers')
    # Root deliberately enables linger: the same negative authority must deny it.
    run(['loginctl','enable-linger','ordinaryuser']);time.sleep(1)
    assert Path('/var/lib/systemd/linger/ordinaryuser').exists()
    assert show(1002)['MainPID']=='0' and not uid_processes(1002)
    record(checks,'linger-cannot-reactivate-withdrawn-target',unit=show(1002))
    deny_attempt(checks,'linger-target-manual-admission-denied')
    run(['loginctl','disable-linger','ordinaryuser'])
    stop(1000);run(['systemctl','stop','user-runtime-dir@1000.service']);drain(1000,'installeduser')
    run(['systemctl','start','user@1000.service'])
    assert context(1000).startswith('unconfined_u:unconfined_r:unconfined_t:') and (PROOFS/'1000').read_bytes()==peer_proof
    record(checks,'peer-fresh-native-admission-preserved',unit=show(1000),context=context(1000))
    passed=True
except BaseException as e:error=str(e);raise
finally:
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=100)
    row=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,
        full_account_protection=False,whole_classification_qualified=False,all_producer_quiescence=False,real_nss_mutations_tested=False,
        production_adapters_qualified=False,monotonic_revision_qualified=False,power_loss_tested=False)
    (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({'passed':row['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}))
    assert cleanup.returncode==0,cleanup.stderr
