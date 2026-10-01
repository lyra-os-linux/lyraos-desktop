"""Read-only independent inspection after the native D-Bus activation experiment."""
import hashlib, json, os, pwd, grp, subprocess
from pathlib import Path
assert os.geteuid()==0
assert {'lyra.parental-selinux-test=1','lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
def run(*args,check=True):
    return subprocess.run(args,capture_output=True,text=True,check=check,timeout=30).stdout
names={'producerfixture','producercontrol'}
units={unit:run('systemctl','show',unit,'-p','MainPID','--value').strip() for unit in
       ('sshd.service','user@31200.service','user@31201.service',
        'user-runtime-dir@31200.service','user-runtime-dir@31201.service')}
paths=('/var/lib/lyra-parental-test','/usr/lib64/security/pam_lyra_producer_registry_fixture.so',
       '/etc/pam.d/lyra-producer-fixture','/home/producerfixture','/home/producercontrol','/usr/bin/lyra-dbus-activation-fixture',
       '/etc/dbus-1/system.d/lyra-parental-dbus-fixture.conf')
processes=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdecimal():continue
    try:
        uids=[int(v) for v in next(line.split()[1:] for line in (proc/'status').read_text().splitlines() if line.startswith('Uid:'))]
        group=(proc/'cgroup').read_text()
        if any(v in (31200,31201) for v in uids) or any(v in group for v in ('lyra-producer-','lyra-dbus-fixture-','org.lyra.ParentalDbusFixture.','/user-31200.slice/','/user-31201.slice/')):
            processes.append(dict(pid=int(proc.name),uids=uids,cgroup=group.strip()))
    except FileNotFoundError:pass
result=dict(units=units,absent_paths={path:not Path(path).exists() for path in paths},
            accounts_removed=not names & {p.pw_name for p in pwd.getpwall()},
            groups_removed=not names & {g.gr_name for g in grp.getgrall()},
            processes=processes,sessions=run('loginctl','list-sessions','--no-legend'),
            policy_removed=not any(line.split()[0]=='lyra-producer-registry' for line in run('semodule','-l').splitlines()),
            enforce=run('getenforce').strip(),sshd_enabled=run('systemctl','is-enabled','sshd.service',check=False).strip(),
            vendor_pam_sha256=hashlib.sha256(Path('/usr/lib/pam.d/systemd-user').read_bytes()).hexdigest(),
            kernel=run('uname','-r').strip(),packages=run('rpm','-q','openssh-server','openssh-clients','systemd','pam','selinux-policy-targeted'),
            complete_kernel_audit=False,audit_backlog_warnings=run('journalctl','-b','-k','--no-pager','-g','audit_lost=',check=False))
service_paths=list(Path('/usr/share/dbus-1/system-services').glob('org.lyra.ParentalDbusFixture.*'))+list(Path('/run/systemd/system').glob('lyra-dbus-fixture-*'))
activatable=run('busctl','--system','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ListActivatableNames')
result['activation_removed']=not service_paths and 'org.lyra.ParentalDbusFixture.' not in activatable
result['remaining_service_paths']=[str(p) for p in service_paths]
result['bus_service_pid']=run('systemctl','show','dbus.service','-p','MainPID','--value').strip()
result['bus_service_preserved']=result['bus_service_pid']=='449'
result['broker_package']=run('rpm','-q','dbus-broker').strip()
result['passed']=all(v=='0' for v in units.values()) and all(result['absent_paths'].values()) and all(result[k] for k in ('accounts_removed','groups_removed','policy_removed')) and not processes and not result['sessions'].strip() and result['enforce']=='Permissive' and result['sshd_enabled']=='disabled' and result['activation_removed'] and result['bus_service_preserved']
Path('/root/dbus-activation-restored.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));assert result['passed']
