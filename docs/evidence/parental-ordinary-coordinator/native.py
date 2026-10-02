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
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (GUARD,WRITER,Path(__file__),BASE/'common.py',BASE/'helper.py',BASE/'state.py',BASE/'bridge.py',BASE/'withdrawal.py',BASE/'coordinator.py',BASE/'ordinary-coordinator.py',BASE/'race-worker.py',BASE/'cleanup.py',BASE/'restore-check.py')})
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
    g=gate();operation=secrets.token_hex(16);plan=g.plan(1002,operation);before=state()
    expect('Denied',lambda:g.block_and_check(plan,lambda p,r:False));assert state()==before
    record(checks,'coordinator-denied-no-storage-effects')
    expect('UnsupportedProducer',lambda:g.block_and_check(plan,lambda p,r:True))
    assert g.state(1002)=='BlockedUntilAuthorizedRecovery' and not (PROOFS/'1002').exists()
    assert show(1002)['MainPID']==old_pid and show(1000)['MainPID']==peer_pid
    record(checks,'missing-producers-blocked-but-old-manager-still-active',pid=old_pid,peer_pid=peer_pid,quiescence_proven=False)
    stop_target();deny_attempt(checks,'post-gate-new-admission-denied-peer-preserved')
    expect('UnsupportedProducer',lambda:g.resume_and_check(1002,operation,lambda p,r:True))
    record(checks,'zero-target-processes-still-require-all-producers')
    for round_no in range(3):
        reset_case();release=BASE/f'round-{round_no}.go';release.unlink(missing_ok=True)
        operations=[secrets.token_hex(16),secrets.token_hex(16)]
        workers=[subprocess.Popen(['/usr/bin/python3',str(BASE/'race-worker.py'),op,release.name],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for op in operations]
        try:
            end=time.monotonic()+25
            while not all((BASE/('ready-'+op+'.json')).exists() for op in operations) and time.monotonic()<end:time.sleep(.01)
            ready=[json.loads((BASE/('ready-'+op+'.json')).read_text()) for op in operations]
            assert ready[0]['digest']==ready[1]['digest'] and ready[0]['proof_hash']==ready[1]['proof_hash']
            release.write_text('go\n')
            output=[p.communicate(timeout=30) for p in workers]
            assert all(p.returncode==0 for p in workers),output
            results=[json.loads((BASE/('race-'+op+'.json')).read_text()) for op in operations]
            winners=[x for x in results if x['code']=='UnsupportedProducer']
            losers=[x for x in results if x['code'] in {'Busy','Conflict'}]
            assert len(winners)==len(losers)==1,results
            marker=decode((PROOFS/'.deny-1002').read_bytes());journal=decode((PROOFS/'.withdrawal-1002.json').read_bytes())
            assert marker['operation']==journal['operation']==winners[0]['operation'] and not (PROOFS/'1002').exists()
            assert journal['revision']==2 and show(1000)['MainPID']==peer_pid and (PROOFS/'1000').read_bytes()==peer_proof
            record(checks,f'race-{round_no}-one-operation-persisted',ready=ready,workers=results,worker_rc=[p.returncode for p in workers],marker=marker,journal=journal,peer_pid=peer_pid)
            before=state()
            expect('Conflict',lambda:g.resume_and_check(1002,losers[0]['operation'],lambda p,r:True))
            expect('UnsupportedProducer',lambda:g.resume_and_check(1002,winners[0]['operation'],lambda p,r:True))
            assert state()==before
            record(checks,f'race-{round_no}-loser-rejected-winner-retry-blocked')
            deny_attempt(checks,f'race-{round_no}-new-target-denied-peer-preserved')
        finally:
            for p in workers:
                if p.poll() is None:p.kill();p.communicate(timeout=10)
    # A held target lock must not block another UID's fresh native admission.
    stop(1000);run(['systemctl','stop','user-runtime-dir@1000.service']);drain(1000,'installeduser')
    with make().lock(1002,True):
        peer_plan=g.plan(1000,secrets.token_hex(16))
        expect('Denied',lambda:g.block_and_check(peer_plan,lambda p,r:False))
        run(['systemctl','start','user@1000.service']);assert context(1000).startswith('unconfined_u:unconfined_r:unconfined_t:')
        assert (PROOFS/'1000').read_bytes()==peer_proof
        record(checks,'held-target-lock-other-uid-plan-and-native-admission-independent',unit=show(1000),context=context(1000))
    passed=True
except BaseException as e:error=str(e);raise
finally:
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=100)
    row=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,
        full_account_protection=False,whole_classification_qualified=False,all_producer_quiescence=False,real_nss_mutations_tested=False,
        production_adapters_qualified=False,monotonic_revision_qualified=False,power_loss_tested=False)
    (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({'passed':row['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}))
    assert cleanup.returncode==0,cleanup.stderr
