"""Root filesystem integration in a guarded disposable guest; no installation."""
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import grp
import shutil
import subprocess
import sys
import time
import unittest

BASE = Path('/root/lyra-service-storage-test')
DATA = BASE / 'fixtures'


def guard():
    assert os.geteuid() == 0
    cmd = Path('/proc/cmdline').read_text().split()
    assert 'lyra.parental-identity-test=1' in cmd and 'lyra.parental-selinux-test=1' in cmd
    assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'
    assert Path(__file__).resolve().parent == BASE


guard()


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


co = load('coordinator', 'coordinator.py')
w = load('withdrawal', 'withdrawal.py')
op = load('storage_operations', 'operations.py')
i = load('storage_inventory', 'inventory.py')
writer = load('storage_writer', 'writer.py')
c = load('storage_classifier', 'classifier.py')
b = load('storage_binding', 'binding.py')


def identify(uid):
    account = pwd.getpwuid(uid)
    # Limit this laboratory to a unique files-backed identity, no remote NSS.
    local = [line.split(':') for line in Path('/etc/passwd').read_text().splitlines()
             if line and int(line.split(':')[2]) == uid]
    assert len(local) == 1 and local[0][0] == account.pw_name and int(local[0][3]) == account.pw_gid
    group = grp.getgrgid(account.pw_gid)
    local_group = [line.split(':') for line in Path('/etc/group').read_text().splitlines()
                   if line and int(line.split(':')[2]) == account.pw_gid]
    assert len(local_group) == 1 and local_group[0][0] == group.gr_name
    return dict(user=account.pw_name, uid=uid, gid=account.pw_gid, group=group.gr_name)


IDENTITIES = {uid: identify(uid) for uid in (1000, 1002)}


def atomic(directory, name, payload):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        writer.RegistryStore._atomic(fd, name, payload)
    finally:
        os.close(fd)


def encode(row):
    return (json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n').encode()


def decode_proof(payload, uid):
    # Strict synthetic JSON proof, deliberately not the historical PAM format.
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out: raise w.WithdrawalError('InvalidProof')
            out[key] = value
        return out
    try:
        row = json.loads(payload, object_pairs_hook=unique)
        parsed = c.identity(row)
        if parsed.uid != uid: raise ValueError()
        return row
    except Exception as exc:
        raise w.WithdrawalError('InvalidProof') from exc


def files(directory):
    out = {}
    for p in sorted(directory.rglob('*')):
        if p.is_file() and not p.is_symlink():
            s = p.stat()
            out[str(p.relative_to(directory))] = dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                inode=s.st_ino, uid=s.st_uid, gid=s.st_gid, mode=s.st_mode & 0o777, size=s.st_size)
    return out


