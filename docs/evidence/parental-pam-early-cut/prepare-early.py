import sys
sys.path.insert(0,"/root/unit-stop-jobs")
from bridge import *
from fixture import *
from live_common import *
import secrets,shutil,subprocess,signal
from guard import GuardedExecution,MaskedSources
from linux import Linux
import support as typed
from effects import Effects
from jobs import StopJobs
from recovery import retain
from restart import Origins
from backend import NativeStopBackend
from pam import PamExecution,capture as capture_pam,PROFILE,PROFILE_PATH,BODY
PAM_PROFILE=Path(PROFILE_PATH)
assert not PAM_PROFILE.exists() and not PAM_PROFILE.is_symlink() and not Path("/usr/lib/pam.d",PROFILE).exists()
EFFECT_DIR=Path("/var/lib/lyra-unit-stop-effects-test")
SENDER=Path("/usr/libexec/lyra-unit-stop-jobs-drop-stop")
PROBE=Path('/usr/libexec/lyra-unit-stop-jobs-probe')
assert not any(p.exists() or p.is_symlink() for p in (PROBE,SENDER,EFFECT_DIR))
SELECTED=(TARGET_UNITS[1],)
point=sys.argv[1];kind=sys.argv[2];assert kind in ('origin','intent');assert point in ('partial-write','temp-fsynced','renamed','directory-fsynced')
assert point in ('partial-write','temp-fsynced','renamed','directory-fsynced')
assert not (BASE/'crash-finally-ran').exists()
checks=[];paused_helper=None
CLOSE_HOLD=Path("/run/lyra-pam-close-hold-test")
assert not CLOSE_HOLD.exists() and not CLOSE_HOLD.is_symlink()
ORIGINAL_GUARD=GUARD
GUARD=BASE/"pam-close-hold.c"
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
meta['source_sha256'][ORIGINAL_GUARD.name]=hashlib.sha256(ORIGINAL_GUARD.read_bytes()).hexdigest()
meta['source_sha256'].update({n:hashlib.sha256((BASE/n).read_bytes()).hexdigest() for n in ('guard.py','running.py','linux.py','support.py','reference.py','namespace.py','catalog.py','probe.c','drop-stop.c','effects.py','jobs.py','backend.py','pam.py','recovery.py','cold.py','restart.py','restarted-reader.py','early-worker.py','postboot-consumer.py','postboot.py')})
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

