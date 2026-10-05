"""Bridge decisions with actual catalog locks and memory withdrawal storage.

Historical VM evidence qualifies the underlying writer, not this composition.
"""
from contextlib import contextmanager
import fcntl
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace as N
import unittest

import test_parental_operation_journal as old
import test_parental_service_classifier as lab

spec = importlib.util.spec_from_file_location('parental_service_binding', lab.ROOT / 'docs/evidence/parental-service-withdrawal/binding.py')
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
c = lab.c


class Store:
    def __init__(self, identities):
        self.identities = identities
        self.rows = {uid: old.Storage() for uid in identities}
        self.locked = False
        self.after_marker = lambda: None

    @contextmanager
    def lock(self, uid, exclusive):
        self.locked = True
        try:
            yield uid, ('proof', 'marker', 'journal', 'lock')
        finally:
            self.locked = False

    def read(self, fd, name): return self.rows[fd].files.get(name)
    def snapshot(self, fd, names): return [self.read(fd, name) for name in names[:3]]
    fingerprint = staticmethod(old.Storage.fingerprint)
    def decode_proof(self, proof, uid): return self.identities[uid].copy()
    def plan(self, uid, operation): return self.rows[uid].plan(uid, operation)
    def retire(self, fd, names, record): return self.rows[fd].retire(fd, names, record)
    def atomic(self, fd, name, data):
        self.rows[fd].atomic(fd, name, data)
        if name == 'marker': self.after_marker()


class Inventory:
    def __init__(self, identities):
        self.identities = identities
        self.locked_now = False
        self.revision = 1
        self.digest = 'd'*64

    @contextmanager
    def locked(self, uid):
        self.locked_now = True
        try: yield uid
        finally: self.locked_now = False

    def read_locked(self, fd, uid):
        assert self.locked_now and fd == uid
        return N(identity=N(**self.identities[uid]), revision=self.revision, digest=self.digest)


