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
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [GUARD,WRITER,*BASE.glob('*.py')]},initial_boot_id=boot_id(),fault=False)
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
sources=create_units()
for name in BOOT_UNITS:run(['systemctl','start',name])
baseline={n:wait_active(n) for n in (TARGET_UNITS[0],TARGET_UNITS[2],PEER_UNITS[0],PEER_UNITS[1])}
assert all('/system.slice/' in r['ControlGroup'] and int(r['MainPID'])>0 for r in baseline.values())
record(checks,'preboot-live-target-and-peer-service-timer-baselines',units=baseline)
prepare_bindings('system-units',[(n,hashlib.sha256(sources[n]).hexdigest()) for n in TARGET_UNITS])
operation=secrets.token_hex(16);owner=factory();plan=owner.plan(1002,operation)
def authorize_owner(row):unlocked_authority();return True
assert owner.begin(plan,authorize_owner)=='AdmissionWithdrawnNoQuiescence'
run(['loginctl','terminate-user','1002']);run(['systemctl','stop','user@1002.service','user-runtime-dir@1002.service'])
assert unit_show(TARGET_UNITS[0])['MainPID']==baseline[TARGET_UNITS[0]]['MainPID']
meta=config();meta.update(operation=operation,proof_hash=plan.withdrawal.proof_hash,unit_sources={n:v.hex() for n,v in sources.items()},
    fixture_pam_sha256=hashlib.sha256(PAM.read_bytes()).hexdigest(),fixture_module_sha256=hashlib.sha256(MODULE.read_bytes()).hexdigest());save(meta)
gate=owned_factory();callbacks=[]
def authorize_fence(row):unlocked_authority();callbacks.append(row['name']);return True
for n in TARGET_UNITS[:3]:gate.resume(1002,operation,('system-units',n),authorize_fence)
child=run(['/usr/bin/python3',str(BASE/'child.py')],check=False)
assert child['rc']==91 and not child['stderr']
rows=records();assert [rows[n]['phase'] for n in TARGET_UNITS]==['fenced']*3+['intent']
assert all(os.readlink(MASKS_DIR/n)=='/dev/null' for n in TARGET_UNITS)
record(checks,'effect-synced-crash91-pending-owner-with-four-physical-masks',child=child,records=rows,authorization_callbacks_outside_all_locks=True)
commands=[];authorizations=[];adapter=live_adapter(commands,authorizations)
expect('UnverifiedAdmission',lambda:adapter.inhibit(target()));assert not commands
record(checks,'pending-owner-refuses-live-adapter-without-auto-completion')
for name in ('ordinaryuser','installeduser'):run(['loginctl','enable-linger',name])
for n in BOOT_UNITS:
    p=WANTS/n;assert not p.exists() and not p.is_symlink();p.symlink_to(VENDOR_UNITS/n)
UNIT.write_text('[Unit]\nDescription=Disposable owned mask boot inspection\nAfter=local-fs.target\nBefore=systemd-logind.service user@1000.service user@1002.service user@1003.service '+ ' '.join(BOOT_UNITS)+'\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 /root/owned-unit-boot/recover-at-boot.py\n[Install]\nWantedBy=multi-user.target\n')
run(['restorecon',str(UNIT)]);run(['systemctl','daemon-reload']);run(['systemctl','enable',UNIT.name])
fd=os.open(WANTS,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
fd=os.open(UNIT,os.O_RDONLY);os.fsync(fd);os.close(fd)
meta=config();meta.update(before_reboot_files=persistent(),before_reboot_records=records());save(meta)
record(checks,'vm-only-readonly-hook-linger-and-boot-producer-wants',unit=UNIT.read_text(),wants=meta['before_reboot_files']['wants'])
save_result('prepared',checks,metadata=meta,kernel_reboot_tested=False)
