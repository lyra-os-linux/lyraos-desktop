import importlib.util,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'docs/evidence'
if 'coordinator' not in sys.modules:
    s=importlib.util.spec_from_file_location('coordinator',P/'parental-coordinator/coordinator.py');c=importlib.util.module_from_spec(s);sys.modules[s.name]=c;s.loader.exec_module(c)
s=importlib.util.spec_from_file_location('dbus_dependencies_test',P/'parental-dbus-config/dependencies.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
class DependencyTests(unittest.TestCase):
    def parse(self,body):return m.dependencies(('<busconfig>'+body+'</busconfig>').encode(),'/usr/share/dbus-1/system.conf')
    def refused(self,body,code='UnsupportedBusConfiguration'):
        with self.assertRaises(m.GateError) as e:self.parse(body)
        self.assertEqual(e.exception.code,code)
    def test_relative_include_and_directory(self):
        self.assertEqual([d.path for d in self.parse('<include>local.conf</include><includedir>system.d</includedir>')],['/usr/share/dbus-1/local.conf','/usr/share/dbus-1/system.d'])
    def test_local_optional_include_is_recorded_not_discarded(self):
        d=self.parse('<include ignore_missing="yes">/etc/dbus-1/system-local.conf</include>')[0]
        self.assertTrue(d.optional);self.assertEqual(d.path,'/etc/dbus-1/system-local.conf')
    def test_directive_order_and_duplicate_sources_preserved(self):
        rows=self.parse('<servicedir>/one</servicedir><servicedir>/two</servicedir><servicedir>/one</servicedir>');self.assertEqual([x.path for x in rows],['/one','/two','/one'])
    def test_standard_system_not_guessed_from_latest_upstream(self):self.assertEqual(self.parse('<standard_system_servicedirs/>')[0].path,'')
    def test_selinux_dependency_keeps_separate_root_and_condition(self):
        d=self.parse('<include if_selinux_enabled="yes" selinux_root_relative="yes">contexts/dbus_contexts</include>')[0];self.assertEqual((d.kind,d.path,d.condition),('selinux-include','contexts/dbus_contexts','selinux-enabled'))
    def test_session_environment_not_silently_supported(self):self.refused('<standard_session_servicedirs/>')
    def test_unknown_directive_refused(self):self.refused('<future_producer/>')
    def test_nested_dependency_refused(self):self.refused('<policy user="root"><include>/new</include></policy>')
    def test_unknown_include_attribute_refused(self):self.refused('<include future="yes">/new</include>')
    def test_invalid_boolean_refused(self):self.refused('<include ignore_missing="maybe">/new</include>')
    def test_relative_servicedir_refused(self):self.refused('<servicedir>relative</servicedir>')
    def test_entity_expansion_refused(self):
        with self.assertRaises(m.GateError):m.dependencies(b'<!DOCTYPE busconfig [<!ENTITY a "xxx">]><busconfig><include>&a;</include></busconfig>','/config')
    def test_standard_external_doctype_never_fetched(self):
        self.assertEqual(m.dependencies(b'<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN" "http://invalid.test/no-network"><busconfig/>','/config'),())
    def test_oversize_refused(self):
        with self.assertRaises(m.GateError):m.dependencies(b'x'*65537,'/config')
    def test_malformed_xml_refused(self):self.refused('<include>','InvalidBusConfiguration')
    def test_empty_dependency_refused(self):self.refused('<include/>')
