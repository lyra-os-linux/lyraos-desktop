import copy,importlib.util,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'docs/evidence'
for name,file in [('coordinator','parental-coordinator/coordinator.py'),('catalog','parental-service-catalog/catalog.py'),('systemd_reference_test','parental-systemd-reference/reference.py')]:
 if name in sys.modules:continue
 s=importlib.util.spec_from_file_location(name,P/file);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m)
m=sys.modules['systemd_reference_test']
def props():
 values={'Id':'real.service','Names':['real.service','alias.service'],'LoadState':'loaded','FragmentPath':'/units/real.service','DropInPaths':['/units/real.service.d/extra.conf'],'NeedDaemonReload':False,'User':'serviceuser','Group':'','PAMName':'','DynamicUser':False,'RootDirectory':'','RootImage':'','SupplementaryGroups':[],'Type':'dbus','ExecStartEx':[['/bin/program',['/bin/program','--flag'],[],0,0,0,0,0,0,0]]}
 return {n:dict(type=s,data=values[n]) for n,s in m.SPECS.items()}
class ReferenceTests(unittest.TestCase):
 def setUp(self):self.rows=props();self.stamps={};self.calls=0
 def user(self,name):return m.LocalIdentity(name,456,457)
 def group(self,name):return 458
 def fingerprint(self,path):return self.stamps.get(path,('inode','hash'))
 def read(self,name):return copy.deepcopy(self.rows)
 def capture(self):return m.capture('alias.service',self.read,self.user,self.group,self.fingerprint)
 def expect(self,code,fn):
  with self.assertRaises(m.GateError) as e:fn()
  self.assertEqual(e.exception.code,code)
 def test_canonical_alias_and_configured_identity(self):r=self.capture();self.assertEqual(r.configuration.canonical,'real.service');self.assertEqual(r.configuration.identity.uid,456);self.assertEqual(r.configuration.configured_gid,457)
 def test_explicit_group_resolved(self):self.rows['Group']['data']='othergroup';self.assertEqual(self.capture().configuration.configured_gid,458)
 def test_signature_mismatch_refused(self):self.rows['DynamicUser']['type']='s';self.expect('UnverifiedUnitProperties',self.capture)
 def test_boolean_as_integer_refused(self):self.rows['DynamicUser']['data']=0;self.expect('UnverifiedUnitProperties',self.capture)
 def test_unloaded_or_reload_needed_refused(self):
  self.rows['LoadState']['data']='not-found';self.expect('UnverifiedLoadedUnit',self.capture);self.rows=props();self.rows['NeedDaemonReload']['data']=True;self.expect('UnverifiedLoadedUnit',self.capture)
 def test_missing_requested_alias_refused(self):self.rows['Names']['data']=['real.service'];self.expect('UnverifiedUnitAlias',self.capture)
 def test_dynamic_pam_chroot_and_supplementary_groups_refused(self):
  for field,value in [('DynamicUser',True),('PAMName','login'),('RootDirectory','/other'),('RootImage','/image'),('SupplementaryGroups',['wheel'])]:
   self.rows=props();self.rows[field]['data']=value;self.expect('UnsupportedUnitExecution',self.capture)
 def test_privileged_command_flags_refused(self):self.rows['ExecStartEx']['data'][0][2]=['privileged'];self.expect('UnsupportedUnitExecution',self.capture)
 def test_multiple_commands_refused(self):self.rows['ExecStartEx']['data']*=2;self.expect('UnsupportedUnitExecution',self.capture)
 def test_specifiers_and_environment_deferred_refused(self):self.rows['ExecStartEx']['data'][0][1].append('$VARIABLE');self.expect('UnsupportedUnitExecution',self.capture)
 def test_unknown_local_identity_refused(self):self.user=lambda _:None;self.expect('InvalidIdentity',self.capture)
 def test_changed_fragment_or_executable_invalidates(self):
  for path in ('/units/real.service','/bin/program','/etc/passwd'):
   self.stamps={};r=self.capture();self.stamps[path]=('replacement','hash');self.expect('Conflict',lambda:m.check(r,self.read,self.user,self.group,self.fingerprint))
 def test_changed_dropin_list_invalidates(self):r=self.capture();self.rows['DropInPaths']['data'].append('/units/new.conf');self.expect('Conflict',lambda:m.check(r,self.read,self.user,self.group,self.fingerprint))
 def test_property_change_during_capture_refused(self):
  def read(name):
   self.calls+=1;row=self.read(name)
   if self.calls==2:row['User']['data']='otheruser'
   return row
  self.expect('Conflict',lambda:m.capture('alias.service',read,self.user,self.group,self.fingerprint))
 def test_runtime_pid_and_timestamps_are_not_configuration(self):
  r=self.capture();self.rows['ExecStartEx']['data'][0][3:]=[10,20,30,40,999,0,0];self.assertEqual(m.check(r,self.read,self.user,self.group,self.fingerprint),r)
 def test_same_properties_do_not_hide_source_change(self):
  def fingerprint(path):
   self.calls+=1;return ('old','hash') if self.calls<=5 else ('new','hash')
  self.expect('Conflict',lambda:m.capture('alias.service',self.read,self.user,self.group,fingerprint))
