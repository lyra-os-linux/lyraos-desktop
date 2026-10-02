"""Decision tests; the native VM, not these doubles, qualifies systemd behavior."""
import importlib.util,sys,unittest,json
from pathlib import Path
from contextlib import contextmanager
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
c=load('coordinator',ROOT/'docs/evidence/parental-coordinator/coordinator.py')
w=load('withdrawal',ROOT/'docs/evidence/parental-ordinary-withdrawal/withdrawal.py')
o=load('ordinary_coordinator',ROOT/'docs/evidence/parental-ordinary-coordinator/ordinary-coordinator.py')
a=load('manager_adapters',ROOT/'docs/evidence/parental-manager-adapters/adapters.py')
class Store:
    def __init__(self):
        row=dict(schema=1,uid=1002,operation='a'*32,proof_hash='b'*64,phase='blocked',revision=1)
        self.files={'marker':w.encode(row),'journal':w.encode(dict(row,phase='retired',revision=2)),'proof':None}
        self.locked=False
    @contextmanager
    def lock(self,uid,exclusive):
        assert uid==1002 and not exclusive
        self.locked=True
        try:yield 1,('proof','marker','journal','lock')
        finally:self.locked=False
    def read(self,dfd,name):return self.files[name]
class Tests(unittest.TestCase):
    def setUp(self):
        self.s=Store();self.t=o.Target(1002,'a'*32,'b'*64);self.calls=[];self.id_ok=True;self.pam_ok=True;self.empty=False;self.auth=lambda t:True
        self.classification=a.Classification(self.s,a.Identity('ordinaryuser',1002,1003,'ordinaryuser'),lambda i:self.id_ok,lambda:self.pam_ok)
        self.manager=a.UserManager(self.classification,self.execute,lambda uid:self.empty,lambda t:self.auth(t),settle_seconds=0)
    def execute(self,args):
        self.assertTrue(self.s.locked);self.calls.append(args)
        if args==['systemctl','stop','user-runtime-dir@1002.service']:self.empty=True
        return {'rc':0}
    def expect(self,code,action):
        with self.assertRaises(c.GateError) as got:action()
        self.assertEqual(got.exception.code,code)
    def test_classification_does_not_claim_process_quiescence(self):
        self.assertTrue(self.classification.inhibited(self.t));self.assertFalse(self.manager.quiescent(self.t));self.assertEqual(self.calls,[])
    def test_authorized_revoke_scoped_commands(self):
        self.assertTrue(self.manager.revoke(self.t));self.assertEqual(self.calls,[['loginctl','terminate-user','1002'],['systemctl','stop','user@1002.service'],['systemctl','stop','user-runtime-dir@1002.service']])
    def test_denied_no_commands(self):
        self.auth=lambda t:False;self.expect('Denied',lambda:self.manager.revoke(self.t));self.assertEqual(self.calls,[])
    def test_truthy_denied(self):
        self.auth=lambda t:1;self.expect('Denied',lambda:self.manager.revoke(self.t));self.assertEqual(self.calls,[])
    def test_auth_exception(self):
        def fail(t):raise OSError()
        self.auth=fail;self.expect('AuthorizationFailure',lambda:self.manager.revoke(self.t));self.assertEqual(self.calls,[])
    def test_identity_changed_during_auth(self):
        def grant(t):self.id_ok=False;return True
        self.auth=grant;self.expect('InvalidIdentity',lambda:self.manager.revoke(self.t));self.assertEqual(self.calls,[])
    def test_marker_changed_during_auth(self):
        def grant(t):self.s.files['marker']=None;return True
        self.auth=grant;self.expect('UnverifiedClassification',lambda:self.manager.revoke(self.t));self.assertEqual(self.calls,[])
    def test_other_uid_rejected(self):self.expect('InvalidIdentity',lambda:self.manager.revoke(o.Target(1000,'a'*32,'b'*64)))
    def test_wrong_operation(self):self.expect('Conflict',lambda:self.classification.inhibited(o.Target(1002,'c'*32,'b'*64)))
    def test_wrong_proof_hash(self):self.expect('Conflict',lambda:self.classification.inhibited(o.Target(1002,'a'*32,'c'*64)))
    def test_missing_journal(self):
        self.s.files['journal']=None;self.expect('UnverifiedClassification',lambda:self.manager.revoke(self.t));self.assertEqual(self.calls,[])
    def test_corrupt_marker(self):
        self.s.files['marker']=b'{}';self.expect('UnverifiedClassification',lambda:self.classification.inhibited(self.t))
    def test_retirement_incomplete(self):
        self.s.files['journal']=self.s.files['marker'];self.expect('RecoveryRequired',lambda:self.classification.inhibited(self.t))
    def test_proof_recreated(self):
        self.s.files['proof']=b'restored';self.expect('UnverifiedClassification',lambda:self.classification.inhibited(self.t))
    def test_installation_changed(self):
        self.pam_ok=False;self.expect('UnverifiedAdmission',lambda:self.manager.revoke(self.t));self.assertEqual(self.calls,[])
    def test_processes_remaining(self):
        self.execute=lambda args:{'rc':0};self.manager.execute=self.execute
        self.expect('UnverifiedQuiescence',lambda:self.manager.revoke(self.t))
    def test_command_failure_blocks(self):
        self.manager.execute=lambda args:{'rc':1};self.expect('Busy',lambda:self.manager.revoke(self.t))
    def test_delayed_logind_teardown_waits_for_observed_state(self):
        self.manager.settle_seconds=.5
        remaining=[False,False,True]
        self.manager.observe=lambda uid:remaining.pop(0)
        self.assertTrue(self.manager.revoke(self.t));self.assertEqual(remaining,[])
    def test_unbounded_wait_rejected(self):
        with self.assertRaises(ValueError):a.UserManager(self.classification,self.execute,lambda uid:True,lambda t:True,settle_seconds=31)
    def test_already_absent_idempotent(self):
        self.empty=True;self.manager.execute=lambda args:{'rc':1 if args[0]=='loginctl' else 0};self.assertTrue(self.manager.revoke(self.t))
    def test_post_command_revalidation(self):
        def execute(args):self.empty=True;self.pam_ok=False;return {'rc':0}
        self.manager.execute=execute;self.expect('UnverifiedAdmission',lambda:self.manager.revoke(self.t))
if __name__=='__main__':unittest.main()
