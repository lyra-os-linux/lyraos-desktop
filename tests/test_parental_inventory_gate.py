"""Inventory decisions with synthetic catalogs/adapters; no global coverage claim."""
import sys,unittest,dataclasses,json,hashlib
from contextlib import contextmanager
previous_coordinator=sys.modules.get('coordinator')
import test_parental_ordinary_coordinator as f
sys.modules['coordinator']=f.base
i=f.load('inventory_gate',f.ROOT/'docs/evidence/parental-inventory-gate/inventory.py')
if previous_coordinator is not None:sys.modules['coordinator']=previous_coordinator
def row(uid=1002):
    return dict(schema=1,identity=dict(user='ordinaryuser',uid=uid,gid=1003,group='ordinaryuser'),revision=1,producers={n:dict(state='registered',adapter_digest='c'*64,routes=[dict(id=n,digest='d'*64)]) for n in f.base.REQUIRED})
class MemoryInventory:
    def __init__(self):self.row=row();self.has_lock=False
    def snapshot(self,uid):return i.decode(json.dumps(self.row).encode(),uid)
    @contextmanager
    def locked(self,uid):
        self.has_lock=True
        try:yield 1
        finally:self.has_lock=False
    def read_locked(self,fd,uid):assert self.has_lock;return self.snapshot(uid)
class Tests(unittest.TestCase):
    def setUp(self):
        self.s=f.Store();self.adapters={n:f.Adapter(self.s) for n in f.base.REQUIRED};self.inner=f.c.OrdinaryCoordinator(self.s,f.Error,self.adapters)
        self.inventory=MemoryInventory();self.digests={n:'c'*64 for n in f.base.REQUIRED};self.routes_ok=True;self.prompts=[]
        self.bindings={n:i.Binding(a,lambda n=n:self.digests[n],lambda identity,routes:self.routes_ok) for n,a in self.adapters.items()}
        self.gate=i.InventoryGate(self.inventory,self.inner,self.bindings,'registered-test');self.plan=self.gate.plan(1002,'a'*32)
    def auth(self,p,r):self.prompts.append((p,r));return True
    def begin(self,auth=None,revoke=False):return self.gate.block_and_check(self.plan,auth or self.auth,revoke)
    def expect(self,code,fn):
        with self.assertRaises(f.base.GateError) as got:fn()
        self.assertEqual(got.exception.code,code)
    def test_default_whole_policy_never_accepts_all_seven_names(self):
        gate=i.InventoryGate(self.inventory,f.c.OrdinaryCoordinator(self.s,f.Error,self.adapters),self.bindings)
        self.expect('UnverifiedCoverage',lambda:gate.plan(1002,'a'*32));self.assertFalse(self.s.events);self.assertFalse(self.prompts)
    def test_registered_result_is_never_account_active(self):
        self.assertEqual(self.begin(revoke=True),'CheckedWithinRegisteredInventory');self.assertTrue(self.s.blocked);self.assertFalse(self.s.proof)
        self.assertFalse(any(hasattr(self.gate,n) for n in ('publish','enroll','unblock','resume_and_check')))
    def test_revision_changed_before_authorization_no_prompt_or_effect(self):
        self.inventory.row['revision']=2;self.expect('Conflict',self.begin);self.assertFalse(self.prompts);self.assertFalse(self.s.events)
    def test_catalog_bytes_changed_without_revision_no_prompt(self):
        self.inventory.row['producers']['cron']['routes'][0]['digest']='e'*64;self.expect('Conflict',self.begin);self.assertFalse(self.prompts)
    def test_changed_during_authorization_no_withdrawal(self):
        def auth(p,r):self.assertFalse(self.inventory.has_lock);self.inventory.row['revision']=2;return True
        self.expect('Conflict',lambda:self.begin(auth));self.assertFalse(self.s.events);self.assertTrue(self.s.proof)
    def test_adapter_replaced_before_prompt(self):
        self.inner.adapters=dict(self.inner.adapters);self.inner.adapters['cron']=self.adapters['ssh']
        self.expect('UnverifiedAdapterBinding',self.begin);self.assertFalse(self.prompts);self.assertFalse(self.s.events)
    def test_adapter_digest_changed_during_prompt(self):
        def auth(p,r):self.digests['cron']='e'*64;return True
        self.expect('UnverifiedAdapterBinding',lambda:self.begin(auth));self.assertFalse(self.s.events)
    def test_route_observer_changed_during_prompt(self):
        def auth(p,r):self.routes_ok=False;return True
        self.expect('UnverifiedAdapterBinding',lambda:self.begin(auth));self.assertFalse(self.s.events)
    def test_denied_preserves_positive_proof(self):
        self.expect('Denied',lambda:self.begin(lambda p,r:False));self.assertTrue(self.s.proof);self.assertFalse(self.s.events)
    def test_truthy_auth_denied(self):self.expect('Denied',lambda:self.begin(lambda p,r:1))
    def test_auth_exception_no_effect(self):
        def auth(p,r):raise OSError()
        self.expect('AuthorizationFailure',lambda:self.begin(auth));self.assertFalse(self.s.events)
    def test_mid_adapter_change_keeps_barrier_and_stops_remaining_callbacks(self):
        first=sorted(f.base.REQUIRED)[0]
        def inhibit(t):self.s.events.append('first');self.inventory.row['revision']=2;return True
        self.adapters[first].inhibit=inhibit
        self.expect('Conflict',self.begin);self.assertEqual(self.s.events,['blocked','first']);self.assertTrue(self.s.blocked);self.assertFalse(self.s.proof)
    def test_missing_family_no_effect(self):
        del self.inventory.row['producers']['cron'];self.expect('UnsupportedProducer',self.begin);self.assertFalse(self.prompts);self.assertFalse(self.s.events)
    def test_unsupported_family_never_hidden_by_zero_activity(self):
        self.inventory.row['producers']['cron'].update(state='unsupported',routes=[])
        self.expect('Conflict',self.begin);self.expect('UnsupportedProducer',lambda:self.gate.plan(1002,'a'*32));self.assertFalse(self.s.events)
    def test_extra_family_is_unknown(self):
        self.inventory.row['producers']['at']=self.inventory.row['producers']['cron'];self.expect('UnknownProducer',self.begin);self.assertFalse(self.s.events)
    def test_claim_complete_cannot_issue_certificate(self):
        self.inventory.row['producers']['cron']['state']='complete';self.expect('UnverifiedCoverage',self.begin)
    def test_target_uid_tampering_refused(self):
        bad=dataclasses.replace(self.plan,withdrawal=self.s.plan(1000,'a'*32));self.expect('InvalidPlan',lambda:self.gate.block_and_check(bad,self.auth));self.assertFalse(self.prompts)
    def test_policy_tampering_refused(self):
        bad=dataclasses.replace(self.plan,policy='whole-account');self.expect('InvalidPlan',lambda:self.gate.block_and_check(bad,self.auth))
    def test_stale_inner_plan_preserves_inventory_and_proof(self):
        self.s.revision+=1;self.expect('Conflict',self.begin);self.assertTrue(self.s.proof);self.assertFalse(self.s.events);self.assertFalse(self.prompts)
    def test_callbacks_cannot_run_outside_inventory_context(self):
        target=f.c.Target(1002,'a'*32,'b'*64);self.expect('UnverifiedInventory',lambda:self.inner.adapters['cron'].inhibit(target));self.assertFalse(self.s.events)
    def test_malformed_inner_plan_refused(self):
        bad=dataclasses.replace(self.plan,withdrawal=None);self.expect('InvalidPlan',lambda:self.gate.block_and_check(bad,self.auth));self.assertFalse(self.prompts)
    def test_revoke_boolean_required(self):self.expect('InvalidPlan',lambda:self.begin(revoke=1))
    def test_binding_authority_exception(self):
        def fail():raise OSError()
        b=dict(self.bindings);b['cron']=i.Binding(self.adapters['cron'],fail,lambda identity,routes:True)
        gate=i.InventoryGate(self.inventory,f.c.OrdinaryCoordinator(self.s,f.Error,self.adapters),b,'registered-test')
        self.expect('UnverifiedAdapterBinding',lambda:gate.plan(1002,'a'*32))
