import copy,importlib.util,sys,unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace as N
P=Path(__file__).resolve().parents[1]/'docs/evidence'
for name,file in [('coordinator','parental-coordinator/coordinator.py'),('withdrawal','parental-ordinary-withdrawal/withdrawal.py'),('operation_journal','parental-operation-journal/operations.py'),('effects','parental-unit-stop-jobs/effects.py'),('stop_jobs_test','parental-unit-stop-jobs/jobs.py')]:
 if name in sys.modules:continue
 spec=importlib.util.spec_from_file_location(name,P/file);mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod)
e=sys.modules['effects'];j=sys.modules['stop_jobs_test']
BOOT='11111111-1111-1111-1111-111111111111'
def owner_row():return dict(schema=1,action='withdraw-admission',identity=dict(uid=1002,gid=1003,user='ordinaryuser',group='ordinaryuser'),operation='a'*32,proof_hash='b'*64,proof_snapshot='c'*64,inventory_revision=1,inventory_digest='d'*64,phase='retired',revision=3)
class Storage:
 def __init__(self):self.rows={};self.locked=False;self.writes=0
 @contextmanager
 def lock(self,uid,exclusive):
  self.locked=True
  try:yield 1,None
  finally:self.locked=False
 def read(self,fd,name):return self.rows.get(name)
 def atomic(self,fd,name,data):self.rows[name]=data;self.writes+=1
class Owner:
 def __init__(self):
  self.row=owner_row();self.withdrawal=Storage();self.inventory=self;self.routes=(('test.service','e'*64),)
 @contextmanager
 def locked(self,uid):yield 1
 def read_locked(self,fd,uid):return N(producers=[N(name='system-units',state='registered',routes=self.routes)])
 def _owner(self,fd,names,uid):return copy.deepcopy(self.row),'unused'
 def _inventory(self,row,fd):pass
 def _storage(self,fn):return fn()
class Backend:
 def __init__(self,effects,storage):self.effects=effects;self.storage=storage;self.ready=True;self.requests=[];self.reply={'type':'o','data':['/org/freedesktop/systemd1/job/22']};self.hook=lambda:None
 def request(self,unit):
  assert not self.storage.locked
  assert self.effects.read(unit)['phase']=='intent'
  self.requests.append(unit);self.hook();return copy.deepcopy(self.reply)
 def drained(self,unit):return self.ready
