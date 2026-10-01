"""Crash/lock proof for the registry writer; disposable VM only."""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import uuid

assert os.geteuid() == 0
assert 'lyra.parental-selinux-test=1' in Path('/proc/cmdline').read_text().split()
assert 'lyra.parental-identity-test=1' in Path('/proc/cmdline').read_text().split()
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'

SOURCE = Path('/root/identity-registry-transaction.py')
BASE = Path('/var/lib/lyra-parental-transaction-test')
assert SOURCE.is_file() and not BASE.exists()
spec = importlib.util.spec_from_file_location('registry_transaction', SOURCE)
store_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store_module)
RegistryStore = store_module.RegistryStore
CRASH_EXIT = store_module.CRASH_EXIT
checks = []
result = {'kind': 'registry-transaction-crash-proof', 'full_account_protection': False,
          'checks': checks}


def cmd(*args):
    return subprocess.run([sys.executable, str(SOURCE), *map(str, args)],
                          capture_output=True, text=True, timeout=30)


def generation():
    return secrets.token_hex(16)


def record(state, gen):
    return {'state': state, 'user': 'identitytest', 'uid': 24000, 'gid': 25000,
            'group': 'identitytest', 'generation': gen}


def new_case(name):
    path = BASE / name
    path.mkdir(mode=0o700)
    subprocess.run(['restorecon', str(path)], check=True, capture_output=True, text=True)
    return path


def check(name, fn):
    try:
        detail = fn()
        checks.append({'name': name, 'passed': True, 'detail': detail})
        print(json.dumps(checks[-1]), flush=True)
    except Exception as error:
        checks.append({'name': name, 'passed': False, 'error': str(error)})
        print(json.dumps(checks[-1]), flush=True)
        raise


def test_crash(point):
    path = new_case('crash-' + point)
    old = generation(); new = generation()
    store = RegistryStore(path)
    store.seed([record('active', old)])
    checkpoint = point.removesuffix('-temp-synced').removesuffix('-published')
    if checkpoint in {'journal-prepared', 'registry-blocked', 'journal-blocked'}:
        p = cmd('begin', path, old, '--crash-at', point)
    elif checkpoint in {'registry-tombstone', 'journal-tombstoned'}:
        assert cmd('begin', path, old).returncode == 0
        p = cmd('tombstone', path, old, '--crash-at', point)
    elif checkpoint in {'registry-new-active', 'journal-committed', 'journal-removed'}:
        assert cmd('begin', path, old).returncode == 0
        assert cmd('tombstone', path, old).returncode == 0
        p = cmd('publish', path, old, '--record-json', json.dumps(record('active', new)),
                '--crash-at', point)
    else:
        raise AssertionError(point)
    assert p.returncode == CRASH_EXIT, {'point': point, 'rc': p.returncode, 'stderr': p.stderr}
    recovery = cmd('recover', path)
    assert recovery.returncode == 0, recovery.stderr
    rows, journal = RegistryStore(path).snapshot()
    if point == 'journal-prepared-temp-synced':
        assert recovery.stdout.strip() == 'clean', recovery.stdout
        assert next(r for r in rows if r['generation'] == old)['state'] == 'active', rows
        assert journal is None, journal
        expected = 'unchanged-before-transaction'
    elif point in {'journal-committed-published', 'journal-removed'}:
        assert next(r for r in rows if r['generation'] == old)['state'] == 'tombstone', rows
        assert next(r for r in rows if r['generation'] == new)['state'] == 'active', rows
        assert journal is None, journal
        expected = 'committed'
    else:
        old_row = next(r for r in rows if r['generation'] == old)
        assert old_row['state'] in {'recovering', 'tombstone'}, rows
        assert old_row['state'] != 'active', rows
        if checkpoint == 'registry-new-active' and point.endswith('-published'):
            assert next(r for r in rows if r['generation'] == new)['state'] == 'recovering', rows
        if point == 'journal-committed-temp-synced':
            assert next(r for r in rows if r['generation'] == new)['state'] == 'recovering', rows
        assert journal and journal['phase'] == 'recovering', journal
        expected = 'blocked'
    leftovers = [name for name in os.listdir(path) if name.endswith('.tmp')]
    assert not leftovers, leftovers
    return {'recovery': recovery.stdout.strip(), 'outcome': expected,
            'old_state': next(r for r in rows if r['generation'] == old)['state'],
            'journal_present': journal is not None}


def test_concurrent_begin():
    path = new_case('concurrent')
    old = generation()
    RegistryStore(path).seed([record('active', old)])
    procs = [subprocess.Popen([sys.executable, str(SOURCE), 'begin', str(path), old],
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
             for _ in range(2)]
    outcomes = [p.communicate(timeout=30) + (p.returncode,) for p in procs]
    assert sorted(x[2] for x in outcomes) == [0, 1], outcomes
    rows, journal = RegistryStore(path).snapshot()
    assert journal and next(r for r in rows if r['generation'] == old)['state'] == 'transitioning'
    RegistryStore(path).recover()
    rows, journal = RegistryStore(path).snapshot()
    assert journal and next(r for r in rows if r['generation'] == old)['state'] == 'recovering'
    return {'writer_exit_codes': sorted(x[2] for x in outcomes), 'state_after_recovery': 'recovering'}


try:
    BASE.mkdir(mode=0o700)
    subprocess.run(['restorecon', str(BASE)], check=True, capture_output=True, text=True)
    points = ['journal-prepared-temp-synced', 'journal-prepared-published',
              'registry-blocked-temp-synced', 'registry-blocked-published',
              'journal-blocked-temp-synced', 'journal-blocked-published',
              'registry-tombstone-temp-synced', 'registry-tombstone-published',
              'journal-tombstoned-temp-synced', 'journal-tombstoned-published',
              'registry-new-active-temp-synced', 'registry-new-active-published',
              'journal-committed-temp-synced', 'journal-committed-published',
              'journal-removed']
    for point in points:
        check('crash-' + point, lambda point=point: test_crash(point))
    check('concurrent-begin-serialized', test_concurrent_begin)
    result['passed'] = True
finally:
    if BASE.exists():
        shutil.rmtree(BASE)
    result['fixtures_removed'] = not BASE.exists()
    result['passed'] = bool(result.get('passed') and result['fixtures_removed'] and
                            all(item['passed'] for item in checks))
    result['source_sha256'] = __import__('hashlib').sha256(SOURCE.read_bytes()).hexdigest()
    Path('/root/identity-registry-transaction-result.json').write_text(json.dumps(result, indent=2) + '\n')

assert result['passed'], result
