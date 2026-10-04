"""Independent read-only inspection after the reboot fixture is removed."""
import hashlib,json,os,subprocess
from pathlib import Path
assert os.geteuid()==0
assert {'lyra.parental-selinux-test=1','lyra.parental-identity-test=1'}<=set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
BASE=Path('/root/guarded-unit-stop');meta=json.loads((BASE/'config.json').read_text())
def run(args,check=True):
    p=subprocess.run(args,capture_output=True,text=True,timeout=30)
    if check:assert p.returncode==0,(args,p.stdout,p.stderr)
    return p.stdout
units={unit:run(['systemctl','show',unit,'-p','MainPID','--value']).strip() for unit in
       ('user@1000.service','user-runtime-dir@1000.service','user@1003.service','user@1002.service','user-runtime-dir@1003.service','user-runtime-dir@1002.service','gdm.service','sshd.service')}
paths=('/var/lib/lyra-ordinary-attestation-test','/var/lib/lyra-parental-test','/var/lib/lyra-parental-roles-test','/usr/lib64/security/pam_lyra_withdrawal_fixture.so',
       '/etc/systemd/system/lyra-guarded-unit-stop-unused.service',
       '/etc/systemd/system/multi-user.target.wants/lyra-guarded-unit-stop-unused.service',
       '/var/lib/systemd/linger/parentaltest','/var/lib/systemd/linger/ordinaryuser','/var/lib/systemd/linger/installeduser')
processes=[]
for p in Path('/proc').iterdir():
    if not p.name.isdecimal():continue
    try:
        uids=[int(v) for v in next(line.split()[1:] for line in (p/'status').read_text().splitlines() if line.startswith('Uid:'))]
        cgroup=(p/'cgroup').read_text().strip()
        if any(uid in (1000,1002,1003) for uid in uids) or any(part in cgroup for part in ('/user-1000.slice/','/user-1002.slice/','/user-1003.slice/')):
            processes.append(dict(pid=int(p.name),uids=uids,cgroup=cgroup))
    except FileNotFoundError:pass
pam=Path('/etc/pam.d/systemd-user')
row=dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),units=units,
    absent_paths={p:not Path(p).exists() for p in paths},processes=processes,
    sessions=run(['loginctl','list-sessions','--no-legend']),enforce=run(['getenforce']).strip(),
    pam_preserved=hashlib.sha256(pam.read_bytes()).hexdigest()==meta['original_pam_sha256'],
    pam_mode_preserved=pam.stat().st_mode&0o777==meta['original_pam_mode'],
    vendor_preserved=hashlib.sha256(Path('/usr/lib/pam.d/systemd-user').read_bytes()).hexdigest()==meta['vendor_sha256'],
    account_files_preserved=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in meta['account_sha256'].items()),
    sshd_disabled=run(['systemctl','is-enabled','sshd.service'],check=False).strip()=='disabled',
    packages=run(['rpm','-q','systemd','pam','selinux-policy-targeted']),kernel=run(['uname','-r']).strip(),
    complete_kernel_audit=False,audit_backlog_warnings=run(['journalctl','-b','-k','--no-pager','-g','audit_lost='],check=False))
row['passed']=all(v=='0' for v in units.values()) and all(row['absent_paths'].values()) and not processes and not row['sessions'].strip() and row['enforce']=='Permissive' and all(row[k] for k in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
(BASE/'restored.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