def verify_catalog(identity,units,sources):
    expected={u.name for u in units}
    discovered={p.name for p in VENDOR_UNITS.glob(PREFIX+'target-*') if p.name.endswith(('.service','.timer'))}
    if discovered!=expected:return False
    for u in units:
        p=VENDOR_UNITS/u.name;s=p.lstat()
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o022 or s.st_nlink!=1 or p.read_bytes()!=sources[u.name]:return False
        if any((d/(u.name+'.d')).exists() for d in (MASKS_DIR,VENDOR_UNITS)):return False
        row=unit_show(u.name)
        if row['Id']!=u.name or set(row['Names'].split())!={u.name} or row['Transient']!='no' or row['DropInPaths']:return False
        if row['LoadState']=='loaded':
            if row['FragmentPath']!=str(p):return False
            if u.kind=='service' and (row['User'],row['Group'],row['PAMName'],row['KillMode'])!=(identity.user,identity.group,PROFILE if u.name==TARGET_UNITS[1] else '','control-group'):return False
            if u.kind=='timer' and set(row['Triggers'].split())!={u.service}:return False
        elif row['LoadState']!='masked':return False
    account=pwd.getpwnam(identity.user);group=grp.getgrnam(identity.group)
    return (account.pw_uid,account.pw_gid,group.gr_gid)==(identity.uid,identity.gid,identity.gid)


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
    PAM_PROFILE.write_bytes(BODY);PAM_PROFILE.chmod(0o644);run(['restorecon',str(PAM_PROFILE)])
    sources=create_units()
    sources[TARGET_UNITS[1]]=sources[TARGET_UNITS[1]].replace(b'PAMName=systemd-user',('PAMName='+PROFILE).encode())
    (VENDOR_UNITS/TARGET_UNITS[1]).write_bytes(sources[TARGET_UNITS[1]])
    run(['restorecon',str(VENDOR_UNITS/TARGET_UNITS[1])])
    run(['cc','-Wall','-Wextra','-Werror','-O2',str(BASE/'probe.c'),'-o',str(PROBE)]);PROBE.chmod(0o755)
    run(['cc','-Wall','-Wextra','-Werror','-O2',str(BASE/'drop-stop.c'),'-o',str(SENDER),'-lsystemd']);SENDER.chmod(0o755);run(['restorecon',str(SENDER)])
    sources[TARGET_UNITS[0]]=sources[TARGET_UNITS[0]].replace(b'/usr/bin/sleep 600',str(PROBE).encode())
    (VENDOR_UNITS/TARGET_UNITS[0]).write_bytes(sources[TARGET_UNITS[0]]);run(['restorecon',str(PROBE)]);run(['systemctl','daemon-reload'])
    for n in (TARGET_UNITS[1],PEER_UNITS[0],PEER_UNITS[2]):run(['systemctl','start',n])
    baseline={n:wait_active(n) for n in (TARGET_UNITS[1],PEER_UNITS[0],PEER_UNITS[1])}
    for name,row in baseline.items():
        uid=1002 if name in TARGET_UNITS else 1000
        assert '/system.slice/' in row['ControlGroup'] and int(row['MainPID'])>0
        assert next(x for x in scoped_processes((name,)) if x['pid']==int(row['MainPID']))['uids']==[uid]*4
        record(checks,'baseline-'+name,unit=row)
    expect('UnsupportedUnitExecution',lambda:typed.capture(TARGET_UNITS[1],typed.properties,typed.user,typed.group,typed.fingerprint))
    catalog_row=prepare_bindings('system-units',[(n,hashlib.sha256(sources[n]).hexdigest()) for n in SELECTED])
    # Establish installation durability BEFORE withdrawal/effect operations.
    # Do not flush the guest after the pending operation or immediately before cut.
    os.sync()
    installed_paths=(PAM,MODULE,PAM_PROFILE,PROBE,SENDER,*tuple(VENDOR_UNITS/n for n in sources))
    installed_files={str(p):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),inode=p.stat().st_ino,mode=p.stat().st_mode&0o777,uid=p.stat().st_uid,gid=p.stat().st_gid,nlink=p.stat().st_nlink) for p in installed_paths}
    record(checks,'fixture-installation-durable-before-withdrawal',installed_files=installed_files,sync_before_withdrawal=True)
    owner=factory();operation=secrets.token_hex(16);plan=owner.plan(1002,operation);owner.begin(plan,lambda _:True);storage=owner.withdrawal
    target=oc.Target(1002,operation,plan.withdrawal.proof_hash)
    # Native logind cannot revoke unguarded system.slice User= producers.
    run(['loginctl','terminate-user','1002']);run(['systemctl','stop','user@1002.service','user-runtime-dir@1002.service'])
    for name in (TARGET_UNITS[1],):assert unit_show(name)['MainPID']==baseline[name]['MainPID']
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
    def pam_props(name):
        rows=typed.properties(name)
        path=json.loads(typed.run(['busctl','--system','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','LoadUnit','s',name]))['data'][0]
        for prop in ('KillMode','Delegate'):rows[prop]=json.loads(typed.run(['busctl','--system','--json=short','get-property','org.freedesktop.systemd1',path,'org.freedesktop.systemd1.Service',prop]))
        return rows
    def profile_bytes(path):return typed.file_data(path,8192)[0]
    original_properties={u.name:pam_props(u.name) for u in units}
    refs={u.name:capture_pam(u.name,pam_props,typed.user,typed.group,typed.fingerprint,profile_bytes) for u in units}
    record(checks,'references-captured-before-owned-masks',references={n:__import__('dataclasses').asdict(r) for n,r in refs.items()},general_pam_capture_refused=True)
    checked_masks=integration.CheckedMasks(owned_factory(),target,SELECTED)
    def fenced(name):return checked_masks.masked(name) is True and unit_show(name)['LoadState']=='masked'
    def props(name):return {k:v for k,v in typed.properties(name).items() if k in ('Id','Names','LoadState','FragmentPath','NeedDaemonReload')}
    def runtime(name):
        output=__import__('json').loads(typed.run(['busctl','--system','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','LoadUnit','s',name]))
        assert output['type']=='o' and len(output['data'])==1
        return {n:json.loads(typed.run(['busctl','--system','--json=short','get-property','org.freedesktop.systemd1',output['data'][0],'org.freedesktop.systemd1.Service',n])) for n in ('MainPID','ControlGroup')}
    backend=Linux(runtime)
    source_guard=MaskedSources({n:r.execution for n,r in refs.items()},props,typed.fingerprint,fenced)
    def parent(pin):
        return int(next(line.split()[1] for line in backend.data(pin,'status').decode().splitlines() if line.startswith('PPid:')))
    backend.parent=parent
    def members(name):return tuple(sorted(p['pid'] for p in scoped_processes((name,))))
    guarded=PamExecution(units,refs,backend,source_guard,fenced,execute,members)
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
    original_parent=backend.parent
    def changed_parent():backend.parent=lambda pin:1
    auth_hook=changed_parent
    expect('Conflict',revoke);assert not commands
    backend.parent=original_parent;auth_hook=lambda:None
    assert state()==negative_before and ledger_state()==journal_before
    record(checks,'changed-pam-helper-parent-during-authorization-refused-before-stop')
    with guarded.batch():
        helper={n:__import__('dataclasses').asdict(row) for n,(_,row,_) in guarded.helpers.items()}
        record(checks,'main-and-pam-helper-pinned-with-executor-credentials-and-parent',helpers=helper)
    EFFECT_DIR.mkdir(mode=0o700)
    fd=os.open(EFFECT_DIR/'.gate-1002.lock',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.fsync(fd);os.close(fd)
    fd=os.open(EFFECT_DIR,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    effects=Effects(factory(),Withdrawal(EFFECT_DIR,writer.RegistryStore._atomic,decode_proof),target,dict(config()['resource_routes']),boot_id)
    n=TARGET_UNITS[1];native=NativeStopBackend(effects,SELECTED,{n:baseline[n]['ControlGroup']},{n:pins},SENDER,'never-dropped.service',lambda:all(fenced(x) for x in SELECTED))
    (BASE/'crash-properties.json').write_text(json.dumps(original_properties[n])+'\n');(BASE/'crash-properties.json').chmod(0o600)
    def artifacts():
        files={str(path):dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),inode=path.stat().st_ino,mode=path.stat().st_mode&0o777,uid=path.stat().st_uid,gid=path.stat().st_gid,nlink=path.stat().st_nlink) for directory in (PROOFS,LEDGER) for path in directory.iterdir() if path.is_file()}
        mask=MASKS_DIR/n;st=mask.lstat()
        return dict(files=files,mask=dict(path=str(mask),inode=st.st_ino,uid=st.st_uid,gid=st.st_gid,mode=st.st_mode,link=os.readlink(mask)))
    checkpoint=dict(installed_files=installed_files,old_boot=boot_id(),unit=n,operation=operation,proof_hash=target.proof_hash,point=point,kind=kind,artifacts=artifacts(),checks=checks,metadata=meta,peer_proof_sha256=hashlib.sha256(peer_proof).hexdigest(),source_sha256={name:hashlib.sha256((BASE/name).read_bytes()).hexdigest() for name in ('prepare-early.py','postboot.py','postboot-consumer.py','early-worker.py')})
    fd=os.open(BASE,os.O_RDONLY|os.O_DIRECTORY)
    try:writer.RegistryStore._atomic(fd,'early-state.json',(json.dumps(checkpoint,indent=2)+'\n').encode())
    finally:os.close(fd)
    # Checkpoint is durable BEFORE the worker: no guest disk write after pause.
    with (Path('/run')/'lyra-atomic-worker-output').open('wb') as output:
        child=subprocess.Popen(['python3',str(BASE/'early-worker.py'),operation,target.proof_hash,point,kind],stdout=output,stderr=output,start_new_session=True)
    deadline=time.monotonic()+8
    ready_path=Path('/run/lyra-atomic-cut-ready.json')
    while not ready_path.exists():
        assert child.poll() is None,Path('/run/lyra-atomic-worker-output').read_text()
        assert time.monotonic()<deadline;time.sleep(.02)
    ready=json.loads(ready_path.read_text());assert ready['pid']==child.pid and ready['point']==point
    assert ready['request_entries']==ready['request_returns']==0 and ready['kind']==kind
    while next(line.split()[1] for line in Path('/proc',str(child.pid),'status').read_text().splitlines() if line.startswith('State:'))!='T':
        assert time.monotonic()<deadline;time.sleep(.01)
    print(json.dumps(dict(armed=True,old_boot=checkpoint['old_boot'],point=point,worker_pid=child.pid,ready=ready)),flush=True)
    os._exit(0)
except BaseException as e:error=repr(e);raise
finally:
    CLOSE_HOLD.unlink(missing_ok=True)
    (BASE/'crash-properties.json').unlink(missing_ok=True)
    for pin in pins:os.close(pin)
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=140)
    PROBE.unlink(missing_ok=True);SENDER.unlink(missing_ok=True);PAM_PROFILE.unlink(missing_ok=True)
    if EFFECT_DIR.exists():
        (BASE/'effect-state.json').write_text(json.dumps({p.name:p.read_text() for p in EFFECT_DIR.iterdir()},indent=2)+'\n');shutil.rmtree(EFFECT_DIR)
    row=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,full_account_protection=False,global_coverage_qualified=False,general_pam_runtime_qualified=False,production_adapters_qualified=False,power_loss_tested=False,profile_removed=not PAM_PROFILE.exists(),close_hold_removed=not CLOSE_HOLD.exists(),admission_checks_unchanged=True)
    (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(dict(passed=row['passed'],checks=len(checks),cleanup_rc=cleanup.returncode)));assert cleanup.returncode==0,cleanup.stderr