class Tests(unittest.TestCase):
 def setUp(self):
  self.owner=Owner();self.storage=Storage();self.boot=BOOT;self.fenced=True
  self.effects=e.Effects(self.owner,self.storage,N(uid=1002,operation='a'*32,proof_hash='b'*64),{'test.service':'e'*64},lambda:self.boot)
  self.backend=Backend(self.effects,self.storage);self.jobs=j.StopJobs(self.effects,self.backend,lambda:self.fenced,settle_seconds=0)
 def stop(self):return self.jobs(['systemctl','stop','test.service'])
 def rejects(self,code,fn):
  with self.assertRaises(e.GateError) as error:fn()
  self.assertEqual(error.exception.code,code)
 def uncertain(self):self.backend.reply=None;self.rejects('Busy',self.stop)
 def test_intent_durable_before_request_and_drained_after_acceptance(self):self.assertEqual(self.stop(),{'rc':0});self.assertEqual(self.effects.read('test.service')['phase'],'observed-drained');self.assertEqual(self.storage.writes,3)
 def test_missing_reply_stays_uncertain_and_second_request_refused(self):self.uncertain();self.assertEqual(self.effects.read('test.service')['phase'],'uncertain');self.rejects('RecoveryRequired',self.stop);self.assertEqual(self.backend.requests,['test.service'])
 def test_invalid_typed_reply_is_uncertain(self):self.backend.reply={'type':'s','data':['/org/freedesktop/systemd1/job/22']};self.rejects('Busy',self.stop);self.assertEqual(self.effects.read('test.service')['phase'],'uncertain')
 def test_acceptance_while_processes_alive_is_busy(self):self.backend.ready=False;self.rejects('Busy',self.stop);self.assertEqual(self.effects.read('test.service')['phase'],'accepted')
 def test_reconciliation_has_fresh_authorization_and_no_request(self):
  self.uncertain();self.assertEqual(self.jobs.reconcile('test.service',lambda row:not self.storage.locked)['phase'],'observed-drained');self.assertEqual(self.backend.requests,['test.service'])
 def test_denied_reconcile_retains_uncertain(self):self.uncertain();before=self.storage.writes;self.rejects('Denied',lambda:self.jobs.reconcile('test.service',lambda _:False));self.assertEqual(self.storage.writes,before)
 def test_alive_descendant_prevents_reconciliation(self):self.uncertain();self.backend.ready=False;self.rejects('Busy',lambda:self.jobs.reconcile('test.service',lambda _:True));self.assertEqual(self.effects.read('test.service')['phase'],'uncertain')
 def test_completed_status_still_requires_live_drained_observation(self):self.stop();self.backend.ready=False;self.rejects('Busy',lambda:self.jobs.reconcile('test.service',lambda _:True))
 def test_owner_changed_in_authorization_refused(self):
  self.uncertain()
  def authorize(row):self.owner.row['operation']='f'*32;return True
  self.rejects('Conflict',lambda:self.jobs.reconcile('test.service',authorize))
 def test_callback_cannot_mutate_verified_record(self):
  self.uncertain()
  def authorize(row):row['owner']['operation']='f'*32;return True
  self.assertEqual(self.jobs.reconcile('test.service',authorize)['owner']['operation'],'a'*32)
 def test_boot_change_does_not_reuse_old_job_identifier(self):self.uncertain();self.boot='22222222-2222-2222-2222-222222222222';self.rejects('RecoveryRequired',lambda:self.jobs.reconcile('test.service',lambda _:True))
 def test_lost_mask_before_request_has_no_intent(self):self.fenced=False;self.rejects('UnverifiedAdmission',self.stop);self.assertEqual(self.storage.writes,0);self.assertEqual(self.backend.requests,[])
 def test_lost_mask_after_request_retains_acceptance_without_completion(self):
  self.backend.hook=lambda:setattr(self,'fenced',False);self.rejects('UnverifiedAdmission',self.stop);self.assertEqual(self.effects.read('test.service')['phase'],'accepted')
 def test_changed_catalog_refuses_effect(self):self.owner.routes=(('other.service','e'*64),);self.rejects('UnverifiedProducerCatalog',self.stop);self.assertEqual(self.backend.requests,[])
 def test_unknown_unit_refused(self):self.rejects('UnsupportedProducer',lambda:self.jobs(['systemctl','stop','peer.service']));self.assertEqual(self.backend.requests,[])
 def test_transport_exception_records_uncertainty(self):
  def lost():raise ConnectionResetError()
  self.backend.hook=lost;self.rejects('Busy',self.stop);self.assertEqual(self.effects.read('test.service')['phase'],'uncertain')
 def test_intent_left_by_interruption_cannot_resubmit(self):self.effects.begin('test.service');self.rejects('RecoveryRequired',self.stop);self.assertEqual(self.backend.requests,[])
 def test_duplicate_json_fields_refused(self):self.rejects('InvalidStopJournal',lambda:e.decode(b'{"schema":1,"schema":1}'))
 def test_stale_transition_cannot_overwrite_completion(self):row=self.effects.begin('test.service');self.effects.advance(row,'observed-drained');self.rejects('Conflict',lambda:self.effects.advance(row,'uncertain'))
 def test_no_commands_or_pid_inventory_in_effect_record(self):self.stop();row=self.effects.read('test.service');self.assertEqual(set(row),e.FIELDS);self.assertFalse({'argv','pid','processes','command'} & set(row))