class SchemaTests(unittest.TestCase):
    def check(self,value,code='InvalidInventory'):
        with self.assertRaises(f.base.GateError) as got:i.decode(json.dumps(value).encode(),1002)
        self.assertEqual(got.exception.code,code)
    def test_boolean_and_float_revisions(self):
        for v in (True,1.0,0,-1,2**63):r=row();r['revision']=v;self.check(r)
    def test_wrong_uid_or_identity(self):
        for field,value in (('uid',1000),('gid',True),('user','../bad'),('group','')):
            r=row();r['identity'][field]=value;self.check(r)
    def test_duplicate_json_key(self):
        with self.assertRaises(f.base.GateError):i.decode(b'{"schema":1,"schema":1}',1002)
    def test_invalid_and_duplicate_routes(self):
        for routes in ([],[dict(id='../path',digest='d'*64)],[dict(id='x',digest='d'*64)]*2,[dict(id='x',digest='bad')]):
            r=row();r['producers']['cron']['routes']=routes;self.check(r)
    def test_missing_schema_and_extra_fields(self):
        r=row();r['complete']=True;self.check(r)
    def test_truncated_or_malformed_bytes(self):
        for data in (b'',b'{',b'\xff',b'[]'):
            with self.subTest(data=data),self.assertRaises(f.base.GateError):i.decode(data,1002)
if __name__=='__main__':unittest.main()
