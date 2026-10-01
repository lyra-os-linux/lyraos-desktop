"""Root-only disposable VM checks; process interruption is not power-loss testing."""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

assert os.geteuid() == 0
assert {'lyra.parental-selinux-test=1', 'lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'
SOURCE = Path('/root/barrier-writer.py')
spec = importlib.util.spec_from_file_location('writer', SOURCE)
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
A, B, C, D = ('a'*32, 'b'*32, 'c'*32, 'd'*32)
def row(gen, user='testa', uid=24000, gid=25000):
    return dict(state='active', user=user, uid=uid, gid=gid, group=user, generation=gen)
checks = []
def check(name, condition, **details):
    item = dict(name=name, passed=bool(condition), **details)
    checks.append(item); print(json.dumps(item), flush=True)
    assert condition, item

def expect_busy(action):
    try: action()
    except w.StoreError as error:
        assert str(error).startswith('busy:'), str(error)
        return str(error)
    raise AssertionError('expected Busy')

def admit(store, gen):
    # Model exactly the lock/barrier/record section; native PAM is qualified separately.
    with store._locked(shared=True) as dfd:
        return not (store.directory / f'.barrier-{gen}').exists() and any(
            r['generation'] == gen and r['state'] == 'active' for r in store._rows(dfd))

result = dict(kind='generation-barrier-writer-interruption', checks=checks,
              source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              power_loss_tested=False, native_pam_tested=False)
try:
    with tempfile.TemporaryDirectory(prefix='lyra-registry-v2-', dir='/root') as tmp:
        store = w.RegistryStore(tmp)
        store.seed([row(A), row(B, 'testb', 24001, 25001)])
        fd = os.open(Path(tmp) / f'.lease-{A}.lock', os.O_RDONLY)
        inode = os.fstat(fd).st_ino
        try:
            fcntl.flock(fd, fcntl.LOCK_SH)
            error = expect_busy(lambda: store.begin(A))
            rows, journals = store.snapshot()
            check('busy-persists-barrier-and-transitioning', not admit(store, A) and
                  rows[0]['state'] == 'transitioning' and journals[A]['phase'] == 'blocked', error=error)
            check('unrelated-account-still-admissible', admit(store, B))
            expect_busy(lambda: store.tombstone(A))
            check('busy-does-not-tombstone-live-generation', store.snapshot()[0][0]['state'] == 'transitioning')
            store.begin(B); store.tombstone(B)
            try:
                store.publish(B, row(D))
            except w.StoreError as conflict:
                check('cannot-reuse-identity-with-live-transition', 'ambiguous' in str(conflict))
            else:
                raise AssertionError('live transitioning identity was reused')
            store.publish(B, row(D, 'testb', 24001, 25001))
            check('unrelated-transition-completes-with-a-live-and-pending', admit(store, D) and
                  A in store.snapshot()[1] and B not in store.snapshot()[1])
            check('active-session-lease-inode-preserved', os.stat(Path(tmp) / f'.lease-{A}.lock').st_ino == inode)
        finally: os.close(fd)
        store.begin(A); store.tombstone(A); store.publish(A, row(C))
        check('resume-after-session-release-enrolls-new-generation', admit(store, C) and
              not admit(store, A) and store.snapshot()[1] == {})
        # A newer interrupted begin must not have its barrier cleared by an older
        # committed publication journal during recovery.
    phases = {
        'begin': ['barrier-old-temp-synced', 'barrier-old-published', 'journal-prepared-temp-synced',
                  'journal-prepared-published', 'registry-blocked-temp-synced', 'registry-blocked-published',
                  'journal-blocked-temp-synced', 'journal-blocked-published'],
        'tombstone': ['registry-tombstone-temp-synced', 'registry-tombstone-published',
                      'journal-tombstoned-temp-synced', 'journal-tombstoned-published'],
        'publish': ['journal-target-temp-synced', 'journal-target-published',
                    'barrier-new-temp-synced', 'barrier-new-published', 'registry-new-active-temp-synced',
                    'registry-new-active-published', 'journal-committed-temp-synced',
                    'journal-committed-published', 'barrier-new-removed', 'journal-removed']}
    for command, points in phases.items():
        for point in points:
            with tempfile.TemporaryDirectory(prefix='lyra-registry-crash-', dir='/root') as tmp:
                store = w.RegistryStore(tmp); store.seed([row(A), row(B, 'testb', 24001, 25001)])
                if command != 'begin': store.begin(A)
                if command == 'publish': store.tombstone(A)
                argv = ['python3', str(SOURCE), command, tmp, A, '--crash-at', point]
                if command == 'publish': argv += ['--record-json', json.dumps(row(C))]
                p = subprocess.run(argv, capture_output=True, text=True, timeout=20)
                assert p.returncode == w.CRASH_EXIT, (point, p.returncode, p.stderr)
                before_a, before_c = admit(store, A), admit(store, C)
                outcome = store.recover()
                committed = point in ('journal-committed-published', 'barrier-new-removed', 'journal-removed')
                prebarrier = point == 'barrier-old-temp-synced'
                check('crash-' + point, admit(store, B) and
                      admit(store, A) == prebarrier and admit(store, C) == committed and
                      (not before_c or committed) and (not before_a or prebarrier),
                      outcome=outcome, old_before_recovery=before_a, new_before_recovery=before_c)
                stable = store.snapshot()
                store.recover()
                check('repeat-recovery-' + point, store.snapshot() == stable)
    with tempfile.TemporaryDirectory(prefix='lyra-registry-overlap-', dir='/root') as tmp:
        store = w.RegistryStore(tmp); store.seed([row(A)]); store.begin(A); store.tombstone(A)
        p = subprocess.run(['python3', str(SOURCE), 'publish', tmp, A, '--record-json', json.dumps(row(C)),
                            '--crash-at', 'journal-committed-published'], capture_output=True, timeout=20)
        assert p.returncode == w.CRASH_EXIT
        # Use a separate writer process so the prior committed journal is pending.
        # The published generation has not yet been admitted; root begin is allowed
        # only after removing its *publication* barrier through explicit recovery.
        # Test a newer barrier arriving after commit/removal but before old journal cleanup.
        with store._locked() as dfd:
            store._remove_barrier(dfd, C)
        p = subprocess.run(['python3', str(SOURCE), 'begin', tmp, C,
                            '--crash-at', 'barrier-old-published'], capture_output=True, timeout=20)
        assert p.returncode == w.CRASH_EXIT
        outcome = store.recover()
        check('committed-recovery-preserves-newer-orphan-barrier', not admit(store, C) and
              store.snapshot()[0][-1]['state'] == 'recovering', outcome=outcome)
    result['passed'] = True
finally:
    Path('/root/barrier-writer-result.json').write_text(json.dumps(result, indent=2) + '\n')
