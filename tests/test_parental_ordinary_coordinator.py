"""Decision/ordering tests; fake adapters never qualify real producer coverage."""
import importlib.util,sys,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
base=load('coordinator',ROOT/'docs/evidence/parental-coordinator/coordinator.py')
c=load('ordinary_coordinator',ROOT/'docs/evidence/parental-ordinary-coordinator/ordinary-coordinator.py')
class Error(RuntimeError):pass
class Store:
    def __init__(self):self.blocked=False;self.proof=True;self.revision=0;self.operation=None;self.events=[]
    def plan(self,uid,operation):return SimpleNamespace(uid=uid,operation=operation,proof_hash='b'*64,revision=self.revision)
    def begin(self,plan,authorize):
        if plan.revision!=self.revision:raise Error('Conflict')
        if authorize(plan) is not True:raise Error('Denied')
        if plan.revision!=self.revision:raise Error('Conflict')
        self.blocked=True;self.proof=False;self.operation=plan.operation;self.revision+=1;self.events.append('blocked')
    def resume(self,uid,operation,authorize):
        if not self.blocked:raise Error('RecoveryRequired')
        if operation!=self.operation:raise Error('Conflict')
        if authorize(dict(uid=uid,operation=operation,proof_hash='b'*64)) is not True:raise Error('Denied')
        self.proof=False;self.events.append('resumed')
    def inspect(self,uid):return 'BlockedUntilAuthorizedRecovery' if self.blocked else 'ExistingOrdinaryProofNeedsVerification'
class Adapter:
    def __init__(self,store):self.store=store
    def inhibit(self,target):assert self.store.blocked;self.store.events.append('inhibit');return True
    def revoke(self,target):self.store.events.append('revoke');return True
    def quiescent(self,target):self.store.events.append('quiescent');return True
    def inhibited(self,target):self.store.events.append('recheck');return True
class OrdinaryCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.store=Store();self.adapters={n:Adapter(self.store) for n in base.REQUIRED}
        self.gate=c.OrdinaryCoordinator(self.store,Error,self.adapters);self.plan=self.gate.plan(1002,'a'*32)
    def begin(self,authorize=lambda p,r:True,revoke=False):return self.gate.block_and_check(self.plan,authorize,revoke)
    def expect(self,code,action=None):
        with self.assertRaises(base.GateError) as got:(action or self.begin)()
        self.assertEqual(got.exception.code,code)
    def test_denied_has_no_effect(self):
        self.expect('Denied',lambda:self.begin(lambda p,r:False));self.assertFalse(self.store.blocked);self.assertTrue(self.store.proof)
    def test_truthy_authorization_denied(self):
        self.expect('Denied',lambda:self.begin(lambda p,r:'yes'));self.assertFalse(self.store.blocked)
    def test_authorization_failure_has_no_effect(self):
        def fail(p,r):raise OSError('auth unavailable')
        self.expect('AuthorizationFailure',lambda:self.begin(fail));self.assertFalse(self.store.blocked)
    def test_stale_before_prompt(self):
        self.store.revision+=1
        self.expect('Conflict',lambda:self.begin(lambda p,r:self.fail('prompted')));self.assertFalse(self.store.blocked)
    def test_change_during_authorization(self):
        def grant(p,r):self.store.revision+=1;return True
        self.expect('Conflict',lambda:self.begin(grant));self.assertFalse(self.store.blocked)
    def test_missing_producer_after_durable_withdrawal(self):
        self.gate.adapters.pop('cron');self.expect('UnsupportedProducer');self.assertTrue(self.store.blocked);self.assertFalse(self.store.proof)
    def test_no_adapters_never_pass(self):
        self.gate.adapters={};self.expect('UnsupportedProducer');self.assertTrue(self.store.blocked)
    def test_adapter_false_keeps_blocked(self):
        self.gate.adapters['cron'].inhibit=lambda t:False;self.expect('UnsupportedProducer');self.assertTrue(self.store.blocked)
    def test_adapter_exception_keeps_blocked(self):
        def fail(t):raise OSError('producer gone')
        self.gate.adapters['cron'].inhibit=fail;self.expect('AdapterFailure');self.assertTrue(self.store.blocked)
    def test_not_quiescent_keeps_blocked(self):
        self.gate.adapters['cron'].quiescent=lambda t:False;self.expect('UnverifiedQuiescence');self.assertTrue(self.store.blocked)
    def test_reactivation_after_drain_keeps_blocked(self):
        self.gate.adapters['cron'].inhibited=lambda t:False;self.expect('UnsupportedProducer');self.assertTrue(self.store.blocked)
    def test_revoke_is_explicit_and_follows_inhibition(self):
        self.assertEqual(self.begin(revoke=True),'CheckedWithinAdapterScope')
        e=self.store.events;self.assertLess(e.index('blocked'),e.index('inhibit'));self.assertLess(e.index('inhibit'),e.index('revoke'));self.assertLess(e.index('revoke'),e.index('quiescent'));self.assertLess(e.index('quiescent'),e.index('recheck'))
    def test_no_implicit_revoke_or_publication(self):
        self.assertEqual(self.begin(),'CheckedWithinAdapterScope');self.assertNotIn('revoke',self.store.events)
        self.assertTrue(self.store.blocked);self.assertFalse(self.store.proof)
        self.assertFalse(any(hasattr(self.gate,n) for n in ('publish','enroll','tombstone','unblock')))
    def test_resume_wrong_operation_is_conflict(self):
        self.begin();self.expect('Conflict',lambda:self.gate.resume_and_check(1002,'c'*32,lambda p,r:True));self.assertTrue(self.store.blocked)
    def test_resume_same_operation_still_checks_coverage(self):
        self.begin();self.gate.adapters={};self.expect('UnsupportedProducer',lambda:self.gate.resume_and_check(1002,'a'*32,lambda p,r:True));self.assertFalse(self.store.proof)
    def test_reconcile_is_read_only_and_not_ordinary(self):
        self.assertEqual(self.gate.state(1002),'ExistingOrdinaryProofNeedsVerification')
        self.begin();before=self.store.events[:];self.assertEqual(self.gate.state(1002),'BlockedUntilAuthorizedRecovery');self.assertEqual(before,self.store.events)
    def test_resume_authorization_cannot_change_verified_target(self):
        self.begin();seen=[]
        self.gate.adapters['cron'].inhibit=lambda t:(seen.append(t) or True)
        def grant(row,revoke):row['uid']=1000;row['operation']='c'*32;return True
        self.assertEqual(self.gate.resume_and_check(1002,'a'*32,grant),'CheckedWithinAdapterScope')
        self.assertEqual((seen[0].uid,seen[0].operation),(1002,'a'*32))
    def test_storage_error_never_reaches_adapter(self):
        def fail(p,a):raise Error('UnsafeState')
        self.store.begin=fail;self.expect('StorageFailure');self.assertEqual(self.store.events,[])
    def test_loss_of_negative_authority_detected_after_callbacks(self):
        self.gate.adapters['cron'].inhibited=lambda t:(setattr(self.store,'blocked',False) or True)
        self.expect('UnverifiedClassification');self.assertFalse(self.store.proof)
if __name__=='__main__':unittest.main()
