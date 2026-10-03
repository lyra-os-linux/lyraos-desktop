"""Ownership decisions with declared memory storage; native VM verifies filesystem."""
import sys,unittest,json,tempfile,os,hashlib
from contextlib import contextmanager
from types import SimpleNamespace as N
import test_parental_operation_journal as j
saved=sys.modules.get('coordinator');sys.modules['coordinator']=j.f.c;sys.modules['operation_journal']=j.o
m=j.f.load('owned_inhibitions',j.f.ROOT/'docs/evidence/parental-owned-inhibitions/ownership.py')
if saved is not None:sys.modules['coordinator']=saved
class Inventory(j.Inventory):
    def read_locked(self,fd,uid):
        s=super().read_locked(fd,uid);s.producers=(N(name='system-units',state='registered',adapter_digest='b'*64,routes=(('a.service','c'*64),)),N(name='dbus-activation',state='registered',adapter_digest='b'*64,routes=(('org.lyra.Test','c'*64),)))
        return s
class Ledger:
    fingerprint=staticmethod(j.Storage.fingerprint)
    def __init__(self):self.files={};self.writes=[];self.held=False
    @contextmanager
    def lock(self,uid,exclusive):
        if self.held:raise j.Error('Busy')
        assert uid==1;self.held=True
        try:yield 2,()
        finally:self.held=False
    def read(self,fd,name):return self.files.get(name)
    def atomic(self,fd,name,data):assert self.held;self.files[name]=data;self.writes.append(name)
class Backend:
    family='system-units'
    def __init__(self,fd):self.fd=fd;self.status='available';self.stamp=None;self.calls=0
    @contextmanager
    def opened(self):yield self.fd
    def state(self,fd,name,digest):return dict(state=self.status,stamp=self.stamp)
    def apply(self,fd,name,digest):
        self.calls+=1;self.status='fenced';self.stamp=dict(device=1,inode=5,digest='f'*64)
