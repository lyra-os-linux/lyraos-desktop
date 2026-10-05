import copy,importlib.util,sys,unittest
from pathlib import Path
from types import SimpleNamespace as N
from dataclasses import replace
P=Path(__file__).resolve().parents[1]/'docs/evidence';old=dict(sys.modules);loaded=[]
for name,file in [('coordinator','parental-coordinator/coordinator.py'),('catalog','parental-service-catalog/catalog.py'),('reference','parental-systemd-reference/reference.py'),('running','parental-running-reference/running.py'),('guard','parental-guarded-unit-stop/guard.py'),('pam_unit_test','parental-pam-unit-stop/pam.py')]:
 loaded.append(name);spec=importlib.util.spec_from_file_location(name,P/file);mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod)
m=sys.modules['pam_unit_test'];r=sys.modules['reference'];running=sys.modules['running']
for name in loaded:
 if name in old:sys.modules[name]=old[name]
 else:sys.modules.pop(name,None)
STAMP=(1,2,0,33261,1,50,1,1,'a'*64)
def props():
 v=dict(Id='test.service',Names=['test.service'],LoadState='loaded',FragmentPath='/units/test.service',DropInPaths=[],NeedDaemonReload=False,User='test',Group='test',PAMName=m.PROFILE,DynamicUser=False,RootDirectory='',RootImage='',SupplementaryGroups=[],Type='exec',ExecStartEx=[['/bin/sleep',['/bin/sleep','600'],[],0,0,0,0,0,0,0]],KillMode='control-group',Delegate=False)
 return {n:dict(type=s,data=v[n]) for n,s in dict(r.SPECS,KillMode='s',Delegate='b').items()}
class Backend:
 def __init__(self,ref):
  self.rows={100:running.Observation(100,10,(1002,)*4,(1003,)*4,(1003,),(0,)*3,(1,2,'a'*64),ref.configuration.argv,'0::/system.slice/test.service'),101:running.Observation(101,11,(1002,)*4,(1003,)*4,(),(0,)*3,(1,2,'a'*64),('executor',),'0::/system.slice/test.service')}
  self.dead=set();self.closed=[];self.effects=[];self.parents={101:100};self.member_ids=(100,101)
 def runtime(self,n):return {'MainPID':dict(type='u',data=0 if 100 in self.dead else 100),'ControlGroup':dict(type='s',data='/system.slice/test.service')}
 def pin(self,pid):return pid
 def close(self,pin):self.closed.append(pin)
 def pid(self,pin):return pin
 def exited(self,pin):return pin in self.dead
 def parent(self,pin):return self.parents.get(pin,1)
 def read(self,pin):return self.rows[pin]
 def execute(self,args):self.effects.append(args);self.dead.update(self.rows);return {'rc':0}
