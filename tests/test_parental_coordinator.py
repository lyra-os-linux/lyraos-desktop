"""Tests the experimental gate's refusal/ordering, not real adapter coverage."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'docs/evidence/parental-coordinator/coordinator.py'
# dataclasses need the module registered during dynamic import.
import sys
spec = importlib.util.spec_from_file_location('parental_coordinator', SOURCE)
c = importlib.util.module_from_spec(spec);sys.modules[spec.name] = c;spec.loader.exec_module(c)
A = dict(user='child', uid=1003, gid=1004, group='child')
B = dict(user='ordinary', uid=1002, gid=1002, group='ordinary')


class StoreError(RuntimeError): pass


class Store:
    def __init__(self):
        self.rows = [dict(A, generation='a'*32, state='active')]
        self.barrier = False;self.events = [];self.busy = False
    def snapshot(self): return self.rows, {}
    def begin(self, gen):
        self.events.append('barrier');self.barrier = True;self.rows[0]['state']='transitioning'
        if self.busy:raise StoreError('busy: generation has admitted sessions; barrier remains durable')
    def recover(self):
        self.barrier=True;self.rows[0]['state']='recovering'


class Adapter:
    def __init__(self, store):self.store=store
    def inhibit(self, gen):
        assert self.store.barrier;self.store.events.append('inhibit');return True
    def revoke(self, gen):self.store.events.append('revoke');return True
    def quiescent(self, gen):self.store.events.append('quiescent');return True
    def inhibited(self, gen):self.store.events.append('recheck');return True


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.store=Store();self.adapters={n:Adapter(self.store) for n in c.REQUIRED}
        self.gate=c.Coordinator(self.store,StoreError,self.adapters)
        self.plan=self.gate.plan('a'*32)
    def expect(self, code, auth=lambda p,r:True, revoke=False):
        with self.assertRaises(c.GateError) as got:self.gate.block_and_check(self.plan,auth,revoke)
        self.assertEqual(got.exception.code,code)
    def test_denied_has_no_effect(self):
        self.expect('Denied',lambda p,r:False);self.assertFalse(self.store.barrier)
    def test_truthy_auth_is_not_authorization(self):
        self.expect('Denied',lambda p,r:'yes');self.assertFalse(self.store.barrier)
    def test_stale_plan_has_no_effect(self):
        self.store.rows[0]['uid']=1200;self.expect('Conflict');self.assertFalse(self.store.barrier)
    def test_change_during_auth_has_no_effect(self):
        def authorize(p,r):self.store.rows[0]['uid']=1200;return True
        self.expect('Conflict',authorize);self.assertFalse(self.store.barrier)
    def test_missing_producer_blocks_even_without_leases(self):
        self.gate.adapters.pop('cron');self.expect('UnsupportedProducer');self.assertTrue(self.store.barrier)
    def test_busy_does_not_skip_coverage_check(self):
        self.store.busy=True;self.gate.adapters={};self.expect('UnsupportedProducer');self.assertTrue(self.store.barrier)
    def test_adapter_failure_preserves_barrier(self):
        def fail(gen):raise OSError('adapter unavailable')
        self.gate.adapters['cron'].inhibit=fail;self.expect('AdapterFailure');self.assertTrue(self.store.barrier)
    def test_not_quiescent_preserves_barrier(self):
        self.gate.adapters['cron'].quiescent=lambda gen:False
        self.expect('UnverifiedQuiescence');self.assertTrue(self.store.barrier)
    def test_reactivation_after_drain_preserves_barrier(self):
        self.gate.adapters['cron'].inhibited=lambda gen:False
        self.expect('UnsupportedProducer');self.assertTrue(self.store.barrier)
    def test_lease_still_busy_at_final_check(self):
        self.store.busy=True;self.expect('Busy');self.assertTrue(self.store.barrier)
    def test_success_has_no_publication_and_no_implicit_revoke(self):
        self.assertEqual(self.gate.block_and_check(self.plan,lambda p,r:True),'CheckedWithinAdapterScope')
        self.assertNotIn('revoke',self.store.events)
        self.assertTrue(self.store.barrier);self.assertEqual(self.store.rows[0]['state'],'transitioning')
        self.assertLess(self.store.events.index('inhibit'),self.store.events.index('quiescent'))
        self.assertLess(self.store.events.index('quiescent'),self.store.events.index('recheck'))
    def test_explicit_revoke_follows_inhibition(self):
        self.gate.block_and_check(self.plan,lambda p,r:True,revoke=True)
        self.assertLess(self.store.events.index('inhibit'),self.store.events.index('revoke'))
        self.assertLess(self.store.events.index('revoke'),self.store.events.index('quiescent'))
    def test_reconcile_does_not_enroll(self):
        self.assertEqual(self.gate.reconcile(),'BlockedUntilAuthorizedRecovery')
        self.assertEqual(self.store.rows[0]['state'],'recovering');self.assertTrue(self.store.barrier)
        with self.assertRaises(c.GateError):self.gate.plan('a'*32)
    def test_clean_reconciliation_does_not_claim_blocked_or_verified(self):
        self.store.recover=lambda:None
        self.assertEqual(self.gate.reconcile(),'ExistingAssociationNeedsVerification')
        self.assertFalse(self.store.barrier)
        self.assertEqual(self.store.rows[0]['state'],'active')
    def test_tombstone_reconciliation_does_not_enroll(self):
        self.store.recover=lambda:None;self.store.rows[0]['state']='tombstone'
        self.assertEqual(self.gate.reconcile(),'Tombstoned')
        self.assertEqual(self.store.rows[0]['state'],'tombstone')
    def test_classification(self):
        self.assertEqual(c.classify(A,[A],[B]),'Supervised')
        self.assertEqual(c.classify(B,[A],[B]),'Ordinary')
        self.assertEqual(c.classify(dict(A,uid=1200),[A],[B]),'Blocked')
        self.assertEqual(c.classify(dict(B,uid=1200),[A],[B]),'Unknown')
        self.assertEqual(c.classify(A,[],[]),'Unknown')
        self.assertEqual(c.classify(dict(A,uid=True),[A],[B]),'Unknown')
        self.assertEqual(c.classify(A,[A,dict(A,uid=1200)],[B]),'Blocked')

if __name__=='__main__':unittest.main()
