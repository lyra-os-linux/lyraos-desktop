"""Read-only inventory of the explicitly marked disposable identity VM."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

assert os.geteuid() == 0
assert {'lyra.parental-selinux-test=1', 'lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'


def run(argv):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    return dict(argv=argv, rc=p.returncode, stdout=p.stdout, stderr=p.stderr)


files = {}
for root in ('/etc/pam.d', '/usr/lib/pam.d'):
    for name in ('systemd-user', 'login', 'sshd', 'gdm-password', 'gdm-autologin',
                 'cron', 'crond', 'common-session', 'common-session-pc'):
        path = Path(root) / name
        if path.is_file():
            files[str(path)] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                   content=path.read_text(), symlink=path.is_symlink())
commands = [
    ['getenforce'],
    ['rpm', '-q', 'systemd', 'pam', 'gdm', 'openssh-server', 'selinux-policy-targeted'],
    ['systemctl', 'cat', 'user@1003.service'],
    ['systemd-analyze', 'cat-config', 'systemd/logind.conf'],
    ['loginctl', 'list-sessions', '--no-legend'],
    ['loginctl', 'list-users', '--no-legend'],
    ['systemctl', 'show', 'user@1003.service', 'user@1002.service', 'gdm.service',
     'sshd.service', 'systemd-logind.service', '-p', 'Id', '-p', 'ActiveState', '-p', 'MainPID'],
]
result = dict(kind='read-only-disposable-session-inventory',
              full_account_protection=False, pam=files,
              commands=[run(argv) for argv in commands],
              linger_files=[p.name for p in Path('/var/lib/systemd/linger').glob('*')],
              source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
Path('/root/identity-session-inventory.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