class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        fd=os.open(self.temp.name,os.O_RDONLY|os.O_DIRECTORY);self.addCleanup(os.close,fd)
        self.s=j.Storage();self.i=Inventory();self.owner=j.o.Operations(self.s,j.Error,self.i);self.owner.begin(self.owner.plan(1002,'a'*32),lambda _:True)
        self.ledger=Ledger();self.backend=Backend(fd);self.version='b'*64
        self.r=m.Resource('system-units','a.service','c'*64,self.backend,lambda:self.version)
        self.gate=m.OwnedInhibitions(self.owner,self.ledger,[self.r]);self.key=('system-units','a.service')
    def plan(self):return self.gate.plan(1002,'a'*32,self.key)
    def run_plan(self,auth=lambda _:True):return self.gate.execute(self.plan(),auth)
    def expect(self,code,fn):
        with self.assertRaises(j.f.c.GateError) as got:fn()
        self.assertEqual(got.exception.code,code)
    def test_intent_precedes_effect_and_finished_owner_retained(self):
        def effect(*args):
            row=m.decode(next(iter(self.ledger.files.values())));self.assertEqual(row['phase'],'intent');Backend.apply(self.backend,*args)
        self.backend.apply=effect;self.assertEqual(self.run_plan(),'OwnedFilesystemInhibitionNoQuiescence')
        row=m.decode(next(iter(self.ledger.files.values())));self.assertEqual(row['owner']['operation'],'a'*32);self.assertEqual(row['phase'],'fenced')
    def test_denied_has_zero_effects(self):self.expect('Denied',lambda:self.run_plan(lambda _:False));self.assertFalse(self.ledger.writes);self.assertEqual(self.backend.calls,0)
    def test_truthy_denied(self):self.expect('Denied',lambda:self.run_plan(lambda _:1));self.assertFalse(self.ledger.writes)
    def test_authorization_exception(self):
        def fail(_):raise OSError()
        self.expect('AuthorizationFailure',lambda:self.run_plan(fail));self.assertFalse(self.ledger.writes)
    def test_authorization_outside_locks_and_detached_payload(self):
        def auth(row):
            self.assertFalse(self.ledger.held);self.assertFalse(self.s.locked);row['owner']['operation']='b'*32;return True
        self.run_plan(auth);self.assertEqual(m.decode(next(iter(self.ledger.files.values())))['owner']['operation'],'a'*32)
    def test_inventory_change_in_prompt_no_effect(self):
        def auth(_):self.i.revision=2;return True
        self.expect('Conflict',lambda:self.run_plan(auth));self.assertFalse(self.ledger.writes)
    def test_version_change_in_prompt_no_effect(self):
        def auth(_):self.version='e'*64;return True
        self.expect('UnverifiedProducerCatalog',lambda:self.run_plan(auth));self.assertFalse(self.ledger.writes)
    def test_effect_appears_during_prompt_not_adopted(self):
        def auth(_):self.backend.status='fenced';self.backend.stamp=dict(device=1,inode=5,digest='f'*64);return True
        self.expect('UnownedInhibition',lambda:self.run_plan(auth));self.assertFalse(self.ledger.writes)
    def test_wrong_operation_before_prompt(self):self.expect('Conflict',lambda:self.gate.resume(1002,'b'*32,self.key,lambda _:self.fail('prompted')))
    def test_unregistered_resource_refused(self):self.expect('UnsupportedProducer',lambda:self.gate.plan(1002,'a'*32,('system-units','unknown.service')))
    def test_wrong_route_digest_refused(self):
        self.gate=m.OwnedInhibitions(self.owner,self.ledger,[m.Resource('system-units','a.service','d'*64,self.backend,lambda:'b'*64)]);self.expect('UnverifiedProducerCatalog',self.plan)
    def test_preexisting_unowned_mask_not_adopted(self):self.backend.status='fenced';self.expect('UnownedInhibition',self.plan);self.assertFalse(self.ledger.writes)
    def test_three_crash_boundaries_resume_without_phase_regression(self):
        for point in ('intent-synced','effect-synced','fenced-journal-synced'):
            with self.subTest(point=point):
                self.ledger.files={};self.ledger.writes=[];self.backend.status='available';self.backend.stamp=None
                def crash(p):
                    if p==point:raise j.Stop()
                self.gate.crash=crash
                with self.assertRaises(j.Stop):self.run_plan()
                self.assertTrue(self.s.files['marker']);self.gate.crash=lambda _:None
                self.gate.resume(1002,'a'*32,self.key,lambda _:True)
                self.assertEqual(m.decode(next(iter(self.ledger.files.values())))['phase'],'fenced')
    def test_finished_retry_readonly(self):
        self.run_plan();before=self.ledger.files.copy();writes=self.ledger.writes[:];calls=self.backend.calls
        self.run_plan();self.assertEqual(before,self.ledger.files);self.assertEqual(writes,self.ledger.writes);self.assertEqual(calls,self.backend.calls)
    def test_different_owner_in_shared_ledger_conflicts(self):
        self.run_plan();name=next(iter(self.ledger.files));row=m.decode(self.ledger.files[name]);row['owner']['operation']='b'*32;self.ledger.files[name]=m.encode(row)
        self.expect('OwnershipConflict',self.plan)
    def test_lost_ledger_never_adopts_existing_fence(self):self.run_plan();self.ledger.files={};self.expect('UnownedInhibition',self.plan)
    def test_removed_completed_mask_never_recreated(self):self.run_plan();self.backend.status='available';self.backend.stamp=None;self.expect('ResourceChanged',self.plan)
    def test_replaced_completed_mask_refused(self):self.run_plan();self.backend.stamp=dict(device=1,inode=6,digest='f'*64);self.expect('ResourceChanged',self.plan)
    def test_global_ledger_contention_is_busy(self):self.ledger.held=True;self.expect('Busy',self.plan)
    def test_missing_ledger_lock_not_misattributed_to_inventory(self):
        @contextmanager
        def inventory(uid):
            try:yield 1
            except FileNotFoundError as e:raise j.f.c.GateError('UnknownInventory') from e
        @contextmanager
        def missing(uid,exclusive):
            raise FileNotFoundError('ledger lock')
            yield
        self.i.locked=inventory;self.ledger.lock=missing
        self.expect('StorageFailure',self.plan);self.assertFalse(self.ledger.writes)
    def test_backend_oserror_not_misattributed_to_inventory(self):
        @contextmanager
        def inventory(uid):
            try:yield 1
            except OSError as e:raise j.f.c.GateError('UnsafeInventory') from e
        def fail(*args):raise OSError('resource directory')
        self.i.locked=inventory;self.backend.state=fail
        self.expect('StorageFailure',self.plan);self.assertFalse(self.ledger.writes)
    def test_missing_barrier_never_repaired(self):self.s.files['marker']=None;self.expect('RecoveryRequired',self.plan);self.assertFalse(self.ledger.writes)
    def test_recreated_positive_proof_never_removed(self):self.s.files['proof']=b'ordinary';self.expect('RecoveryRequired',self.plan);self.assertEqual(self.s.files['proof'],b'ordinary')
    def test_corrupt_ledger_preserves_negative_authority(self):
        self.run_plan();name=next(iter(self.ledger.files));self.ledger.files[name]=b'{}';self.expect('InvalidFenceJournal',self.plan);self.assertTrue(self.s.files['marker'])
    def test_malformed_plan_refused(self):self.expect('InvalidPlan',lambda:self.gate.execute({},lambda _:True))
    def test_inspection_readonly_and_no_reopening_api(self):
        self.run_plan();old=self.ledger.files.copy();self.assertEqual(self.gate.inspect(1002,'a'*32,self.key),'fenced');self.assertEqual(old,self.ledger.files)
        self.assertFalse(any(hasattr(self.gate,n) for n in ('unmask','unblock','enroll','restore_route')))
    def test_strict_schema(self):
        row=m.decode(self.plan().entry)
        for key,value in (('revision',True),('phase','active'),('revision',2),('effect',dict(device=1,inode=2,digest='f'*64)),('name','../a.service'),('schema',True)):
            bad=dict(row);bad[key]=value
            with self.subTest(key=key),self.assertRaises(j.f.c.GateError):m.encode(bad)
        for data in (b'{"schema":1,"schema":1}',b'[]',b'\xff'):
            with self.assertRaises(j.f.c.GateError):m.decode(data)
if __name__=='__main__':unittest.main()