def system_state():
    paths = [Path('/etc/passwd'), Path('/etc/group')]
    for directory in ('/etc/pam.d', '/usr/lib/pam.d'):
        paths.extend(sorted(p for p in Path(directory).glob('*') if p.is_file()))
    return dict(files={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                selinux=subprocess.check_output(['getenforce'], text=True).strip())


@contextmanager
def exclusive(path):
    with path.open('rb') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


class Fixture:
    def __init__(self, directory, create=False):
        self.root = directory
        self.catalog_dir = directory / 'catalog'
        self.inventory_dir = directory / 'inventory'
        self.ledger = directory / 'ledger'
        self.allow = True
        self.auth_calls = 0
        self.probes = []
        if create:
            directory.mkdir(mode=0o700)
            for path in (self.catalog_dir, self.inventory_dir, self.ledger): path.mkdir(mode=0o700)
            self.catalog = dict(schema=1, revision=1, accounts=[])
            for uid, token in ((1002, 'a'), (1000, 'b')):
                self.catalog['accounts'].append(dict(association=token*32, generation=token*32,
                    identity=IDENTITIES[uid], revision=1, kind='ordinary', state='active',
                    operation='', barrier=False, policy='', adapters={}))
                inventory = dict(schema=1, identity=IDENTITIES[uid], revision=1,
                    producers={name: dict(state='registered', adapter_digest='c'*64,
                        routes=[dict(id='fixture-'+name, digest='d'*64)]) for name in co.REQUIRED})
                atomic(self.inventory_dir, f'{uid}.json', encode(inventory))
                atomic(self.inventory_dir, f'.inventory-{uid}.lock', b'')
                atomic(self.ledger, str(uid), encode(IDENTITIES[uid]))
                atomic(self.ledger, f'.gate-{uid}.lock', b'')
            atomic(self.catalog_dir, 'catalog.json', encode(self.catalog))
            atomic(self.catalog_dir, 'catalog.lock', b'')
        self.reader = c.Reader(self.catalog_dir)  # default root owner, unchanged
        self.inventory = i.Inventory(self.inventory_dir,
            lambda observed: c.Identity(**identify(observed.uid)) == c.Identity(**vars(observed)))
        self.withdrawal = w.Withdrawal(self.ledger, writer.RegistryStore._atomic, decode_proof)
        planner = c.Planner(self.reader, lambda sender: 0 if sender == ':1.20' else None,
            lambda uid, association: self.allow is True,
            lambda uid: c.Identity(**identify(uid)), time.monotonic)
        # Root here has explicit trusted technical capability. It is not guardian.
        self.bridge = b.Bridge(c, planner, op.Operations, self.withdrawal, w.WithdrawalError, self.inventory)

    def plan(self): return self.bridge.plan(':1.20', 'a'*32, 1)

    def authorize(self, payload):
        checked = []
        for path in (self.catalog_dir / 'catalog.lock', self.inventory_dir / '.inventory-1002.lock',
                     self.ledger / '.gate-1002.lock'):
            with exclusive(path): checked.append(path.name)
        self.auth_calls += 1
        self.probes.append(checked)
        return True

    def execute(self, plan, auth=None):
        return self.bridge.execute(':1.20', plan.identifier, auth or self.authorize)

    def resume(self, operation, auth=None):
        return self.bridge.resume(':1.20', 'a'*32, operation, auth or self.authorize)


class Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = Fixture(DATA / self._testMethodName, create=True)

    def expect(self, code, fn):
        with self.assertRaises((c.Error, co.GateError)) as got: fn()
        self.assertEqual(got.exception.code, code)

    def test_retirement_peer_and_catalog_unchanged(self):
        f = self.fixture
        initial = files(f.root); plan = f.plan()
        self.assertEqual(initial, files(f.root))
        self.assertEqual(f.execute(plan), 'AdmissionWithdrawnNoQuiescence')
        self.expect('Blocked', lambda: f.bridge.inspect_admission(':1.20', 'a'*32))
        self.assertEqual(f.bridge.inspect_admission(':1.20', 'b'*32), 'OrdinaryEligible')
        current = files(f.root)
        for name, state in initial.items():
            if name.startswith(('catalog/', 'inventory/')) or '1000' in name:
                self.assertEqual(state, current[name], name)
        self.assertFalse((f.ledger / '1002').exists())
        self.assertEqual(op.decode((f.ledger / '.operation-1002.json').read_bytes())['phase'], 'retired')
        self.assertEqual(len(f.probes[0]), 3)

    def test_denied_execution_never_writes(self):
        f = self.fixture; plan = f.plan(); before = files(f.root)
        self.expect('Denied', lambda: f.execute(plan, lambda _: False))
        self.assertEqual(before, files(f.root))

    def test_busy_each_real_lock_no_prompt(self):
        f = self.fixture; plan = f.plan(); before = files(f.root)
        for path in (f.catalog_dir / 'catalog.lock', f.inventory_dir / '.inventory-1002.lock',
                     f.ledger / '.gate-1002.lock'):
            with self.subTest(lock=path.name), exclusive(path):
                self.expect('Busy', lambda: f.execute(plan))
        self.assertEqual(f.auth_calls, 0)
        self.assertEqual(before, files(f.root))

    def test_first_marker_holds_all_real_locks(self):
        f = self.fixture; plan = f.plan(); checked = []
        def atomic_probe(fd, name, data):
            if name == '.deny-1002':
                for path in (f.catalog_dir / 'catalog.lock', f.inventory_dir / '.inventory-1002.lock',
                             f.ledger / '.gate-1002.lock'):
                    with self.assertRaises(BlockingIOError), exclusive(path): pass
                    checked.append(path.name)
            writer.RegistryStore._atomic(fd, name, data)
        f.withdrawal.atomic = atomic_probe
        f.execute(plan)
        self.assertGreaterEqual(len(checked), 3)

    def test_changed_catalog_after_dialog_no_marker(self):
        f = self.fixture; plan = f.plan()
        def auth(payload):
            f.authorize(payload)
            f.catalog['revision'] = 2
            with exclusive(f.catalog_dir / 'catalog.lock'):
                atomic(f.catalog_dir, 'catalog.json', encode(f.catalog))
            return True
        self.expect('AuthorizationFailure', lambda: f.execute(plan, auth))
        self.assertFalse((f.ledger / '.deny-1002').exists())
        self.assertEqual((f.ledger / '1002').read_bytes(), encode(IDENTITIES[1002]))

    def test_changed_inventory_after_dialog_no_marker(self):
        f = self.fixture; plan = f.plan()
        def auth(payload):
            f.authorize(payload)
            row = json.loads((f.inventory_dir / '1002.json').read_bytes()); row['revision'] = 2
            with exclusive(f.inventory_dir / '.inventory-1002.lock'):
                atomic(f.inventory_dir, '1002.json', encode(row))
            return True
        self.expect('Conflict', lambda: f.execute(plan, auth))
        self.assertFalse((f.ledger / '.deny-1002').exists())

    def test_changed_proof_after_dialog_no_marker(self):
        f = self.fixture; plan = f.plan()
        def auth(payload):
            f.authorize(payload)
            with exclusive(f.ledger / '.gate-1002.lock'):
                atomic(f.ledger, '1002', json.dumps(IDENTITIES[1002], indent=2).encode())
            return True
        self.expect('Conflict', lambda: f.execute(plan, auth))
        self.assertFalse((f.ledger / '.deny-1002').exists())

    def test_new_process_retry_identical_files(self):
        f = self.fixture; plan = f.plan(); f.execute(plan); before = files(f.root)
        child = subprocess.run([sys.executable, __file__, 'resume', str(f.root), plan.identifier],
                               capture_output=True, text=True, timeout=20)
        self.assertEqual(child.returncode, 0, child.stderr)
        result = json.loads(child.stdout)
        self.assertEqual(result['result'], 'AdmissionWithdrawnNoQuiescence')
        self.assertEqual(result['auth_calls'], 1)
        self.assertEqual(len(result['locks_free'][0]), 3)
        self.assertEqual(before, files(f.root))

    def test_process_exit_after_durable_intent_fresh_resume(self):
        f = self.fixture
        child = subprocess.run([sys.executable, __file__, 'crash', str(f.root)],
                               capture_output=True, text=True, timeout=20)
        self.assertEqual(child.returncode, 91, child.stderr)
        self.assertEqual(json.loads(child.stdout)['auth_calls'], 1)
        owner = op.decode((f.ledger / '.deny-1002').read_bytes())
        self.assertFalse((f.ledger / '.operation-1002.json').exists())
        self.assertTrue((f.ledger / '1002').exists())
        self.expect('Blocked', lambda: f.bridge.inspect_admission(':1.20', 'a'*32))
        child = subprocess.run([sys.executable, __file__, 'resume', str(f.root), owner['operation']],
                               capture_output=True, text=True, timeout=20)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(json.loads(child.stdout)['auth_calls'], 1)
        self.assertFalse((f.ledger / '1002').exists())
        self.expect('Blocked', lambda: f.bridge.inspect_admission(':1.20', 'a'*32))

    def test_missing_marker_before_prompt_and_generation_conflict(self):
        f = self.fixture; before = files(f.root)
        self.expect('RecoveryRequired', lambda: f.resume('c'*32))
        self.assertEqual(f.auth_calls, 0); self.assertEqual(before, files(f.root))
        plan = f.plan(); f.execute(plan); f.auth_calls = 0
        f.catalog['accounts'][0]['generation'] = 'e'*32
        with exclusive(f.catalog_dir / 'catalog.lock'):
            atomic(f.catalog_dir, 'catalog.json', encode(f.catalog))
        before = files(f.root)
        self.expect('Conflict', lambda: f.resume(plan.identifier))
        self.assertEqual(f.auth_calls, 0); self.assertEqual(before, files(f.root))

    def test_corrupt_owner_and_wrong_operation_preserve_negative_state(self):
        f = self.fixture; plan = f.plan(); f.execute(plan); f.auth_calls = 0
        self.expect('Conflict', lambda: f.resume('f'*32))
        with exclusive(f.ledger / '.gate-1002.lock'):
            atomic(f.ledger, '.operation-1002.json', b'corrupt\n')
        before = files(f.root)
        self.expect('InvalidOperationJournal', lambda: f.resume(plan.identifier))
        self.expect('Blocked', lambda: f.bridge.inspect_admission(':1.20', 'a'*32))
        self.assertEqual(before, files(f.root)); self.assertEqual(f.auth_calls, 0)


if len(sys.argv) > 1:
    action = sys.argv[1]
    path = Path(sys.argv[2])
    assert path.parent == DATA and path.is_dir() and not path.is_symlink()
    fixture = Fixture(path)
    if action == 'resume':
        result = fixture.resume(sys.argv[3])
        print(json.dumps(dict(result=result, auth_calls=fixture.auth_calls, locks_free=fixture.probes)))
    elif action == 'crash':
        fixture.bridge.operations.crash_at = 'intent-marker-synced'
        plan = fixture.plan()
        def auth(payload):
            result = fixture.authorize(payload)
            print(json.dumps(dict(auth_calls=fixture.auth_calls, locks_free=fixture.probes)), flush=True)
            return result
        fixture.execute(plan, auth)
        raise AssertionError('crash not reached')
    else:
        raise AssertionError('unknown action')
else:
    assert not DATA.exists()
    before = system_state()
    DATA.mkdir(mode=0o700)
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        receipt = dict(passed=result.wasSuccessful(), tests=result.testsRun,
                       failures=len(result.failures), errors=len(result.errors),
                       root_files=all(p.stat().st_uid == 0 and p.stat().st_mode & 0o077 == 0
                           for p in DATA.rglob('*')), state_before=before,
                       state_after=system_state(), snapshots=files(DATA),
                       real_polkit=False, account_mutation=False, quiescence=False)
        assert receipt['state_after'] == before
        (BASE / 'result.json').write_text(json.dumps(receipt, indent=2)+'\n')
    finally:
        guard()
        assert DATA.parent == BASE and DATA.name == 'fixtures' and not DATA.is_symlink()
        shutil.rmtree(DATA)
    assert not DATA.exists()
    print(json.dumps(dict(passed=receipt['passed'], tests=receipt['tests'], cleanup=True)))
    sys.exit(0 if receipt['passed'] and receipt['root_files'] else 1)
