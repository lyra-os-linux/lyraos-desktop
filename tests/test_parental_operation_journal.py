"""Durability decisions with explicit memory storage; VM proves actual fsync/PAM."""
import sys,json,unittest,hashlib,dataclasses
from contextlib import contextmanager
import test_parental_manager_adapters as f
prior=sys.modules.get('coordinator');sys.modules['coordinator']=f.c;sys.modules['withdrawal']=f.w
o=f.load('operation_journal',f.ROOT/'docs/evidence/parental-operation-journal/operations.py')
if prior is not None:sys.modules['coordinator']=prior
class Stop(RuntimeError):pass
class Error(RuntimeError):pass
class Storage:
    def __init__(self):self.files={'proof':b'ordinary','marker':None,'journal':None};self.locked=False;self.writes=[];self.crash_at=None
    @contextmanager
    def lock(self,uid,exclusive):
        self.locked=True
        try:yield 1,('proof','marker','journal','lock')
        finally:self.locked=False
    def read(self,fd,n):return self.files.get(n)
    def snapshot(self,fd,n):return [self.read(fd,x) for x in n[:3]]
    fingerprint=staticmethod(f.w.Withdrawal.fingerprint)
    def decode_proof(self,p,uid):return dict(uid=uid,user='ordinaryuser',gid=1003,group='ordinaryuser')
    def plan(self,uid,op):
        if self.files['marker'] or self.files['journal']:raise Error('RecoveryRequired')
        return o.WithdrawalPlan(uid,op,self.fingerprint(self.snapshot(1,('proof','marker','journal'))),hashlib.sha256(self.files['proof']).hexdigest())
    def atomic(self,fd,n,data):self.files[n]=data;self.writes.append(n)
    def retire(self,fd,n,row):
        if self.files['proof'] is not None:self.files['proof']=None;self.writes.append('proof-unlinked')
        if self.crash_at=='proof-unlinked':raise Stop()
        self.atomic(fd,'journal',f.w.encode(dict(row,phase='retired',revision=2)))
        if self.crash_at=='retired-journal-synced':raise Stop()
class Inventory:
    def __init__(self):self.revision=1;self.digest='d'*64
    @contextmanager
    def locked(self,uid):yield 1
    def read_locked(self,fd,uid):
        from types import SimpleNamespace as N
        return N(identity=N(user='ordinaryuser',uid=uid,gid=1003,group='ordinaryuser'),revision=self.revision,digest=self.digest)
