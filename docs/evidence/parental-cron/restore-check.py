"""Read-only independent inspection after the native cron experiment."""
import hashlib, json, os, pwd, grp, subprocess
from pathlib import Path
assert os.geteuid()==0
assert {'lyra.parental-selinux-test=1','lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
def run(*args,check=True):
    return subprocess.run(args,capture_output=True,text=True,check=check,timeout=30).stdout
names={'cronfixture','croncontrol'}
units={unit:run('systemctl','show',unit,'-p','MainPID','--value').strip() for unit in
       ('sshd.service','user@31300.service','user@31301.service',
        'user-runtime-dir@31300.service','user-runtime-dir@31301.service')}
paths=('/var/lib/lyra-parental-test','/usr/lib64/security/pam_lyra_producer_registry_fixture.so',
       '/etc/pam.d/crond','/home/cronfixture','/home/croncontrol',
       '/usr/bin/lyra-cron-identity-fixture','/etc/cron.d/lyra-parental-fixture',
       '/var/spool/cron/tabs/cronfixture','/var/spool/cron/tabs/croncontrol',
       '/etc/systemd/system/multi-user.target.wants/cron.service')
processes=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdecimal():continue
    try:
        uids=[int(v) for v in next(line.split()[1:] for line in (proc/'status').read_text().splitlines() if line.startswith('Uid:'))]
        group=(proc/'cgroup').read_text()
        if any(v in (31300,31301) for v in uids) or any(v in group for v in ('cron.service','/user-31300.slice/','/user-31301.slice/')):
            processes.append(dict(pid=int(proc.name),uids=uids,cgroup=group.strip()))
    except FileNotFoundError:pass
result=dict(units=units,absent_paths={path:not Path(path).exists() for path in paths},
            accounts_removed=not names & {p.pw_name for p in pwd.getpwall()},
            groups_removed=not names & {g.gr_name for g in grp.getgrall()},
            processes=processes,sessions=run('loginctl','list-sessions','--no-legend'),
            policy_removed=not any(line.split()[0]=='lyra-cron-registry' for line in run('semodule','-l').splitlines()),
            enforce=run('getenforce').strip(),sshd_enabled=run('systemctl','is-enabled','sshd.service',check=False).strip(),
            vendor_pam_sha256=hashlib.sha256(Path('/usr/lib/pam.d/systemd-user').read_bytes()).hexdigest(),
            kernel=run('uname','-r').strip(),packages=run('rpm','-q','openssh-server','openssh-clients','systemd','pam','selinux-policy-targeted'),
            complete_kernel_audit=False,audit_backlog_warnings=run('journalctl','-b','-k','--no-pager','-g','audit_lost=',check=False))
before=set(Path('/root/cron-packages-before.txt').read_text().splitlines())
after=set(run('rpm','-qa','--qf','%{NAME}\n').splitlines())
result['package_set_restored']=before==after
result['introduced_packages_removed']=not {'cron','cronie','debianutils'} & after
result['cron_binary_removed']=not Path('/usr/sbin/cron').exists()
result['cron_pam_removed']=not Path('/usr/lib/pam.d/crond').exists()
result['common_pam_preserved']=all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha for path,sha in json.loads(Path('/root/cron-result.json').read_text())['common_pam_sha256'].items())
result['passed']=all(v=='0' for v in units.values()) and all(result['absent_paths'].values()) and all(result[k] for k in ('accounts_removed','groups_removed','policy_removed')) and not processes and not result['sessions'].strip() and result['enforce']=='Permissive' and result['sshd_enabled']=='disabled' and result['package_set_restored'] and result['introduced_packages_removed'] and result['cron_binary_removed'] and result['cron_pam_removed'] and result['common_pam_preserved']
Path('/root/cron-restored.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));assert result['passed']
