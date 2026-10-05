import copy,importlib.util,sys,unittest
from pathlib import Path
from types import SimpleNamespace as N
P=Path(__file__).resolve().parents[1]/'docs/evidence'
_previous=dict(sys.modules)
_loaded=[]
for name,file in [('coordinator','parental-coordinator/coordinator.py'),('catalog','parental-service-catalog/catalog.py'),('reference','parental-systemd-reference/reference.py'),('running','parental-running-reference/running.py'),('guard','parental-guarded-unit-stop/guard.py'),('cold_unit_test','parental-cold-unit-stop/cold.py')]:
 _loaded.append(name)
 spec=importlib.util.spec_from_file_location(name,P/file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m)
m=sys.modules['cold_unit_test'];r=sys.modules['reference']
for _name in _loaded:
 if _name in _previous:sys.modules[_name]=_previous[_name]
 else:sys.modules.pop(_name,None)
BOOT='11111111-1111-1111-1111-111111111111'
class Tests(unittest.TestCase):
 def setUp(self):
  self.ref=r.Reference(r.Configuration('test.service','test.service',r.LocalIdentity('test',1002,1003),1003,'/bin/sleep',('/bin/sleep','600'),'/units/test.service',(),'exec'),())
  values=dict(MainPID=0,ControlGroup='',ActiveState='inactive',SubState='dead',Job=[0,'/'],InvocationID=[])
  self.rows={k:dict(type=s,data=values[k]) for k,s in m.SPECS.items()};self.clear=True;self.fenced=True;self.boot=BOOT;self.commands=[]
  self.backend=N(runtime=lambda n:{k:copy.deepcopy(self.rows[k]) for k in ('MainPID','ControlGroup')})
  self.revalidate=lambda ref:ref
  self.guard=m.MixedExecution((N(name='test.service',kind='service'),),{'test.service':self.ref},self.backend,lambda ref:self.revalidate(ref),lambda n:self.fenced,lambda a:self.commands.append(a),lambda n:copy.deepcopy(self.rows),lambda n:self.clear,lambda:self.boot)
 def observe(self):return m.observe(self.ref,lambda n:copy.deepcopy(self.rows),lambda n:self.clear,lambda:self.boot,self.revalidate)
 def reject(self,code,fn):
  with self.assertRaises(m.GateError) as e:fn()
  self.assertEqual(e.exception.code,code)
 def test_inactive_zero_pid_is_observation_without_pid_handle(self):self.assertEqual(self.observe().reference,self.ref)
 def test_zero_pid_active_service_refused(self):self.rows['ActiveState']['data']='active';self.reject('Busy',self.observe)
 def test_populated_cgroup_with_empty_property_refused(self):self.clear=False;self.reject('Busy',self.observe)
 def test_pending_job_refused(self):self.rows['Job']['data']=[17,'/org/freedesktop/systemd1/job/17'];self.reject('Busy',self.observe)
 def test_boolean_pid_refused(self):self.rows['MainPID']['data']=False;self.reject('Busy',self.observe)
 def test_boolean_job_id_refused(self):self.rows['Job']['data']=[False,'/'];self.reject('UnverifiedRuntime',self.observe)
 def test_wrong_signature_refused(self):self.rows['MainPID']['type']='t';self.reject('UnverifiedRuntime',self.observe)
 def test_invocation_bad_bytes_refused(self):self.rows['InvocationID']['data']=[True]*16;self.reject('UnverifiedRuntime',self.observe)
 def test_foreign_cgroup_refused(self):self.rows['ControlGroup']['data']='/system.slice/foreign.service';self.reject('UnsupportedRuntime',self.observe)
 def test_failed_drained_service_has_distinct_state(self):self.rows['ActiveState']['data']='failed';self.rows['SubState']['data']='failed';self.assertEqual(self.observe().state,'failed')
 def test_stop_of_cold_service_does_not_send_or_create_job(self):
  with self.guard.batch():self.assertEqual(self.guard(['systemctl','stop','test.service']),{'rc':0})
  self.assertEqual(self.commands,[])
 def test_completed_cold_check_is_repeated_before_each_effect(self):
  with self.guard.batch():
   self.guard(['systemctl','stop','test.service']);self.clear=False;self.reject('Busy',lambda:self.guard(['systemctl','stop','test.service']))
  self.assertEqual(self.commands,[])
 def test_invocation_changes_during_authorization_refused(self):
  with self.guard.batch():
   self.rows['InvocationID']['data']=[1]*16;self.reject('Conflict',self.guard.check)
 def test_boot_changes_refused(self):
  with self.guard.batch():self.boot='22222222-2222-2222-2222-222222222222';self.reject('Conflict',self.guard.check)
 def test_admission_mask_changes_refused(self):
  with self.guard.batch():self.fenced=False;self.reject('UnverifiedAdmission',self.guard.check)
 def test_source_change_refused(self):
  with self.guard.batch():self.revalidate=lambda _:None;self.reject('InvalidPlan',self.guard.check)
 def test_requires_batch_and_closed_unit(self):self.reject('InvalidPlan',lambda:self.guard(['systemctl','stop','test.service']));self.reject('UnsupportedProducer',lambda:self.guard(['systemctl','stop','other.service']))
 def test_exception_resets_batch(self):
  try:
   with self.guard.batch():raise RuntimeError('callback failed')
  except RuntimeError:pass
  with self.guard.batch():self.guard.check()
if __name__=='__main__':unittest.main()
