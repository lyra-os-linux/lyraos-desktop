"""Bounded closed-catalog process discovery, trusted backend, no coverage issuer."""
from dataclasses import dataclass
from contextlib import contextmanager
from coordinator import GateError
import re
@dataclass(frozen=True)
class Observation:
    pid:int
    uid:int
    uids:tuple
    route:str
    unit:str
    cgroup:str
    executable:tuple
    argv:tuple
    start_ticks:int
class Discovery:
    def __init__(self,uid,routes,backend,rounds=2,limit=64):
        if type(uid) is not int or uid<=0 or type(rounds) is not int or not 1<=rounds<=4 or type(limit) is not int or not 1<=limit<=64:raise GateError('InvalidInventory')
        self.uid=uid;self.routes=frozenset(routes);self.backend=backend;self.rounds=rounds;self.limit=limit
        if not self.routes or any(type(r) is not str for r in self.routes):raise GateError('UnsupportedProducer')
    def validate(self,row,pid):
        if type(row) is not Observation or type(row.pid) is not int or row.pid!=pid or row.uid!=self.uid or row.uids!=(self.uid,)*4 or row.route not in self.routes:raise GateError('UnsupportedProducer')
        if type(row.unit) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:@-]*\.service',row.unit) or row.cgroup.rsplit('/',1)[-1]!=row.unit or not row.cgroup.startswith('0::/system.slice/'):raise GateError('UnsupportedProducer')
        if type(row.start_ticks) is not int or row.start_ticks<=0 or type(row.executable) is not tuple or len(row.executable)!=3 or type(row.argv) is not tuple or len(row.argv)!=2 or row.argv[1]!=row.route:raise GateError('UnsupportedProducer')
    def pids(self):
        values=tuple(self.backend.pids(self.uid))
        if len(values)>self.limit or len(set(values))!=len(values) or any(type(p) is not int or p<=0 for p in values):raise GateError('UnverifiedQuiescence')
        return tuple(sorted(values))
    @contextmanager
    def capture(self):
        pins=[]
        try:
            version=self.backend.version();pids=self.pids();rows=[]
            for pid in pids:
                pin=self.backend.pin(pid);pins.append(pin);row=self.backend.read(pid);self.validate(row,pid)
                if self.backend.exited(pin) or self.backend.read(pid)!=row:raise GateError('Conflict')
                rows.append((row,pin))
            if self.backend.version()!=version or self.pids()!=pids:raise GateError('Conflict')
            yield tuple(rows),version
        except OSError as e:raise GateError('Busy') from e
        finally:
            for pin in pins:self.backend.close(pin)
    def empty(self):
        with self.capture() as (rows,_):return not rows
    def drain(self):
        for _ in range(self.rounds):
            with self.capture() as (rows,version):
                if not rows:return True
                # Complete validation and pinning precede every effect.
                for row,pin in rows:
                    if self.backend.version()!=version:raise GateError('Conflict')
                    if self.backend.exited(pin):continue
                    if self.backend.read(row.pid)!=row:raise GateError('Conflict')
                    if self.backend.stop(row) is not True:raise GateError('Busy')
            self.backend.after_batch()
        if self.empty():return True
        raise GateError('Busy')
