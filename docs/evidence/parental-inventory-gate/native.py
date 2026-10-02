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
meta['source_sha256'].update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'fixture.py',BASE/'inventory.py')})
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
    spec=importlib.util.spec_from_file_location('manager_adapters',BASE/'manager_adapters.py');ma=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ma;spec.loader.exec_module(ma)
    spec=importlib.util.spec_from_file_location('inventory_gate',BASE/'inventory.py');ig=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ig;spec.loader.exec_module(ig)
    storage=make();expected_pam=PAM.read_bytes();expected_module=MODULE.read_bytes()
    classification=ma.Classification(storage,ma.Identity('ordinaryuser',1002,1003,'ordinaryuser'),identity,lambda:secure(PAM,expected_pam) and secure(MODULE,expected_module) and run(['getenforce'])['stdout'].strip()=='Enforcing')
    manager=ma.UserManager(classification,run,lambda uid:not uid_processes(uid),lambda t:True)
    originals={'classification':classification,'user-manager':manager}
    digest=hashlib.sha256((BASE/'manager_adapters.py').read_bytes()).hexdigest();guard=hashlib.sha256(GUARD.read_bytes()).hexdigest()
    row=manifest(1002,digest,guard);peerrow=manifest(1000,digest,guard);publish(1002,row);publish(1000,peerrow)
    inventory=ig.Inventory(CATALOG,identity)
    snapshot=inventory.snapshot(1002);assert snapshot.identity.uid==1002 and len(snapshot.producers)==7 and len([p for p in snapshot.producers if p.state=='unsupported'])==5
    record(checks,'root-protected-inventory-records-unsupported-families',revision=snapshot.revision,digest=snapshot.digest,states={p.name:p.state for p in snapshot.producers})
    calls=[];prompt=[]
    class Trace:
        def __init__(self,real):self.real=real
        def invoke(self,m,t):calls.append(m);return getattr(self.real,m)(t)
        def inhibit(self,t):return self.invoke('inhibit',t)
        def revoke(self,t):return self.invoke('revoke',t)
        def inhibited(self,t):return self.invoke('inhibited',t)
        def quiescent(self,t):return self.invoke('quiescent',t)
    adapters={n:Trace(a) for n,a in originals.items()}
    bindings={n:ig.Binding(a,lambda:digest,lambda ident,routes:identity(ident)) for n,a in adapters.items()}
    coord=oc.OrdinaryCoordinator(storage,WithdrawalError,adapters);gate=ig.InventoryGate(inventory,coord,bindings)
    def authorization(p,r):prompt.append('called');return True
    before=state();expect('UnverifiedCoverage',lambda:gate.plan(1002,secrets.token_hex(16)));assert state()==before and not calls and not prompt
    record(checks,'whole-account-preflight-refuses-partial-catalog-without-authority-effects')
    claimed=json.loads(json.dumps(row))
    for name,p in claimed['producers'].items():
        if p['state']=='unsupported':p.update(state='registered',routes=[dict(id=name+'-claimed',digest='d'*64)])
    publish(1002,claimed)
    expect('UnverifiedCoverage',lambda:gate.plan(1002,secrets.token_hex(16)));assert state()==before and not calls and not prompt
    record(checks,'seven-registered-family-names-do-not-issue-whole-coverage')
    operation=secrets.token_hex(16);innerplan=coord.plan(1002,operation);candidate=ig.Plan(innerplan,inventory.snapshot(1002),'whole-account')
    expect('UnverifiedCoverage',lambda:gate.block_and_check(candidate,authorization,revoke=True));assert not prompt and not calls and state()==before
    record(checks,'forced-candidate-cannot-bypass-whole-coverage-check')
    changed=json.loads(json.dumps(claimed));changed['revision']=2;publish(1002,changed)
    expect('Conflict',lambda:gate.block_and_check(candidate,authorization));assert not calls and not prompt and state()==before
    record(checks,'stale-revision-rejected-before-authorization-or-withdrawal')
    changed=json.loads(json.dumps(claimed));changed['producers']['cron']['routes'][0]['digest']='e'*64;publish(1002,changed)
    expect('Conflict',lambda:gate.block_and_check(candidate,authorization));assert state()==before
    record(checks,'changed-route-digest-rejected-without-revision-bump')
    changed=json.loads(json.dumps(claimed));changed['identity']['group']='installeduser';publish(1002,changed)
    expect('InvalidIdentity',lambda:inventory.snapshot(1002));assert state()==before
    record(checks,'divergent-full-nss-tuple-rejected')
    changed=json.loads(json.dumps(claimed));changed['producers']['cron']['state']='complete';publish(1002,changed)
    expect('UnverifiedCoverage',lambda:inventory.snapshot(1002));assert state()==before
    record(checks,'configuration-cannot-self-assert-complete-coverage')
    changed=json.loads(json.dumps(row));del changed['producers']['cron'];publish(1002,changed)
    expect('UnsupportedProducer',lambda:inventory.snapshot(1002))
    record(checks,'missing-required-family-rejected')
    changed=json.loads(json.dumps(row));changed['producers']['at']=dict(state='unsupported',adapter_digest='0'*64,routes=[]);publish(1002,changed)
    expect('UnknownProducer',lambda:inventory.snapshot(1002))
    record(checks,'extra-unrecognized-family-rejected')
    publish(1002,row);p=CATALOG/'1002.json'
    p.chmod(0o640)
    try:expect('UnsafeInventory',lambda:inventory.snapshot(1002))
    finally:p.chmod(0o600)
    record(checks,'group-readable-inventory-refused')
    link=CATALOG/'hardlink';os.link(p,link)
    try:expect('UnsafeInventory',lambda:inventory.snapshot(1002))
    finally:link.unlink()
    record(checks,'inventory-hardlink-refused')
    p.unlink();p.symlink_to('/etc/passwd')
    try:expect('UnsafeInventory',lambda:inventory.snapshot(1002))
    finally:p.unlink();publish(1002,row)
    record(checks,'inventory-symlink-refused-without-reading-target')
    p.write_bytes(b'x'*65537);p.chmod(0o600)
    try:expect('UnsafeInventory',lambda:inventory.snapshot(1002))
    finally:publish(1002,row)
    record(checks,'oversized-inventory-refused')
    p.write_bytes(b'{"schema":1,"schema":1}\n')
    try:expect('InvalidInventory',lambda:inventory.snapshot(1002))
    finally:publish(1002,row)
    record(checks,'duplicate-json-key-refused')
    lock=CATALOG/'.inventory-1002.lock';saved=lock.stat().st_ino;lock.rename(CATALOG/'saved-lock')
    try:expect('UnknownInventory',lambda:inventory.snapshot(1002));assert not lock.exists()
    finally:(CATALOG/'saved-lock').rename(lock)
    assert lock.stat().st_ino==saved
    record(checks,'missing-lock-refused-without-recreating-lock')
    fd=os.open(lock,os.O_RDONLY);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    try:
        expect('Busy',lambda:inventory.snapshot(1002));peer_snapshot=inventory.snapshot(1000);assert peer_snapshot.identity.uid==1000 and show(1000)['MainPID']==peer_pid
    finally:os.close(fd)
    record(checks,'busy-target-inventory-lock-does-not-block-peer-read')
    with inventory.locked(1002):
        try:publish(1002,row)
        except BlockingIOError:pass
        else:raise AssertionError('writer bypassed shared inventory lock')
        assert inventory.snapshot(1000)==peer_snapshot
    record(checks,'cooperating-writer-cannot-replace-live-target-snapshot')
    CATALOG.chmod(0o750)
    try:expect('UnsafeInventory',lambda:inventory.snapshot(1002))
    finally:CATALOG.chmod(0o700)
    record(checks,'group-accessible-inventory-directory-refused')
    publish(1002,row);assert state()==before and show(1000)['MainPID']==peer_pid and show(1002)['MainPID']==old_pid and not calls and not prompt
    record(checks,'all-preflight-refusals-preserve-ordinary-managers-and-proofs',peer_pid=peer_pid,target_pid=old_pid,authorization_calls=len(prompt),adapter_calls=len(calls))
    # Previously withdrawn accounts must keep their negative authority too.
    storage.begin(innerplan,lambda p:True)
    negative_before=state();expect('UnverifiedCoverage',lambda:gate.plan(1002,operation));assert state()==negative_before and not prompt and not calls
    record(checks,'inventory-refusal-never-removes-existing-withdrawal-authority')
    passed=True
except BaseException as e:error=str(e);raise
finally:
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=140)
    result=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,
        full_account_protection=False,whole_namespace_inventory_qualified=False,complete_coverage_issuer_implemented=False,
        production_adapters_qualified=False,global_monotonic_revision_qualified=False,anti_rollback_qualified=False,power_loss_tested=False,real_nss_mutations_tested=False,all_producer_quiescence=False)
    (BASE/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}));assert cleanup.returncode==0,cleanup.stderr
