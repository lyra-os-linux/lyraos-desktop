import importlib.util,os,sys,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];E=P/'docs/evidence'
for name,file in [('coordinator','parental-coordinator/coordinator.py'),('namespace','parental-namespace-guard/namespace.py'),('source_set_test','parental-source-set/sources.py')]:
 if name in sys.modules:continue
 s=importlib.util.spec_from_file_location(name,E/file);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m)
m=sys.modules['source_set_test']
class SourceSetTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='.sources-test-',dir=P);self.base=Path(self.tmp.name)
  self.tree=self.base/'present';self.tree.mkdir(mode=0o700)
  self.optional_dir=self.base/'future'/'services';self.config=self.base/'config';self.config.write_bytes(b'config')
  self.override=self.base/'override.conf';self.lock=self.base/'lock';self.lock.write_bytes(b'');self.lock.chmod(0o600)
  self.alias=self.base/'lib';self.alias.symlink_to('present',target_is_directory=True)
  self.args=dict(owner=os.getuid(),ancestor_owners=(0,Path('/').stat().st_uid,Path('/home').stat().st_uid))
  self.ns=m.SourceSet([str(self.tree),str(self.optional_dir)],[str(self.config),str(self.override)],[str(self.override)],str(self.lock),aliases=((str(self.alias),'present'),),**self.args)
  self.effects=[]
 def tearDown(self):self.tmp.cleanup()
 def expect(self,code,fn):
  with self.assertRaises(m.GateError) as e:fn()
  self.assertEqual(e.exception.code,code)
 def effect(self):self.effects.append(1);return True
 def changed(self,change):
  plan=self.ns.plan()
  def auth(_):change();return True
  self.expect('Conflict',lambda:self.ns.execute(plan,auth,[self.effect]));self.assertFalse(self.effects)
 def test_optional_absences_are_retained(self):
  s=self.ns.plan();self.assertEqual({row[0] for row in s.missing},{str(self.override),str(self.optional_dir)});self.assertEqual(s.missing[0][2],('future','services'))
 def test_override_creation_after_authorization_refuses(self):self.changed(lambda:self.override.write_bytes(b'new'))
 def test_first_missing_ancestor_creation_refuses(self):self.changed(lambda:(self.base/'future').mkdir(mode=0o700))
 def test_complete_optional_tree_creation_refuses(self):self.changed(lambda:self.optional_dir.mkdir(parents=True,mode=0o700))
 def test_alias_replaced_with_same_target_refuses(self):
  def change():self.alias.unlink();self.alias.symlink_to('present',target_is_directory=True)
  self.changed(change)
 def test_unknown_alias_target_refuses(self):
  self.alias.unlink();self.alias.symlink_to('other',target_is_directory=True);self.expect('UnsupportedProducerAlias',self.ns.plan)
 def test_symlink_at_missing_component_is_not_absence(self):
  (self.base/'future').symlink_to(self.tree,target_is_directory=True);self.expect('UnverifiedProducerNamespace',self.ns.plan)
 def test_required_config_missing_refuses(self):self.config.unlink();self.expect('UnverifiedProducerNamespace',self.ns.plan)
 def test_regular_config_change_refuses(self):self.changed(lambda:self.config.write_bytes(b'edited'))
 def test_source_addition_in_alternate_directory_refuses(self):
  self.optional_dir.mkdir(parents=True,mode=0o700);self.changed(lambda:(self.optional_dir/'new.service').write_bytes(b'new'))
 def test_change_after_first_effect_stops_remaining(self):
  def first():self.effects.append(1);self.override.write_bytes(b'new')
  self.expect('Conflict',lambda:self.ns.execute(self.ns.plan(),lambda _:True,[first,self.effect]));self.assertEqual(self.effects,[1])
 def test_missing_parent_permissions_refused(self):
  (self.base/'future').mkdir(mode=0o777);(self.base/'future').chmod(0o777);self.expect('UnsafeProducerNamespace',self.ns.plan)
 def test_fresh_snapshot_records_new_optional_source_but_not_coverage(self):
  self.override.write_bytes(b'new');s=self.ns.plan();self.assertIn(str(self.override),{x.path for x in s.entries});self.assertFalse(hasattr(s,'complete'))
 def test_unchanged_plan_allows_internal_callback(self):self.assertEqual(self.ns.execute(self.ns.plan(),lambda _:True,[self.effect]),(True,))
 def test_combined_file_and_directory_budget_refused(self):
  (self.tree/'large').write_bytes(b'12345');self.ns.bytes_limit=8;self.expect('ProducerNamespaceLimit',self.ns.plan)
 def test_different_specification_rejects_plan(self):
  other=m.SourceSet([str(self.tree)],[str(self.config)],[],str(self.lock),**self.args)
  self.expect('InvalidPlan',lambda:other.check(self.ns.plan()))
