"""Closed experimental PAM profile; never qualify arbitrary PAMName stacks."""
from contextlib import contextmanager,ExitStack
from dataclasses import dataclass
import copy
from coordinator import GateError
import reference as configured
from guard import GuardedExecution
from running import Observation
PROFILE='lyra-parental-unit-test'
PROFILE_PATH='/etc/pam.d/'+PROFILE
MODULE='/usr/lib64/security/pam_lyra_withdrawal_fixture.so'
PERMIT='/usr/lib64/security/pam_permit.so'
SELINUX='/usr/lib64/security/pam_selinux.so'
EXECUTOR='/usr/lib/systemd/systemd-executor'
BODY=b'account required pam_permit.so\nsession required pam_selinux.so close\nsession required pam_selinux.so nottys open\nsession required pam_lyra_withdrawal_fixture.so\n'
@dataclass(frozen=True)
class PamReference:
    execution:configured.Reference
    profile:str

def capture(name,properties,user,group,fingerprint,profile_bytes):
    def limited(requested):
        rows=properties(requested)
        if type(rows) is not dict or set(rows)!=set(configured.SPECS)|{'KillMode','Delegate'}:raise GateError('UnverifiedUnitProperties')
        if rows['PAMName']!={'type':'s','data':PROFILE} or rows['KillMode']!={'type':'s','data':'control-group'} or rows['Delegate']!={'type':'b','data':False} or rows['Delegate']['data'] is not False:raise GateError('UnsupportedPamExecution')
        if profile_bytes(PROFILE_PATH)!=BODY:raise GateError('UnsupportedPamProfile')
        # Internal execution projection used solely behind this explicit PAM
        # envelope. The general reference.capture still rejects all PAMName.
        projected=copy.deepcopy({k:rows[k] for k in configured.SPECS})
        projected['PAMName']={'type':'s','data':''};return projected
    base=configured.capture(name,limited,user,group,fingerprint)
    if base.configuration.identity.uid==0:raise GateError('UnsupportedPamExecution')
    paths=(PROFILE_PATH,MODULE,PERMIT,SELINUX,EXECUTOR)
    stamps=tuple((p,fingerprint(p)) for p in paths)
    if profile_bytes(PROFILE_PATH)!=BODY or tuple((p,fingerprint(p)) for p in paths)!=stamps:raise GateError('Conflict')
    return PamReference(configured.Reference(base.configuration,base.fingerprints+stamps),PROFILE)

class PamExecution:
    def __init__(self,units,references,backend,sources,fences,execute,members):
        self.refs=dict(references);self.backend=backend;self.members=members;self.sources=sources
        if not self.refs or any(type(r) is not PamReference or r.profile!=PROFILE for r in self.refs.values()):raise GateError('InvalidPlan')
        self.guard=GuardedExecution(units,{n:r.execution for n,r in self.refs.items()},backend,sources,fences,execute)
        self.helpers=None;self.done=set()
    def helper(self,name,pin,main_pid):
        ref=self.refs[name].execution;row=self.backend.read(pin);cfg=ref.configuration
        if type(row) is not Observation or type(row.pid) is not int or row.pid<=0 or type(row.start_ticks) is not int or row.start_ticks<=0 or any(type(v) is not tuple or any(type(n) is not int for n in v) for v in (row.uids,row.gids,row.groups,row.capabilities)):raise GateError('UnverifiedRuntime')
        if self.backend.exited(pin) or self.backend.pid(pin)!=row.pid or self.backend.parent(pin)!=main_pid:raise GateError('Conflict')
        if row.uids!=(cfg.identity.uid,)*4 or row.gids!=(cfg.configured_gid,)*4 or row.groups!=() or row.capabilities!=(0,)*3:raise GateError('UnsupportedRuntimeCredentials')
        stamp=dict(ref.fingerprints)[EXECUTOR]
        if row.executable!=(stamp[0],stamp[1],stamp[-1]) or row.cgroup!='0::/system.slice/'+name:raise GateError('UnsupportedPamHelper')
        return row
    def check(self):
        if self.helpers is None:raise GateError('InvalidPlan')
        self.guard.check()
        for n,(pin,expected,main) in self.helpers.items():
            if n in self.done:
                if not self.backend.exited(pin):raise GateError('UnverifiedQuiescence')
            else:
                if set(self.members(n))!={main,expected.pid} or self.helper(n,pin,main)!=expected:raise GateError('Conflict')
        self.guard.check()
    @contextmanager
    def batch(self):
        if self.helpers is not None:raise GateError('InvalidPlan')
        with ExitStack() as stack:
            stack.enter_context(self.guard.batch());self.helpers={};self.done=set()
            try:
                for n in self.refs:
                    main=self.guard._pins[n].observation.pid
                    pids=self.members(n)
                    if type(pids) is not tuple or len(pids)!=2 or any(type(p) is not int or p<=0 for p in pids) or len(set(pids))!=2 or main not in pids:raise GateError('UnsupportedPamHelper')
                    other=next(p for p in pids if p!=main);pin=self.backend.pin(other);stack.callback(self.backend.close,pin)
                    row=self.helper(n,pin,main)
                    if self.helper(n,pin,main)!=row:raise GateError('Conflict')
                    self.helpers[n]=(pin,row,main)
                self.check();yield self
            finally:self.helpers=None;self.done=set()
    def __call__(self,args):
        if args==['systemctl','daemon-reload'] and self.helpers is None:return self.guard(args)
        self.check();result=self.guard(args)
        if result.get('rc')==0:self.done.add(args[2])
        return result
