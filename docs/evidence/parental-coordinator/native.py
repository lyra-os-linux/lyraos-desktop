"""Negative coordinator gates with a real PAM manager in the marked VM."""
from common import *
from coordinator import Coordinator,GateError,fingerprint
import secrets,subprocess
checks=[]
assert run(['getenforce'])['stdout'].strip()=='Permissive'
assert not DIRECTORY.exists() and not MODULE.exists() and not UNIT.exists() and not CONFIG.exists()
assert all(show(uid)['MainPID']=='0' and not uid_processes(uid) for uid in (1002,1003))
assert not run(['loginctl','list-sessions','--no-legend'])['stdout'].strip()
assert all(not Path('/var/lib/systemd/linger',n).exists() for n in ('parentaltest','ordinaryuser'))
BASE.mkdir(mode=0o700,exist_ok=True)
for uid,name in ((1003,'parentaltest'),(1002,'ordinaryuser')):drain(uid,name)
original=PAM.read_bytes();(BASE/'original-pam').write_bytes(original)
meta=dict(original_pam_sha256=hashlib.sha256(original).hexdigest(),original_pam_mode=PAM.stat().st_mode&0o777,
    vendor_sha256=hashlib.sha256(VENDOR.read_bytes()).hexdigest(),
    account_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('/etc/passwd','/etc/group')},
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (GUARD,WRITER,Path(__file__),BASE/'common.py',BASE/'coordinator.py',BASE/'cleanup.py')})
save(meta);passed=False;error=None
try:
    run(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(GUARD),'-o',str(MODULE),'-lpam','-lselinux'])
    MODULE.chmod(0o755);run(['restorecon',str(MODULE)])
    DIRECTORY.mkdir(mode=0o700);run(['restorecon',str(DIRECTORY)])
    store=writer.RegistryStore(DIRECTORY);generation=secrets.token_hex(16)
    store.seed([dict(state='active',**IDENTITY,generation=generation)]);install_pam(generation);run(['setenforce','1'])
    run(['systemctl','start','user@1003.service']);assert context(1003)==CONTEXT
    run(['loginctl','enable-linger','ordinaryuser']);wait_state(1002,'active')
    ordinary=show(1002)['MainPID'];managed=show(1003)['MainPID']
    assert int(ordinary)>0 and ':unconfined_t:' in context(1002)
    record(checks,'real-managed-and-ordinary-managers-active',managed=show(1003),ordinary=show(1002),context=context(1003))
    gate=Coordinator(store,writer.StoreError,{})
    # Authorization is a trusted controller fixture, not a Polkit test.
    before=file_state();clean_outcome=gate.reconcile()
    assert clean_outcome=='ExistingAssociationNeedsVerification' and file_state()==before
    record(checks,'clean-reconciliation-neither-blocks-nor-declares-enforcement-verified',outcome=clean_outcome,files_unchanged=True)
    plan=gate.plan(generation);before=file_state()
    try:gate.block_and_check(plan,lambda p,r:False)
    except GateError as e:assert e.code=='Denied'
    else:raise AssertionError('denied caller changed state')
    assert file_state()==before and show(1003)['MainPID']==managed and show(1002)['MainPID']==ordinary
    record(checks,'denied-controller-authorization-has-no-durable-effect',files_unchanged=True,managed_pid=managed,ordinary_pid=ordinary)
    try:gate.block_and_check(plan,lambda p,r:True)
    except GateError as e:assert e.code=='UnsupportedProducer';code=e.code
    else:raise AssertionError('missing coverage passed')
    assert (DIRECTORY/f'.barrier-{generation}').exists() and holders()
    assert show(1003)['MainPID']==managed and show(1002)['MainPID']==ordinary
    record(checks,'missing-adapters-persist-block-with-live-manager',code=code,snapshot=store.snapshot(),holders=holders(),managed_pid=managed,ordinary_pid=ordinary)
    try:store.begin(generation)
    except writer.StoreError as e:assert str(e).startswith('busy: generation has admitted sessions;');busy=str(e)
    else:raise AssertionError('manager lease absent')
    record(checks,'native-lease-remains-busy-after-coordinator-refusal',error=busy,holders=holders())
    stop(1003);drain(1003,'parentaltest');assert not holders() and not uid_processes(1003)
    store.begin(generation) # A bare writer can pass its lease check here.
    record(checks,'exclusive-lease-alone-is-insufficient-for-coordinator',holders=[],snapshot=store.snapshot())
    plan=gate.plan(generation)
    try:gate.block_and_check(plan,lambda p,r:True)
    except GateError as e:assert e.code=='UnsupportedProducer';code=e.code
    else:raise AssertionError('empty leases were mistaken for coverage')
    assert not holders() and (DIRECTORY/f'.barrier-{generation}').exists()
    assert show(1002)['MainPID']==ordinary
    record(checks,'missing-adapters-deny-even-with-no-lease-holders',code=code,snapshot=store.snapshot(),ordinary_pid=ordinary)
    run(['systemctl','reset-failed','user@1003.service'],check=False)
    cursor=json.loads(run(['journalctl','-n','1','-o','json'])['stdout'])['__CURSOR']
    attempt=run(['systemctl','start','user@1003.service'],check=False)
    log=run(['journalctl','-b','--after-cursor='+cursor,'-u','user@1003.service','--no-pager','-o','cat'])['stdout']
    cause='pam_lyra_identity_registry_fixture(systemd-user:session): Experimental registry-backed admission rejected session'
    assert attempt['rc']!=0 and show(1003)['ExecMainStatus']=='224' and show(1003)['MainPID']=='0' and cause in log
    record(checks,'native-pam-denies-manager-after-coordinator-block',unit=show(1003),journal=log,ordinary_pid=ordinary)
    outcome=gate.reconcile();rows,journals=store.snapshot()
    assert outcome=='BlockedUntilAuthorizedRecovery' and rows[0]['state']=='recovering'
    assert (DIRECTORY/f'.barrier-{generation}').exists() and not holders()
    record(checks,'reconciliation-never-reenrolls-blocked-identity',outcome=outcome,snapshot=[rows,journals],barrier_present=True)
    try:gate.plan(generation)
    except GateError as e:assert e.code=='RecoveryRequired';code=e.code
    else:raise AssertionError('recovering identity got a transition plan')
    assert show(1002)['MainPID']==ordinary and ':unconfined_t:' in context(1002)
    record(checks,'recovering-requires-separate-authorized-operation',code=code,ordinary_pid=ordinary,snapshot=store.snapshot())
    passed=True
except BaseException as e:
    error=str(e);raise
finally:
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=90)
    row=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,
        cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,full_account_protection=False,
        production_authorization_tested=False,complete_classification_tested=False,real_producer_adapters_tested=False)
    (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({'passed':row['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}))
    assert cleanup.returncode==0,cleanup.stderr
