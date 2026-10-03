"""Read-only integration decisions; VM qualifies actual live producer behavior."""
import unittest,sys,dataclasses
from types import SimpleNamespace as N
import test_parental_owned_inhibitions as f
prior=sys.modules.get('coordinator');sys.modules['coordinator']=f.j.f.c;sys.modules['owned_inhibitions']=f.m
m=f.j.f.load('owned_live',f.j.f.ROOT/'docs/evidence/parental-owned-live/integration.py')
if prior is not None:sys.modules['coordinator']=prior
class Tests(unittest.TestCase):
    def setUp(self):
        self.fixture=f.Tests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.gate=self.fixture.gate;self.target=N(uid=1002,operation='a'*32,proof_hash=self.fixture.plan().entry and f.m.decode(self.fixture.plan().entry)['owner']['proof_hash'])
        self.masks=m.CheckedMasks(self.gate,self.target,('a.service',))
    def expect(self,code,fn):
        with self.assertRaises(f.j.f.c.GateError) as got:fn()
        self.assertEqual(got.exception.code,code)
    def ready(self):self.fixture.run_plan()
    def test_absent_intent_cannot_become_mask_via_reader(self):self.expect('UnverifiedAdmission',lambda:self.masks.install(('a.service',)));self.assertFalse(self.fixture.ledger.writes)
    def test_completed_mask_checked_without_mutation(self):
        self.ready();before=self.fixture.ledger.files.copy();calls=self.fixture.backend.calls
        self.assertTrue(self.masks.install(('a.service',)));self.assertTrue(self.masks.masked('a.service'));self.assertEqual(before,self.fixture.ledger.files);self.assertEqual(calls,self.fixture.backend.calls)
    def test_partial_intent_does_not_claim_inhibition(self):
        self.fixture.gate.crash=lambda _:(_ for _ in ()).throw(f.j.Stop())
        with self.assertRaises(f.j.Stop):self.fixture.run_plan()
        self.expect('UnverifiedAdmission',lambda:self.masks.masked('a.service'))
    def test_removed_completed_mask_never_repaired(self):
        self.ready();self.fixture.backend.status='available';self.fixture.backend.stamp=None;before=self.fixture.ledger.files.copy()
        self.expect('ResourceChanged',lambda:self.masks.masked('a.service'));self.assertEqual(before,self.fixture.ledger.files)
    def test_different_proof_hash_not_accepted(self):
        self.ready();other=m.CheckedMasks(self.gate,N(uid=1002,operation='a'*32,proof_hash='e'*64),('a.service',));self.expect('OwnershipConflict',lambda:other.masked('a.service'))
    def test_catalog_change_invalidates_reader(self):self.ready();self.fixture.i.revision=2;self.expect('Conflict',lambda:self.masks.masked('a.service'))
    def test_backend_version_change_invalidates_reader(self):self.ready();self.fixture.version='e'*64;self.expect('UnverifiedProducerCatalog',lambda:self.masks.masked('a.service'))
    def test_unknown_or_partial_resource_list_refused(self):
        self.expect('UnsupportedProducer',lambda:self.masks.masked('b.service'));self.expect('UnverifiedProducerCatalog',lambda:self.masks.install(()))
    def test_binding_captures_immutable_target(self):self.ready();self.target.uid=1000;self.target.operation='b'*32;self.assertTrue(self.masks.masked('a.service'))
    def test_invalid_target_and_empty_catalog_refused(self):
        for uid,operation,proof in ((True,'a'*32,'b'*64),(1002,'bad','b'*64),(1002,'a'*32,'bad')):
            with self.subTest(uid=uid):self.expect('InvalidTarget',lambda:m.Reader(self.gate,N(uid=uid,operation=operation,proof_hash=proof)))
        self.expect('UnsupportedProducer',lambda:m.CheckedMasks(self.gate,self.target,()))
    def route_setup(self):
        backend=self.fixture.backend;backend.family='dbus-activation';backend.stamp=dict(device=1,inode=5,digest='c'*64)
        def apply(*args):backend.calls+=1;backend.status='fenced'
        backend.apply=apply
        resource=f.m.Resource('dbus-activation','org.lyra.Test','c'*64,backend,lambda:'b'*64)
        gate=f.m.OwnedInhibitions(self.fixture.owner,self.fixture.ledger,[resource]);self.route=N(name='org.lyra.Test',digest='c'*64,unit='a.service')
        self.routes=m.CheckedRoutes(gate,self.target,(self.route,));self.route_gate=gate
    def test_unprepared_routes_not_retired_by_reader(self):self.route_setup();self.expect('UnverifiedAdmission',lambda:self.routes.retire((self.route,)));self.assertFalse(self.fixture.ledger.writes)
    def test_completed_routes_readonly_and_original_bound(self):
        self.route_setup();self.route_gate.resume(1002,'a'*32,('dbus-activation','org.lyra.Test'),lambda _:True);before=self.fixture.ledger.files.copy();calls=self.fixture.backend.calls
        self.assertEqual(self.routes.inspect(self.route),'retired');self.assertTrue(self.routes.retire((self.route,)));self.assertEqual(before,self.fixture.ledger.files);self.assertEqual(calls,self.fixture.backend.calls)
    def test_changed_route_unit_or_digest_not_accepted(self):
        self.route_setup()
        for name,digest,unit in (('org.lyra.Test','d'*64,'a.service'),('org.lyra.Test','c'*64,'b.service'),('org.lyra.Other','c'*64,'a.service')):
            self.expect('UnverifiedProducerCatalog',lambda:self.routes.inspect(N(name=name,digest=digest,unit=unit)))
        self.expect('UnverifiedProducerCatalog',lambda:self.routes.retire(()))
    def test_no_authorization_or_effect_api_on_readers(self):
        self.assertFalse(any(hasattr(self.masks,n) for n in ('execute','authorize','unmask','unblock','enroll')))
if __name__=='__main__':unittest.main()
