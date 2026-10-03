"""Read-only ownership checks for existing scoped live producer adapters.

Prepare owned filesystem fences with fresh authorization outside classification
locks first. These facades never create, repair or remove an inhibition.
Live adapters still must reload, inspect activation and authorize revocation.
"""
from dataclasses import dataclass
from coordinator import GateError
import owned_inhibitions as ownership
import re

@dataclass(frozen=True)
class Binding:
    uid:int
    operation:str
    proof_hash:str

class Reader:
    def __init__(self,gate,target):
        if type(target.uid) is not int or not 0<target.uid<2**32-1 or type(target.operation) is not str or not re.fullmatch('[0-9a-f]{32}',target.operation) or type(target.proof_hash) is not str or not re.fullmatch('[0-9a-f]{64}',target.proof_hash):raise GateError('InvalidTarget')
        self.gate=gate;self.binding=Binding(target.uid,target.operation,target.proof_hash)
    def check(self,family,name):
        b=self.binding;plan=self.gate.plan(b.uid,b.operation,(family,name))
        if type(plan) is not ownership.Plan:raise GateError('InvalidPlan')
        row=ownership.decode(plan.entry);owner=row['owner']
        if (owner['identity']['uid'],owner['operation'],owner['proof_hash'])!=(b.uid,b.operation,b.proof_hash):raise GateError('OwnershipConflict')
        if (row['family'],row['name'])!=(family,name):raise GateError('OwnershipConflict')
        if row['phase']!='fenced' or row['revision']!=2:raise GateError('UnverifiedAdmission')
        return row

class CheckedMasks:
    def __init__(self,gate,target,names):
        self.reader=Reader(gate,target);self.names=tuple(names)
        if not self.names or len(self.names)>64 or any(type(n) is not str for n in self.names) or len(set(self.names))!=len(self.names):raise GateError('UnsupportedProducer')
    def masked(self,name):
        if name not in self.names:raise GateError('UnsupportedProducer')
        self.reader.check('system-units',name);return True
    def install(self,names):
        if tuple(names)!=self.names:raise GateError('UnverifiedProducerCatalog')
        # The legacy method name is retained, but it only checks prepared
        # owned masks here. No mutation or authorization under an outer lease.
        for name in self.names:self.masked(name)
        return True

class CheckedRoutes:
    def __init__(self,gate,target,routes):
        self.reader=Reader(gate,target);self.routes=tuple(routes)
        if not self.routes or len(self.routes)>64:raise GateError('UnsupportedProducer')
        self.bindings=tuple((r.name,r.digest,r.unit) for r in self.routes)
        if len({r[0] for r in self.bindings})!=len(self.bindings):raise GateError('InvalidRoute')
    def inspect(self,route):
        if (route.name,route.digest,route.unit) not in self.bindings:raise GateError('UnverifiedProducerCatalog')
        row=self.reader.check('dbus-activation',route.name)
        if row['route_digest']!=route.digest:raise GateError('UnverifiedProducerCatalog')
        return 'retired'
    def retire(self,routes):
        if tuple((r.name,r.digest,r.unit) for r in routes)!=self.bindings:raise GateError('UnverifiedProducerCatalog')
        for route in self.routes:self.inspect(route)
        return True
