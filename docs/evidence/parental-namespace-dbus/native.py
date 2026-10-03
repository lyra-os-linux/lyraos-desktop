from bridge import *
from fixture import *
from live_common import *
from pending_common import *
from proc_inventory import *
from dataclasses import asdict
from namespace import Namespace
from binding import BrokerFence
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
meta['source_sha256'].update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'operations.py',BASE/'inventory.py',BASE/'ownership.py',BASE/'integration.py',BASE/'inventory_fixture.py',BASE/'live_common.py',BASE/'pending_common.py',BASE/'discovery.py',BASE/'proc_inventory.py',BASE/'namespace.py',BASE/'binding.py')})
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
    sources=create_routes();baseline={s:probe(s) for s in PEERS}
    for s,row in baseline.items():record(checks,'baseline-'+s,**row)
    pending={}
    for s in ('TargetUnit','TargetExec'):
        item,pin,client=launch_pending(s);pending[s]=(item,pin,client);pins.append(pin)
        record(checks,'actual-unowned-pending-'+s,descriptor=item,name_has_owner=owner(s))
    catalog_row=prepare_bindings('dbus-activation',[(PREFIX+s,hashlib.sha256(sources[str(service_path(s))].encode()).hexdigest()) for s in TARGET])
    owner_store=factory();operation=secrets.token_hex(16);plan=owner_store.plan(1002,operation)
    owner_store.begin(plan,lambda row:(unlocked_authority() is None));storage=owner_store.withdrawal;target=oc.Target(1002,operation,plan.withdrawal.proof_hash)
    run(['loginctl','terminate-user','1002']);run(['systemctl','stop','user@1002.service','user-runtime-dir@1002.service'])
    spec=importlib.util.spec_from_file_location('manager_adapters',BASE/'manager_adapters.py');ma=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ma;spec.loader.exec_module(ma)
    da=sys.modules['dbus_adapter'];expected_pam=PAM.read_bytes();expected_module=MODULE.read_bytes()
    c=ma.Classification(storage,ma.Identity('ordinaryuser',1002,1003,'ordinaryuser'),ic.identity,lambda:secure(PAM,expected_pam) and secure(MODULE,expected_module) and run(['getenforce'])['stdout'].strip()=='Enforcing')
    routes=tuple(da.Route(PREFIX+s,hashlib.sha256(sources[str(service_path(s))].encode()).hexdigest(),unit_name(s) if systemd(s) else '') for s in TARGET)
    auth=False;effects=[]
    def grant(t,a,r):unlocked_authority();return auth
    def reload():effects.append('reload');return reload_bus()
    def stopping(r):effects.append('drain');return discovery.drain()
    def observing(r):return discovery.empty() and observe(r,pins)
    adapter=da.DBusActivation(c,routes,lambda i,r:catalog(i,r,sources),integration.CheckedRoutes(owned_factory(),target,routes),reload,lambda r:not({x.name for x in r}&activatable()),stopping,observing,grant,settle_seconds=0)
    backend=ProcInventory(sources,lambda:adapter.inhibited(target));discovery=Discovery(1002,[r.name for r in routes],backend,rounds=2)
    owned=owned_factory()
    for r in routes:owned.resume(1002,operation,('dbus-activation',r.name),lambda row:(unlocked_authority() is None))
    ledger_before=ledger_state();proof_before=state();auth=True;assert adapter.inhibit(target) and not adapter.quiescent(target)
    with discovery.capture() as (rows,epoch):captured=[asdict(row) for row,pin in rows]
    assert {row['pid'] for row in captured}=={pending[s][0]['pid'] for s in pending} and set(json.loads(LIVE.read_text()))==set(PEERS)
    record(checks,'automatic-discovery-finds-both-pending-without-live-registration',rows=captured,version=epoch,completed_only_live=list(json.loads(LIVE.read_text())))
    lock=BASE/'sources.lock';assert not lock.exists();lock.write_bytes(b'');lock.chmod(0o600)
    namespace=Namespace([str(SERVICES),str(POLICY.parent)],str(lock))
    unknown=SERVICES/(PREFIX+'Unclassified.service')
    assert not unknown.exists() and not unknown.is_symlink()
    known={PREFIX+s for s in SHORTS}
    def classified():
        active={p.name[:-8] for p in SERVICES.glob(PREFIX+'*.service')}
        retired={p.name.removeprefix('.lyra-withdrawn-') for p in SERVICES.glob('.lyra-withdrawn-'+PREFIX+'*')}
        return active|retired==known
    fence=BrokerFence(namespace,classified,activatable,[PREFIX+s for s in TARGET])
    current=fence.plan();original_version=backend.version
    def version():fence.check(current);return original_version(),current
    backend.version=version
    def add_unknown():
        unknown.write_text('[D-BUS Service]\nName='+PREFIX+'Unclassified\nUser=ordinaryuser\nExec=/usr/bin/sleep 600\n');unknown.chmod(0o644)
        run(['restorecon',str(unknown)])
    def repair_unknown():
        unknown.unlink(missing_ok=True);assert reload_bus()
    record(checks,'root-source-trees-and-loaded-view-bound',roots=current.sources.roots,entry_count=len(current.sources.entries),loaded_names=sorted(current.loaded),lock_inode=lock.stat().st_ino)
    def denied(_):unlocked_authority();return False
    expect('Denied',lambda:fence.execute(current,denied,[lambda:adapter.revoke(target)]));assert not backend.events
    record(checks,'namespace-denial-before-any-native-stop')
    def add_after_auth(_):
        unlocked_authority()
        fd=os.open(lock,os.O_RDONLY)
        try:
            ic.fcntl.flock(fd,ic.fcntl.LOCK_EX|ic.fcntl.LOCK_NB);add_unknown()
        finally:os.close(fd)
        return True
    expect('Conflict',lambda:fence.execute(current,add_after_auth,[lambda:adapter.revoke(target)]))
    assert not backend.events and ledger_state()==ledger_before and state()==proof_before
    record(checks,'source-added-after-authorization-refuses-before-any-native-stop',stop_count=len(backend.events),processes=uid_processes(1002))
    assert reload_bus() and PREFIX+'Unclassified' in activatable()
    expect('UnsupportedProducer',fence.plan)
    record(checks,'already-present-unclassified-loaded-route-refuses-new-plan',loaded=True,stop_count=len(backend.events))
    repair_unknown();current=fence.plan()
    assert fence.check(current) and adapter.inhibited(target) and not uid_processes(1002)==[]
    record(checks,'explicit-root-reconciliation-confirms-disk-and-loaded-view',loaded_names=sorted(current.loaded),ledger=ledger_state())
    real_stop=backend.stop
    def stop_then_add(row):
        result=real_stop(row)
        if len(backend.events)==1:add_unknown() # Explicit trusted-root fault outside writer protocol.
        return result
    backend.stop=stop_then_add
    expect('Conflict',lambda:fence.execute(current,lambda _:True,[lambda:adapter.revoke(target)]))
    assert len(backend.events)==1 and backend.events[0]['result']['rc']==0 and len(uid_processes(1002))==1
    assert ledger_state()==ledger_before and state()==proof_before
    record(checks,'source-added-between-native-stops-prevents-second-stop',events=backend.events.copy(),processes=uid_processes(1002))
    backend.stop=real_stop;repair_unknown();current=fence.plan()
    def guarded_stop(row):
        with lock.open('rb') as f:
            try:ic.fcntl.flock(f,ic.fcntl.LOCK_EX|ic.fcntl.LOCK_NB)
            except BlockingIOError:pass
            else:raise AssertionError('writer EX unexpectedly acquired during effect')
        return real_stop(row)
    backend.stop=guarded_stop
    assert fence.execute(current,lambda _:(unlocked_authority() is None),[lambda:adapter.revoke(target)])==(True,)
    assert adapter.quiescent(target) and not uid_processes(1002) and all(select.select([p],[],[],0)[0] for p in pins)
    record(checks,'fresh-reconciled-plan-drains-native-pending-producers',events=backend.events.copy(),pidfds_exited=len(pins),processes=uid_processes(1002),writer_excluded=True)
    assert namespace.check(current.sources) and fence.check(current)
    record(checks,'post-drain-source-and-loaded-view-revalidated')
    outcomes={}
    for s,(item,pin,client) in pending.items():
        stdout,stderr=client.communicate(timeout=5);outcomes[s]=dict(rc=client.returncode,stdout=stdout,stderr=stderr)
    record(checks,'pending-client-outcomes-recorded',outcomes=outcomes)
    for s in TARGET:
        result=run(['busctl','--system','--timeout=5','call',PREFIX+s,'/org/lyra/ParentalDbusFixture','org.lyra.ParentalDbusFixture','Probe'],check=False)
        assert result['rc'] and any(x in result['stderr'] for x in ('ServiceUnknown','not activatable','not provided by any .service')) and not owner(s)
        record(checks,'retired-route-cannot-reactivate-'+s,command=result)
    assert ledger_state()==ledger_before and state()==proof_before
    assert adapter.inhibit(target) and adapter.revoke(target) and ledger_state()==ledger_before and state()==proof_before
    record(checks,'discovery-and-retries-preserve-owner-and-negative-journals',ledger=ledger_state())
    expect('UnsupportedProducer',lambda:oc.OrdinaryCoordinator(storage,WithdrawalError,{'classification':c,'dbus-activation':adapter})._check(target,False))
    record(checks,'closed-discovery-refuses-global-coverage')
    deny_attempt(checks,'withdrawn-user-manager-remains-denied')
    assert all(probe(s)['pid']==baseline[s]['pid'] for s in PEERS) and ushow('dbus.service')['MainPID']==meta['broker_pid'] and show(1000)['MainPID']==peer_pid and (PROOFS/'1000').read_bytes()==peer_proof
    record(checks,'peer-and-shared-broker-preserved',owners={s:probe(s) for s in PEERS},broker_pid=meta['broker_pid'],peer_pid=peer_pid)
    passed=True
except BaseException as e:error=str(e);raise
finally:
    (SERVICES/(PREFIX+'Unclassified.service')).unlink(missing_ok=True)
    if (BASE/'sources.lock').exists():(BASE/'sources.lock').unlink()
    close_clients()
    for pin in pins:os.close(pin)
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=140)
    row=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,
        owned_live_producer_inhibition_qualified=True,owned_live_producer_revocation_qualified=True,ownership_ledger_reboot_qualified=False,full_account_protection=False,all_producer_quiescence=False,production_adapters_qualified=False,pending_activation_races_qualified=False,closed_pending_activation_pair_tested=True,transport_failure_controls_tested=False,production_pending_discovery_qualified=False,closed_pending_discovery_qualified=True,closed_namespace_guard_qualified=True,global_source_coverage_qualified=False,
        boot_route_recovery_qualified=False,whole_dbus_namespace_qualified=False,real_nss_mutations_tested=False,monotonic_revision_qualified=False,power_loss_tested=False)
    (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({'passed':row['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}));assert cleanup.returncode==0,cleanup.stderr
