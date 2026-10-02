"""Decision tests, never substitutes for real broker activation evidence."""
import sys,unittest
import test_parental_manager_adapters as f
sys.modules['coordinator']=f.c
d=f.load('dbus_adapter',f.ROOT/'docs/evidence/parental-dbus-adapter/dbus-adapter.py')
class Retirement:
    def __init__(self):self.states={}
    def inspect(self,r):return self.states.get(r.name,'active')
    def retire(self,routes):
        for r in routes:self.states[r.name]='retired'
        return True
class Tests(unittest.TestCase):
    execute=f.Tests.execute
    expect=f.Tests.expect
    def setUp(self):
        f.Tests.setUp(self);self.retirement=Retirement();self.catalog=True;self.bus_absent=False;self.effects=[];self.empty=False;self.auth=lambda t,a,r:True
        self.routes=(d.Route('org.lyra.Unit','c'*64,'a.service'),d.Route('org.lyra.Exec','d'*64))
        self.adapter=d.DBusActivation(self.classification,self.routes,lambda i,r:self.catalog,self.retirement,self.reload,lambda r:self.bus_absent,self.stop,lambda r:self.empty,lambda t,a,r:self.auth(t,a,r),settle_seconds=0)
    def reload(self):self.assertTrue(self.s.locked);self.effects.append('reload');self.bus_absent=True;return True
    def stop(self,r):self.assertTrue(self.s.locked);self.effects.append('stop');self.empty=True;return True
    def test_inhibition_does_not_revoke(self):
        self.assertTrue(self.adapter.inhibit(self.t));self.assertFalse(self.adapter.quiescent(self.t));self.assertEqual(self.effects,['reload'])
    def test_denied_inhibition_has_no_effects(self):
        self.auth=lambda t,a,r:False;self.expect('Denied',lambda:self.adapter.inhibit(self.t));self.assertFalse(self.effects);self.assertFalse(self.retirement.states)
    def test_truthy_denied(self):
        self.auth=lambda t,a,r:1;self.expect('Denied',lambda:self.adapter.inhibit(self.t));self.assertFalse(self.effects)
    def test_auth_exception(self):
        def fail(t,a,r):raise OSError()
        self.auth=fail;self.expect('AuthorizationFailure',lambda:self.adapter.inhibit(self.t));self.assertFalse(self.effects)
    def test_target_changed_during_auth(self):
        def grant(t,a,r):self.s.files['marker']=None;return True
        self.auth=grant;self.expect('UnverifiedClassification',lambda:self.adapter.inhibit(self.t));self.assertFalse(self.retirement.states)
    def test_catalog_changed_during_auth(self):
        def grant(t,a,r):self.catalog=False;return True
        self.auth=grant;self.expect('UnverifiedProducerCatalog',lambda:self.adapter.inhibit(self.t));self.assertFalse(self.retirement.states)
    def test_failed_reload_keeps_retirement(self):
        self.adapter.reload=lambda:False;self.expect('UnverifiedAdmission',lambda:self.adapter.inhibit(self.t));self.assertEqual(len(self.retirement.states),2)
    def test_cached_activation_refuses_admission(self):
        self.adapter.reload=lambda:True;self.expect('UnverifiedAdmission',lambda:self.adapter.inhibit(self.t));self.assertEqual(len(self.retirement.states),2)
    def test_partial_failure_does_not_stop(self):
        def retire(routes):self.retirement.states[routes[0].name]='retired';raise f.c.GateError('UnsafeRoutes')
        self.retirement.retire=retire;self.expect('UnsafeRoutes',lambda:self.adapter.inhibit(self.t));self.assertEqual(len(self.retirement.states),1);self.assertFalse(self.effects)
    def test_stop_requires_prior_fence(self):
        self.expect('UnverifiedAdmission',lambda:self.adapter.revoke(self.t));self.assertFalse(self.effects)
    def test_denied_revocation_preserves_fences(self):
        self.adapter.inhibit(self.t);self.auth=lambda t,a,r:False;self.expect('Denied',lambda:self.adapter.revoke(self.t));self.assertEqual(self.effects,['reload']);self.assertEqual(len(self.retirement.states),2)
    def test_stop_failure_refuses_completion(self):
        self.adapter.inhibit(self.t);self.adapter.stop_payloads=lambda r:False;self.expect('Busy',lambda:self.adapter.revoke(self.t))
    def test_survivors_refuse_completion(self):
        self.adapter.inhibit(self.t);self.adapter.stop_payloads=lambda r:True;self.expect('UnverifiedQuiescence',lambda:self.adapter.revoke(self.t))
    def test_revocation_rechecks_catalog(self):
        self.adapter.inhibit(self.t)
        def stop(r):self.catalog=False;self.empty=True;return True
        self.adapter.stop_payloads=stop;self.expect('UnverifiedProducerCatalog',lambda:self.adapter.revoke(self.t))
    def test_revocation_rechecks_bus(self):
        self.adapter.inhibit(self.t)
        def stop(r):self.bus_absent=False;self.empty=True;return True
        self.adapter.stop_payloads=stop;self.expect('UnverifiedAdmission',lambda:self.adapter.revoke(self.t))
    def test_missing_retirement_never_claims_quiescence(self):
        self.adapter.inhibit(self.t);self.retirement.states.clear();self.empty=True;self.expect('UnverifiedAdmission',lambda:self.adapter.quiescent(self.t))
    def test_idempotent_retirement_keeps_negative_authority(self):
        self.adapter.inhibit(self.t);self.adapter.revoke(self.t);self.adapter.inhibit(self.t);self.adapter.revoke(self.t);self.assertEqual(len(self.retirement.states),2)
    def test_empty_catalog_unsupported(self):
        with self.assertRaises(f.c.GateError):d.DBusActivation(self.classification,(),lambda i,r:True,self.retirement,self.reload,lambda r:True,self.stop,lambda r:True,self.auth)
    def test_invalid_and_duplicate_routes(self):
        for route in (d.Route('../bad','c'*64),d.Route('org.lyra.X','x'*64),d.Route('org.lyra.X','c'*64,'a@x.service')):
            with self.subTest(route=route),self.assertRaises(f.c.GateError):d.DBusActivation(self.classification,(route,),lambda i,r:True,self.retirement,self.reload,lambda r:True,self.stop,lambda r:True,self.auth)
        with self.assertRaises(f.c.GateError):d.DBusActivation(self.classification,(self.routes[0],self.routes[0]),lambda i,r:True,self.retirement,self.reload,lambda r:True,self.stop,lambda r:True,self.auth)
    def test_unbounded_wait_rejected(self):
        with self.assertRaises(ValueError):d.DBusActivation(self.classification,self.routes,lambda i,r:True,self.retirement,self.reload,lambda r:True,self.stop,lambda r:True,self.auth,settle_seconds=31)
if __name__=='__main__':unittest.main()
