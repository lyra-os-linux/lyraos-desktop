from bridge import *
from fixture import *
from live_common import *
from pending_common import *
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
meta['source_sha256'].update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'operations.py',BASE/'inventory.py',BASE/'ownership.py',BASE/'integration.py',BASE/'inventory_fixture.py',BASE/'live_common.py',BASE/'pending_common.py')})
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
    baseline={s:probe(s) for s in PEERS}
    for s,row in baseline.items():record(checks,'baseline-'+s,**row)
    pending={}
    for s in ('TargetUnit','TargetExec'):
        item,pin,client=launch_pending(s);pending[s]=(item,pin,client);pins.append(pin)
        record(checks,'actual-pending-activation-before-name-'+s,descriptor=item,client_pid=client.pid,client_pending=client.poll() is None,name_has_owner=owner(s))
    assert set(json.loads(LIVE.read_text()))==set(PEERS)
    catalog_row=prepare_bindings('dbus-activation',[(PREFIX+s,hashlib.sha256(sources[str(service_path(s))].encode()).hexdigest()) for s in TARGET])
    owner_store=factory();operation=secrets.token_hex(16);plan=owner_store.plan(1002,operation)
    def owner_auth(row):unlocked_authority();return True
    owner_store.begin(plan,owner_auth);storage=owner_store.withdrawal;target=oc.Target(1002,operation,plan.withdrawal.proof_hash)
    run(['loginctl','terminate-user','1002']);run(['systemctl','stop','user@1002.service','user-runtime-dir@1002.service'])
    for item,pin,client in pending.values():verify_descriptor(item,pin);assert client.poll() is None
    record(checks,'withdrawal-does-not-revoke-pending-no-pam-producers',processes=uid_processes(1002))
    spec=importlib.util.spec_from_file_location('manager_adapters',BASE/'manager_adapters.py');ma=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ma;spec.loader.exec_module(ma)
    da=sys.modules['dbus_adapter'];expected_pam=PAM.read_bytes();expected_module=MODULE.read_bytes()
    c=ma.Classification(storage,ma.Identity('ordinaryuser',1002,1003,'ordinaryuser'),ic.identity,lambda:secure(PAM,expected_pam) and secure(MODULE,expected_module) and run(['getenforce'])['stdout'].strip()=='Enforcing')
    routes=tuple(da.Route(PREFIX+s,hashlib.sha256(sources[str(service_path(s))].encode()).hexdigest(),unit_name(s) if systemd(s) else '') for s in TARGET)
    auth=False;reload_fault=False;stop_fault=False;release_in_stop=False;effects=[];faults=[]
    def reload():
        effects.append('reload-config')
        if reload_fault:
            fault=run(['busctl','--address=unix:path=/run/lyra-pending-no-such-bus.sock','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ReloadConfig'],check=False)
            assert fault['rc']!=0;faults.append(fault);return False
        return reload_bus()
    def stopping(r):
        effects.append('stop-payloads')
        if stop_fault:
            fault=run(['busctl','--system','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','StopUnit','ss','invalid/name.service','replace'],check=False)
            assert fault['rc']!=0;faults.append(fault);return False
        if release_in_stop:release(pending['TargetExec'][0],pending['TargetExec'][1])
        return stop_payloads(r)
    auth_calls=[]
    def live_authorize(t,a,r):unlocked_authority();auth_calls.append(a);return auth
    adapter=da.DBusActivation(c,routes,lambda i,r:catalog(i,r,sources),integration.CheckedRoutes(owned_factory(),target,routes),reload,lambda r:not({x.name for x in r}&activatable()),stopping,lambda r:observe(r,pins),live_authorize,settle_seconds=0)
    gate=owned_factory();fence_calls=[]
    def fence_authorize(row):unlocked_authority();fence_calls.append(row['name']);return True
    for r in routes:gate.resume(1002,operation,('dbus-activation',r.name),fence_authorize)
    journal_before=ledger_state();proof_before=state()
    record(checks,'owned-retirements-do-not-discard-existing-pending-requests',records={r.name:ownership.decode(gate.plan(1002,operation,('dbus-activation',r.name)).entry) for r in routes},pending=uid_processes(1002),authorization_callbacks_outside_all_locks=True)
    expect('Denied',lambda:adapter.inhibit(target));assert not effects and ledger_state()==journal_before
    record(checks,'denied-live-inhibition-keeps-owner-and-pending-producers')
    auth=True;reload_fault=True
    expect('UnverifiedAdmission',lambda:adapter.inhibit(target));assert ledger_state()==journal_before
    for item,pin,client in pending.values():verify_descriptor(item,pin)
    record(checks,'reload-transport-failure-refuses-success-retaining-physical-retirements',command=faults[-1],ledger=ledger_state())
    reload_fault=False;assert adapter.inhibit(target) and adapter.inhibited(target) and not adapter.quiescent(target)
    for s in TARGET:assert PREFIX+s not in activatable()
    for s in ('TargetColdUnit','TargetColdExec'):
        result=run(['busctl','--system','--timeout=5','call',PREFIX+s,'/org/lyra/ParentalDbusFixture','org.lyra.ParentalDbusFixture','Probe'],check=False)
        assert result['rc']!=0 and any(x in result['stderr'] for x in ('ServiceUnknown','not activatable','not provided by any .service')) and not owner(s)
        record(checks,'retired-cold-route-denies-new-activation-'+s,command=result)
    record(checks,'successful-reload-does-not-prove-pending-producers-quiescent',processes=uid_processes(1002),pending_names={s:owner(s) for s in pending})
    item,pin,client=pending['TargetUnit'];release(item,pin)
    assert probe('TargetUnit')['pid']==item['pid'] and not adapter.quiescent(target)
    record(checks,'inflight-systemd-payload-can-acquire-name-after-route-retirement',descriptor=item,owner=owner('TargetUnit'),ledger=ledger_state())
    auth=False;before=effects.copy();expect('Denied',lambda:adapter.revoke(target));assert effects==before
    record(checks,'denied-revocation-keeps-live-and-pending-producers')
    auth=True;stop_fault=True
    expect('Busy',lambda:adapter.revoke(target));assert not adapter.quiescent(target) and ledger_state()==journal_before
    record(checks,'actual-stop-request-failure-refuses-quiescence',command=faults[-1],processes=uid_processes(1002))
    stop_fault=False;release_in_stop=True
    # The old fixture only observes completed probes. An Exec producer becoming
    # an owner inside stop is absent from LIVE, so its callback misses it.
    expect('UnverifiedQuiescence',lambda:adapter.revoke(target));release_in_stop=False
    assert select.select([pending['TargetUnit'][1]],[],[],0)[0] and not select.select([pending['TargetExec'][1]],[],[],0)[0]
    assert owner('TargetExec') and 'TargetExec' not in json.loads(LIVE.read_text()) and not adapter.quiescent(target)
    record(checks,'legacy-completed-only-stop-misses-exec-race-but-gate-refuses-success',remaining=uid_processes(1002),descriptor=pending['TargetExec'][0],owner=owner('TargetExec'),ledger=ledger_state())
    item,pin,client=pending['TargetExec'];register_observation(item,pin)
    record(checks,'root-fixture-registers-verified-pinned-exec-observation',descriptor=item,pending_pidfd_still_live=True)
    assert adapter.revoke(target) and adapter.quiescent(target) and adapter.inhibited(target)
    assert not uid_processes(1002) and all(select.select([p],[],[],0)[0] for p in pins)
    record(checks,'authorized-stop-with-pending-observation-revokes-both-payloads',pidfds_exited=len(pins),processes=uid_processes(1002),ledger=ledger_state())
    outcomes={}
    for s,(item,pin,client) in pending.items():
        stdout,stderr=client.communicate(timeout=5);outcomes[s]=dict(rc=client.returncode,stdout=stdout,stderr=stderr)
        if client.returncode==0:assert stdout.split()==['uu','1002',str(item['pid'])]
    record(checks,'original-pending-client-outcomes-archived',outcomes=outcomes)
    for s in TARGET:
        result=run(['busctl','--system','--timeout=5','call',PREFIX+s,'/org/lyra/ParentalDbusFixture','org.lyra.ParentalDbusFixture','Probe'],check=False)
        assert result['rc']!=0 and any(x in result['stderr'] for x in ('ServiceUnknown','not activatable','not provided by any .service')) and not owner(s)
        record(checks,'post-revocation-route-cannot-reactivate-'+s,command=result)
    assert ledger_state()==journal_before and state()==proof_before
    before=effects.copy();assert adapter.inhibit(target) and adapter.revoke(target) and ledger_state()==journal_before and state()==proof_before
    record(checks,'authorized-idempotent-retries-keep-journals-and-negative-authority',ledger=ledger_state())
    partial=oc.OrdinaryCoordinator(storage,WithdrawalError,{'classification':c,'dbus-activation':adapter})
    expect('UnsupportedProducer',lambda:partial._check(target,False));assert state()==proof_before
    record(checks,'pending-closed-catalog-does-not-complete-global-coverage')
    deny_attempt(checks,'withdrawn-user-manager-remains-denied')
    assert all(probe(s)['pid']==baseline[s]['pid'] for s in PEERS) and ushow('dbus.service')['MainPID']==meta['broker_pid'] and show(1000)['MainPID']==peer_pid and (PROOFS/'1000').read_bytes()==peer_proof
    record(checks,'peer-owners-manager-and-shared-broker-survive-pending-matrix',owners={s:probe(s) for s in PEERS},broker_pid=meta['broker_pid'],peer_pid=peer_pid)
    passed=True
except BaseException as e:error=str(e);raise
finally:
    close_clients()
    for pin in pins:os.close(pin)
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=140)
    row=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,
        owned_live_producer_inhibition_qualified=True,owned_live_producer_revocation_qualified=True,ownership_ledger_reboot_qualified=False,full_account_protection=False,all_producer_quiescence=False,production_adapters_qualified=False,pending_activation_races_qualified=False,closed_pending_activation_pair_tested=True,transport_failure_controls_tested=True,production_pending_discovery_qualified=False,
        boot_route_recovery_qualified=False,whole_dbus_namespace_qualified=False,real_nss_mutations_tested=False,monotonic_revision_qualified=False,power_loss_tested=False)
    (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({'passed':row['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}));assert cleanup.returncode==0,cleanup.stderr
