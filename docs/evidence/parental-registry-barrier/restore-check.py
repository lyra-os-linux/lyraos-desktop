"""Independent post-run guest inspection; does not change the guest."""
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess
assert os.geteuid() == 0
assert {'lyra.parental-selinux-test=1', 'lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'
def run(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True, timeout=30).stdout
units = {unit: run('systemctl', 'show', unit, '-p', 'MainPID', '--value').strip()
         for unit in ('gdm.service', 'user@1003.service', 'user@1002.service', 'user@476.service')}
paths = ('/var/lib/lyra-parental-test', '/usr/lib64/security/pam_lyra_identity_registry_fixture.so',
         '/usr/lib64/security/pam_lyra_identity_registry_fixture.lifetime-saved',
         '/usr/lib64/security/pam_lyra_identity_registry_fixture.manager-saved',
         '/etc/pam.d/lyra-identity-probe', '/etc/pam.d/lyra-identity-probe.new',
         '/root/manager-worker.backup', '/opt/lyra-parental-probe/manager-session',
         '/var/lib/systemd/linger/parentaltest', '/var/lib/systemd/linger/ordinaryuser')
uid_processes = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdecimal(): continue
    try:
        values = next(line.split()[1:] for line in (proc / 'status').read_text().splitlines() if line.startswith('Uid:'))
        if any(int(value) in (1002, 1003) for value in values): uid_processes.append(int(proc.name))
    except FileNotFoundError: pass
worker = Path('/usr/libexec/gdm/gdm-session-worker')
result = dict(units=units, sessions=run('loginctl', 'list-sessions', '--no-legend'),
              absent_paths={path: not Path(path).exists() for path in paths},
              fixture_account_absent='identitytest' not in {p.pw_name for p in pwd.getpwall()},
              policy_removed=not any(line.split()[0] == 'lyra-registry-gdm' for line in run('semodule', '-l').splitlines()),
              enforce=run('getenforce').strip(), uid_processes=uid_processes,
              worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              worker_label=os.getxattr(worker, 'security.selinux').decode().strip('\x00'),
              kernel=run('uname', '-r').strip(), complete_kernel_audit=False,
              audit_backlog_warnings=run('journalctl', '-b', '-k', '--no-pager', '-g', 'audit_lost='))
result['passed'] = (all(v == '0' for v in units.values()) and not result['sessions'].strip() and
                    all(result['absent_paths'].values()) and result['fixture_account_absent'] and
                    result['policy_removed'] and result['enforce'] == 'Permissive' and not uid_processes and
                    result['worker_sha256'] == '40e1387811b74adcde44b8a34f03db1d032190867e1c5f4092bb9aa1362fdab8')
Path('/root/barrier-restored.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
assert result['passed'], result
