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
meta['source_sha256'].update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'fixture.py',BASE/'dbus-adapter.py',BASE/'service.c')})
meta['broker_pid']=ushow('dbus.service')['MainPID'];assert int(meta['broker_pid'])>0
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
    sources=create_routes()
    baseline={s:probe(s) for s in ('TargetUnit','TargetExec','PeerUnit','PeerExec')}
    for s,row in baseline.items():record(checks,'baseline-'+s,**row)
    assert {PREFIX+s for s in SHORTS}<=activatable()
    storage=make();operation=secrets.token_hex(16);plan=storage.plan(1002,operation);storage.begin(plan,lambda p:True);target=oc.Target(1002,operation,plan.proof_hash)
    run(['loginctl','terminate-user','1002']);run(['systemctl','stop','user@1002.service','user-runtime-dir@1002.service'])
    for s in ('TargetUnit','TargetExec'):assert probe(s)['pid']==baseline[s]['pid']
    record(checks,'withdrawal-and-logind-leave-dbus-payloads-alive')
    for s in ('TargetUnit','TargetExec'):pins.append(os.pidfd_open(baseline[s]['pid']))
    spec=importlib.util.spec_from_file_location('manager_adapters',BASE/'manager_adapters.py');ma=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ma;spec.loader.exec_module(ma)
    spec=importlib.util.spec_from_file_location('dbus_adapter',BASE/'dbus-adapter.py');da=importlib.util.module_from_spec(spec);sys.modules[spec.name]=da;spec.loader.exec_module(da)
    expected_pam=PAM.read_bytes();expected_module=MODULE.read_bytes()
    def identity(i):
        a=pwd.getpwnam(i.user);g=grp.getgrnam(i.group);return (a.pw_uid,a.pw_gid,g.gr_gid)==(i.uid,i.gid,i.gid)
    c=ma.Classification(storage,ma.Identity('ordinaryuser',1002,1003,'ordinaryuser'),identity,lambda:secure(PAM,expected_pam) and secure(MODULE,expected_module) and run(['getenforce'])['stdout'].strip()=='Enforcing')
    routes=tuple(da.Route(PREFIX+s,hashlib.sha256(sources[str(service_path(s))].encode()).hexdigest(),unit_name(s) if systemd(s) else '') for s in TARGET)
    auth=False;effects=[]
    def reload():effects.append('reload-config');return reload_bus()
    def stopping(r):effects.append('stop-payloads');return stop_payloads(r)
    adapter=da.DBusActivation(c,routes,lambda i,r:catalog(i,r,sources),da.RetiredRoutes(SERVICES),reload,lambda r:not({x.name for x in r}&activatable()),stopping,lambda r:observe(r,pins),lambda t,a,r:auth)
    expect('Denied',lambda:adapter.inhibit(target));assert not effects and all(service_path(s).exists() and not retired_path(s).exists() for s in TARGET)
    record(checks,'inhibition-denied-without-retirement-or-bus-effects')
    auth=True;unknown=SERVICES/(PREFIX+'TargetUnknown.service');unknown.write_text(sources[str(service_path('TargetUnit'))]);unknown.chmod(0o644)
    try:expect('UnverifiedProducerCatalog',lambda:adapter.inhibit(target));assert not effects
    finally:unknown.unlink()
    record(checks,'unregistered-route-refused-even-before-activation')
    p=service_path('TargetUnit');original=p.read_bytes();p.write_bytes(original+b'\n')
    try:expect('UnverifiedProducerCatalog',lambda:adapter.inhibit(target));assert not effects
    finally:p.write_bytes(original)
    record(checks,'changed-definition-refused-before-inhibition')
    assert adapter.inhibit(target) and adapter.inhibited(target) and not adapter.quiescent(target)
    assert all(not service_path(s).exists() and retired_path(s).exists() for s in TARGET)
    for s in ('TargetUnit','TargetExec'):assert probe(s)['pid']==baseline[s]['pid']
    record(checks,'persisted-route-retirement-and-reload-preserve-existing-owners',effects=effects.copy(),activatable=sorted(n for n in activatable() if n.startswith(PREFIX)))
    for s in ('TargetColdUnit','TargetColdExec'):
        r=run(['busctl','--system','--timeout=5','call',PREFIX+s,'/org/lyra/ParentalDbusFixture','org.lyra.ParentalDbusFixture','Probe'],check=False)
        assert r['rc'] and any(x in r['stderr'] for x in ('ServiceUnknown','not activatable','not provided by any .service')) and not owner(s),r
        record(checks,'cold-route-denied-'+s,command=r)
    auth=False;before=effects.copy();expect('Denied',lambda:adapter.revoke(target));assert effects==before and probe('TargetExec')['pid']==baseline['TargetExec']['pid']
    record(checks,'revocation-denied-preserves-live-processes-and-fences')
    auth=True;assert adapter.revoke(target) and adapter.quiescent(target);assert effects==['reload-config','stop-payloads']
    assert all(probe(s)['pid']==baseline[s]['pid'] for s in PEERS) and ushow('dbus.service')['MainPID']==meta['broker_pid'] and show(1000)['MainPID']==peer_pid and (PROOFS/'1000').read_bytes()==peer_proof
    record(checks,'registered-payloads-revoked-after-inhibition-peer-and-broker-preserved',effects=effects.copy(),pidfds_exited=len(pins),target_processes=uid_processes(1002),broker_pid=meta['broker_pid'])
    for s in TARGET:
        r=run(['busctl','--system','--timeout=5','call',PREFIX+s,'/org/lyra/ParentalDbusFixture','org.lyra.ParentalDbusFixture','Probe'],check=False)
        assert r['rc'] and any(x in r['stderr'] for x in ('ServiceUnknown','not activatable','not provided by any .service')) and not owner(s),r
        record(checks,'retired-route-cannot-reactivate-'+s,command=r)
    # A restored definition invalidates admission, even with no running owner.
    p=service_path('TargetExec');p.write_text(sources[str(p)]);p.chmod(0o644)
    try:expect('UnverifiedProducerCatalog',lambda:adapter.quiescent(target));assert not uid_processes(1002)
    finally:p.unlink()
    record(checks,'restored-definition-refused-even-with-zero-target-processes')
    before=state();assert adapter.inhibit(target) and adapter.revoke(target) and state()==before
    record(checks,'idempotent-retirement-and-revocation-retain-negative-authority')
    gate=oc.OrdinaryCoordinator(storage,WithdrawalError,{'classification':c,'dbus-activation':adapter})
    expect('UnsupportedProducer',lambda:gate.resume_and_check(1002,operation,lambda p,r:True,revoke=True));record(checks,'registered-dbus-routes-do-not-complete-global-coverage')
    deny_attempt(checks,'withdrawn-user-manager-remains-denied')
    assert all(probe(s)['pid']==baseline[s]['pid'] for s in PEERS) and ushow('dbus.service')['MainPID']==meta['broker_pid']
    record(checks,'peer-owners-and-shared-bus-survive-whole-matrix')
    passed=True
except BaseException as e:error=str(e);raise
finally:
    for pin in pins:os.close(pin)
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=140)
    row=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,
        full_account_protection=False,all_producer_quiescence=False,production_adapters_qualified=False,pending_activation_races_qualified=False,
        boot_route_recovery_qualified=False,whole_dbus_namespace_qualified=False,real_nss_mutations_tested=False,monotonic_revision_qualified=False,power_loss_tested=False)
    (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({'passed':row['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}));assert cleanup.returncode==0,cleanup.stderr
