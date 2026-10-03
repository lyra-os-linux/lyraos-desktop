import importlib.util,sys,unittest
from pathlib import Path
from dataclasses import replace
P=Path(__file__).resolve().parents[1]/'docs/evidence'
if 'coordinator' not in sys.modules:
    spec=importlib.util.spec_from_file_location('coordinator',P/'parental-coordinator/coordinator.py');c=importlib.util.module_from_spec(spec);sys.modules[spec.name]=c;spec.loader.exec_module(c)
spec=importlib.util.spec_from_file_location('discovery_test',P/'parental-pending-discovery/discovery.py');m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def row(pid=1,route='org.lyra.A'):return m.Observation(pid,1002,(1002,)*4,route,'known.service','0::/system.slice/known.service',(1,2,'h'),('binary',route),1)
class Backend:
    def __init__(self):self.rows={1:row()};self.stops=[];self.closed=[];self.epoch=1;self.after=lambda:None;self.failure=False;self.change=False
    def pids(self,uid):return tuple(self.rows)
    def pin(self,pid):return pid
    def close(self,pin):self.closed.append(pin)
    def exited(self,pin):return pin not in self.rows
    def version(self):return self.epoch
    def read(self,pid):return self.rows[pid]
    def stop(self,r):self.stops.append(r.pid);self.rows.pop(r.pid);return not self.failure
    def after_batch(self):self.after()
class DiscoveryTests(unittest.TestCase):
    def setUp(self):self.b=Backend();self.d=m.Discovery(1002,['org.lyra.A'],self.b)
    def expect(self,code,fn):
        with self.assertRaises(m.GateError) as e:fn()
        self.assertEqual(e.exception.code,code)
    def test_unknown_population_refuses_before_effect(self):self.b.rows[2]=row(2,'unknown');self.expect('UnsupportedProducer',self.d.drain);self.assertEqual(self.b.stops,[]);self.assertEqual(self.b.closed,[1,2])
    def test_wrong_identity_refuses_before_effect(self):self.b.rows[1]=replace(row(),uids=(1000,)*4);self.expect('UnsupportedProducer',self.d.drain);self.assertEqual(self.b.stops,[])
    def test_failed_response_does_not_claim_success(self):self.b.failure=True;self.expect('Busy',self.d.drain);self.assertFalse(self.b.rows);self.assertEqual(self.b.closed,[1])
    def test_late_known_producer_is_recaptured(self):
        calls=[]
        def inject():
            if not calls:self.b.rows[2]=row(2)
            calls.append(1)
        self.b.after=inject;self.assertTrue(self.d.drain());self.assertEqual(self.b.stops,[1,2]);self.assertFalse(self.b.rows)
    def test_continuous_producer_exhausts_bound(self):self.b.after=lambda:self.b.rows.update({1:row()});self.expect('Busy',self.d.drain);self.assertEqual(self.b.stops,[1,1]);self.assertTrue(self.b.rows)
    def test_changed_observation_cannot_stop_replacement(self):
        first=self.b.read;calls=[]
        def read(pid):calls.append(pid);return first(pid) if len(calls)==1 else replace(first(pid),start_ticks=2)
        self.b.read=read;self.expect('Conflict',self.d.drain);self.assertEqual(self.b.stops,[])
    def test_bad_limits_refused(self):
        for count in (0,5,True):self.expect('InvalidInventory',lambda:m.Discovery(1002,['org.lyra.A'],self.b,rounds=count))
    def test_population_over_limit_refused(self):self.b.rows[2]=row(2);self.d.limit=1;self.expect('UnverifiedQuiescence',self.d.drain);self.assertEqual(self.b.stops,[])
