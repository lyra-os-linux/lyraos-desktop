import copy,importlib.util,sys,unittest
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'docs/evidence'
for name,file in [('coordinator','parental-coordinator/coordinator.py'),('catalog','parental-service-catalog/catalog.py'),('reference','parental-systemd-reference/reference.py'),('running','parental-running-reference/running.py'),('guarded_unit_stop_test','parental-guarded-unit-stop/guard.py'),('guarded_unit_adapter_test','parental-unit-adapter/unit-adapter.py')]:
 if name in sys.modules:continue
 spec=importlib.util.spec_from_file_location(name,P/file);mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod)
g=sys.modules['guarded_unit_stop_test'];r=sys.modules['reference'];running=sys.modules['running'];ua=sys.modules['guarded_unit_adapter_test']
class Classification:
 identity='fixture'
 @contextmanager
 def verified(self,target):yield
class Backend:
 def __init__(self,refs):
  self.rows={name:running.Observation(pid,99,(1002,)*4,(1003,)*4,(1003,),(0,)*3,(1,2,'a'*64),ref.configuration.argv,'0::/system.slice/'+name) for pid,(name,ref) in enumerate(refs.items(),100)}
  self.closed=[];self.dead=set();self.effects=[]
 def runtime(self,name):return {'MainPID':dict(type='u',data=0 if name in self.dead else self.rows[name].pid),'ControlGroup':dict(type='s',data='/system.slice/'+name)}
 def pin(self,pid):return next(name for name,row in self.rows.items() if row.pid==pid)
 def pid(self,pin):return self.rows[pin].pid
 def exited(self,pin):return pin in self.dead
 def close(self,pin):self.closed.append(pin)
 def read(self,pin):return self.rows[pin]
 def execute(self,args):
  self.effects.append(args)
  if args[2] in self.rows:self.dead.add(args[2])
  return {'rc':0}
