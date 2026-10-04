import copy, importlib.util, sys, unittest
from dataclasses import replace
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'docs/evidence'
for name,file in [('coordinator','parental-coordinator/coordinator.py'),('catalog','parental-service-catalog/catalog.py'),('reference','parental-systemd-reference/reference.py'),('running_reference_test','parental-running-reference/running.py')]:
 if name in sys.modules:continue
 spec=importlib.util.spec_from_file_location(name,P/file);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
m=sys.modules['running_reference_test'];r=sys.modules['reference']
class Backend:
 def __init__(self):
  self.closed=[];self.rows={'MainPID':dict(type='u',data=123),'ControlGroup':dict(type='s',data='/system.slice/test.service')};self.dead=False;self.pin_pid=123;self.hook=lambda:None
  self.row=m.Observation(123,99,(1002,)*4,(1003,)*4,(1003,),(0,)*3,(1,2,'a'*64),('/bin/probe',),'0::/system.slice/test.service')
 def runtime(self,unit):return copy.deepcopy(self.rows)
 def pin(self,pid):return 'pin'
 def pid(self,pin):return self.pin_pid
 def exited(self,pin):return self.dead
 def close(self,pin):self.closed.append(pin)
 def read(self,pin):self.hook();return self.row
class RunningTests(unittest.TestCase):
 def setUp(self):
  self.backend=Backend();self.ref=r.Reference(r.Configuration('alias.service','test.service',r.LocalIdentity('ordinaryuser',1002,1003),1003,'/bin/probe',('/bin/probe',),'/units/test.service',(),'exec'),(('/bin/probe',(1,2,0,33261,1,50,1,1,'a'*64)),));self.revalidate=lambda ref:ref
 def capture(self):return m.capture(self.ref,self.backend,self.revalidate)
 def reject(self,code):
  with self.assertRaises(m.GateError) as error:
   with self.capture():pass
  self.assertEqual(error.exception.code,code)
 def test_verified_main_process_and_closed_handle(self):
  with self.capture() as pin:self.assertEqual(pin.check(),self.backend.row)
  self.assertEqual(self.backend.closed,['pin'])
  with self.assertRaises(m.GateError):pin.check()
 def test_runtime_signature_refused(self):self.backend.rows['MainPID']['type']='s';self.reject('UnverifiedRuntime')
 def test_boolean_pid_refused(self):self.backend.rows['MainPID']['data']=True;self.reject('UnverifiedRuntime')
 def test_inactive_unit_refused(self):self.backend.rows['MainPID']['data']=0;self.reject('UnverifiedRuntime')
 def test_wrong_cgroup_refused(self):self.backend.rows['ControlGroup']['data']='/user.slice/test.service';self.reject('UnsupportedRuntime')
 def test_pidfd_wrong_process_refused_and_closed(self):self.backend.pin_pid=456;self.reject('Conflict');self.assertEqual(self.backend.closed,['pin'])
 def test_exited_pidfd_refused(self):self.backend.dead=True;self.reject('Conflict')
 def test_effective_or_saved_uid_mismatch_refused(self):self.backend.row=replace(self.backend.row,uids=(1002,0,1002,1002));self.reject('UnsupportedRuntimeCredentials')
 def test_effective_gid_mismatch_refused(self):self.backend.row=replace(self.backend.row,gids=(1003,0,1003,1003));self.reject('UnsupportedRuntimeCredentials')
 def test_supplementary_group_refused(self):self.backend.row=replace(self.backend.row,groups=(1003,10));self.reject('UnsupportedRuntimeCredentials')
 def test_capabilities_refused(self):self.backend.row=replace(self.backend.row,capabilities=(1,0,0));self.reject('UnsupportedRuntimeCredentials')
 def test_wrong_executable_inode_refused(self):self.backend.row=replace(self.backend.row,executable=(1,3,'a'*64));self.reject('UnsupportedRuntime')
 def test_wrong_argv_refused(self):self.backend.row=replace(self.backend.row,argv=('/bin/probe','other'));self.reject('UnsupportedRuntime')
 def test_exec_with_same_pid_and_start_invalidates_handle(self):
  with self.capture() as pin:
   self.backend.row=replace(self.backend.row,executable=(1,4,'b'*64),argv=('/bin/other',))
   with self.assertRaises(m.GateError):pin.check()
 def test_replaced_main_pid_invalidates_handle(self):
  with self.capture() as pin:
   self.backend.rows['MainPID']['data']=456
   with self.assertRaises(m.GateError):pin.check()
 def test_changed_start_ticks_invalidates_handle(self):
  with self.capture() as pin:
   self.backend.row=replace(self.backend.row,start_ticks=100)
   with self.assertRaises(m.GateError):pin.check()
 def test_configuration_changed_during_process_capture_refused(self):
  self.backend.hook=lambda:setattr(self,'revalidate',lambda ref:None)
  # Callback closes over current state, so the second check sees the change.
  with self.assertRaises(m.GateError):
   with m.capture(self.ref,self.backend,lambda ref:self.revalidate(ref)):pass
  self.assertEqual(self.backend.closed,['pin'])
 def test_proc_disappears_busy_and_pin_closed(self):
  def fail():raise FileNotFoundError()
  self.backend.hook=fail;self.reject('Busy');self.assertEqual(self.backend.closed,['pin'])
