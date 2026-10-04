import importlib.util,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'docs/evidence'
if 'coordinator' not in sys.modules:
 s=importlib.util.spec_from_file_location('coordinator',P/'parental-coordinator/coordinator.py');c=importlib.util.module_from_spec(s);sys.modules[s.name]=c;s.loader.exec_module(c)
s=importlib.util.spec_from_file_location('service_catalog_test',P/'parental-service-catalog/catalog.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
PATH='/one/org.lyra.Test.service'
DATA=b'[D-BUS Service]\nName=org.lyra.Test\nUser=root\nExec=/usr/bin/false\n'
def resolve(user):return m.LocalIdentity(user,0,0)
class CatalogTests(unittest.TestCase):
 def expect(self,code,fn):
  with self.assertRaises(m.GateError) as e:fn()
  self.assertEqual(e.exception.code,code)
 def decode(self,data=DATA,path=PATH,lookup=resolve):return m.decode(path,data,lookup)
 def test_typed_exec_declaration(self):r=self.decode();self.assertEqual(r.argv,('/usr/bin/false',));self.assertEqual(r.declared_identity.uid,0);self.assertFalse(r.systemd_unit)
 def test_typed_systemd_reference_retains_declared_identity(self):r=self.decode(DATA+b'SystemdService=dbus-test.service\n');self.assertEqual(r.systemd_unit,'dbus-test.service');self.assertEqual(r.declared_identity.user,'root')
 def test_duplicate_across_roots_refused_even_identical(self):self.expect('AmbiguousProducerCatalog',lambda:m.catalog([(PATH,DATA),('/two/org.lyra.Test.service',DATA)],resolve))
 def test_duplicate_field_refused(self):self.expect('UnsupportedServiceDefinition',lambda:self.decode(DATA+b'User=root\n'))
 def test_unknown_field_refused(self):self.expect('UnsupportedServiceDefinition',lambda:self.decode(DATA+b'FutureActivation=yes\n'))
 def test_additional_section_refused(self):self.expect('UnsupportedServiceDefinition',lambda:self.decode(DATA+b'[Other]\n'))
 def test_missing_user_refused(self):self.expect('UnsupportedServiceDefinition',lambda:self.decode(DATA.replace(b'User=root\n',b'')))
 def test_file_name_mismatch_refused(self):self.expect('UnsupportedServiceDefinition',lambda:self.decode(path='/one/wrong.service'))
 def test_quoted_shell_and_relative_exec_refused(self):
  for command in (b'false',b'/bin/sh -c "anything"',b'/usr/bin/false;id',b'/usr/bin/../bin/false'):
   self.expect('UnsupportedServiceDefinition',lambda:self.decode(DATA.replace(b'/usr/bin/false',command)))
 def test_simple_arguments_preserved_without_execution(self):r=self.decode(DATA.replace(b'/usr/bin/false',b'/usr/bin/program --no-debug'));self.assertEqual(r.argv,('/usr/bin/program','--no-debug'))
 def test_nonlocal_or_ambiguous_identity_refused(self):self.expect('InvalidIdentity',lambda:self.decode(lookup=lambda _:None))
 def test_numeric_or_wrong_identity_refused(self):self.expect('UnsupportedServiceDefinition',lambda:self.decode(DATA.replace(b'User=root',b'User=1002')));self.expect('InvalidIdentity',lambda:self.decode(lookup=lambda _:m.LocalIdentity('other',0,0)))
 def test_controls_and_oversize_refused(self):
  for data in (DATA+b'\0',b'x'*8193):self.expect('InvalidServiceDefinition',lambda:self.decode(data))
 def test_root_declaration_still_requires_adapter(self):self.expect('UnsupportedProducer',lambda:m.require_adapters([self.decode()],{}))
 def test_unqualified_binding_refused(self):self.expect('UnverifiedAdapterBinding',lambda:m.require_adapters([self.decode()],{'org.lyra.Test':lambda _:False}))
 def test_population_limit_refused(self):self.expect('ProducerNamespaceLimit',lambda:m.catalog([(PATH,DATA),('/two/org.lyra.Next.service',DATA.replace(b'org.lyra.Test',b'org.lyra.Next'))],resolve,limit=1))
