"""Filesystem integration tests; explicit current-user fixture owner, no VM claims."""
import fcntl, importlib.util, os, sys, tempfile, unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]
if 'coordinator' not in sys.modules:
    spec=importlib.util.spec_from_file_location('coordinator',P/'docs/evidence/parental-coordinator/coordinator.py')
    c=importlib.util.module_from_spec(spec);sys.modules[spec.name]=c;spec.loader.exec_module(c)
spec=importlib.util.spec_from_file_location('namespace_guard_test',P/'docs/evidence/parental-namespace-guard/namespace.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

class NamespaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='.namespace-test-',dir=P)
        self.base=Path(self.temp.name);self.root=self.base/'sources';self.root.mkdir(mode=0o700)
        self.lock=self.base/'authority.lock';self.lock.write_bytes(b'');self.lock.chmod(0o600)
        self.source=self.root/'known.service';self.source.write_bytes(b'User=ordinaryuser\n');self.source.chmod(0o600)
        self.ns=m.Namespace([str(self.root)],str(self.lock),owner=os.getuid(),ancestor_owners=(0,Path('/').stat().st_uid,Path('/home').stat().st_uid))
        self.effects=[]
    def tearDown(self):self.temp.cleanup()
    def effect(self):self.effects.append('effect');return 'scoped'
    def expect(self,code,fn):
        with self.assertRaises(m.GateError) as e:fn()
        self.assertEqual(e.exception.code,code)
    def run_changed(self,change):
        plan=self.ns.plan()
        def auth(_):change();return True
        self.expect('Conflict',lambda:self.ns.execute(plan,auth,[self.effect]))
        self.assertEqual(self.effects,[])
    def test_unchanged_sources_allow_scoped_callbacks(self):
        result=self.ns.execute(self.ns.plan(),lambda _:True,[self.effect])
        self.assertEqual(result,('scoped',));self.assertEqual(self.effects,['effect'])
    def test_new_unknown_extension_after_authorization_invalidates(self):
        self.run_changed(lambda:(self.root/'new.unknown').write_bytes(b'new'))
    def test_removed_route_after_authorization_invalidates(self):self.run_changed(self.source.unlink)
    def test_same_size_content_edit_invalidates(self):
        self.run_changed(lambda:self.source.write_bytes(b'User=another_user\n'))
    def test_identical_content_atomic_replacement_invalidates(self):
        def replace():
            new=self.root/'staged';new.write_bytes(self.source.read_bytes());new.chmod(0o600);new.replace(self.source)
        self.run_changed(replace)
    def test_nested_new_source_invalidates(self):
        child=self.root/'nested';child.mkdir(mode=0o700)
        self.run_changed(lambda:(child/'new.timer').write_bytes(b'new'))
    def test_empty_source_tree_addition_invalidates(self):
        self.source.unlink();self.run_changed(lambda:(self.root/'first').write_bytes(b'first'))
    def test_change_after_first_effect_stops_remaining_effects(self):
        plan=self.ns.plan()
        def changed():self.effects.append('first');(self.root/'late').write_bytes(b'new')
        self.expect('Conflict',lambda:self.ns.execute(plan,lambda _:True,[changed,self.effect]))
        self.assertEqual(self.effects,['first'])
    def test_denied_authorization_no_effect(self):
        self.expect('Denied',lambda:self.ns.execute(self.ns.plan(),lambda _:False,[self.effect]))
        self.assertFalse(self.effects)
    def test_writer_lock_is_available_during_authorization(self):
        def auth(_):
            with self.lock.open('rb') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return True
        self.ns.execute(self.ns.plan(),auth,[self.effect]);self.assertEqual(self.effects,['effect'])
    def test_cooperating_writer_excluded_during_effect(self):
        def effect():
            with self.lock.open('rb') as f:
                with self.assertRaises(BlockingIOError):fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.ns.execute(self.ns.plan(),lambda _:True,[effect])
    def test_exclusive_writer_causes_busy(self):
        with self.lock.open('rb') as f:
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.expect('Busy',self.ns.plan)
    def test_lock_replacement_during_effect_detected(self):
        plan=self.ns.plan()
        def effect():
            new=self.base/'newlock';new.write_bytes(b'');new.chmod(0o600);new.replace(self.lock)
        self.expect('Conflict',lambda:self.ns.execute(plan,lambda _:True,[effect,self.effect]))
        self.assertFalse(self.effects)
    def test_symlink_hardlink_fifo_refused(self):
        extra=self.root/'extra'
        for make in (lambda:extra.symlink_to(self.source),lambda:os.link(self.source,extra),lambda:os.mkfifo(extra,0o600)):
            make();self.expect('UnsafeProducerNamespace',self.ns.plan);extra.unlink()
    def test_missing_or_writable_source_tree_refused(self):
        self.root.chmod(0o777);self.expect('UnsafeProducerNamespace',self.ns.plan)
        self.root.chmod(0o700);self.source.unlink();self.root.rmdir();self.expect('UnverifiedProducerNamespace',self.ns.plan)
    def test_symlink_ancestor_refused(self):
        alias=self.base/'alias';alias.symlink_to(self.root,target_is_directory=True)
        ns=m.Namespace([str(alias)],str(self.lock),owner=os.getuid(),ancestor_owners=(0,Path('/').stat().st_uid,Path('/home').stat().st_uid))
        self.expect('UnverifiedProducerNamespace',ns.plan)
    def test_file_byte_entry_depth_limits_refused(self):
        for options in ({'bytes_limit':1},{'entries':1}):
            ns=m.Namespace([str(self.root)],str(self.lock),owner=os.getuid(),ancestor_owners=(0,Path('/').stat().st_uid,Path('/home').stat().st_uid),**options)
            self.expect('ProducerNamespaceLimit',ns.plan)
        nested=self.root/'one';nested.mkdir(mode=0o700);(nested/'two').mkdir(mode=0o700)
        ns=m.Namespace([str(self.root)],str(self.lock),owner=os.getuid(),ancestor_owners=(0,Path('/').stat().st_uid,Path('/home').stat().st_uid),depth=1)
        self.expect('ProducerNamespaceLimit',ns.plan)
    def test_root_set_mismatch_cannot_reuse_plan(self):
        peer=self.base/'peer';peer.mkdir(mode=0o700)
        ns=m.Namespace([str(peer)],str(self.lock),owner=os.getuid(),ancestor_owners=(0,Path('/').stat().st_uid,Path('/home').stat().st_uid))
        self.expect('InvalidPlan',lambda:ns.check(self.ns.plan()))
    def test_no_reader_creates_missing_lock(self):
        self.lock.unlink();self.expect('UnverifiedProducerNamespace',self.ns.plan);self.assertFalse(self.lock.exists())
    def test_writable_regular_source_refused(self):
        self.source.chmod(0o666);self.expect('UnsafeProducerNamespace',self.ns.plan)

    def test_lock_replacement_during_authorization_invalidates(self):
        def replace():
            new=self.base/'newlock';new.write_bytes(b'');new.chmod(0o600);new.replace(self.lock)
        self.run_changed(replace)
    def test_root_directory_replacement_invalidates(self):
        def replace():
            self.root.rename(self.base/'oldtree');self.root.mkdir(mode=0o700)
            self.source.write_bytes(b'User=ordinaryuser\n');self.source.chmod(0o600)
        self.run_changed(replace)
    def test_exception_during_authorization_has_no_effect(self):
        def auth(_):raise RuntimeError('lost caller')
        self.expect('AuthorizationFailure',lambda:self.ns.execute(self.ns.plan(),auth,[self.effect]))
        self.assertFalse(self.effects)
    def test_second_pass_detects_interleaved_source_creation(self):
        original=self.ns.collect;calls=[]
        def collect():
            result=original();calls.append(1)
            if len(calls)==1:(self.root/'late').write_bytes(b'new')
            return result
        self.ns.collect=collect;self.expect('Conflict',self.ns.plan)
    def discovery(self,plan,after_stop):
        spec=importlib.util.spec_from_file_location('namespace_discovery_test',P/'docs/evidence/parental-pending-discovery/discovery.py')
        d=importlib.util.module_from_spec(spec);sys.modules[spec.name]=d;spec.loader.exec_module(d)
        ns=self.ns
        class Backend:
            def __init__(self):
                self.rows={pid:d.Observation(pid,1002,(1002,)*4,'org.lyra.Known','known.service','0::/system.slice/known.service',(1,2,'fixture'),('fixture','org.lyra.Known'),pid) for pid in (1,2)}
                self.stops=[];self.closed=[]
            def version(self):return ns.check(plan)
            def pids(self,uid):return tuple(self.rows)
            def pin(self,pid):return pid
            def exited(self,pin):return pin not in self.rows
            def close(self,pin):self.closed.append(pin)
            def read(self,pid):return self.rows[pid]
            def stop(self,row):self.stops.append(row.pid);self.rows.pop(row.pid);after_stop();return True
            def after_batch(self):pass
        backend=Backend()
        return d.Discovery(1002,['org.lyra.Known'],backend),backend
    def test_discovery_source_change_before_drain_prevents_all_stops(self):
        plan=self.ns.plan();discovery,backend=self.discovery(plan,lambda:None)
        (self.root/'newroute').write_bytes(b'new')
        self.expect('Conflict',discovery.drain);self.assertFalse(backend.stops)
    def test_discovery_source_change_between_stops_preserves_remaining(self):
        plan=self.ns.plan()
        discovery,backend=self.discovery(plan,lambda:(self.root/'newroute').write_bytes(b'new'))
        self.expect('Conflict',lambda:self.ns.execute(plan,lambda _:True,[discovery.drain]))
        self.assertEqual(backend.stops,[1]);self.assertEqual(tuple(backend.rows),(2,));self.assertEqual(backend.closed,[1,2])
