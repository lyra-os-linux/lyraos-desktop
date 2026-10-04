from bridge import *
from fixture import *
from live_common import *
import secrets,shutil,subprocess
from guard import GuardedExecution,MaskedSources
from linux import Linux
import support as typed
from effects import Effects
from jobs import StopJobs
from backend import NativeStopBackend
EFFECT_DIR=Path("/var/lib/lyra-unit-stop-effects-test")
SENDER=Path("/usr/libexec/lyra-unit-stop-jobs-drop-stop")
PROBE=Path('/usr/libexec/lyra-unit-stop-jobs-probe')
assert not any(p.exists() or p.is_symlink() for p in (PROBE,SENDER,EFFECT_DIR))
SELECTED=(TARGET_UNITS[0],TARGET_UNITS[2],TARGET_UNITS[3])
checks=[]
assert run(['getenforce'])['stdout'].strip()=='Permissive'
assert not any(p.exists() for p in (DIRECTORY,MODULE,UNIT,ROLES,PROOFS))
assert not run(['loginctl','list-sessions','--no-legend'])['stdout'].strip()
assert all(show(uid)['MainPID']=='0' and not uid_processes(uid) for uid in (1000,1002,1003))
assert not any(Path('/var/lib/systemd/linger',n).exists() for n in ('installeduser','ordinaryuser','parentaltest'))
BASE.mkdir(mode=0o700,exist_ok=True)
for uid,name in ((1000,'installeduser'),(1002,'ordinaryuser'),(1003,'parentaltest')):drain(uid,name)
original=PAM.read_bytes();(BASE/'original-pam').write_bytes(original)
meta=dict(original_pam_sha256=hashlib.sha256(original).hexdigest(),original_pam_mode=PAM.stat().st_mode&0o777,
    vendor_sha256=hashlib.sha256(VENDOR.read_bytes()).hexdigest(),account_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('/etc/passwd','/etc/group')},
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (GUARD,WRITER,Path(__file__),BASE/'common.py',BASE/'helper.py',BASE/'state.py',BASE/'bridge.py',BASE/'withdrawal.py',BASE/'coordinator.py',BASE/'ordinary-coordinator.py',BASE/'manager_adapters.py',BASE/'cleanup.py',BASE/'restore-check.py')})
meta['source_sha256'].update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'fixture.py',BASE/'unit-adapter.py')})
meta['source_sha256'].update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'operations.py',BASE/'inventory.py',BASE/'ownership.py',BASE/'integration.py',BASE/'inventory_fixture.py',BASE/'live_common.py')})
meta['source_sha256'].update({n:hashlib.sha256((BASE/n).read_bytes()).hexdigest() for n in ('guard.py','running.py','linux.py','support.py','reference.py','namespace.py','catalog.py','probe.c','drop-stop.c','effects.py','jobs.py','backend.py')})
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
    sources=create_units()
    run(['cc','-Wall','-Wextra','-Werror','-O2',str(BASE/'probe.c'),'-o',str(PROBE)]);PROBE.chmod(0o755)
    run(['cc','-Wall','-Wextra','-Werror','-O2',str(BASE/'drop-stop.c'),'-o',str(SENDER),'-lsystemd']);SENDER.chmod(0o755);run(['restorecon',str(SENDER)])
    sources[TARGET_UNITS[0]]=sources[TARGET_UNITS[0]].replace(b'/usr/bin/sleep 600',str(PROBE).encode())
    (VENDOR_UNITS/TARGET_UNITS[0]).write_bytes(sources[TARGET_UNITS[0]]);run(['restorecon',str(PROBE)]);run(['systemctl','daemon-reload'])
    for n in (TARGET_UNITS[0],TARGET_UNITS[3],PEER_UNITS[0],PEER_UNITS[2]):run(['systemctl','start',n])
    baseline={n:wait_active(n) for n in (TARGET_UNITS[0],TARGET_UNITS[2],PEER_UNITS[0],PEER_UNITS[1])}
    for name,row in baseline.items():
        uid=1002 if name in TARGET_UNITS else 1000
        assert '/system.slice/' in row['ControlGroup'] and int(row['MainPID'])>0
        assert next(x for x in scoped_processes((name,)) if x['pid']==int(row['MainPID']))['uids']==[uid]*4
        record(checks,'baseline-'+name,unit=row)
    catalog_row=prepare_bindings('system-units',[(n,hashlib.sha256(sources[n]).hexdigest()) for n in SELECTED])
    owner=factory();operation=secrets.token_hex(16);plan=owner.plan(1002,operation);owner.begin(plan,lambda _:True);storage=owner.withdrawal
    target=oc.Target(1002,operation,plan.withdrawal.proof_hash)
    # Native logind cannot revoke unguarded system.slice User= producers.
    run(['loginctl','terminate-user','1002']);run(['systemctl','stop','user@1002.service','user-runtime-dir@1002.service'])
    for name in (TARGET_UNITS[0],TARGET_UNITS[2]):assert unit_show(name)['MainPID']==baseline[name]['MainPID']
    record(checks,'logind-withdrawal-does-not-revoke-no-pam-system-producers',units={n:unit_show(n) for n in TARGET_UNITS})
    inv=scoped_processes(TARGET_UNITS)
    for row in inv:pins.append(os.pidfd_open(row['pid']))
    record(checks,'registered-system-scope-processes-pinned',processes=inv,pidfds=len(pins))
    spec=importlib.util.spec_from_file_location('manager_adapters',BASE/'manager_adapters.py');ma=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ma;spec.loader.exec_module(ma)
    spec=importlib.util.spec_from_file_location('unit_adapter',BASE/'unit-adapter.py');ua=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ua;spec.loader.exec_module(ua)
    expected_pam=PAM.read_bytes();expected_module=MODULE.read_bytes()
    def secure(p,expected):
        s=p.lstat();return stat.S_ISREG(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022 and s.st_nlink==1 and p.read_bytes()==expected
    def identity(i):
        a=pwd.getpwnam(i.user);g=grp.getgrnam(i.group);return (a.pw_uid,a.pw_gid,g.gr_gid)==(i.uid,i.gid,i.gid)
    c=ma.Classification(storage,ma.Identity('ordinaryuser',1002,1003,'ordinaryuser'),identity,lambda:secure(PAM,expected_pam) and secure(MODULE,expected_module) and run(['getenforce'])['stdout'].strip()=='Enforcing')
    all_units=tuple(ua.Unit(n,'timer',n[:-6]+'.service') if n.endswith('.timer') else ua.Unit(n,'service') for n in TARGET_UNITS)
    units=tuple(u for u in all_units if u.name in SELECTED)
    authorization=False;commands=[];job_controller=None
    def execute(args):
        commands.append(list(args))
        return job_controller(args) if args[:2]==['systemctl','stop'] else run(args,check=False)
    change_catalog=False;auth_checks=[]
    def live_authorize(t,a,u):
        unlocked_authority();auth_checks.append(a)
        if change_catalog:ic.publish(1002,dict(catalog_row,revision=2))
        return authorization
    refs={u.name:typed.capture(u.name,typed.properties,typed.user,typed.group,typed.fingerprint) for u in units if u.kind=='service'}
    record(checks,'references-captured-before-owned-masks',references={n:__import__('dataclasses').asdict(r) for n,r in refs.items()},excluded_guarded_service=TARGET_UNITS[1])
    checked_masks=integration.CheckedMasks(owned_factory(),target,SELECTED)
    def fenced(name):return checked_masks.masked(name) is True and unit_show(name)['LoadState']=='masked'
    def props(name):return {k:v for k,v in typed.properties(name).items() if k in ('Id','Names','LoadState','FragmentPath','NeedDaemonReload')}
    def runtime(name):
        output=__import__('json').loads(typed.run(['busctl','--system','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','LoadUnit','s',name]))
        assert output['type']=='o' and len(output['data'])==1
        return {n:json.loads(typed.run(['busctl','--system','--json=short','get-property','org.freedesktop.systemd1',output['data'][0],'org.freedesktop.systemd1.Service',n])) for n in ('MainPID','ControlGroup')}
    backend=Linux(runtime)
    source_guard=MaskedSources(refs,props,typed.fingerprint,fenced)
    guarded=GuardedExecution(units,refs,backend,source_guard,fenced,execute)
    auth_hook=lambda:None
    def authorize_live(t,a,u):
        unlocked_authority();auth_checks.append(a)
        assert u==units
        auth_hook();return authorization
    adapter=ua.SystemUnits(c,units,lambda i,u:verify_catalog(i,all_units,sources),checked_masks,guarded,lambda n:unit_show(n)['LoadState']=='masked',lambda u:observe(u,pins),authorize_live,settle_seconds=2)
    for name in SELECTED:owned_factory().resume(1002,operation,('system-units',name),lambda row:(unlocked_authority() or True))
    authorization=True;assert adapter.inhibit(target)
    journal_before=ledger_state();negative_before=state();commands.clear()
    record(checks,'owned-inhibition-loaded-old-processes-still-alive',units={n:unit_show(n) for n in SELECTED},ledger=journal_before)
    def revoke():
        with guarded.batch():return adapter.revoke(target)
    authorization=False;expect('Denied',revoke);assert not commands and not observe(units,pins)
    record(checks,'denied-revocation-preserves-target-processes-and-owner')
    authorization=True
    EFFECT_DIR.mkdir(mode=0o700)
    fd=os.open(EFFECT_DIR/'.gate-1002.lock',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.fsync(fd);os.close(fd)
    fd=os.open(EFFECT_DIR,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    effects=Effects(factory(),Withdrawal(EFFECT_DIR,writer.RegistryStore._atomic,decode_proof),target,dict(config()['resource_routes']),boot_id)
    cgroups={n:baseline[n]['ControlGroup'] for n in (TARGET_UNITS[0],TARGET_UNITS[2])}
    members=scoped_processes((TARGET_UNITS[0],))
    assert len(members)==2 and all(m['uids']==[1002]*4 for m in members)
    native=NativeStopBackend(effects,SELECTED,cgroups,{n:[pin for row,pin in zip(inv,pins) if cgroups[n] in row["cgroups"]] for n in cgroups},SENDER,TARGET_UNITS[0],lambda:all(fenced(n) for n in SELECTED))
    job_controller=StopJobs(effects,native,lambda:all(fenced(n) for n in SELECTED),settle_seconds=5)
    expect('Busy',revoke)
    assert commands==[['systemctl','stop',TARGET_UNITS[3]],['systemctl','stop',TARGET_UNITS[0]]]
    assert effects.read(TARGET_UNITS[3])['phase']=='observed-drained'
    uncertain=effects.read(TARGET_UNITS[0]);assert uncertain['phase']=='uncertain' and uncertain['job'] is None
    assert native.pending['active']['data']=='deactivating' and native.pending['job']['data'][0]>0
    assert native.pending['populated']==1 and native.pending['drained'] is False
    assert unit_show(TARGET_UNITS[2])['MainPID']==baseline[TARGET_UNITS[2]]['MainPID']
    assert ledger_state()==journal_before and state()==negative_before
    record(checks,'actual-unread-reply-disconnect-keeps-intent-uncertain-and-blocked',pending=native.pending,requests=list(native.requests),members=members)
    expect('Denied',lambda:job_controller.reconcile(TARGET_UNITS[0],lambda row:(unlocked_authority() or False)))
    assert effects.read(TARGET_UNITS[0])==uncertain
    expect('RecoveryRequired',lambda:job_controller(['systemctl','stop',TARGET_UNITS[0]]))
    assert native.requests==[TARGET_UNITS[3],TARGET_UNITS[0]]
    record(checks,'denied-recovery-and-repeated-stop-do-not-resubmit',requests=list(native.requests))
    end=time.monotonic()+10
    while not native.drained(TARGET_UNITS[0]) and time.monotonic()<end:time.sleep(.05)
    # Reconstruct from the durable row; this is not a power-loss/reboot test.
    recovered=StopJobs(Effects(factory(),Withdrawal(EFFECT_DIR,writer.RegistryStore._atomic,decode_proof),target,dict(config()['resource_routes']),boot_id),native,lambda:all(fenced(n) for n in SELECTED))
    assert recovered.reconcile(TARGET_UNITS[0],lambda row:(unlocked_authority() or True))['phase']=='observed-drained'
    assert native.requests==[TARGET_UNITS[3],TARGET_UNITS[0]]
    record(checks,'reconstructed-controller-observes-parent-and-child-drained-without-resubmission',row=effects.read(TARGET_UNITS[0]),requests=list(native.requests))
    # Already completed services cannot be repinned as active. Qualify the
    # remaining registered producer through an explicitly smaller fresh batch.
    remaining=tuple(u for u in units if u.name==TARGET_UNITS[2])
    fresh_guard=GuardedExecution(remaining,{n:r for n,r in refs.items() if n==TARGET_UNITS[2]},backend,source_guard,fenced,execute)
    def fresh_authorize(t,a,u):
        unlocked_authority();assert u==remaining;return True
    remaining_adapter=ua.SystemUnits(c,remaining,lambda i,u:verify_catalog(i,all_units,sources),checked_masks,fresh_guard,lambda n:unit_show(n)['LoadState']=='masked',lambda u:observe(u,pins),fresh_authorize,settle_seconds=2)
    with fresh_guard.batch():assert remaining_adapter.revoke(target)
    assert commands==[['systemctl','stop',TARGET_UNITS[3]],['systemctl','stop',TARGET_UNITS[0]],['systemctl','stop',TARGET_UNITS[2]]]
    assert native.requests==[TARGET_UNITS[3],TARGET_UNITS[0],TARGET_UNITS[2]]
    assert all(effects.read(n)['phase']=='observed-drained' for n in SELECTED)
    assert all(native.drained(n) for n in SELECTED)
    record(checks,'normal-job-replies-and-concurrent-masked-start-refusals',requests=list(native.requests),starts=list(native.starts),rows={n:effects.read(n) for n in SELECTED})
    assert unit_show(PEER_UNITS[0])['MainPID']==baseline[PEER_UNITS[0]]['MainPID'] and show(1000)['MainPID']==peer_pid and (PROOFS/'1000').read_bytes()==peer_proof
    record(checks,'existing-adapter-stops-selected-scope-peer-preserved',commands=list(commands),units={n:unit_show(n) for n in SELECTED},peer_pid=peer_pid)
    for name in SELECTED:
        r=run(['systemctl','start',name],check=False);assert r['rc']!=0 and 'masked' in r['stderr'].lower()
    assert not scoped_processes(SELECTED) and ledger_state()==journal_before and state()==negative_before
    record(checks,'reactivation-denied-negative-state-and-owned-ledger-unchanged')
    deny_attempt(checks,'target-manager-remains-denied-and-peer-admitted')
    gate_full=oc.OrdinaryCoordinator(storage,WithdrawalError,{'classification':c,'system-units':adapter})
    expect('UnsupportedProducer',lambda:gate_full._check(target,False))
    record(checks,'scoped-stop-does-not-grant-whole-account-coverage')
    passed=True
except BaseException as e:error=repr(e);raise
finally:
    for pin in pins:os.close(pin)
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=140)
    PROBE.unlink(missing_ok=True);SENDER.unlink(missing_ok=True)
    if EFFECT_DIR.exists():
        (BASE/'effect-state.json').write_text(json.dumps({p.name:p.read_text() for p in EFFECT_DIR.iterdir()},indent=2)+'\n');shutil.rmtree(EFFECT_DIR)
    row=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,scoped_guarded_stop_tested=True,full_account_protection=False,global_coverage_qualified=False,shared_privileged_services_qualified=False,production_adapters_qualified=False,monotonic_revision_qualified=False,power_loss_tested=False)
    (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(dict(passed=row['passed'],checks=len(checks),cleanup_rc=cleanup.returncode)));assert cleanup.returncode==0,cleanup.stderr
