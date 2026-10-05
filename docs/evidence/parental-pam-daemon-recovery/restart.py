"""Same-boot reconciliation after losing pidfds; never submit IPC or adopt PIDs.

Root-owned historical configuration permits only cold unit observation. This is
not authentication against root, global antirollback, or orphan-stop authority.
"""
from dataclasses import asdict
from pathlib import Path
import hashlib,json,re
import operation_journal as operations
from coordinator import GateError
from pam import capture as capture_pam
from recovery import RetainedHelper
from cold import observe
from jobs import StopJobs

PROTOCOL=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
FIELDS={'schema','owner','unit','route_digest','boot_id','protocol_digest','properties','reference','invocation'}

def json_value(value):
    return json.loads(json.dumps(value))


def decode(data):
    def unique(pairs):
        row={}
        for key,value in pairs:
            if key in row:raise GateError('InvalidOriginJournal')
            row[key]=value
        return row
    try:
        if type(data) is not bytes or not 0<len(data)<=8192:raise GateError('InvalidOriginJournal')
        row=json.loads(data,object_pairs_hook=unique)
        if type(row) is not dict or set(row)!=FIELDS or type(row['schema']) is not int or row['schema']!=1:
            raise GateError('InvalidOriginJournal')
        operations.validate(row['owner'])
        invocation=row['invocation']
        if type(invocation) is not list or len(invocation)!=16 or any(type(n) is not int or not 0<=n<=255 for n in invocation) or not any(invocation):raise GateError('InvalidOriginJournal')
        for key in ('route_digest','protocol_digest'):
            if type(row[key]) is not str or not re.fullmatch('[0-9a-f]{64}',row[key]):raise GateError('InvalidOriginJournal')
        if type(row['boot_id']) is not str or not re.fullmatch('[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}',row['boot_id']):raise GateError('InvalidOriginJournal')
        if type(row['unit']) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\.service',row['unit']):raise GateError('InvalidOriginJournal')
        if type(row['properties']) is not dict or type(row['reference']) is not dict:
            raise GateError('InvalidOriginJournal')
        return row
    except GateError:raise
    except (ValueError,TypeError,UnicodeError,RecursionError) as error:
        raise GateError('InvalidOriginJournal') from error


class Origins:
    def __init__(self,effects,user,group,fingerprint,profile_bytes,invocation=None):
        self.effects=effects;self.user=user;self.group=group
        self.fingerprint=fingerprint;self.profile_bytes=profile_bytes;self.invocation=invocation

    @staticmethod
    def name(unit):
        return '.origin-'+hashlib.sha256(unit.encode()).hexdigest()+'.json'

    def protocol(self):
        if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=PROTOCOL:
            raise GateError('ProtocolChanged')

    def capture(self,unit,properties):
        return capture_pam(unit,lambda name:json_value(properties),self.user,self.group,self.fingerprint,self.profile_bytes)

    def seal(self,origin,properties):
        if type(origin) is not RetainedHelper or origin.closed:raise GateError('InvalidPlan')
        origin.execution.check()  # Both original processes must still be live.
        unit=origin.unit;props=json_value(properties)
        if self.invocation is None:raise GateError('InvalidPlan')
        invocation=self.invocation(unit)
        if type(invocation) is not dict or set(invocation)!={'type','data'} or invocation['type']!='ay':raise GateError('UnverifiedRuntime')
        invocation=json_value(invocation)
        ref=self.capture(unit,props)
        if ref!=origin.execution.refs[unit]:raise GateError('Conflict')
        if self.effects.routes.get(unit)!=dict(ref.execution.fingerprints)[ref.execution.configuration.fragment][-1]:
            raise GateError('Conflict')
        origin.execution.check()
        if self.invocation(unit)!=invocation:raise GateError('Conflict')
        self.protocol()
        def work():
            with self.effects.locked(unit,True) as (fd,owner,effect):
                if effect is not None or self.effects.storage.read(fd,self.name(unit)) is not None:
                    raise GateError('RecoveryRequired')
                if owner['identity']['uid']!=ref.execution.configuration.identity.uid or self.effects.boot_id()!=origin.boot:
                    raise GateError('Conflict')
                row=dict(schema=1,owner=owner,unit=unit,route_digest=self.effects.routes[unit],boot_id=origin.boot,protocol_digest=PROTOCOL,properties=props,reference=asdict(ref),invocation=invocation['data'])
                data=(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n').encode()
                decode(data)
                self.effects.storage.atomic(fd,self.name(unit),data)
            return json_value(row)
        return self.effects.owner._storage(work)

    def read(self,unit):
        self.protocol()
        def work():
            with self.effects.locked(unit) as (fd,owner,effect):
                raw=self.effects.storage.read(fd,self.name(unit))
                if raw is None:raise GateError('RecoveryRequired')
                row=decode(raw)
                if row['owner']!=owner or row['unit']!=unit or row['route_digest']!=self.effects.routes[unit]:
                    raise GateError('Conflict')
                if row['boot_id']!=self.effects.boot_id():raise GateError('RecoveryRequired')
                if row['protocol_digest']!=PROTOCOL:raise GateError('ProtocolChanged')
            return row
        row=self.effects.owner._storage(work)
        ref=self.capture(unit,row['properties'])
        if json.dumps(asdict(ref),sort_keys=True)!=json.dumps(row['reference'],sort_keys=True):raise GateError('Conflict')
        if row['route_digest']!=dict(ref.execution.fingerprints)[ref.execution.configuration.fragment][-1]:
            raise GateError('Conflict')
        return row,ref


class Restarted:
    def __init__(self,origins,read,empty,revalidate):
        self.origins=origins;self.effects=origins.effects
        self.read=read;self.empty=empty;self.revalidate=revalidate

    def reconcile(self,unit,authorize):
        historical,ref=self.origins.read(unit)
        effect=self.effects.read(unit)
        if effect is None:raise GateError('RecoveryRequired')
        def cold():
            row=observe(ref.execution,self.read,self.empty,self.effects.boot_id,self.revalidate)
            if row.boot!=historical['boot_id']:raise GateError('RecoveryRequired')
            # systemd clears InvocationID after drain. A different nonempty ID
            # indicates a later invocation; do not reconcile it as the original.
            if row.invocation and row.invocation!=tuple(historical['invocation']):raise GateError('Conflict')
            return row
        expected=cold()
        def check():
            if self.origins.read(unit)!=(historical,ref):raise GateError('Conflict')
            if cold()!=expected:raise GateError('Conflict')
            return True
        check()
        try:
            allowed=authorize(dict(unit=unit,uid=self.effects.target.uid,operation=self.effects.target.operation,action='reconcile-cold-pam-unit'))
        except Exception as error:raise GateError('AuthorizationFailure') from error
        if allowed is not True:raise GateError('Denied')
        check()
        if self.effects.read(unit)!=effect:raise GateError('Conflict')
        # No request method exists; this path cannot issue another StopUnit.
        jobs=StopJobs(self.effects,ColdBackend(check),check,settle_seconds=0)
        return jobs.reconcile(unit,lambda row:True)


class ColdBackend:
    def __init__(self,check):self.check=check
    def drained(self,unit):return self.check()