class Tests(unittest.TestCase):
 def setUp(self):
  self.refs={name:r.Reference(r.Configuration(name,name,r.LocalIdentity('ordinaryuser',1002,1003),1003,'/bin/probe',('/bin/probe',),'/units/'+name,(),'exec'),(('/bin/probe',(1,2,0,33261,1,50,1,1,'a'*64)),)) for name in ('a.service','b.service')}
  self.backend=Backend(self.refs);self.units=(ua.Unit('a.timer','timer','a.service'),ua.Unit('a.service','service'),ua.Unit('b.service','service'))
  self.fenced=True;self.fingerprint=(1,2,0,33261,1,50,1,1,'a'*64);self.loaded=self.properties
  self.sources=g.MaskedSources(self.refs,lambda name:self.loaded(name),lambda path:self.fingerprint,lambda name:self.fenced)
  self.guard=g.GuardedExecution(self.units,self.refs,self.backend,self.sources,lambda name:self.fenced,self.backend.execute)
  self.authorization=lambda target,action,units:True
  masks=type('Masks',(),{'masked':lambda _,name:self.fenced})()
  self.adapter=ua.SystemUnits(Classification(),self.units,lambda i,u:True,masks,self.guard,lambda name:self.fenced,lambda units:len(self.backend.dead)==2,lambda *args:self.authorization(*args),settle_seconds=0)
 def properties(self,name):return {'Id':dict(type='s',data=name),'Names':dict(type='as',data=[name]),'LoadState':dict(type='s',data='masked'),'FragmentPath':dict(type='s',data='/etc/systemd/system/'+name),'NeedDaemonReload':dict(type='b',data=False)}
 def revoke(self):
  with self.guard.batch():return self.adapter.revoke('target')
 def rejects(self,code,fn):
  with self.assertRaises(g.GateError) as e:fn()
  self.assertEqual(e.exception.code,code)
 def test_original_adapter_stops_timer_before_pinned_services(self):self.assertTrue(self.revoke());self.assertEqual(self.backend.effects,[['systemctl','stop',u.name] for u in self.units]);self.assertCountEqual(self.backend.closed,self.refs)
 def test_denied_authorization_no_effect_and_all_pins_closed(self):self.authorization=lambda *args:False;self.rejects('Denied',self.revoke);self.assertEqual(self.backend.effects,[]);self.assertCountEqual(self.backend.closed,self.refs)
 def test_exec_changes_inside_authorization_refuse_before_timer_effect(self):
  def authorize(*args):self.backend.rows['b.service']=replace(self.backend.rows['b.service'],argv=('/bin/changed',));return True
  self.authorization=authorize;self.rejects('UnsupportedRuntime',self.revoke);self.assertEqual(self.backend.effects,[])
 def test_restart_inside_authorization_refuses_original_pin(self):
  def authorize(*args):self.backend.dead.add('a.service');return True
  self.authorization=authorize;self.rejects('Conflict',self.revoke);self.assertEqual(self.backend.effects,[])
 def test_source_change_inside_authorization_refused(self):
  def authorize(*args):self.fingerprint=(1,3,0,33261,1,50,1,1,'a'*64);return True
  self.authorization=authorize;self.rejects('Conflict',self.revoke);self.assertEqual(self.backend.effects,[])
 def test_mask_lost_inside_authorization_refused(self):
  def authorize(*args):self.fenced=False;return True
  self.authorization=authorize;self.rejects('UnverifiedAdmission',self.revoke);self.assertEqual(self.backend.effects,[])
 def test_second_service_changes_after_first_effect_refuses_partial_batch(self):
  original=self.guard.execute
  def execute(args):
   result=original(args)
   if args[2]=='a.service':self.backend.rows['b.service']=replace(self.backend.rows['b.service'],argv=('/bin/changed',))
   return result
  self.guard.execute=execute;self.rejects('UnsupportedRuntime',self.revoke);self.assertEqual([a[2] for a in self.backend.effects],['a.timer','a.service'])
 def test_stop_outside_batch_refused(self):self.rejects('InvalidPlan',lambda:self.guard(['systemctl','stop','a.service']));self.assertEqual(self.backend.effects,[])
 def test_unknown_stop_refused(self):self.rejects('UnsupportedProducer',lambda:self.guard(['systemctl','stop','peer.service']));self.assertEqual(self.backend.effects,[])
 def test_incomplete_service_references_refused(self):self.rejects('UnsupportedProducer',lambda:g.GuardedExecution(self.units,{'a.service':self.refs['a.service']},self.backend,self.sources,lambda _:True,self.backend.execute))
 def test_nested_batch_refused(self):
  with self.guard.batch():self.rejects('InvalidPlan',self.revoke)
 def test_stale_loaded_mask_refused(self):
  def properties(name):row=self.properties(name);row['NeedDaemonReload']['data']=True;return row
  self.loaded=properties;self.rejects('UnverifiedAdmission',self.revoke);self.assertEqual(self.backend.effects,[])
 def test_loaded_definition_is_not_accepted_as_mask(self):
  def properties(name):row=self.properties(name);row['LoadState']['data']='loaded';return row
  self.loaded=properties;self.rejects('UnverifiedAdmission',self.revoke)
 def test_mask_signature_mismatch_refused(self):
  def properties(name):row=self.properties(name);row['NeedDaemonReload']['type']='s';return row
  self.loaded=properties;self.rejects('UnverifiedUnitProperties',self.revoke)
 def test_integer_in_place_of_boolean_refused(self):
  def properties(name):row=self.properties(name);row['NeedDaemonReload']['data']=0;return row
  self.loaded=properties;self.rejects('UnverifiedUnitProperties',self.revoke)
 def test_changed_canonical_alias_refused(self):
  def properties(name):row=self.properties(name);row['Id']['data']='other.service';return row
  self.loaded=properties;self.rejects('UnverifiedAdmission',self.revoke)

 def test_mask_path_must_match_owned_system_namespace(self):
  def properties(name):row=self.properties(name);row['FragmentPath']['data']='/dev/null';return row
  self.loaded=properties;self.rejects('UnverifiedAdmission',self.revoke)
 def test_completed_unit_reactivation_refused_before_next_stop(self):
  original=self.backend.runtime
  def runtime(name):
   if name=='a.service' and name in self.backend.dead:return {'MainPID':dict(type='u',data=999),'ControlGroup':dict(type='s',data='/system.slice/'+name)}
   return original(name)
  self.backend.runtime=runtime;self.rejects('UnverifiedQuiescence',self.revoke)
  self.assertEqual([args[2] for args in self.backend.effects],['a.timer','a.service'])
