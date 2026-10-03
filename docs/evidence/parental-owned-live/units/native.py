from bridge import *
from fixture import *
from live_common import *
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
meta['source_sha256'].update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'fixture.py',BASE/'unit-adapter.py')})
meta['source_sha256'].update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'operations.py',BASE/'inventory.py',BASE/'ownership.py',BASE/'integration.py',BASE/'inventory_fixture.py',BASE/'live_common.py')})
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
    for n in (TARGET_UNITS[0],TARGET_UNITS[1],TARGET_UNITS[3],PEER_UNITS[0],PEER_UNITS[2]):run(['systemctl','start',n])
    baseline={n:wait_active(n) for n in (TARGET_UNITS[0],TARGET_UNITS[1],TARGET_UNITS[2],PEER_UNITS[0],PEER_UNITS[1])}
    for name,row in baseline.items():
        uid=1002 if name in TARGET_UNITS else 1000
        assert '/system.slice/' in row['ControlGroup'] and int(row['MainPID'])>0
        assert next(x for x in scoped_processes((name,)) if x['pid']==int(row['MainPID']))['uids']==[uid]*4
        record(checks,'baseline-'+name,unit=row)
    catalog_row=prepare_bindings('system-units',[(n,hashlib.sha256(sources[n]).hexdigest()) for n in TARGET_UNITS])
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
    units=tuple(ua.Unit(n,'timer',n[:-6]+'.service') if n.endswith('.timer') else ua.Unit(n,'service') for n in TARGET_UNITS)
    authorization=False;commands=[]
    def execute(args):commands.append(args);return run(args,check=False)
    change_catalog=False;auth_checks=[]
    def live_authorize(t,a,u):
        unlocked_authority();auth_checks.append(a)
        if change_catalog:ic.publish(1002,dict(catalog_row,revision=2))
        return authorization
    adapter=ua.SystemUnits(c,units,lambda i,u:verify_catalog(i,u,sources),integration.CheckedMasks(owned_factory(),target,TARGET_UNITS),execute,lambda n:unit_show(n)['LoadState']=='masked',lambda u:observe(u,pins),live_authorize)
    before=state();expect('Denied',lambda:adapter.inhibit(target));assert state()==before and not commands and not any((MASKS_DIR/n).is_symlink() for n in TARGET_UNITS)
    record(checks,'inhibition-denied-without-masks-or-command-effects')
    authorization=True
    p=VENDOR_UNITS/UNKNOWN;p.write_bytes(sources[TARGET_UNITS[0]]);p.chmod(0o644);run(['restorecon',str(p)]);run(['systemctl','daemon-reload'])
    expect('UnverifiedProducerCatalog',lambda:adapter.inhibit(target));assert not commands and not any((MASKS_DIR/n).is_symlink() for n in TARGET_UNITS)
    p.unlink();run(['systemctl','daemon-reload'])
    record(checks,'unregistered-unit-refused-even-without-processes')
    p=VENDOR_UNITS/TARGET_UNITS[0];p.write_bytes(sources[p.name]+b'\n')
    expect('UnverifiedProducerCatalog',lambda:adapter.inhibit(target));assert not commands
    p.write_bytes(sources[p.name]);run(['restorecon',str(p)])
    record(checks,'changed-producer-source-refused')
    expect('UnverifiedAdmission',lambda:adapter.inhibit(target));assert not commands and not any((MASKS_DIR/n).is_symlink() for n in TARGET_UNITS)
    record(checks,'unprepared-owned-masks-refuse-live-inhibition-without-reload')
    owned_gate=owned_factory();fence_auth=[]
    def authorize_fence(row):unlocked_authority();fence_auth.append(row['name']);return True
    for name in TARGET_UNITS:owned_gate.resume(1002,operation,('system-units',name),authorize_fence)
    assert len(fence_auth)==len(TARGET_UNITS)
    journal_before=ledger_state()
    record(checks,'owned-masks-prepared-before-live-adapter',records={n:ownership.decode(owned_gate.plan(1002,operation,('system-units',n)).entry) for n in TARGET_UNITS},authorization_callbacks_outside_all_locks=True)
    change_catalog=True
    expect('Conflict',lambda:adapter.inhibit(target));assert not commands and ledger_state()==journal_before
    change_catalog=False;ic.publish(1002,catalog_row)
    record(checks,'catalog-changed-during-live-authorization-refused-before-reload')
    assert adapter.inhibit(target) and adapter.inhibited(target) and not adapter.quiescent(target)
    assert unit_show(TARGET_UNITS[0])['MainPID']==baseline[TARGET_UNITS[0]]['MainPID']
    record(checks,'persistent-masks-do-not-imply-old-processes-stopped',units={n:unit_show(n) for n in TARGET_UNITS},masks={n:os.readlink(MASKS_DIR/n) for n in TARGET_UNITS})
    authorization=False;old_commands=len(commands);expect('Denied',lambda:adapter.revoke(target));assert len(commands)==old_commands and unit_show(TARGET_UNITS[0])['MainPID']==baseline[TARGET_UNITS[0]]['MainPID']
    record(checks,'revocation-denied-leaves-active-process-and-masks')
    authorization=True;old_commands=len(commands)
    assert adapter.revoke(target) and adapter.quiescent(target)
    assert commands[old_commands:]==[['systemctl','stop',TARGET_UNITS[3]],*[['systemctl','stop',n] for n in TARGET_UNITS[:3]]]
    assert unit_show(PEER_UNITS[0])['MainPID']==baseline[PEER_UNITS[0]]['MainPID'] and show(1000)['MainPID']==peer_pid and (PROOFS/'1000').read_bytes()==peer_proof
    record(checks,'registered-timer-before-services-revoked-peer-preserved',commands=commands[old_commands:],pidfds_exited=len(pins),processes=scoped_processes(TARGET_UNITS),target_units={n:unit_show(n) for n in TARGET_UNITS},peer_unit=unit_show(PEER_UNITS[0]))
    for name in TARGET_UNITS:
        r=run(['systemctl','start',name],check=False)
        assert r['rc']!=0 and 'masked' in r['stderr'].lower() and unit_show(name)['MainPID']=='0'
        record(checks,'masked-reactivation-denied-'+name,command=r,unit=unit_show(name))
    time.sleep(.7);assert not scoped_processes(TARGET_UNITS) and not uid_processes(1002)
    record(checks,'no-target-reactivation-after-timer-window')
    old=unit_show(PEER_UNITS[1])['MainPID'];run(['systemctl','stop',PEER_UNITS[1]]);new=wait_active(PEER_UNITS[1],old)
    assert unit_show(PEER_UNITS[0])['MainPID']==baseline[PEER_UNITS[0]]['MainPID'] and show(1000)['MainPID']==peer_pid
    record(checks,'peer-timer-can-reactivate-its-service',old_pid=old,new_unit=new)
    removed=MASKS_DIR/TARGET_UNITS[0];backup=BASE/'saved-mask';removed.rename(backup);run(['systemctl','daemon-reload'])
    expect('ResourceChanged',lambda:adapter.quiescent(target));assert not scoped_processes(TARGET_UNITS)
    old_commands=len(commands);expect('ResourceChanged',lambda:adapter.inhibit(target));assert len(commands)==old_commands and not removed.exists()
    record(checks,'lost-owned-mask-never-recreated-by-live-adapter')
    backup.rename(removed);run(['systemctl','daemon-reload'])
    assert adapter.inhibit(target) and adapter.quiescent(target)
    before=state();assert adapter.inhibit(target) and adapter.revoke(target) and state()==before
    record(checks,'explicit-root-same-inode-restoration-and-idempotent-revoke-keep-owner')
    gate=oc.OrdinaryCoordinator(storage,WithdrawalError,{'classification':c,'system-units':adapter})
    expect('UnsupportedProducer',lambda:gate.resume_and_check(1002,operation,lambda p,r:True,revoke=True))
    record(checks,'scoped-units-do-not-satisfy-all-producer-coverage')
    deny_attempt(checks,'withdrawn-user-manager-remains-denied')
    assert ledger_state()==journal_before
    record(checks,'live-inhibition-revocation-and-retries-never-rewrite-owner-journals',ledger=ledger_state(),authorization_callbacks_outside_all_locks=True)
    passed=True
except BaseException as e:error=str(e);raise
finally:
    for pin in pins:os.close(pin)
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=140)
    row=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,
        owned_live_producer_inhibition_qualified=True,owned_live_producer_revocation_qualified=True,ownership_ledger_reboot_qualified=False,full_account_protection=False,whole_classification_qualified=False,all_producer_quiescence=False,real_nss_mutations_tested=False,
        production_adapters_qualified=False,monotonic_revision_qualified=False,power_loss_tested=False,all_system_units_qualified=False,boot_mask_recovery_qualified=False)
    (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({'passed':row['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}));assert cleanup.returncode==0,cleanup.stderr
