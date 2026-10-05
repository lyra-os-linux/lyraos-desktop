import importlib.util,sys,unittest
from dataclasses import replace
from types import SimpleNamespace as N
from pathlib import Path
import test_parental_pam_unit_stop as fixture
import test_parental_unit_stop_jobs as journal
P=Path(__file__).resolve().parents[1]/'docs/evidence'
saved=dict(sys.modules)
try:
 sys.modules['coordinator']=N(GateError=fixture.m.GateError);sys.modules['pam']=fixture.m;sys.modules['jobs']=journal.j
 spec=importlib.util.spec_from_file_location('recovery_test',P/'parental-pam-helper-recovery/recovery.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
finally:
 for name in ('coordinator','pam','jobs'):
  if name in saved:sys.modules[name]=saved[name]
  else:sys.modules.pop(name,None)
class Tests(unittest.TestCase):
 def setUp(self):
  self.f=fixture.Tests();self.f.setUp();self.f.setup_guard();self.boot=journal.BOOT
  self.owner=journal.Owner();self.storage=journal.Storage();self.effects=journal.e.Effects(self.owner,self.storage,N(uid=1002,operation='a'*32,proof_hash='b'*64),{'test.service':'e'*64},lambda:self.boot)
  self.backend=journal.Backend(self.effects,self.storage);self.calls=[]
 def retain(self):return m.retain(self.f.guard,lambda:self.boot)
 def orphan(self):self.f.backend.dead.add(100);self.f.backend.member_ids=(101,);self.f.backend.parents[101]=1
 def drain(self):self.f.backend.dead.add(101);self.f.backend.member_ids=()
 def authorize(self,row):
  self.assertFalse(self.storage.locked);self.assertFalse(self.owner.withdrawal.locked);self.calls.append(row);return True
 def recover(self,origin,auth=None):return origin.recover(self.effects,self.backend,auth or self.authorize)
 def reject(self,code,fn):
  with self.assertRaises(Exception) as error:fn()
  self.assertEqual(getattr(error.exception,'code',None),code)
 def test_stop_retains_both_pins_and_uses_existing_journal(self):
  with self.retain() as o:
   self.orphan();self.backend.hook=self.drain;self.assertEqual(self.recover(o),{'rc':0});self.assertEqual(self.effects.read('test.service')['phase'],'observed-drained')
  self.assertCountEqual(self.f.backend.closed,[100,101]);self.assertEqual(len(self.calls),1);self.assertEqual(self.backend.requests,['test.service'])
 def test_fresh_orphan_refused(self):
  self.orphan()
  def attempt():
   with self.retain():pass
  self.reject('UnverifiedRuntime',attempt);self.assertEqual(self.backend.requests,[])
 def test_live_parent_refused(self):
  with self.retain() as o:self.reject('UnverifiedRuntime',lambda:self.recover(o))
  self.assertEqual(self.calls,[])
 def test_origin_expires(self):
  with self.retain() as o:self.orphan()
  self.reject('InvalidPlan',o.check);self.assertCountEqual(self.f.backend.closed,[100,101])
 def test_denied_and_nonboolean_auth_create_no_intent(self):
  for value in (False,1,None):
   with self.subTest(value=value):
    self.setUp()
    with self.retain() as o:
     self.orphan();self.reject('Denied',lambda:self.recover(o,lambda _:value))
    self.assertEqual(self.storage.writes,0)
 def test_auth_exception_creates_no_intent(self):
  def fail(_):raise RuntimeError('unavailable')
  with self.retain() as o:
   self.orphan();self.reject('AuthorizationFailure',lambda:self.recover(o,fail))
  self.assertEqual(self.storage.writes,0)
 def test_changed_helper_during_auth_refused(self):
  def auth(row):self.f.backend.rows[101]=replace(self.f.backend.rows[101],start_ticks=999);return self.authorize(row)
  with self.retain() as o:
   self.orphan();self.reject('Conflict',lambda:self.recover(o,auth))
  self.assertEqual(self.storage.writes,0)
 def test_mask_loss_during_auth_refused(self):
  def auth(row):self.f.fenced=False;return True
  with self.retain() as o:
   self.orphan();self.reject('UnverifiedAdmission',lambda:self.recover(o,auth))
  self.assertEqual(self.storage.writes,0)
 def test_owner_change_during_auth_refused(self):
  def auth(row):self.owner.row['operation']='f'*32;return True
  with self.retain() as o:
   self.orphan();self.reject('Conflict',lambda:self.recover(o,auth))
  self.assertEqual(self.backend.requests,[])
 def test_extra_member_and_pid_reuse_refused(self):
  for state in ('extra','reuse'):
   with self.subTest(state=state):
    self.setUp()
    with self.retain() as o:
     self.orphan()
     if state=='extra':self.f.backend.member_ids=(101,102)
     else:self.f.backend.dead.add(101)
     self.reject('Conflict',lambda:self.recover(o))
    self.assertEqual(self.calls,[])
 def test_helper_credentials_executable_argv_and_parent_refused(self):
  for field,value in [('uids',(0,)*4),('executable',(1,3,'b'*64)),('argv',('changed',)),('parent',200)]:
   with self.subTest(field=field):
    self.setUp()
    with self.retain() as o:
     self.orphan()
     if field=='parent':self.f.backend.parents[101]=value
     else:self.f.backend.rows[101]=replace(self.f.backend.rows[101],**{field:value})
     self.reject('Conflict',lambda:self.recover(o))
    self.assertEqual(self.storage.writes,0)
 def test_boot_change_refused_before_auth(self):
  with self.retain() as o:
   self.orphan();self.boot='22222222-2222-2222-2222-222222222222';self.reject('RecoveryRequired',lambda:self.recover(o))
  self.assertEqual(self.calls,[])
 def test_boolean_mainpid_refused(self):
  with self.retain() as o:
   self.orphan();original=self.f.backend.runtime
   def bad(n):row=original(n);row['MainPID']['data']=False;return row
   self.f.backend.runtime=bad;self.reject('UnverifiedRuntime',lambda:self.recover(o))
  self.assertEqual(self.calls,[])
 def test_drain_without_intent_has_no_fabricated_completion(self):
  with self.retain() as o:
   self.orphan();self.drain();self.reject('UnverifiedRuntime',lambda:self.recover(o))
  self.assertEqual(self.storage.writes,0)
 def test_accepted_stop_reconciles_without_resubmission(self):
  with self.retain() as o:
   self.orphan();self.backend.ready=False;self.reject('Busy',lambda:self.recover(o));self.assertEqual(self.effects.read('test.service')['phase'],'accepted')
   self.reject('Busy',lambda:self.recover(o));self.drain();self.backend.ready=True;self.assertEqual(self.recover(o)['phase'],'observed-drained')
  self.assertEqual(len(self.calls),3);self.assertEqual(self.backend.requests,['test.service'])
 def test_uncertain_stop_reconciles_without_resubmission(self):
  with self.retain() as o:
   self.orphan();self.backend.reply=None;self.backend.ready=False;self.reject('Busy',lambda:self.recover(o));self.assertEqual(self.effects.read('test.service')['phase'],'uncertain')
   self.reject('Busy',lambda:self.recover(o));self.drain();self.backend.ready=True;self.assertEqual(self.recover(o)['phase'],'observed-drained')
  self.assertEqual(self.backend.requests,['test.service'])
 def test_backend_ready_cannot_fake_helper_exit(self):
  with self.retain() as o:
   self.orphan();self.backend.ready=True;self.reject('Busy',lambda:self.recover(o))
   self.assertEqual(self.effects.read('test.service')['phase'],'accepted')
   self.reject('Busy',lambda:self.recover(o))
  self.assertEqual(self.backend.requests,['test.service'])
 def test_helper_drains_during_authorization_no_new_intent(self):
  def auth(row):self.drain();return self.authorize(row)
  with self.retain() as o:
   self.orphan();self.reject('UnverifiedRuntime',lambda:self.recover(o,auth))
  self.assertEqual(self.storage.writes,0);self.assertEqual(self.backend.requests,[])
 def test_empty_cgroup_allowed_only_after_retained_helper_exits(self):
  with self.retain() as o:
   self.orphan();original=self.f.backend.runtime
   def empty(n):row=original(n);row['ControlGroup']['data']='';return row
   self.f.backend.runtime=empty;self.reject('UnverifiedRuntime',o.check)
   self.drain();self.assertTrue(o.check())
 def test_different_cgroup_after_exit_refused(self):
  with self.retain() as o:
   self.orphan();self.drain();original=self.f.backend.runtime
   def wrong(n):row=original(n);row['ControlGroup']['data']='/system.slice/other.service';return row
   self.f.backend.runtime=wrong;self.reject('UnverifiedRuntime',o.check)
if __name__=='__main__':unittest.main()