class Tests(lab.Fixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.row = lab.catalog()
        self.identities = {a['identity']['uid']: a['identity'] for a in self.row['accounts']}
        self.store = Store(self.identities)
        self.inventory = Inventory(self.identities)
        self.uid = 1001; self.allow = True; self.now = 100.0
        self.calls = []
        self.bridge = self.new_bridge()

    def new_bridge(self):
        planner = c.Planner(self.reader, lambda _: self.uid,
                            lambda uid, association: self.allow,
                            lambda uid: c.Identity(**self.identities[uid]), lambda: self.now)
        return b.Bridge(c, planner, old.o.Operations, self.store, old.Error, self.inventory)

    def expect(self, code, fn):
        with self.assertRaises((c.Error, old.f.c.GateError)) as got: fn()
        self.assertEqual(got.exception.code, code)

    def plan(self): return self.bridge.plan(':1.20', 'a'*32, 1)
    def execute(self, plan, auth=None): return self.bridge.execute(':1.20', plan.identifier, auth or self.authorize)
    def resume(self, bridge, operation, auth=None):
        return bridge.resume(':1.20', 'a'*32, operation, auth or self.authorize)

    def authorize(self, payload):
        self.assertFalse(self.inventory.locked_now)
        self.assertFalse(self.store.locked)
        with (self.directory / 'catalog.lock').open('rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.calls.append(payload)
        return True

    def test_linked_retirement_negative_overlay_and_peer_untouched(self):
        peer = self.store.rows[1000].files.copy()
        catalog_bytes = (self.directory / 'catalog.json').read_bytes()
        self.assertEqual(self.bridge.inspect_admission(':1.20', 'a'*32), 'OrdinaryEligible')
        plan = self.plan()
        self.assertFalse(self.store.rows[1002].writes)
        self.assertEqual(self.execute(plan), 'AdmissionWithdrawnNoQuiescence')
        self.assertEqual(self.store.rows[1002].writes[0], 'marker')
        self.assertIsNone(self.store.rows[1002].files['proof'])
        self.expect('Blocked', lambda: self.bridge.inspect_admission(':1.20', 'a'*32))
        self.assertEqual(self.bridge.inspect_admission(':1.20', 'b'*32), 'OrdinaryEligible')
        self.assertEqual(peer, self.store.rows[1000].files)
        self.assertEqual(catalog_bytes, (self.directory / 'catalog.json').read_bytes())

    def test_denial_truthy_and_exception_before_write(self):
        for authorize, code in [(lambda _: False, 'Denied'), (lambda _: 1, 'Denied'),
                                (lambda _: (_ for _ in ()).throw(OSError()), 'AuthorizationFailure')]:
            self.setUp(); plan = self.plan()
            self.expect(code, lambda: self.execute(plan, authorize))
            self.assertFalse(self.store.rows[1002].writes)

    def test_owner_payload_cannot_change_durable_binding(self):
        plan = self.plan()
        def auth(payload):
            self.authorize(payload)
            payload['owner']['identity']['uid'] = 1000
            payload['generation'] = 'f'*32
            return True
        self.execute(plan, auth)
        owner = old.o.decode(self.store.rows[1002].files['.operation-1002.json'])
        self.assertEqual(owner['identity']['uid'], 1002)
        self.assertEqual(owner['operation'], plan.identifier)

    def test_changed_catalog_during_auth_has_no_effect(self):
        plan = self.plan()
        def auth(payload):
            self.authorize(payload)
            self.row['revision'] = 2
            (self.directory / 'catalog.json').write_bytes(lab.encoded(self.row))
            return True
        self.expect('AuthorizationFailure', lambda: self.execute(plan, auth))
        self.assertFalse(self.store.rows[1002].writes)

    def test_expiry_or_lost_caller_during_auth_has_no_effect(self):
        for change in (lambda: setattr(self, 'now', 160.0), lambda: setattr(self, 'allow', False),
                       lambda: setattr(self, 'uid', 0)):
            self.setUp(); plan = self.plan()
            def auth(payload): self.authorize(payload); change(); return True
            self.expect('AuthorizationFailure', lambda: self.execute(plan, auth))
            self.assertFalse(self.store.rows[1002].writes)

    def test_proof_and_source_inventory_rechecked_after_auth(self):
        for target in ('proof', 'inventory'):
            self.setUp(); plan = self.plan()
            def auth(payload):
                self.authorize(payload)
                if target == 'proof': self.store.rows[1002].files['proof'] = b'changed'
                else: self.inventory.digest = 'e'*64
                return True
            self.expect('Conflict', lambda: self.execute(plan, auth))
            self.assertFalse(self.store.rows[1002].writes)

    def test_catalog_exclusive_lock_refuses_before_prompt(self):
        plan = self.plan()
        with (self.directory / 'catalog.lock').open('rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.expect('Busy', lambda: self.execute(plan))
        self.assertFalse(self.calls)
        self.assertFalse(self.store.rows[1002].writes)

    def test_catalog_lock_retained_through_first_effect(self):
        plan = self.plan(); checked = []
        def marker():
            with (self.directory / 'catalog.lock').open('rb') as lock:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            checked.append(True)
        self.store.after_marker = marker
        self.execute(plan)
        self.assertTrue(checked)

    def test_revocation_after_intent_preserves_block(self):
        plan = self.plan()
        self.store.after_marker = lambda: setattr(self, 'allow', False)
        self.expect('Denied', lambda: self.execute(plan))
        self.assertIsNotNone(self.store.rows[1002].files['marker'])
        self.assertEqual(self.store.rows[1002].files['proof'], b'ordinary')
        self.allow = True; self.store.after_marker = lambda: None
        self.assertEqual(self.resume(self.new_bridge(), plan.identifier), 'AdmissionWithdrawnNoQuiescence')

    def test_restart_retry_fresh_auth_readonly(self):
        plan = self.plan(); self.execute(plan)
        files = self.store.rows[1002].files.copy(); writes = self.store.rows[1002].writes[:]
        fresh = self.new_bridge()
        self.expect('Denied', lambda: fresh.execute(':1.20', plan.identifier, self.authorize))
        self.assertEqual(self.resume(fresh, plan.identifier), 'AdmissionWithdrawnNoQuiescence')
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(files, self.store.rows[1002].files)
        self.assertEqual(writes, self.store.rows[1002].writes)

    def test_new_instance_resumes_each_existing_owner_checkpoint(self):
        for point in ('intent-marker-synced', 'owned-intent-synced', 'legacy-marker-synced',
                      'legacy-journal-synced', 'owned-blocked-synced', 'owned-retired-synced'):
            self.setUp(); plan = self.plan()
            def crash(actual):
                if actual == point: raise old.Stop()
            self.bridge.operations.crash = crash
            with self.assertRaises(old.Stop): self.execute(plan)
            fresh = self.new_bridge()
            self.assertEqual(self.resume(fresh, plan.identifier), 'AdmissionWithdrawnNoQuiescence')
            self.assertEqual(len(self.calls), 2)

    def test_changed_generation_on_resume_denies_before_prompt(self):
        plan = self.plan(); self.execute(plan); self.calls.clear()
        self.row['accounts'][0]['generation'] = 'e'*32
        (self.directory / 'catalog.json').write_bytes(lab.encoded(self.row))
        files = self.store.rows[1002].files.copy()
        self.expect('Conflict', lambda: self.resume(self.new_bridge(), plan.identifier))
        self.assertFalse(self.calls)
        self.assertEqual(files, self.store.rows[1002].files)

    def test_missing_marker_wrong_operation_and_denied_resume_do_not_write(self):
        plan = self.plan(); self.execute(plan); self.calls.clear()
        files = self.store.rows[1002].files.copy(); writes = self.store.rows[1002].writes[:]
        self.expect('Conflict', lambda: self.resume(self.new_bridge(), 'f'*32))
        self.assertFalse(self.calls)
        self.expect('Denied', lambda: self.resume(self.new_bridge(), plan.identifier, lambda _: False))
        self.assertEqual(files, self.store.rows[1002].files)
        self.assertEqual(writes, self.store.rows[1002].writes)
        self.store.rows[1002].files['marker'] = None
        self.expect('RecoveryRequired', lambda: self.resume(self.new_bridge(), plan.identifier))
        self.assertFalse(self.calls)

    def test_same_account_reentrant_execution_refused_peer_planning_allowed(self):
        plan = self.plan()
        def auth(payload):
            self.authorize(payload)
            self.expect('Busy', lambda: self.execute(plan))
            self.bridge.plan(':1.20', 'b'*32, 1)
            return True
        self.execute(plan, auth)
        self.assertFalse(self.store.rows[1000].writes)


if __name__ == '__main__': unittest.main()
