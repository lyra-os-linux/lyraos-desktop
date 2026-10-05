"""Read-only integrity/scope verifier; never starts a VM or mutates accounts."""
import hashlib
import json
from pathlib import Path

E = Path(__file__).resolve().parent
ROOT = E.parents[2]


def read(name):
    return json.loads((E / name).read_text())


manifest = read('manifest.json')
assert manifest['schema'] == 1
for name, digest in manifest['files'].items():
    assert Path(name).name == name
    assert hashlib.sha256((E / name).read_bytes()).hexdigest() == digest, name
for name, digest in manifest['sources'].items():
    assert name.startswith('docs/evidence/') and '..' not in Path(name).parts
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
assert read('guard.json')['rc'] == 0
assert json.loads(read('guard.json')['stdout'])['guard'] is True
source_hashes = read('source-hashes.json')
assert source_hashes['rc'] == 0
actual = json.loads(source_hashes['stdout'])
assert len(actual) == 8
for path, digest in manifest['sources'].items():
    assert actual[Path(path).name] == digest
result = read('result.json')
assert result['passed'] is True and result['tests'] == 11
assert result['errors'] == result['failures'] == 0 and result['root_files'] is True
assert result['state_before'] == result['state_after']
assert result['state_after']['selinux'] == 'Permissive'
assert result['real_polkit'] is result['account_mutation'] is result['quiescence'] is False
assert result['snapshots']
for state in result['snapshots'].values():
    assert state['uid'] == 0 and state['mode'] == 0o600
execution = read('execution.json')
assert execution['rc'] == 0 and 'Ran 11 tests' in execution['stderr'] and '\nOK\n' in execution['stderr']
assert json.loads(execution['stdout']) == dict(passed=True, tests=11, cleanup=True)
cleanup = read('cleanup-check.json')
assert cleanup['rc'] == 0 and json.loads(cleanup['stdout']) == dict(passed=True, cleanup=True)
assert read('poweroff.json')['rc'] == 0
off = read('vm-off.json')
assert off['vm_off'] is True and off['qemu_returncode'] == 0
assert off['backing_before'] == off['backing_after']
disk = read('disk.json')
assert disk['format'] == 'qcow2' and disk['backing-filename-format'] == 'raw'
assert disk['filename'] == off['same_disk']
assert disk['full-backing-filename'] == '/tmp/lyra-parental-identity-20260928/system.raw'
print('PASS: 11 root filesystem integration tests; real catalog/inventory/ledger locks; '
      'process-exit recovery and readonly retry; account/PAM/SELinux and backing unchanged; '
      'cleanup confirmed, VM OFF. No real Polkit, PAM admission, quiescence or production claim.')
