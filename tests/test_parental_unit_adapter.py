"""Decision tests for registered units; doubles are not native producer coverage."""
import unittest,sys
import test_parental_manager_adapters as f
sys.modules['coordinator']=f.c
u=f.load('unit_adapter',f.ROOT/'docs/evidence/parental-unit-adapter/unit-adapter.py')
class FakeMasks:
    def __init__(self):self.names=set()
    def masked(self,name):return name in self.names
    def install(self,names):self.names.update(names);return True
class Tests(unittest.TestCase):
    execute=f.Tests.execute
    expect=f.Tests.expect
    def setUp(self):
        f.Tests.setUp(self);self.calls=[];self.masks=FakeMasks();self.catalog_ok=True;self.reload_ok=True;self.auth=lambda t,a,c:True;self.empty=False
        self.units=(u.Unit('b.service','service'),u.Unit('a.timer','timer','b.service'),u.Unit('a.service','service'))
        self.adapter=u.SystemUnits(self.classification,self.units,lambda i,c:self.catalog_ok,self.masks,self.exec,lambda name:self.reload_ok,lambda c:self.empty,lambda t,a,c:self.auth(t,a,c),settle_seconds=0)
    def exec(self,args):
        self.assertTrue(self.s.locked);self.calls.append(args)
        if args==['systemctl','stop','a.service']:self.empty=True
        return {'rc':0}
    def test_denied_inhibition_no_masks_or_commands(self):
        self.auth=lambda t,a,c:False;self.expect('Denied',lambda:self.adapter.inhibit(self.t));self.assertFalse(self.masks.names);self.assertFalse(self.calls)
    def test_truthy_denied(self):
        self.auth=lambda t,a,c:1;self.expect('Denied',lambda:self.adapter.inhibit(self.t));self.assertFalse(self.masks.names)
    def test_catalog_changed_in_auth(self):
        def grant(t,a,c):self.catalog_ok=False;return True
        self.auth=grant;self.expect('UnverifiedProducerCatalog',lambda:self.adapter.inhibit(self.t));self.assertFalse(self.masks.names)
    def test_target_changed_in_auth(self):
        def grant(t,a,c):self.s.files['marker']=None;return True
        self.auth=grant;self.expect('UnverifiedClassification',lambda:self.adapter.inhibit(self.t));self.assertFalse(self.masks.names)
    def test_inhibition_does_not_stop_active_units(self):
        self.assertTrue(self.adapter.inhibit(self.t));self.assertFalse(self.adapter.quiescent(self.t));self.assertEqual(self.calls,[['systemctl','daemon-reload']])
    def test_partial_mask_failure_keeps_existing_fences(self):
        def install(names):self.masks.names.add(names[0]);raise f.c.GateError('UnsafeMasks')
        self.masks.install=install
        self.expect('UnsafeMasks',lambda:self.adapter.inhibit(self.t));self.assertEqual(self.masks.names,{'b.service'});self.assertFalse(self.calls)
        self.empty=True;self.expect('UnverifiedAdmission',lambda:self.adapter.quiescent(self.t))
    def test_authorization_exception_has_no_effect(self):
        def fail(t,a,c):raise OSError('authority unavailable')
        self.auth=fail;self.expect('AuthorizationFailure',lambda:self.adapter.inhibit(self.t));self.assertFalse(self.calls);self.assertFalse(self.masks.names)
    def test_stop_timers_before_all_services(self):
        self.adapter.inhibit(self.t);self.assertTrue(self.adapter.revoke(self.t));self.assertEqual(self.calls[1:],[['systemctl','stop','a.timer'],['systemctl','stop','b.service'],['systemctl','stop','a.service']])
    def test_revocation_denied_keeps_masks(self):
        self.adapter.inhibit(self.t);self.auth=lambda t,a,c:False;self.expect('Denied',lambda:self.adapter.revoke(self.t));self.assertEqual(len(self.masks.names),3);self.assertEqual(len(self.calls),1)
    def test_missing_mask_never_claims_quiescence(self):
        self.adapter.inhibit(self.t);self.masks.names.remove('a.timer');self.empty=True;self.expect('UnverifiedAdmission',lambda:self.adapter.quiescent(self.t))
    def test_systemd_reload_does_not_load_masks(self):
        self.reload_ok=False;self.expect('UnverifiedAdmission',lambda:self.adapter.inhibit(self.t));self.assertEqual(len(self.masks.names),3)
    def test_empty_catalog_rejected_even_when_empty(self):
        with self.assertRaises(f.c.GateError):u.SystemUnits(self.classification,(),lambda i,c:True,self.masks,self.exec,lambda n:True,lambda c:True,lambda t,a,c:True)
    def test_timer_route_outside_catalog_rejected(self):
        with self.assertRaises(f.c.GateError):u.SystemUnits(self.classification,(u.Unit('a.timer','timer','missing.service'),),lambda i,c:True,self.masks,self.exec,lambda n:True,lambda c:True,lambda t,a,c:True)
    def test_invalid_names_and_templates_rejected(self):
        for name in ('../a.service','--a.service','a@x.service','a.socket'):
            with self.subTest(name=name),self.assertRaises(f.c.GateError):u.Masks._name(name)
    def test_duplicate_units_rejected(self):
        with self.assertRaises(f.c.GateError):u.SystemUnits(self.classification,(self.units[0],self.units[0]),lambda i,c:True,self.masks,self.exec,lambda n:True,lambda c:True,lambda t,a,c:True)
    def test_revoke_requires_prior_inhibition(self):
        self.expect('UnverifiedAdmission',lambda:self.adapter.revoke(self.t));self.assertFalse(self.calls)
    def test_command_failure_preserves_masks(self):
        self.adapter.inhibit(self.t);self.adapter.execute=lambda args:{'rc':1};self.expect('Busy',lambda:self.adapter.revoke(self.t));self.assertEqual(len(self.masks.names),3)
    def test_incomplete_stop_refuses_completion(self):
        self.adapter.inhibit(self.t);self.adapter.execute=lambda args:{'rc':0};self.expect('UnverifiedQuiescence',lambda:self.adapter.revoke(self.t))
    def test_retry_does_not_unmask(self):
        self.adapter.inhibit(self.t);self.adapter.inhibit(self.t);self.adapter.revoke(self.t);self.adapter.revoke(self.t);self.assertEqual(len(self.masks.names),3)
    def test_catalog_loss_after_stop_refuses_completion(self):
        self.adapter.inhibit(self.t)
        def execute(args):self.catalog_ok=False;self.empty=True;return {'rc':0}
        self.adapter.execute=execute;self.expect('UnverifiedProducerCatalog',lambda:self.adapter.revoke(self.t))
if __name__=='__main__':unittest.main()
