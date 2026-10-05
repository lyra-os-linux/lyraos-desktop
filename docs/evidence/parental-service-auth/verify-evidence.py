"""Read-only verifier of the isolated D-Bus/Polkit receipts and source hashes."""
import hashlib
import json
from pathlib import Path

E = Path(__file__).resolve().parent
ROOT = E.parents[2]


def read(name):
    return json.loads((E / name).read_text())


m = read('manifest.json')
assert m['schema'] == 1
for name, digest in m['files'].items():
    assert Path(name).name == name
    assert hashlib.sha256((E / name).read_bytes()).hexdigest() == digest, name
for name, digest in m['sources'].items():
    assert name.startswith('docs/evidence/') and '..' not in Path(name).parts
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
actual = json.loads(read('source-hashes.json')['stdout'])
assert read('source-hashes.json')['rc'] == 0 and len(actual) == 11
for name, digest in m['sources'].items():
    assert actual[Path(name).name] == digest
r = read('result.json')
assert r['passed'] is True and r['error'] is None and r['cleanup'] is True
assert r['real_dbus'] is r['real_polkit'] is True
assert r['password_authentication'] is r['guardian_binding'] is r['production_integrated'] is False
assert r['state_before'] == r['state_after'] and r['configs_before'] == r['configs_after']
assert r['state_after']['selinux'] == 'Permissive'
cases = {row['case']: row for row in r['cases']}
assert len(cases) == len(r['cases']) == 8
assert set(cases) == {'allow', 'deny', 'cancel', 'revoke', 'catalog-change', 'replay', 'unauthorized', 'own'}
for name, row in cases.items():
    response = row['response']
    assert response['uid'] == (1002 if name == 'unauthorized' else 1000)
    assert response['sender'].startswith(':')
    assert all(event['uid'] == response['uid'] for event in row['events'])
    checks = [e for e in row['events'] if e['event'] == 'polkit']
    if name == 'allow':
        assert response['result'] == row['retry']['result'] == 'AdmissionWithdrawnNoQuiescence'
        assert row['retry']['sender'] != response['sender'] and row['retry']['uid'] == 1000
        assert len(checks) == 1 and checks[0]['returncode'] == 0
        for part in ('catalog', 'inventory'):
            assert row['before'][part] == row['after'][part]
        assert '1002' not in row['after']['ledger'] and '.deny-1002' in row['after']['ledger']
        for path, data in row['before']['ledger'].items():
            if '1000' in path:
                assert data == row['after']['ledger'][path]
    elif name == 'own':
        assert response['result'] == 'OrdinaryEligible' and not checks
        assert row['before'] == row['after']
    else:
        suffix = '.AuthorizationFailure' if name in ('revoke', 'catalog-change') else '.Denied'
        assert response['error'].endswith(suffix)
        assert row['before']['ledger'] == row['after']['ledger']
        if name != 'catalog-change':
            assert row['before'] == row['after']
        if name in ('replay', 'unauthorized'):
            assert not checks
        else:
            assert len(checks) == 1
            assert checks[0]['returncode'] == {'deny': 1, 'cancel': 3, 'revoke': 0, 'catalog-change': 0}[name]
        if name == 'cancel':
            assert response['agent_calls'] == ['org.lyraos.parental.fixture.challenge']
        if name == 'replay':
            assert response['new_sender'] != response['sender']
    for check in checks:
        assert check['sender'] == response['sender']
        assert set(check['locks_free']) == {'catalog.lock', '.inventory-1002.lock', '.gate-1002.lock'}
assert read('execution.json')['rc'] == 0
assert json.loads(read('execution.json')['stdout']) == dict(passed=True, cases=8, error=None, cleanup=True)
assert read('cleanup-check.json')['rc'] == read('poweroff.json')['rc'] == 0
assert json.loads(read('cleanup-check.json')['stdout']) == dict(passed=True, cleanup=True)
off = read('vm-off.json')
assert off['vm_off'] is True and off['qemu_returncode'] == 0
assert off['backing_reference_previous_stage'] == off['backing_after']
assert read('disk.json')['filename'] == off['same_disk']
assert read('disk.json')['backing-filename-format'] == 'raw'
print('PASS: eight real system D-Bus/Polkit scenarios, agent cancellation, '
      'revision/capability revalidation and restarted-server retry; cleanup, '
      'accounts/PAM/configs/backing preserved, VM OFF. No password/guardian/product claim.')
