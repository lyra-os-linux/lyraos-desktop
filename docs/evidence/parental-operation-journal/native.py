from bridge import *
from fixture import *
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
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (GUARD,WRITER,Path(__file__),BASE/'common.py',BASE/'helper.py',BASE/'state.py',BASE/'bridge.py',BASE/'withdrawal.py',BASE/'coordinator.py',BASE/'ordinary-coordinator.py',BASE/'manager_adapters.py',BASE/'cleanup.py',BASE/'restore-check.py')})
meta['source_sha256'].update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'fixture.py',BASE/'inventory.py',BASE/'operations.py',BASE/'child.py',BASE/'op-common.py')})
save(meta);passed=False;error=None;pins=[]

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
    create_inventory()
    exec((BASE/'op-common.py').read_text())
    descriptor=hashlib.sha256((BASE/'manager_adapters.py').read_bytes()).hexdigest();guard=hashlib.sha256(GUARD.read_bytes()).hexdigest()
    catalog=manifest(1002,descriptor,guard);publish(1002,catalog);publish(1000,manifest(1000,descriptor,guard))
    stop_target()
    owner=factory();peer_catalog=(CATALOG/'1000.json').read_bytes();peer_files=state()['1000']
    def reset_owned():
        assert show(1002)['MainPID']=='0' and not uid_processes(1002)
        for n in ('.deny-1002','.withdrawal-1002.json','.operation-1002.json'):(PROOFS/n).unlink(missing_ok=True)
        fd=os.open(PROOFS,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
        write_rows(PROOFS,'1002',[ordinary]);publish(1002,catalog)
    def owned_state():return state()
    def peer_preserved():return show(1000)['MainPID']==peer_pid and state()['1000']==peer_files and (CATALOG/'1000.json').read_bytes()==peer_catalog
    points=('intent-marker-synced','owned-intent-synced','legacy-marker-synced','legacy-journal-synced','owned-blocked-synced','proof-unlinked','retired-journal-synced','owned-retired-synced')
    crashes=[]
    for point in points:
        reset_owned();operation=secrets.token_hex(16);plan=owner.plan(1002,operation);expected=owner._record(plan)
        child=run(['/usr/bin/python3',str(BASE/'child.py'),operation,point],check=False);assert child['rc']==91 and not child['stderr'],child
        marker=(PROOFS/'.deny-1002').read_bytes();assert marker
        status=owner.inspect(1002);assert status in ('BlockedRecoveryRequired','AdmissionWithdrawnNoQuiescence')
        record(checks,'crash-fence-'+point,point=point,child_rc=child['rc'],status=status,marker_sha256=hashlib.sha256(marker).hexdigest())
        deny_attempt(checks,'pam-denies-after-crash-'+point)
        before=owned_state();expect('Conflict',lambda:owner.resume(1002,secrets.token_hex(16),lambda row:(_ for _ in ()).throw(AssertionError('prompted'))));assert owned_state()==before
        expect('Denied',lambda:owner.resume(1002,operation,lambda row:False));assert owned_state()==before
        changed=dict(catalog,revision=2);publish(1002,changed)
        expect('Conflict',lambda:owner.resume(1002,operation,lambda row:(_ for _ in ()).throw(AssertionError('prompted'))));assert owned_state()==before
        publish(1002,catalog)
        # Only private fixture metadata is explicitly restored by the driver;
        # the operations API itself has no catalog rollback/repair method.
        fresh=factory();assert fresh.resume(1002,operation,lambda row:True)=='AdmissionWithdrawnNoQuiescence'
        done=ops.decode((PROOFS/'.operation-1002.json').read_bytes());assert ops.same_owner(done,expected) and done['phase']=='retired' and done['revision']==3 and not(PROOFS/'1002').exists()
        legacy_marker=__import__('withdrawal').decode((PROOFS/'.deny-1002').read_bytes());legacy_journal=__import__('withdrawal').decode((PROOFS/'.withdrawal-1002.json').read_bytes());assert legacy_marker['phase']=='blocked' and legacy_journal['phase']=='retired' and legacy_journal['proof_hash']==expected['proof_hash']
        before=owned_state();assert fresh.resume(1002,operation,lambda row:True)=='AdmissionWithdrawnNoQuiescence' and owned_state()==before and peer_preserved()
        record(checks,'fresh-authorized-resume-'+point,point=point,status=fresh.inspect(1002),owner_operation=done['operation'],owner_revision=done['revision'],proof_absent=True,peer_preserved=True)
        crashes.append(dict(point=point,operation=operation,child_rc=child['rc']))
    record(checks,'eight-subprocess-crashes-never-open-admission',crashes=crashes,peer_pid=peer_pid,peer_proof_sha256=hashlib.sha256(peer_proof).hexdigest())
    # Unsafe owner metadata and root maintenance divergence stay blocked.
    before=owned_state();p=PROOFS/'.operation-1002.json';original=p.read_bytes();p.write_bytes(b'{}')
    expect('InvalidOperationJournal',lambda:owner.resume(1002,crashes[-1]['operation'],lambda row:True));assert (PROOFS/'.deny-1002').read_bytes()==__import__('withdrawal').encode(legacy_marker)
    p.write_bytes(original)
    record(checks,'corrupt-owner-refused-without-changing-barrier')
    write_rows(PROOFS,'1002',[ordinary]);expect('RecoveryRequired',lambda:owner.resume(1002,crashes[-1]['operation'],lambda row:True));assert(PROOFS/'1002').exists()
    record(checks,'recreated-proof-after-retirement-is-never-removed-by-resume')
    (PROOFS/'1002').unlink();fd=os.open(PROOFS,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    marker=PROOFS/'.deny-1002';original_marker=marker.read_bytes();marker.unlink()
    expect('RecoveryRequired',lambda:owner.resume(1002,crashes[-1]['operation'],lambda row:True));assert not marker.exists() and(PROOFS/'.withdrawal-1002.json').exists()
    marker.write_bytes(original_marker);marker.chmod(0o600)
    record(checks,'missing-marker-not-reconstructed-from-owner-record')
    before=owned_state();assert owner.inspect(1002)=='AdmissionWithdrawnNoQuiescence' and owned_state()==before and peer_preserved()
    record(checks,'inspection-read-only-and-peer-manager-preserved')
    passed=True
except BaseException as e:error=str(e);raise
finally:
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=140)
    result=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,
        full_account_protection=False,all_producer_quiescence=False,production_journal_qualified=False,global_monotonic_revision_qualified=False,anti_rollback_qualified=False,power_loss_tested=False,kernel_reboot_tested=False,real_nss_mutations_tested=False,producer_revocation_tested=False)
    (BASE/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}));assert cleanup.returncode==0,cleanup.stderr
