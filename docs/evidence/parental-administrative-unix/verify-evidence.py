"""Read-only verification of bounded real Unix effects in the VM."""
from pathlib import Path
import hashlib
import json

E = Path(__file__).resolve().parent
ROOT = E.parents[2]


def read(name):
    return json.loads((E/name).read_text())


m = read('manifest.json')
assert m['schema'] == 1
for name, digest in m['files'].items():
    assert Path(name).name == name
    assert hashlib.sha256((E/name).read_bytes()).hexdigest() == digest
actual = json.loads(read('source-hashes.json')['stdout'])
assert read('source-hashes.json')['rc'] == 0 and len(actual) == 11
for name, digest in m['sources'].items():
    assert name.startswith('docs/evidence/') and '..' not in Path(name).parts
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest
    assert actual[Path(name).name] == digest
r = read('result.json')
assert r['passed'] is r['restored'] is r['cleanup'] is r['real_unix_effects'] is True
assert r['error'] is None and r['real_polkit'] is r['production_integrated'] is False
assert len(r['checks']) == len(set(r['checks'])) == 13
assert len(r['commands']) == 3 and len(r['noops']) == 2
assert r['noops'] == [dict(method='SetAdmin', is_admin=True), dict(method='SetAdmin', is_admin=False)]
assert all(row['returncode'] == 0 for row in r['commands'])
assert r['commands'][0]['argv'] == ['/usr/sbin/usermod', '-c', 'Lyra fixture $(literal)', '-G', 'users', '--', 'ordinaryuser']
assert r['commands'][1]['argv'] == ['/usr/sbin/usermod', '-aG', 'wheel', '--', 'ordinaryuser']
assert r['commands'][2]['argv'] == ['/usr/bin/gpasswd', '-d', 'ordinaryuser', 'wheel']
assert r['account_hashes_before'] == r['account_hashes_after']
assert r['state_before'] == r['state_after'] and r['state_after']['selinux'] == 'Permissive'
assert r['identity_before'] == r['identity_after'] and r['identity_after']['uid'] == 1002
assert read('execution.json')['rc'] == 0
assert json.loads(read('execution.json')['stdout']) == dict(passed=True, checks=13, commands=3, noops=2, error=None, cleanup=True)
assert read('cleanup-check.json')['rc'] == read('poweroff.json')['rc'] == 0
assert json.loads(read('cleanup-check.json')['stdout']) == dict(passed=True, cleanup=True)
assert json.loads(read('guard.json')['stdout'])['guard'] is True and read('guard.json')['rc'] == 0
off = read('vm-off.json')
assert off['vm_off'] is True and off['qemu_returncode'] == 0
assert off['backing_before'] == off['backing_after']
disk = read('disk.json')
assert disk['filename'] == off['same_disk'] and disk['backing-filename-format'] == 'raw'
print('PASS: 13 controls, three real Unix commands and two no-ops; sealed parameters, '
      'identity/peer preserved, accounts/backups restored, cleanup and backing unchanged, '
      'VM OFF. No real Polkit composition, product recovery or supervision claim.')
