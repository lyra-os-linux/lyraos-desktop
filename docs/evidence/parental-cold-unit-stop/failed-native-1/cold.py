"""Cold observations complement, never fabricate, active process references."""
from contextlib import contextmanager,ExitStack
from dataclasses import dataclass
import re
from coordinator import GateError
from reference import Reference
from guard import GuardedExecution
SPECS={'MainPID':'u','ControlGroup':'s','ActiveState':'s','SubState':'s','Job':'(uo)','InvocationID':'ay'}
@dataclass(frozen=True)
class Cold:
    reference:Reference
    boot:str
    state:str
    substate:str
    invocation:tuple

def observe(ref,read,empty,boot,revalidate):
    if type(ref) is not Reference or revalidate(ref)!=ref:raise GateError('InvalidPlan')
    name=ref.configuration.canonical;rows=read(name)
    if type(rows) is not dict or set(rows)!=set(SPECS):raise GateError('UnverifiedRuntime')
    for key,sig in SPECS.items():
        row=rows[key]
        if type(row) is not dict or set(row)!={'type','data'} or row['type']!=sig:raise GateError('UnverifiedRuntime')
    d={k:r['data'] for k,r in rows.items()}
    if type(d['MainPID']) is not int or d['MainPID']!=0:raise GateError('Busy')
    if any(type(d[k]) is not str for k in ('ControlGroup','ActiveState','SubState')):raise GateError('UnverifiedRuntime')
    if (d['ActiveState'],d['SubState']) not in (('inactive','dead'),('failed','failed')):raise GateError('Busy')
    if d['ControlGroup'] not in ('','/system.slice/'+name):raise GateError('UnsupportedRuntime')
    job=d['Job'];inv=d['InvocationID']
    if type(job) is not list or len(job)!=2 or type(job[0]) is not int or type(job[1]) is not str:raise GateError('UnverifiedRuntime')
    if job!=[0,'/']:raise GateError('Busy')
    if type(inv) is not list or len(inv) not in (0,16) or any(type(n) is not int or not 0<=n<=255 for n in inv):raise GateError('UnverifiedRuntime')
    # Inspect the original canonical cgroup even if systemd reports an empty path.
    if empty(name) is not True:raise GateError('Busy')
    bid=boot()
    if type(bid) is not str or not re.fullmatch('[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}',bid):raise GateError('UnverifiedRuntime')
    if revalidate(ref)!=ref:raise GateError('Conflict')
    return Cold(ref,bid,d['ActiveState'],d['SubState'],tuple(inv))

class MixedExecution:
    def __init__(self,units,references,backend,revalidate,fences,execute,read,empty,boot):
        self.units=tuple(units);self.refs=dict(references);self.backend=backend;self.revalidate=revalidate
        self.fences=fences;self.execute=execute;self.read=read;self.empty=empty;self.boot=boot
        services={u.name for u in self.units if u.kind=='service'}
        if not services or len({u.name for u in self.units})!=len(self.units) or services!=set(self.refs):raise GateError('UnsupportedProducer')
        if any(type(r) is not Reference or r.configuration.canonical!=n for n,r in self.refs.items()):raise GateError('InvalidPlan')
        self.cold=None;self.active=None
    def fence(self):
        if any(self.fences(u.name) is not True for u in self.units):raise GateError('UnverifiedAdmission')
    def check(self):
        if self.cold is None:raise GateError('InvalidPlan')
        self.fence()
        if self.active is not None:self.active.check()
        for n,row in self.cold.items():
            if observe(row.reference,self.read,self.empty,self.boot,self.revalidate)!=row:raise GateError('Conflict')
        self.fence()
    @contextmanager
    def batch(self):
        if self.cold is not None:raise GateError('InvalidPlan')
        self.fence()
        with ExitStack() as stack:
            self.cold={};active={}
            try:
                for n,r in self.refs.items():
                    rows=self.backend.runtime(n);row=rows.get('MainPID') if type(rows) is dict else None
                    if type(row) is not dict or set(row)!={'type','data'} or row['type']!='u' or type(row['data']) is not int:raise GateError('UnverifiedRuntime')
                    if row['data']==0:
                        first=observe(r,self.read,self.empty,self.boot,self.revalidate)
                        if observe(r,self.read,self.empty,self.boot,self.revalidate)!=first:raise GateError('Conflict')
                        self.cold[n]=first
                    else:active[n]=r
                if active:
                    units=tuple(u for u in self.units if u.kind=='timer' or u.name in active)
                    self.active=GuardedExecution(units,active,self.backend,self.revalidate,self.fences,self.execute)
                    stack.enter_context(self.active.batch())
                self.check();yield self
            finally:self.cold=None;self.active=None
    def __call__(self,args):
        if args==['systemctl','daemon-reload'] and self.cold is None:return self.execute(args)
        if type(args) is not list or len(args)!=3 or args[:2]!=['systemctl','stop'] or args[2] not in {u.name for u in self.units}:raise GateError('UnsupportedProducer')
        self.check()
        if args[2] in self.cold:return {'rc':0} # Live re-observation; no IPC/job/journal completion.
        if self.active is not None:return self.active(args)
        return self.execute(args) # Closed timer, still checked against every cold service.
