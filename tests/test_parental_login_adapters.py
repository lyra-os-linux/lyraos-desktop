"""Route integrity decisions; positive native coverage requires VM evidence."""
import unittest
import test_parental_manager_adapters as f
l=f.load('login_adapters',f.ROOT/'docs/evidence/parental-login-adapters/login-adapters.py')
class LoginTests(unittest.TestCase):
    def setUp(self):
        f.Tests.setUp(self);self.route_ok=True
        self.manager=l.LoginRoute('sshd',self.classification,lambda:self.route_ok,
            self.execute,lambda uid:self.empty,lambda t:self.auth(t),settle_seconds=0)
    execute=f.Tests.execute
    expect=f.Tests.expect
    def test_changed_route_blocks_before_authorization(self):
        self.route_ok=False;self.auth=lambda t:self.fail('authorization reached')
        self.expect('UnverifiedAdmission',lambda:self.manager.revoke(self.t));self.assertEqual(self.calls,[])
    def test_route_changed_during_auth_has_no_effect(self):
        def grant(t):self.route_ok=False;return True
        self.auth=grant;self.expect('UnverifiedAdmission',lambda:self.manager.revoke(self.t));self.assertEqual(self.calls,[])
    def test_changed_route_detected_after_commands(self):
        def execute(args):self.empty=True;self.route_ok=False;return {'rc':0}
        self.manager.execute=execute;self.expect('UnverifiedAdmission',lambda:self.manager.revoke(self.t))
    def test_routes_cannot_claim_admission_without_guard(self):
        self.route_ok=False
        for action in (self.manager.inhibit,self.manager.inhibited,self.manager.quiescent):
            self.expect('UnverifiedAdmission',lambda:action(self.t))
    def test_zero_processes_does_not_excuse_route_integrity(self):
        self.empty=True;self.route_ok=False;self.expect('UnverifiedAdmission',lambda:self.manager.quiescent(self.t))
    def test_shared_daemons_never_stopped(self):
        self.assertTrue(self.manager.revoke(self.t));self.assertEqual(self.calls,[['loginctl','terminate-user','1002'],['systemctl','stop','user@1002.service'],['systemctl','stop','user-runtime-dir@1002.service']])
    def test_denied_no_route_effects(self):
        self.auth=lambda t:False;self.expect('Denied',lambda:self.manager.revoke(self.t));self.assertEqual(self.calls,[])
    def test_other_uid_rejected(self):self.expect('InvalidIdentity',lambda:self.manager.revoke(f.o.Target(1000,'a'*32,'b'*64)))
    def test_unsupported_route_refused(self):
        with self.assertRaises(ValueError):l.LoginRoute('gdm-autologin',self.classification,lambda:True,self.execute,lambda uid:True,lambda t:True)
    def test_gdm_password_supported_under_same_checks(self):
        route=l.LoginRoute('gdm-password',self.classification,lambda:self.route_ok,self.execute,lambda uid:self.empty,lambda t:self.auth(t),settle_seconds=0)
        self.assertTrue(route.inhibited(self.t));self.assertFalse(route.quiescent(self.t));self.assertTrue(route.revoke(self.t))
if __name__=='__main__':unittest.main()
