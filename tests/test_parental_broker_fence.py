"""Decision tests; actual broker integration is in the separate native matrix."""
import importlib.util,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'docs/evidence'
if 'coordinator' not in sys.modules:
    s=importlib.util.spec_from_file_location('coordinator',P/'parental-coordinator/coordinator.py');c=importlib.util.module_from_spec(s);sys.modules[s.name]=c;s.loader.exec_module(c)
s=importlib.util.spec_from_file_location('broker_fence_test',P/'parental-namespace-dbus/binding.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
from contextlib import contextmanager
class Sources:
    def __init__(self):self.epoch=1
    @contextmanager
    def locked(self):yield
    def snapshot(self):return self.epoch
    def check(self,expected):
        if self.epoch!=expected:raise m.GateError('Conflict')
    def execute(self,expected,authorize,effects):
        self.check(expected)
        if authorize(expected) is not True:raise m.GateError('Denied')
        self.check(expected);return tuple(f() for f in effects)
class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.sources=Sources();self.names={'peer'};self.known=True;self.calls=[]
        self.f=m.BrokerFence(self.sources,lambda:self.known,lambda:self.names,{'target'})
    def expect(self,code,fn):
        with self.assertRaises(m.GateError) as e:fn()
        self.assertEqual(e.exception.code,code)
    def effect(self):self.calls.append(1);return True
    def test_closed_unchanged_plan_checks_callbacks(self):
        self.assertEqual(self.f.execute(self.f.plan(),lambda _:True,[self.effect]),(True,));self.assertEqual(self.calls,[1])
    def test_loaded_target_refuses_plan(self):self.names.add('target');self.expect('UnverifiedAdmission',self.f.plan)
    def test_unclassified_source_refuses_plan(self):self.known=False;self.expect('UnsupportedProducer',self.f.plan)
    def test_loaded_view_change_after_authorization_stops_effect(self):
        p=self.f.plan()
        def auth(_):self.names.add('new');return True
        self.expect('Conflict',lambda:self.f.execute(p,auth,[self.effect]));self.assertFalse(self.calls)
    def test_changed_loaded_view_after_effect_stops_next(self):
        p=self.f.plan()
        def effect():self.calls.append(1);self.names.add('new')
        self.expect('Conflict',lambda:self.f.execute(p,lambda _:True,[effect,self.effect]));self.assertEqual(self.calls,[1])
    def test_source_change_after_authorization_stops_effect(self):
        p=self.f.plan()
        def auth(_):self.sources.epoch+=1;return True
        self.expect('Conflict',lambda:self.f.execute(p,auth,[self.effect]));self.assertFalse(self.calls)
    def test_denied_no_effect(self):self.expect('Denied',lambda:self.f.execute(self.f.plan(),lambda _:False,[self.effect]));self.assertFalse(self.calls)
    def test_malformed_loaded_response_refused(self):self.names=['peer'];self.expect('UnverifiedAdmission',self.f.plan)
