from state import *
import secrets
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
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (GUARD,WRITER,Path(__file__),BASE/'common.py',BASE/'helper.py',BASE/'withdrawal.py',BASE/'worker.py',BASE/'state.py',BASE/'recover-at-boot.py',BASE/'verify-boot.py',BASE/'cleanup.py',BASE/'restore-check.py')},
    initial_boot_id=boot_id(),fault=False)
save(meta)
run(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(GUARD),'-o',str(MODULE),'-lpam','-lselinux']);MODULE.chmod(0o755);run(['restorecon',str(MODULE)])
DIRECTORY.mkdir(mode=0o700);ROLES.mkdir(mode=0o700);PROOFS.mkdir(mode=0o700)
for uid in (1000,1002,1003):
    fd=os.open(PROOFS/f'.gate-{uid}.lock',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.fsync(fd);os.close(fd)
fd=os.open(PROOFS,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
protected=dict(state='active',**IDENTITY,generation=secrets.token_hex(16))
target=dict(state='ordinary',user='ordinaryuser',uid=1002,gid=1003,group='ordinaryuser',generation=secrets.token_hex(16))
peer=dict(state='ordinary',user='installeduser',uid=1000,gid=1001,group='installeduser',generation=secrets.token_hex(16))
writer.RegistryStore(DIRECTORY).seed([protected]);run(['restorecon','-R',str(DIRECTORY)])
write_rows(ROLES,'role-index',[protected,target,peer])
for row in (target,peer):write_rows(PROOFS,str(row['uid']),[row])
install_pam(protected['generation']);run(['setenforce','1'])
for name,uid in (('ordinaryuser',1002),('installeduser',1000)):
    run(['systemctl','start',f'user@{uid}.service']);assert context(uid).startswith('unconfined_u:unconfined_r:unconfined_t:')
    record(checks,name+'-ordinary-baseline',unit=show(uid),context=context(uid))
operation=secrets.token_hex(16);peer_pid=show(1000)['MainPID'];target_pid=show(1002)['MainPID']
child=run(['/usr/bin/python3',str(BASE/'worker.py'),'marker-synced',operation],check=False)
assert child['rc']==91 and show(1000)['MainPID']==peer_pid and show(1002)['MainPID']==target_pid
assert (PROOFS/'1002').exists() and (PROOFS/'.deny-1002').exists() and not (PROOFS/'.withdrawal-1002.json').exists()
record(checks,'marker-only-crash91-with-both-old-managers-still-active',worker_rc=child['rc'],peer_pid=peer_pid,target_pid=target_pid)
for name in ('ordinaryuser','installeduser'):run(['loginctl','enable-linger',name])
meta.update(operation=operation,before_reboot_files=state());save(meta)
UNIT.write_text('[Unit]\nDescription=Disposable ordinary-withdrawal boot inspection\nAfter=local-fs.target\nBefore=systemd-logind.service user@1000.service user@1002.service user@1003.service\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 /root/withdrawal-boot/recover-at-boot.py\n[Install]\nWantedBy=multi-user.target\n')
run(['restorecon',str(UNIT)]);run(['systemctl','daemon-reload']);run(['systemctl','enable',UNIT.name])
record(checks,'vm-hook-installed-before-logind-and-two-ordinary-lingers',unit=UNIT.read_text())
save_result('prepared',checks,metadata=meta)