class Tests(unittest.TestCase):
 def setUp(self):
  self.rows=props();self.body=m.BODY;self.fenced=True;self.stamp=STAMP
 def capture(self):return m.capture('test.service',lambda n:copy.deepcopy(self.rows),lambda n:r.LocalIdentity(n,1002,1003),lambda n:1003,lambda p:self.stamp,lambda p:self.body)
 def reject(self,code,fn):
  with self.assertRaises(m.GateError) as e:fn()
  self.assertEqual(e.exception.code,code)
 def setup_guard(self):
  self.ref=self.capture();self.backend=Backend(self.ref.execution)
  self.guard=m.PamExecution((N(name='test.service',kind='service'),),{'test.service':self.ref},self.backend,lambda ref:ref,lambda n:self.fenced,self.backend.execute,lambda n:self.backend.member_ids)
 def test_explicit_envelope_contains_profile_and_module_fingerprints(self):self.assertEqual(type(self.capture()),m.PamReference);self.assertIn(m.PROFILE_PATH,dict(self.capture().execution.fingerprints));self.assertIn(m.SELINUX,dict(self.capture().execution.fingerprints))
 def test_selinux_module_changes_during_capture_refused(self):
  reads=0
  def fingerprint(path):
   nonlocal reads
   if path==m.SELINUX:
    reads+=1
    if reads>1:return STAMP[:-1]+('b'*64,)
   return STAMP
  self.reject('Conflict',lambda:m.capture('test.service',lambda n:copy.deepcopy(self.rows),lambda n:r.LocalIdentity(n,1002,1003),lambda n:1003,fingerprint,lambda n:self.body))
 def test_general_capture_still_refuses_pam(self):self.reject('UnsupportedUnitExecution',lambda:r.capture('test.service',lambda n:{k:v for k,v in self.rows.items() if k in r.SPECS},lambda n:r.LocalIdentity(n,1002,1003),lambda n:1003,lambda p:STAMP))
 def test_arbitrary_profile_refused(self):self.rows['PAMName']['data']='login';self.reject('UnsupportedPamExecution',self.capture)
 def test_includes_or_other_profile_body_refused(self):self.body=b'session include systemd-user\n';self.reject('UnsupportedPamProfile',self.capture)
 def test_killmode_process_refused(self):self.rows['KillMode']['data']='process';self.reject('UnsupportedPamExecution',self.capture)
 def test_delegation_refused(self):self.rows['Delegate']['data']=True;self.reject('UnsupportedPamExecution',self.capture)
 def test_delegate_integer_false_refused(self):self.rows['Delegate']['data']=0;self.reject('UnsupportedPamExecution',self.capture)
 def test_both_pins_retained_closed_and_complete_stop_verified(self):
  self.setup_guard()
  with self.guard.batch():self.guard(['systemctl','stop','test.service']);self.guard.check()
  self.assertCountEqual(self.backend.closed,[100,101])
 def test_missing_helper_refused(self):
  self.setup_guard();self.backend.member_ids=(100,)
  def batch():
   with self.guard.batch():pass
  self.reject('UnsupportedPamHelper',batch);self.assertEqual(self.backend.effects,[])
 def test_extra_member_refused(self):
  self.setup_guard();self.backend.member_ids=(100,101,102)
  def batch():
   with self.guard.batch():pass
  self.reject('UnsupportedPamHelper',batch)
 def test_helper_parent_changes_refused_before_effect(self):
  self.setup_guard()
  with self.guard.batch():self.backend.parents[101]=200;self.reject('Conflict',lambda:self.guard(['systemctl','stop','test.service']))
  self.assertEqual(self.backend.effects,[])
 def test_helper_uid_changes_refused(self):
  self.setup_guard()
  with self.guard.batch():self.backend.rows[101]=replace(self.backend.rows[101],uids=(0,)*4);self.reject('UnsupportedRuntimeCredentials',self.guard.check)
 def test_helper_exec_changes_refused(self):
  self.setup_guard()
  with self.guard.batch():self.backend.rows[101]=replace(self.backend.rows[101],executable=(1,3,'b'*64));self.reject('UnsupportedPamHelper',self.guard.check)
 def test_helper_argv_changes_refused(self):
  self.setup_guard()
  with self.guard.batch():self.backend.rows[101]=replace(self.backend.rows[101],argv=('changed',));self.reject('Conflict',self.guard.check)
 def test_auxiliary_capabilities_refused(self):
  self.setup_guard()
  with self.guard.batch():self.backend.rows[101]=replace(self.backend.rows[101],capabilities=(1,0,0));self.reject('UnsupportedRuntimeCredentials',self.guard.check)
 def test_mask_loss_refused(self):
  self.setup_guard()
  with self.guard.batch():self.fenced=False;self.reject('UnverifiedAdmission',self.guard.check)
 def test_helper_alive_after_success_not_quiescent(self):
  self.setup_guard()
  with self.guard.batch():self.guard(['systemctl','stop','test.service']);self.backend.dead.remove(101);self.reject('UnverifiedQuiescence',self.guard.check)
if __name__=='__main__':unittest.main()