class Tests(unittest.TestCase):
    def setUp(self):
        self.s=Storage();self.i=Inventory();self.o=o.Operations(self.s,Error,self.i);self.plan=self.o.plan(1002,'a'*32)
    def expect(self,code,fn):
        with self.assertRaises(f.c.GateError) as got:fn()
        self.assertEqual(got.exception.code,code)
    def begin(self,auth=lambda p:True):return self.o.begin(self.plan,auth)
    def resume(self,op='a'*32,auth=lambda p:True):return self.o.resume(1002,op,auth)
    def test_first_effect_is_marker_accepted_as_negative_authority(self):
        self.begin();self.assertEqual(self.s.writes[0],'marker');self.assertFalse(self.s.files['proof']);self.assertEqual(o.decode(self.s.files['.operation-1002.json'])['phase'],'retired')
    def test_denied_before_effects(self):self.expect('Denied',lambda:self.begin(lambda p:False));self.assertFalse(self.s.writes)
    def test_truthy_denied(self):self.expect('Denied',lambda:self.begin(lambda p:1));self.assertFalse(self.s.writes)
    def test_authority_exception(self):
        def auth(p):raise OSError()
        self.expect('AuthorizationFailure',lambda:self.begin(auth));self.assertFalse(self.s.writes)
    def test_inventory_change_during_auth_no_effect(self):
        def auth(p):self.i.revision=2;return True
        self.expect('Conflict',lambda:self.begin(auth));self.assertFalse(self.s.writes)
    def test_proof_change_during_auth_no_effect(self):
        def auth(p):self.s.files['proof']=b'changed';return True
        self.expect('Conflict',lambda:self.begin(auth));self.assertFalse(self.s.writes)
    def test_authorization_payload_mutation_cannot_change_owner(self):
        def auth(p):p['identity']['uid']=1000;p['operation']='b'*32;p['action']='enroll';return True
        self.begin(auth);r=o.decode(self.s.files['.operation-1002.json']);self.assertEqual(r['identity']['uid'],1002);self.assertEqual(r['operation'],'a'*32);self.assertEqual(r['action'],'withdraw-admission')
    def test_six_own_crash_boundaries_resume_with_same_owner(self):
        for point in ('intent-marker-synced','owned-intent-synced','legacy-marker-synced','legacy-journal-synced','owned-blocked-synced','owned-retired-synced'):
            with self.subTest(point=point):
                self.setUp()
                def crash(p):
                    if p==point:raise Stop()
                self.o.crash=crash
                with self.assertRaises(Stop):self.begin()
                self.assertIsNotNone(self.s.files['marker']);self.o.crash=lambda p:None
                self.assertEqual(self.resume(),'AdmissionWithdrawnNoQuiescence');self.assertFalse(self.s.files['proof'])
    def test_two_historical_retirement_crashes_resume(self):
        for point in ('proof-unlinked','retired-journal-synced'):
            with self.subTest(point=point):
                self.setUp();self.s.crash_at=point
                with self.assertRaises(Stop):self.begin()
                self.s.crash_at=None;self.assertEqual(self.resume(),'AdmissionWithdrawnNoQuiescence')
    def test_retry_finished_is_read_only(self):
        self.begin();old=self.s.files.copy();writes=self.s.writes[:];self.resume();self.assertEqual(self.s.files,old);self.assertEqual(self.s.writes,writes)
    def test_no_phase_regression_on_resume(self):
        self.s.crash_at='retired-journal-synced'
        with self.assertRaises(Stop):self.begin()
        old=self.s.files['journal'];self.s.crash_at=None;self.s.writes=[];self.resume();self.assertEqual(self.s.files['journal'],old);self.assertEqual(self.s.writes,['.operation-1002.json'])
    def test_new_operation_after_retirement_refused(self):
        self.begin();self.expect('RecoveryRequired',lambda:self.o.plan(1002,'b'*32))
    def test_wrong_operation_does_not_prompt_or_write(self):
        self.begin();writes=self.s.writes[:];self.expect('Conflict',lambda:self.resume('b'*32,lambda r:self.fail('prompted')));self.assertEqual(self.s.writes,writes)
    def test_resume_denied_preserves_records(self):
        self.begin();old=self.s.files.copy();self.expect('Denied',lambda:self.resume(auth=lambda r:False));self.assertEqual(old,self.s.files)
    def test_stale_inventory_on_resume_no_prompt(self):
        self.begin();self.i.digest='e'*64;old=self.s.files.copy();self.expect('Conflict',lambda:self.resume(auth=lambda r:self.fail('prompted')));self.assertEqual(old,self.s.files)
    def test_recreated_proof_after_retirement_never_removed(self):
        self.begin();self.s.files['proof']=b'ordinary';self.expect('RecoveryRequired',self.resume);self.assertEqual(self.s.files['proof'],b'ordinary')
    def test_missing_marker_never_reconstructed(self):
        self.begin();self.s.files['marker']=None;old=self.s.files.copy();self.expect('RecoveryRequired',self.resume);self.assertEqual(old,self.s.files)
    def test_corrupt_owner_does_not_change_barrier(self):
        self.begin();self.s.files['.operation-1002.json']=b'{}';marker=self.s.files['marker'];self.expect('InvalidOperationJournal',self.resume);self.assertEqual(marker,self.s.files['marker'])
    def test_inspect_is_read_only_and_never_active(self):
        self.begin();old=self.s.files.copy();self.assertEqual(self.o.inspect(1002),'AdmissionWithdrawnNoQuiescence');self.assertEqual(old,self.s.files);self.assertFalse(any(hasattr(self.o,n) for n in ('publish','enroll','unblock','revoke_producers')))
class SchemaTests(unittest.TestCase):
    def row(self):
        t=Tests();t.setUp();return t.o._record(t.plan)
    def test_round_trip(self):r=self.row();self.assertEqual(o.decode(o.encode(r)),r)
    def test_invalid_phase_revision_and_action(self):
        for key,v in (('revision',True),('revision',2),('phase','active'),('action','enroll'),('inventory_revision',False),('operation','bad'),('proof_hash','bad')):
            r=self.row();r[key]=v
            with self.subTest(key=key,value=v),self.assertRaises(f.c.GateError):o.encode(r)
    def test_duplicate_and_malformed_json(self):
        for data in (b'{"schema":1,"schema":1}',b'{}',b'\xff',b'[]',b'{'):
            with self.subTest(data=data),self.assertRaises(f.c.GateError):o.decode(data)
if __name__=='__main__':unittest.main()
