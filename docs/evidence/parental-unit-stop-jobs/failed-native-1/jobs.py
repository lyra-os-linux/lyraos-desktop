"""StopUnit acceptance is not quiescence. Unknown results never resubmit."""
import json,time
from coordinator import GateError
from effects import JOB

def job_reply(row):
    if type(row) is not dict or set(row)!={'type','data'} or row['type']!='o' or type(row['data']) is not list or len(row['data'])!=1 or type(row['data'][0]) is not str or not JOB.fullmatch(row['data'][0]):raise GateError('UnverifiedStopReply')
    return row['data'][0]

class StopJobs:
    def __init__(self,effects,backend,check_fences,settle_seconds=5):
        if type(settle_seconds) not in (int,float) or not 0<=settle_seconds<=10:raise ValueError('unbounded stop observation')
        self.effects=effects;self.backend=backend;self.check_fences=check_fences;self.settle_seconds=settle_seconds
    def fences(self):
        if self.check_fences() is not True:raise GateError('UnverifiedAdmission')
    def __call__(self,args):
        if type(args) is not list or len(args)!=3 or args[:2]!=['systemctl','stop'] or args[2] not in self.effects.routes:raise GateError('UnsupportedProducer')
        self.fences();unit=args[2];row=self.effects.begin(unit)
        # Intent is durable; the effect-journal EX lock is released before IPC.
        # The historical adapter may still hold its classification SH lease.
        try:reply=self.backend.request(unit)
        except Exception:
            self.effects.advance(row,'uncertain');raise GateError('Busy')
        try:job=job_reply(reply)
        except GateError:
            self.effects.advance(row,'uncertain');raise GateError('Busy')
        row=self.effects.advance(row,'accepted',job)
        end=time.monotonic()+self.settle_seconds
        while True:
            self.fences()
            if self.backend.drained(unit) is True:
                self.fences();self.effects.advance(row,'observed-drained');return dict(rc=0)
            if time.monotonic()>=end:raise GateError('Busy')
            time.sleep(.05)
    def reconcile(self,unit,authorize):
        row=self.effects.read(unit)
        if row is None:raise GateError('RecoveryRequired')
        self.fences()
        try:allowed=authorize(json.loads(json.dumps(row)))
        except Exception as e:raise GateError('AuthorizationFailure') from e
        if allowed is not True:raise GateError('Denied')
        if self.effects.read(unit)!=row:raise GateError('Conflict')
        self.fences()
        if self.backend.drained(unit) is not True:raise GateError('Busy')
        self.fences()
        if row['phase']=='observed-drained':return row
        return self.effects.advance(row,'observed-drained')
