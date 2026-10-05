"""Isolated catalog/planning tests; no production transport or admission hook."""
import dataclasses
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('parental_service_classifier', ROOT / 'docs/evidence/parental-service-classifier/classifier.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def account(uid=1002, token='a'):
    return dict(association=token*32, generation=token*32,
                identity=dict(user=f'user{uid}', uid=uid, gid=uid, group=f'user{uid}'),
                revision=1, kind='ordinary', state='active', operation='',
                barrier=False, policy='', adapters={})


def catalog():
    return dict(schema=1, revision=1, accounts=[account(), account(1000, 'b')])


def encoded(row):
    return json.dumps(row).encode()


class Assertions:
    def expect(self, code, fn):
        with self.assertRaises(c.Error) as got:
            fn()
        self.assertEqual(got.exception.code, code)


class Tests(Assertions, unittest.TestCase):
    def test_ordinary_requires_exact_positive_identity(self):
        snap = c.decode(encoded(catalog()))
        observer = lambda uid: c.Identity(**account(uid)['identity'])
        self.assertEqual(c.classify(snap, 1002, observer), 'OrdinaryEligible')
        self.expect('RecoveryRequired', lambda: c.classify(snap, 1003, observer))
        self.expect('InvalidIdentity', lambda: c.classify(snap, 1002, lambda _: observer(1000)))
        self.expect('InvalidIdentity', lambda: c.classify(snap, 1002, lambda _: None))

    def test_all_negative_states_preserve_peer(self):
        for state in ('provisioning', 'transitioning', 'recovering', 'tombstone', 'active'):
            with self.subTest(state=state):
                row = catalog()
                row['accounts'][0].update(state=state, operation='c'*32, barrier=state == 'active')
                snap = c.decode(encoded(row))
                observer = lambda uid: c.Identity(**account(uid)['identity'])
                self.expect('Blocked', lambda: c.classify(snap, 1002, observer))
                self.assertEqual(c.classify(snap, 1000, observer), 'OrdinaryEligible')

    def test_supervised_needs_real_observation_not_stored_digests(self):
        row = catalog()
        row['accounts'][0].update(kind='supervised', policy='c'*64, adapters={'gdm': 'd'*64})
        snap = c.decode(encoded(row))
        observer = lambda uid: c.Identity(**account(uid)['identity'])
        self.expect('UnsupportedProducer', lambda: c.classify(snap, 1002, observer))
        self.expect('UnsupportedProducer', lambda: c.classify(snap, 1002, observer, ('gdm',)))
        applied = lambda a: (a.generation, a.policy, a.adapters)
        self.assertEqual(c.classify(snap, 1002, observer, ('gdm',), applied), 'SupervisedEligible')
        self.expect('UnsupportedProducer', lambda: c.classify(snap, 1002, observer, ('gdm', 'ssh'), applied))
        for observed in [('e'*32, 'c'*64, (('gdm', 'd'*64),)), ('a'*32, 'e'*64, (('gdm', 'd'*64),))]:
            self.expect('UnsupportedProducer', lambda: c.classify(snap, 1002, observer, ('gdm',), lambda _: observed))

    def test_duplicate_unknown_and_non_json_payloads_rejected(self):
        for data in [b'', b'\xff', b'{}', b'[]', b'{"schema":1,"schema":1}',
                     b'{"schema":NaN}', b'['*2000, b' '*65537]:
            self.expect('InvalidCatalog', lambda: c.decode(data))
        row = catalog(); row['extra'] = 'permissive'
        self.expect('InvalidCatalog', lambda: c.decode(encoded(row)))
        row = catalog(); row['accounts'][0]['identity']['extra'] = 1
        self.expect('InvalidCatalog', lambda: c.decode(encoded(row)))

    def test_schema_types_and_impossible_states(self):
        for field, values in {'schema': [True, 2], 'revision': [True, 0, -1, 2**63]}.items():
            for value in values:
                row = catalog(); row[field] = value
                self.expect('InvalidCatalog', lambda: c.decode(encoded(row)))
        for field, value in [('barrier', 1), ('kind', 'adult'), ('state', []),
                             ('operation', 'bad'), ('revision', 2), ('generation', 'bad'),
                             ('policy', 'c'*64), ('adapters', {'gdm': 'd'*64})]:
            row = catalog(); row['accounts'][0][field] = value
            self.expect('InvalidCatalog', lambda: c.decode(encoded(row)))
        for field, value in [('uid', True), ('gid', 0), ('user', '../root'), ('group', '')]:
            row = catalog(); row['accounts'][0]['identity'][field] = value
            self.expect('InvalidCatalog', lambda: c.decode(encoded(row)))

    def test_catalog_collision_never_selects_ordinary(self):
        for field in ('association', 'generation', 'uid', 'user'):
            row = catalog()
            if field in ('uid', 'user'):
                row['accounts'][1]['identity'][field] = row['accounts'][0]['identity'][field]
            else:
                row['accounts'][1][field] = row['accounts'][0][field]
            self.expect('InvalidCatalog', lambda: c.decode(encoded(row)))

    def test_snapshot_is_deeply_immutable(self):
        row = catalog(); snap = c.decode(encoded(row)); digest = snap.digest
        row['accounts'][0]['identity']['uid'] = 9999
        self.assertEqual(snap.accounts[0].identity.uid, 1002)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            snap.accounts[0].identity.uid = 9999
        self.assertEqual(snap.digest, digest)


class Fixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.directory.chmod(0o700)
        for name, data in [('catalog.lock', b''), ('catalog.json', encoded(catalog()))]:
            p = self.directory / name; p.write_bytes(data); p.chmod(0o600)
        # Explicit user-owned laboratory; does NOT demonstrate root ownership.
        self.reader = c.Reader(self.directory, owner=os.getuid())


class Files(Fixture, Assertions, unittest.TestCase):
    def test_reader_never_creates_missing_files(self):
        for name in ('catalog.json', 'catalog.lock'):
            self.setUp()
            (self.directory / name).unlink()
            before = sorted(p.name for p in self.directory.iterdir())
            self.expect('RecoveryRequired', self.reader.snapshot)
            self.assertEqual(before, sorted(p.name for p in self.directory.iterdir()))

    def test_read_preserves_all_bytes_and_metadata(self):
        def snapshot():
            return {p.name: (p.read_bytes(), p.stat().st_ino, p.stat().st_mode, p.stat().st_mtime_ns)
                    for p in self.directory.iterdir()}
        before = snapshot(); self.reader.snapshot(); self.reader.snapshot()
        self.assertEqual(before, snapshot())

    def test_unsafe_file_and_directory_rejected(self):
        for name in ('catalog.json', 'catalog.lock'):
            self.setUp(); (self.directory / name).chmod(0o644)
            self.expect('UnsafeCatalog', self.reader.snapshot)
        self.setUp(); self.directory.chmod(0o755)
        self.expect('UnsafeCatalog', self.reader.snapshot)
        self.setUp(); self.reader.owner = os.getuid()+1
        self.expect('UnsafeCatalog', self.reader.snapshot)

    def test_symlink_hardlink_and_fifo_rejected(self):
        for name in ('catalog.json', 'catalog.lock'):
            for kind in ('symlink', 'hardlink', 'fifo'):
                self.setUp(); p = self.directory / name
                p.rename(self.directory / 'saved')
                if kind == 'symlink': p.symlink_to('saved')
                elif kind == 'hardlink': os.link(self.directory / 'saved', p)
                else: os.mkfifo(p, 0o600)
                self.expect('UnsafeCatalog', self.reader.snapshot)

    def test_exclusive_lock_blocks_read_without_mutation(self):
        with (self.directory / 'catalog.lock').open('rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.expect('Busy', self.reader.snapshot)
        self.reader.snapshot()

    def test_orphan_temporary_cannot_replace_missing_catalog(self):
        (self.directory / 'catalog.json').rename(self.directory / '.catalog.tmp')
        self.expect('RecoveryRequired', self.reader.snapshot)
        self.assertFalse((self.directory / 'catalog.json').exists())

    def test_directory_symlink_and_oversize_file_rejected(self):
        link = self.directory / 'alias'
        link.symlink_to(self.directory, target_is_directory=True)
        self.expect('UnsafeCatalog', c.Reader(link, owner=os.getuid()).snapshot)
        (self.directory / 'catalog.json').write_bytes(b' '*65537)
        self.expect('UnsafeCatalog', self.reader.snapshot)


class Planning(Fixture, Assertions, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.now = 100.0; self.uid = 1001; self.allow = True; self.lookups = 0
        self.observed = c.Identity(**account()['identity'])
        original = self.reader.snapshot
        def read():
            self.lookups += 1
            return original()
        self.reader.snapshot = read
        self.planner = c.Planner(self.reader, lambda _: self.uid,
                                 lambda uid, assoc: self.allow,
                                 lambda _: self.observed, lambda: self.now)

    def plan(self):
        return self.planner.plan(':1.20', 'a'*32, 1)

    def test_denied_known_and_unknown_targets_never_read_catalog(self):
        self.allow = False
        for association in ('a'*32, 'f'*32):
            self.expect('Denied', lambda: self.planner.plan(':1.20', association, 1))
        self.assertEqual(self.lookups, 0)

    def test_plan_bound_to_sender_and_not_rebuilt_on_restart(self):
        plan = self.plan()
        self.assertEqual(self.planner.validate(':1.20', plan.identifier), plan)
        self.expect('Denied', lambda: self.planner.validate(':1.21', plan.identifier))
        self.planner._plans.clear()
        self.expect('Denied', lambda: self.planner.validate(':1.20', plan.identifier))

    def test_revalidation_rechecks_caller_capability_and_identity(self):
        plan = self.plan()
        self.allow = False
        self.expect('Denied', lambda: self.planner.validate(':1.20', plan.identifier))
        self.allow = True; self.uid = 0
        self.expect('Denied', lambda: self.planner.validate(':1.20', plan.identifier))
        self.uid = 1001; self.observed = c.Identity(**account(1000)['identity'])
        self.expect('InvalidIdentity', lambda: self.planner.validate(':1.20', plan.identifier))

    def test_plan_expiration_and_exact_catalog_binding(self):
        plan = self.plan(); self.now = plan.expires
        self.expect('Conflict', lambda: self.planner.validate(':1.20', plan.identifier))
        self.now = 100.0
        row = catalog(); row['revision'] = 2
        (self.directory / 'catalog.json').write_bytes(encoded(row))
        self.expect('Conflict', lambda: self.planner.validate(':1.20', plan.identifier))

    def test_negative_stale_and_supervised_plans_refused(self):
        self.expect('Conflict', lambda: self.planner.plan(':1.20', 'a'*32, True))
        self.expect('Conflict', lambda: self.planner.plan(':1.20', 'a'*32, 2))
        row = catalog(); row['accounts'][0].update(barrier=True, operation='c'*32)
        (self.directory / 'catalog.json').write_bytes(encoded(row))
        self.expect('Blocked', self.plan)
        row = catalog(); row['accounts'][0].update(kind='supervised', policy='c'*64, adapters={'gdm': 'd'*64})
        (self.directory / 'catalog.json').write_bytes(encoded(row))
        self.expect('UnsupportedOperation', self.plan)

    def test_capacity_bounds_and_expired_plan_cleanup(self):
        for _ in range(128): self.plan()
        self.expect('Busy', self.plan)
        self.now += 60
        self.plan()
        self.assertEqual(len(self.planner._plans), 1)

    def test_revocation_during_snapshot_is_rechecked(self):
        plan = self.plan()
        original = self.reader.snapshot
        def read():
            snap = original()
            self.allow = False
            return snap
        self.reader.snapshot = read
        self.expect('Denied', lambda: self.planner.validate(':1.20', plan.identifier))

    def test_invalid_or_lost_sender_and_root_without_capability_denied(self):
        for uid in (None, True, -1):
            self.uid = uid
            self.expect('Denied', self.plan)
        self.uid = 0; self.allow = False
        self.expect('Denied', self.plan)
        self.uid = 1001; self.allow = True
        self.expect('Denied', lambda: self.planner.plan('org.example.Gui', 'a'*32, 1))
        self.planner.resolve_sender = lambda _: (_ for _ in ()).throw(RuntimeError('lost sender'))
        self.expect('Denied', self.plan)
        self.assertEqual(self.lookups, 0)


if __name__ == '__main__':
    unittest.main()
