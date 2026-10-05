import copy,importlib.util,json,sys,unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as N
import test_parental_pam_helper_recovery as previous
fixture=previous.fixture;journal=previous.journal
P=Path(__file__).resolve().parents[1]/'docs/evidence';saved=dict(sys.modules)
try:
 sys.modules['reference']=fixture.r;sys.modules['guard']=N(GuardedExecution=fixture.m.GuardedExecution)
 sys.modules['coordinator']=N(GateError=fixture.m.GateError);sys.modules['pam']=fixture.m;sys.modules['recovery']=previous.m;sys.modules['jobs']=journal.j
 spec=importlib.util.spec_from_file_location('cold_restart_test',P/'parental-cold-unit-stop/cold.py');cold=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cold;spec.loader.exec_module(cold);sys.modules['cold']=cold
 spec=importlib.util.spec_from_file_location('daemon_restart_test',P/'parental-pam-daemon-recovery/restart.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
finally:
 for name in ('coordinator','pam','recovery','jobs','cold','cold_restart_test','reference','guard'):
  if name in saved:sys.modules[name]=saved[name]
  else:sys.modules.pop(name,None)
class Tests(unittest.TestCase):
 def setUp(self):
  self.f=fixture.Tests();self.f.setUp();self.f.setup_guard();self.boot=journal.BOOT;self.invocation=dict(type='ay',data=list(range(16)))
  self.owner=journal.Owner();self.owner.routes=(('test.service','a'*64),);self.storage=journal.Storage()
  self.effects=journal.e.Effects(self.owner,self.storage,N(uid=1002,operation='a'*32,proof_hash='b'*64),{'test.service':'a'*64},lambda:self.boot)
  self.origins=self.new_origins();self.auth_calls=[];self.empty=True
  data=dict(MainPID=0,ControlGroup='',ActiveState='inactive',SubState='dead',Job=[0,'/'],InvocationID=list(range(16)))
  self.rows={k:dict(type=s,data=data[k]) for k,s in cold.SPECS.items()}
  self.restart=m.Restarted(self.origins,lambda n:copy.deepcopy(self.rows),lambda n:self.empty,self.f.guard.sources)
 def new_origins(self):return m.Origins(self.effects,lambda n:fixture.r.LocalIdentity(n,1002,1003),lambda n:1003,lambda p:self.f.stamp,lambda p:self.f.body,lambda n:copy.deepcopy(self.invocation))
 def seal(self):
  with previous.m.retain(self.f.guard,lambda:self.boot) as origin:return self.origins.seal(origin,self.f.rows)
 def pending(self,phase='accepted'):
  self.seal();row=self.effects.begin('test.service')
  if phase!='intent':row=self.effects.advance(row,phase,'/org/freedesktop/systemd1/job/22' if phase=='accepted' else None)
  return row
 def authorize(self,row):
  self.assertFalse(self.storage.locked);self.assertFalse(self.owner.withdrawal.locked);self.auth_calls.append(row);return True
 def reconcile(self,auth=None):return self.restart.reconcile('test.service',auth or self.authorize)
 def reject(self,code,fn):
  with self.assertRaises(Exception) as error:fn()
  self.assertEqual(getattr(error.exception,'code',None),code)
 def mutate(self,fn):
  name=self.origins.name('test.service');row=json.loads(self.storage.rows[name]);fn(row);self.storage.rows[name]=(json.dumps(row)+'\n').encode()
 def test_new_objects_reconstruct_cold_reference_and_complete_existing_stop(self):
  self.pending();self.origins=self.new_origins();self.restart.origins=self.origins
  row=self.reconcile();self.assertEqual(row['phase'],'observed-drained');self.assertEqual(len(self.auth_calls),1)
  self.assertEqual(self.storage.writes,4)
 def test_no_pid_or_argv_in_authorization_request(self):
  self.pending();self.reconcile();self.assertEqual(set(self.auth_calls[0]),{'unit','uid','operation','action'})
 def test_all_pending_phases_reconcile_without_backend_request(self):
  self.assertFalse(hasattr(m.ColdBackend(lambda:True),'request'))
  for phase in ('intent','accepted','uncertain'):
   with self.subTest(phase=phase):
    self.setUp();self.pending(phase);self.assertEqual(self.reconcile()['phase'],'observed-drained')
 def test_missing_origin_refused_even_if_unit_empty(self):
  self.effects.begin('test.service');self.reject('RecoveryRequired',self.reconcile);self.assertEqual(self.auth_calls,[])
 def test_origin_without_effect_never_fabricates_completion(self):
  self.seal();before=self.storage.writes;self.reject('RecoveryRequired',self.reconcile);self.assertEqual(self.storage.writes,before)
 def test_live_orphan_before_authorization_refused(self):
  self.pending();self.empty=False;before=self.storage.writes;self.reject('Busy',self.reconcile);self.assertEqual(self.auth_calls,[]);self.assertEqual(self.storage.writes,before)
 def test_mainpid_zero_and_job_zero_not_sufficient(self):
  self.pending();self.rows['ActiveState']['data']='deactivating';self.rows['SubState']['data']='stop-sigterm';self.reject('Busy',self.reconcile)
 def test_denial_does_not_modify_journal(self):
  self.pending();before=self.storage.writes;self.reject('Denied',lambda:self.reconcile(lambda _:False));self.assertEqual(self.storage.writes,before)
 def test_nonboolean_authorization_refused(self):
  self.pending();self.reject('Denied',lambda:self.reconcile(lambda _:1));self.assertEqual(self.effects.read('test.service')['phase'],'accepted')
 def test_authorization_exception_keeps_pending(self):
  self.pending()
  def fail(_):raise RuntimeError()
  self.reject('AuthorizationFailure',lambda:self.reconcile(fail));self.assertEqual(self.effects.read('test.service')['phase'],'accepted')
 def test_cgroup_repopulates_during_auth_refused(self):
  self.pending()
  def auth(row):self.empty=False;return self.authorize(row)
  self.reject('Busy',lambda:self.reconcile(auth));self.assertEqual(self.effects.read('test.service')['phase'],'accepted')
 def test_invocation_changes_during_auth_refused(self):
  self.pending()
  def auth(row):self.rows['InvocationID']['data']=[0]*16;return True
  self.reject('Conflict',lambda:self.reconcile(auth))
 def test_mask_loss_during_auth_refused(self):
  self.pending();self.restart.revalidate=lambda ref:ref if self.f.fenced else (_ for _ in ()).throw(fixture.m.GateError('UnverifiedAdmission'))
  def auth(row):self.f.fenced=False;return True
  self.reject('UnverifiedAdmission',lambda:self.reconcile(auth))
 def test_owner_changes_during_auth_refused(self):
  self.pending()
  def auth(row):self.owner.row['operation']='f'*32;return True
  self.reject('Conflict',lambda:self.reconcile(auth))
 def test_origin_changes_during_auth_refused(self):
  self.pending()
  def auth(row):self.mutate(lambda r:r['properties']['Names']['data'].append('alias.service'));return True
  self.reject('Conflict',lambda:self.reconcile(auth))
 def test_effect_changes_during_auth_refused(self):
  self.pending()
  def auth(row):self.effects.advance(self.effects.read('test.service'),'observed-drained');return True
  self.reject('Conflict',lambda:self.reconcile(auth))
 def test_boot_change_refuses_old_job(self):
  self.pending();self.boot='22222222-2222-2222-2222-222222222222';self.reject('RecoveryRequired',self.reconcile)
 def test_source_changed_refused(self):
  self.pending();self.f.stamp=fixture.STAMP[:-1]+('b'*64,);self.reject('Conflict',self.reconcile)
 def test_arbitrary_pam_profile_in_origin_refused(self):
  self.pending();self.mutate(lambda r:r['properties']['PAMName'].update(data='login'));self.reject('UnsupportedPamExecution',self.reconcile)
 def test_origin_cannot_be_resealed_or_created_after_effect(self):
  with previous.m.retain(self.f.guard,lambda:self.boot) as origin:
   self.origins.seal(origin,self.f.rows);self.reject('RecoveryRequired',lambda:self.origins.seal(origin,self.f.rows))
  self.setUp();self.effects.begin('test.service')
  with previous.m.retain(self.f.guard,lambda:self.boot) as origin:self.reject('RecoveryRequired',lambda:self.origins.seal(origin,self.f.rows))
 def test_cannot_seal_after_main_exit(self):
  with previous.m.retain(self.f.guard,lambda:self.boot) as origin:
   self.f.backend.dead.add(100);self.reject('Conflict',lambda:self.origins.seal(origin,self.f.rows))
  self.assertEqual(self.storage.writes,0)
 def test_duplicate_fields_and_oversize_origin_refused(self):
  self.reject('InvalidOriginJournal',lambda:m.decode(b'{"schema":1,"schema":1}'));self.reject('InvalidOriginJournal',lambda:m.decode(b'x'*8193))
 def test_boolean_reference_field_cannot_equal_integer(self):
  self.pending();self.mutate(lambda r:r['reference']['execution']['fingerprints'][0][1].__setitem__(0,True));self.reject('Conflict',self.reconcile)
 def test_completed_journal_still_requires_empty_unit_and_auth(self):
  self.pending();self.reconcile();self.empty=False;self.reject('Busy',self.reconcile);self.empty=True;self.reconcile();self.assertEqual(len(self.auth_calls),2)
 def test_new_invocation_before_authorization_refused(self):
  self.pending();self.rows['InvocationID']['data']=[1]*16;self.reject('Conflict',self.reconcile);self.assertEqual(self.auth_calls,[])
 def test_cleared_invocation_allowed_only_after_empty_observation(self):
  self.pending();self.rows['InvocationID']['data']=[];self.empty=False;self.reject('Busy',self.reconcile);self.empty=True;self.assertEqual(self.reconcile()['phase'],'observed-drained')
 def test_invalid_live_invocation_cannot_be_sealed(self):
  for value in ([],[0]*16,[True]*16):
   with self.subTest(value=value):
    self.setUp();self.invocation['data']=value;self.reject('InvalidOriginJournal',self.seal);self.assertEqual(self.storage.writes,0)
 def test_invocation_changes_during_sealing_refused(self):
  reads=0
  def changing(n):
   nonlocal reads
   reads+=1;return dict(type='ay',data=list(range(16)) if reads==1 else [1]*16)
  self.origins.invocation=changing;self.reject('Conflict',self.seal);self.assertEqual(self.storage.writes,0)
if __name__=='__main__':unittest.main()
