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
meta['source_sha256'].update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'fixture.py',BASE/'cron-adapter.py',BASE/'cron-ordinary-guard.c',BASE/'cron-state.cil',BASE/'payload.c',BASE/'withdrawal-pam-guard.c')})
save(meta);passed=False;error=None;pins=[];monitor_pins=[]

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
    sources=create_cron();run(['systemctl','start','cron.service']);daemon=cron_pid();assert int(daemon)>0
    wait_tick(1002,1);wait_tick(1000,1)
    originals=[live(rows(1002,k)[0]) for k in ('user','system')];peer_originals=[live(rows(1000,k)[0]) for k in ('user','system')]
    assert all(len(rows(uid,k))==1 for uid in (1000,1002) for k in ('user','system'))
    record(checks,'baseline-native-user-and-system-jobs',target=originals,peer=peer_originals,cron_pid=daemon)
    monitors=[monitor(i) for i in originals];assert len({i['pid'] for i in monitors})==2
    for i in originals:pins.append(os.pidfd_open(i['pid']))
    for i in monitors:monitor_pins.append(os.pidfd_open(i['pid']))
    record(checks,'registered-payload-and-root-monitor-pidfds-pinned',target=originals,monitors=monitors,payload_pidfds=len(pins),monitor_pidfds=len(monitor_pins))
    storage=make();operation=secrets.token_hex(16);plan=storage.plan(1002,operation);storage.begin(plan,lambda p:True);label();target=oc.Target(1002,operation,plan.proof_hash)
    run(['loginctl','terminate-user','1002']);run(['systemctl','stop','user@1002.service','user-runtime-dir@1002.service'])
    for item in originals:assert pid_identity(item['pid'])==item
    record(checks,'withdrawal-and-logind-leave-registered-cron-payloads-alive')
    spec=importlib.util.spec_from_file_location('manager_adapters',BASE/'manager_adapters.py');ma=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ma;spec.loader.exec_module(ma)
    spec=importlib.util.spec_from_file_location('cron_adapter',BASE/'cron-adapter.py');ca=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ca;spec.loader.exec_module(ca)
    expected_pam=PAM.read_bytes();expected_module=MODULE.read_bytes()
    def identity(i):
        a=pwd.getpwnam(i.user);g=grp.getgrnam(i.group);return (a.pw_uid,a.pw_gid,g.gr_gid)==(i.uid,i.gid,i.gid)
    c=ma.Classification(storage,ma.Identity('ordinaryuser',1002,1003,'ordinaryuser'),identity,lambda:safe(PAM,expected_pam) and safe(MODULE,expected_module) and run(['getenforce'])['stdout'].strip()=='Enforcing')
    jobs=(ca.Job('ordinaryuser','user',hashlib.sha256(sources[str(table(1002))]).hexdigest()),ca.Job(SYSTEM.name,'system',hashlib.sha256(sources[str(SYSTEM)]).hexdigest()))
    auth=False;signals=[]
    def stop_jobs(i,j):signals.append(dict(uid=i.uid,pids=[x['pid'] for x in originals]));return signal_payloads(i,j,originals,pins)
    adapter=ca.Cron(c,jobs,lambda i,j:catalog(i,j,sources),lambda i,j:admission(i,j,sources),stop_jobs,lambda j:observe(j,pins,monitor_pins),lambda t,j:auth)
    assert catalog(c.identity,jobs,sources) is True and admission(c.identity,jobs,sources) is True
    record(checks,'baseline-registered-catalog-and-admission-verified',tables={str(p):dict(uid=p.stat().st_uid,gid=p.stat().st_gid,mode=p.stat().st_mode&0o777,nlink=p.stat().st_nlink) for p in (table(1002),SYSTEM)})
    unknown=SYSTEM.with_name(SYSTEM.name+'-unknown');unknown.write_bytes(sources[str(SYSTEM)]);unknown.chmod(0o644)
    try:expect('UnverifiedProducerCatalog',lambda:adapter.inhibit(target));assert not signals
    finally:unknown.unlink()
    record(checks,'unregistered-system-table-refused-even-without-job-execution')
    old=SYSTEM.read_bytes();SYSTEM.write_bytes(old+b'\n')
    try:expect('UnverifiedProducerCatalog',lambda:adapter.inhibit(target));assert not signals
    finally:SYSTEM.write_bytes(old)
    record(checks,'changed-job-definition-refused')
    old=CRONPAM.read_bytes();CRONPAM.write_bytes(CRONVENDOR.read_bytes())
    try:expect('UnverifiedAdmission',lambda:adapter.inhibit(target));assert not signals
    finally:CRONPAM.write_bytes(old)
    record(checks,'removed-account-guard-refused-before-revocation')
    before=state();assert adapter.inhibit(target) and adapter.inhibited(target) and not adapter.quiescent(target) and state()==before and not signals
    record(checks,'verified-existing-account-fence-does-not-stop-running-jobs')
    start=cursor();negative=denied_tick(start,1,2)
    record(checks,'next-real-minute-denies-both-target-routes-peer-continues',**negative)
    expect('Denied',lambda:adapter.revoke(target));assert not signals and all(pid_identity(i['pid'])==i for i in originals)
    record(checks,'revocation-denied-keeps-live-jobs-and-account-barrier')
    auth=True;assert adapter.revoke(target) and adapter.quiescent(target)
    assert all(pid_identity(i['pid'])==i for i in peer_originals) and cron_pid()==daemon and show(1000)['MainPID']==peer_pid and (PROOFS/'1000').read_bytes()==peer_proof
    record(checks,'authorized-payload-revocation-reaps-root-monitors-without-root-signals',signals=signals.copy(),payload_pidfds_exited=len(pins),monitor_pidfds_exited=len(monitor_pins),target_processes=uid_processes(1002),peer=peer_originals,cron_pid=daemon)
    start=cursor();negative=denied_tick(start,1,3)
    assert adapter.quiescent(target) and cron_pid()==daemon and all(pid_identity(i['pid'])==i for i in peer_originals)
    record(checks,'next-real-minute-cannot-reactivate-revoked-target-peer-continues',**negative)
    old=CRONPAM.read_bytes();CRONPAM.write_bytes(CRONVENDOR.read_bytes())
    try:expect('UnverifiedAdmission',lambda:adapter.quiescent(target));assert not uid_processes(1002)
    finally:CRONPAM.write_bytes(old)
    record(checks,'lost-admission-guard-refused-even-with-zero-target-processes')
    before=state();assert adapter.inhibit(target) and adapter.revoke(target) and state()==before
    record(checks,'idempotent-verification-and-revocation-keep-negative-authority')
    gate=oc.OrdinaryCoordinator(storage,WithdrawalError,{'classification':c,'cron':adapter})
    expect('UnsupportedProducer',lambda:gate.resume_and_check(1002,operation,lambda p,r:True,revoke=True));record(checks,'registered-cron-does-not-complete-global-coverage')
    deny_attempt(checks,'withdrawn-user-manager-remains-denied')
    assert all(pid_identity(i['pid'])==i for i in peer_originals) and cron_pid()==daemon
    record(checks,'peer-jobs-and-shared-daemon-preserved-through-whole-matrix',cron_pid=daemon,peer=peer_originals)
    passed=True
except BaseException as e:error=str(e);raise
finally:
    for pin in pins+monitor_pins:os.close(pin)
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=140)
    row=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,
        full_account_protection=False,all_producer_quiescence=False,production_adapters_qualified=False,pending_admission_races_qualified=False,
        whole_cron_namespace_qualified=False,arbitrary_descendants_qualified=False,real_nss_mutations_tested=False,monotonic_revision_qualified=False,power_loss_tested=False,clock_modified=False)
    (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({'passed':row['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}));assert cleanup.returncode==0,cleanup.stderr
