from boot_common import *
import secrets
checks=[]
assert run(['getenforce'])['stdout'].strip()=='Permissive'
assert not any(p.exists() for p in (DIRECTORY,MODULE,UNIT,CONFIG,ROLES,PROOFS,LEDGER,ic.CATALOG))
assert not run(['loginctl','list-sessions','--no-legend'])['stdout'].strip()
assert all(show(uid)['MainPID']=='0' and not uid_processes(uid) for uid in (1000,1002,1003))
assert not any(Path('/var/lib/systemd/linger',n).exists() for n in ('installeduser','ordinaryuser','parentaltest'))
BASE.mkdir(mode=0o700,exist_ok=True)
for uid,name in ((1000,'installeduser'),(1002,'ordinaryuser'),(1003,'parentaltest')):drain(uid,name)
original=PAM.read_bytes();(BASE/'original-pam').write_bytes(original)
meta=dict(original_pam_sha256=hashlib.sha256(original).hexdigest(),original_pam_mode=PAM.stat().st_mode&0o777,
    vendor_sha256=hashlib.sha256(VENDOR.read_bytes()).hexdigest(),account_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('/etc/passwd','/etc/group')},
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [GUARD,WRITER,*BASE.glob('*.py'),BASE/'service.c']},initial_boot_id=boot_id(),fault=False)
save(meta)
run(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(GUARD),'-o',str(MODULE),'-lpam','-lselinux']);MODULE.chmod(0o755);run(['restorecon',str(MODULE)])
DIRECTORY.mkdir(mode=0o700);ROLES.mkdir(mode=0o700);PROOFS.mkdir(mode=0o700)
for uid in (1000,1002,1003):
    fd=os.open(PROOFS/f'.gate-{uid}.lock',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.fsync(fd);os.close(fd)
fd=os.open(PROOFS,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
protected=dict(state='active',**IDENTITY,generation=secrets.token_hex(16))
ordinary=dict(state='ordinary',user='ordinaryuser',uid=1002,gid=1003,group='ordinaryuser',generation=secrets.token_hex(16))
peer=dict(state='ordinary',user='installeduser',uid=1000,gid=1001,group='installeduser',generation=secrets.token_hex(16))
writer.RegistryStore(DIRECTORY).seed([protected]);run(['restorecon','-R',str(DIRECTORY)])
write_rows(ROLES,'role-index',[protected,ordinary,peer])
for row in (ordinary,peer):write_rows(PROOFS,str(row['uid']),[row])
install_pam(protected['generation']);run(['setenforce','1'])
for uid in (1000,1002):
    run(['systemctl','start',f'user@{uid}.service']);assert context(uid).startswith('unconfined_u:unconfined_r:unconfined_t:')
    record(checks,f'baseline-ordinary-{uid}',unit=show(uid),context=context(uid))
sources=create_routes()
baseline={s:probe(s) for s in ('TargetUnit','TargetExec','PeerUnit','PeerExec')}
for s,row in baseline.items():record(checks,'baseline-'+s,**row)
assert {PREFIX+s for s in SHORTS}<=activatable()
prepare_bindings('dbus-activation',[(PREFIX+s,hashlib.sha256(sources[str(service_path(s))].encode()).hexdigest()) for s in TARGET])
operation=secrets.token_hex(16);store=factory();plan=store.plan(1002,operation)
def authorize_owner(row):unlocked_authority();return True
assert store.begin(plan,authorize_owner)=='AdmissionWithdrawnNoQuiescence'
run(['loginctl','terminate-user','1002']);run(['systemctl','stop','user@1002.service','user-runtime-dir@1002.service'])
for s in ('TargetUnit','TargetExec'):assert probe(s)['pid']==baseline[s]['pid']
record(checks,'withdrawal-leaves-preboot-dbus-owners-alive')
meta=config();meta.update(operation=operation,proof_hash=plan.withdrawal.proof_hash,
    fixture_pam_sha256=hashlib.sha256(PAM.read_bytes()).hexdigest(),fixture_module_sha256=hashlib.sha256(MODULE.read_bytes()).hexdigest(),initial_broker=broker(),broker_pid=broker()['pid']);save(meta)
gate=owned_factory();callbacks=[]
def authorize_fence(row):unlocked_authority();callbacks.append(row['name']);return True
for s in TARGET[:3]:gate.resume(1002,operation,('dbus-activation',PREFIX+s),authorize_fence)
child=run(['/usr/bin/python3',str(BASE/'child.py')],check=False)
assert child['rc']==91 and not child['stderr']
rows=records();assert [rows[s]['phase'] for s in TARGET]==['fenced']*3+['intent']
assert all(not service_path(s).exists() and retired_path(s).exists() for s in TARGET)
record(checks,'effect-synced-crash91-pending-owner-with-four-physical-retirements',child=child,records=rows,authorization_callbacks_outside_all_locks=True)
effects=[];authorizations=[];adapter=live_adapter(effects,authorizations)
expect('UnverifiedAdmission',lambda:adapter.inhibit(target()));assert not effects and not authorizations
record(checks,'pending-owner-refuses-live-adapter-without-auto-completion')
for name in ('ordinaryuser','installeduser'):run(['loginctl','enable-linger',name])
UNIT.write_text('[Unit]\nDescription=Disposable owned route boot inspection\nAfter=local-fs.target\nBefore=dbus.service systemd-logind.service user@1000.service user@1002.service user@1003.service\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 /root/owned-dbus-boot/recover-at-boot.py\n[Install]\nWantedBy=multi-user.target\n')
run(['restorecon',str(UNIT)]);run(['systemctl','daemon-reload']);run(['systemctl','enable',UNIT.name])
for p in (UNIT,BINARY,POLICY,*[UNITS/unit_name(s) for s in SHORTS if systemd(s)]):
    fd=os.open(p,os.O_RDONLY);os.fsync(fd);os.close(fd)
for p in (UNIT.parent,UNITS,POLICY.parent,BINARY.parent,UNIT.parent/'multi-user.target.wants'):
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
meta=config();meta.update(before_reboot_files=persistent(),before_reboot_records=records());save(meta)
record(checks,'vm-only-readonly-hook-before-broker-and-two-ordinary-lingers',unit=UNIT.read_text(),broker=broker())
save_result('prepared',checks,metadata=meta,kernel_reboot_tested=False)
