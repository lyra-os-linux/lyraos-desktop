"""Real user-manager PAM with a persistent role index; marked VM only."""
from helper import *
import secrets,subprocess,shutil
PROOFS=Path('/var/lib/lyra-ordinary-attestation-test');PROOF=PROOFS/'1002'
ROLES=Path('/var/lib/lyra-parental-roles-test');INDEX=ROLES/'role-index'
checks=[]
assert run(['getenforce'])['stdout'].strip()=='Permissive'
assert not any(p.exists() for p in (DIRECTORY,MODULE,UNIT,CONFIG,ROLES,PROOFS))
assert not run(['loginctl','list-sessions','--no-legend'])['stdout'].strip()
assert all(show(uid)['MainPID']=='0' and not uid_processes(uid) for uid in (1002,1003))
assert all(not Path('/var/lib/systemd/linger',n).exists() for n in ('parentaltest','ordinaryuser'))
BASE.mkdir(mode=0o700,exist_ok=True)
for uid,name in ((1003,'parentaltest'),(1002,'ordinaryuser')):drain(uid,name)
original=PAM.read_bytes();(BASE/'original-pam').write_bytes(original)
meta=dict(original_pam_sha256=hashlib.sha256(original).hexdigest(),original_pam_mode=PAM.stat().st_mode&0o777,
    vendor_sha256=hashlib.sha256(VENDOR.read_bytes()).hexdigest(),
    account_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('/etc/passwd','/etc/group')},
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (GUARD,WRITER,Path(__file__),BASE/'common.py',BASE/'cleanup.py',BASE/'withdrawal.py',BASE/'helper.py',BASE/'worker.py')})
save(meta);passed=False;error=None

def write_roles(rows):
    lines=['LYRA-ROLE-INDEX-V1\n']
    for r in rows:
        lines.append('|'.join(str(r[k]) for k in ('state','user','uid','gid','group','generation'))+'\n')
    fd=os.open(ROLES,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:writer.RegistryStore._atomic(fd,'role-index',''.join(lines).encode())
    finally:os.close(fd)
    run(['restorecon','-R',str(ROLES)])

def write_proof(row,uid=None):
    data=('LYRA-ROLE-INDEX-V1\n'+'|'.join(str(row[k]) for k in ('state','user','uid','gid','group','generation'))+'\n').encode()
    fd=os.open(PROOFS,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:writer.RegistryStore._atomic(fd,str(row['uid'] if uid is None else uid),data)
    finally:os.close(fd)
    run(['restorecon','-R',str(PROOFS)])

def restore_state(data):
    fd=os.open(DIRECTORY,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:writer.RegistryStore._atomic(fd,'identity-registry',data)
    finally:os.close(fd)
    run(['restorecon',str(DIRECTORY/'identity-registry')])
    assert (DIRECTORY/'identity-registry').stat().st_mode&0o777==0o600
    assert (DIRECTORY/'identity-registry').read_bytes()==data

def attempt(name,uid,allowed):
    run(['systemctl','reset-failed',f'user@{uid}.service'],check=False)
    cursor=json.loads(run(['journalctl','-n','1','-o','json'])['stdout'])['__CURSOR']
    child=run(['systemctl','start',f'user@{uid}.service'],check=False);unit=show(uid)
    journal=run(['journalctl','-b','--after-cursor='+cursor,'-u',f'user@{uid}.service','--no-pager','-o','cat'])['stdout']
    ctx=None
    if allowed:
        assert child['rc']==0 and unit['ActiveState']=='active' and int(unit['MainPID'])>0,(name,child,unit,journal)
        ctx=context(uid)
        assert ctx==CONTEXT if uid==1003 else ':unconfined_t:' in ctx,ctx
    else:
        assert child['rc']!=0 and unit['MainPID']=='0' and unit['ExecMainStatus']=='224',(name,child,unit,journal)
        assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in journal,journal
    record(checks,name,uid=uid,allowed=allowed,unit=unit,context=ctx,journal=journal)
    stop(uid);run(['systemctl','stop',f'user-runtime-dir@{uid}.service']);drain(uid,'parentaltest' if uid==1003 else 'ordinaryuser')

def expect(code,action):
    try:action()
    except WithdrawalError as e:assert str(e)==code,(e,code)
    else:raise AssertionError('expected '+code)

def reset_case(ordinary):
    assert show(1002)['MainPID']=='0' and not uid_processes(1002)
    for name in ('.deny-1002','.withdrawal-1002.json'):(PROOFS/name).unlink(missing_ok=True)
    fd=os.open(PROOFS,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    write_proof(ordinary)

try:
    run(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(GUARD),'-o',str(MODULE),'-lpam','-lselinux'])
    MODULE.chmod(0o755);run(['restorecon',str(MODULE)])
    DIRECTORY.mkdir(mode=0o700);run(['restorecon',str(DIRECTORY)])
    ROLES.mkdir(mode=0o700);PROOFS.mkdir(mode=0o700)
    for uid in (1002,1003):
        fd=os.open(PROOFS/f'.gate-{uid}.lock',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.fsync(fd);os.close(fd)
    fd=os.open(PROOFS,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    generation=secrets.token_hex(16);protected=dict(state='active',**IDENTITY,generation=generation)
    ordinary=dict(state='ordinary',user='ordinaryuser',uid=1002,gid=1003,group='ordinaryuser',generation=secrets.token_hex(16))
    writer.RegistryStore(DIRECTORY).seed([protected]);write_roles([protected,ordinary]);write_proof(ordinary);install_pam(generation)
    run(['restorecon','-R',str(PROOFS)]);run(['setenforce','1'])
    attempt('supervised-baseline',1003,True);attempt('ordinary-baseline',1002,True)
    run(['systemctl','start','user@1003.service']);preserved=show(1003)['MainPID'];store=make()
    operation=secrets.token_hex(16);plan=store.plan(1002,operation)
    expect('Denied',lambda:store.begin(plan,lambda _:False))
    assert not (PROOFS/'.deny-1002').exists() and PROOF.exists()
    record(checks,'authorization-denied-no-effects')
    attempt('ordinary-after-denied',1002,True)
    write_proof(dict(ordinary,generation=secrets.token_hex(16)))
    expect('Conflict',lambda:store.begin(plan,lambda _:True))
    assert not (PROOFS/'.deny-1002').exists();write_proof(ordinary)
    record(checks,'stale-proof-conflict-no-marker')
    plan=store.plan(1002,operation)
    with store.lock(1002,False):
        expect('Busy',lambda:store.begin(plan,lambda _:True))
        assert not (PROOFS/'.deny-1002').exists()
    record(checks,'concurrent-reader-prevents-withdrawal-before-effects')
    with store.lock(1002,True):attempt('writer-lock-denies-concurrent-new-admission',1002,False)
    for point in ('marker-synced','journal-synced','proof-unlinked','retired-journal-synced'):
        reset_case(ordinary);operation=secrets.token_hex(16)
        if point=='marker-synced':
            run(['systemctl','start','user@1002.service']);old_pid=show(1002)['MainPID']
        child=run(['/usr/bin/python3',str(BASE/'worker.py'),point,operation],check=False)
        assert child['rc']==91,child
        marker=decode((PROOFS/'.deny-1002').read_bytes());assert marker['operation']==operation
        expected_proof=point in {'marker-synced','journal-synced'}
        assert PROOF.exists()==expected_proof
        record(checks,point+'-crash91-durable-block',worker_rc=child['rc'],proof_exists=PROOF.exists(),marker=marker)
        if point=='marker-synced':
            assert show(1002)['MainPID']==old_pid and old_pid!='0'
            record(checks,'old-ordinary-manager-survives-admission-withdrawal',pid=old_pid,quiescence_proven=False)
            stop(1002);run(['systemctl','stop','user-runtime-dir@1002.service']);drain(1002,'ordinaryuser')
        attempt(point+'-new-ordinary-denied',1002,False)
        before={p.name:p.read_bytes() for p in PROOFS.iterdir()}
        assert store.inspect(1002)=='BlockedUntilAuthorizedRecovery'
        assert before=={p.name:p.read_bytes() for p in PROOFS.iterdir()}
        record(checks,point+'-reconcile-read-only-no-reenrollment')
        expect('Denied',lambda:store.resume(1002,operation,lambda _:False))
        assert store.resume(1002,operation,lambda _:True)=='AdmissionBlockedProofRetiredNoQuiescence'
        journal=decode((PROOFS/'.withdrawal-1002.json').read_bytes())
        assert journal['revision']==2 and journal['phase']=='retired' and not PROOF.exists()
        record(checks,point+'-authorized-resume-remains-blocked',journal=journal)
        before={p.name:p.read_bytes() for p in PROOFS.iterdir()}
        expect('Conflict',lambda:store.resume(1002,secrets.token_hex(16),lambda _:True))
        assert store.resume(1002,operation,lambda _:True)=='AdmissionBlockedProofRetiredNoQuiescence'
        assert before=={p.name:p.read_bytes() for p in PROOFS.iterdir()}
        record(checks,point+'-same-operation-idempotent-conflicting-operation-denied')
    write_proof(ordinary)
    attempt('restored-old-proof-still-denied-by-marker',1002,False)
    assert store.resume(1002,operation,lambda _:True)=='AdmissionBlockedProofRetiredNoQuiescence' and not PROOF.exists()
    record(checks,'authorized-retry-retires-restored-proof-without-reopening')
    write_proof(ordinary);(PROOFS/'.deny-1002').unlink()
    attempt('missing-marker-existing-journal-still-denies',1002,False)
    expect('RecoveryRequired',lambda:store.resume(1002,operation,lambda _:True))
    (PROOFS/'.withdrawal-1002.json').write_bytes(b'corrupt\n')
    attempt('corrupt-journal-still-denies-old-proof',1002,False)
    assert show(1003)['MainPID']==preserved and context(1003)==CONTEXT
    record(checks,'unrelated-supervised-manager-preserved',pid=preserved)
    passed=True
except BaseException as e:error=str(e);raise
finally:
    if ROLES.exists():shutil.rmtree(ROLES)
    if PROOFS.exists():shutil.rmtree(PROOFS)
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=90)
    row=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,
        cleanup_stderr=cleanup.stderr,full_account_protection=False,whole_classification_qualified=False,
        real_nss_mutations_tested=False,all_producer_quiescence=False,real_reboot_tested=False,power_loss_tested=False,
        generation=(generation if 'generation' in globals() else None))
    (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({'passed':row['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}))
    assert cleanup.returncode==0,cleanup.stderr
