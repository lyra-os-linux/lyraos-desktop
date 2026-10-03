"""Experimental ownership of registered filesystem fences, not live producers.

Trusted-root factory only. Never removes a mask, restores activation or enrolls.
The shared ledger lock serializes cooperating callers across target UIDs.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType
from pathlib import Path
from coordinator import GateError
import operation_journal as operations
import hashlib,json,os,re,stat

PROTOCOL_DIGEST=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
FIELDS={'schema','owner','family','name','route_digest','adapter_digest','protocol_digest','namespace','original','effect','phase','revision'}
HEX=re.compile('[0-9a-f]{64}\\Z')
def stamp(value):
    if type(value) is not dict or set(value)!={'device','inode','digest'}:raise GateError('InvalidFenceJournal')
    if any(type(value[k]) is not int or value[k]<0 for k in ('device','inode')) or type(value['digest']) is not str or not HEX.fullmatch(value['digest']):raise GateError('InvalidFenceJournal')
def validate(row):
    if type(row) is not dict or set(row)!=FIELDS or type(row['schema']) is not int or row['schema']!=1:raise GateError('InvalidFenceJournal')
    operations.validate(row['owner'])
    if row['owner']['phase']!='retired':raise GateError('InvalidFenceJournal')
    family=row['family'];name=row['name']
    if family not in ('system-units','dbus-activation') or type(name) is not str or len(name)>128:raise GateError('InvalidFenceJournal')
    pattern=r'[A-Za-z0-9][A-Za-z0-9_.:-]*\.(service|timer)' if family=='system-units' else r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+'
    if not re.fullmatch(pattern,name):raise GateError('InvalidFenceJournal')
    for k in ('route_digest','adapter_digest','protocol_digest'):
        if type(row[k]) is not str or not HEX.fullmatch(row[k]):raise GateError('InvalidFenceJournal')
    ns=row['namespace']
    if type(ns) is not dict or set(ns)!={'device','inode'} or any(type(ns[k]) is not int or ns[k]<0 for k in ns):raise GateError('InvalidFenceJournal')
    if family=='system-units':
        if row['original'] is not None:raise GateError('InvalidFenceJournal')
    else:stamp(row['original'])
    if type(row['phase']) is not str or row['phase'] not in ('intent','fenced') or type(row['revision']) is not int or row['revision']!=({'intent':1,'fenced':2}[row['phase']]):raise GateError('InvalidFenceJournal')
    if row['phase']=='intent':
        if row['effect'] is not None:raise GateError('InvalidFenceJournal')
    else:stamp(row['effect'])
    return row
def encode(row):return (json.dumps(validate(row),sort_keys=True,separators=(',',':'))+'\n').encode()
def decode(data):
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:raise GateError('InvalidFenceJournal')
            result[k]=v
        return result
    try:return validate(json.loads(data,object_pairs_hook=unique))
    except GateError:raise
    except (ValueError,TypeError,UnicodeError,RecursionError) as e:raise GateError('InvalidFenceJournal') from e

class MaskBackend:
    family='system-units'
    def __init__(self,masks):self.masks=masks
    @contextmanager
    def opened(self):
        fd=self.masks._open()
        try:yield fd
        finally:os.close(fd)
    def state(self,fd,name,digest):
        self.masks._name(name)
        try:s=os.stat(name,dir_fd=fd,follow_symlinks=False)
        except FileNotFoundError:return dict(state='available',stamp=None)
        if not self.masks._masked(fd,name):raise GateError('UnsafeMasks')
        return dict(state='fenced',stamp=dict(device=s.st_dev,inode=s.st_ino,digest=hashlib.sha256(b'/dev/null').hexdigest()))
    def apply(self,fd,name,digest):
        # Retain the already-open namespace rather than reopen a replaced path.
        try:os.symlink('/dev/null',name,dir_fd=fd)
        except FileExistsError:
            if not self.masks._masked(fd,name):raise GateError('UnsafeMasks')
        os.fsync(fd)

class RouteBackend:
    family='dbus-activation'
    def __init__(self,retirement,route_type):self.retirement=retirement;self.route_type=route_type
    @contextmanager
    def opened(self):
        fd=self.retirement._open()
        try:yield fd
        finally:os.close(fd)
    def state(self,fd,name,digest):
        route=self.route_type(name,digest);status=self.retirement._inspect(fd,route)
        source,dest=self.retirement.names(route)
        info=self.retirement._read(fd,dest if status=='retired' else source,(1,2))
        return dict(state={'active':'available','partial':'partial','retired':'fenced'}[status],stamp=dict(device=info[0],inode=info[1],digest=info[2]))
    def apply(self,fd,name,digest):
        route=self.route_type(name,digest);status=self.retirement._inspect(fd,route)
        if status=='retired':return
        source,dest=self.retirement.names(route)
        if status=='active':os.link(source,dest,src_dir_fd=fd,dst_dir_fd=fd,follow_symlinks=False)
        os.fsync(fd)
        if self.retirement._inspect(fd,route)!='partial':raise GateError('UnsafeRoutes')
        os.unlink(source,dir_fd=fd);os.fsync(fd)

@dataclass(frozen=True)
class Resource:
    family:str
    name:str
    digest:str
    backend:object
    current_digest:object

@dataclass(frozen=True)
class Plan:
    uid:int
    operation:str
    key:tuple
    entry:bytes
    ledger_hash:str
    resource_state:bytes

class OwnedInhibitions:
    def __init__(self,owner,ledger,resources,crash_at=None):
        self.owner=owner;self.ledger=ledger;self.crash_at=crash_at
        items=tuple(resources)
        if not items or any(type(r) is not Resource for r in items):raise GateError('UnsupportedProducer')
        self.resources=MappingProxyType({(r.family,r.name):r for r in items})
        if len(self.resources)!=len(items):raise GateError('InvalidResource')
    def crash(self,point):
        if point==self.crash_at:os._exit(91)
    @staticmethod
    def name(resource,namespace):
        # One configured system namespace per family in this ledger. A replaced
        # directory must conflict with its existing owner, not create a new key.
        key=[resource.family,resource.name]
        return hashlib.sha256(json.dumps(key,separators=(',',':')).encode()).hexdigest()+'.json'
    @contextmanager
    def _locked(self,uid,exclusive):
        # Inventory -> negative proof -> global fence ledger. The first two
        # are SH, compatible with a classification adapter's outer SH lease.
        with self.owner.inventory.locked(uid) as inv:
            with self.owner.withdrawal.lock(uid,False) as (proof,names):
                with self.ledger.lock(1,exclusive) as (fd,_):yield inv,proof,names,fd
    def _capture(self,uid,operation,key,inv,proof,names,fd):
        if type(key) is not tuple or len(key)!=2 or any(type(v) is not str for v in key):raise GateError('InvalidResource')
        resource=self.resources.get(key)
        if resource is None:raise GateError('UnsupportedProducer')
        if resource.family!=resource.backend.family:raise GateError('InvalidResource')
        current,_=self.owner._owner(proof,names,uid)
        if current['operation']!=operation:raise GateError('Conflict')
        if current['phase']!='retired':raise GateError('RecoveryRequired')
        self.owner._inventory(current,inv)
        catalog=self.owner.inventory.read_locked(inv,uid)
        producer=next(p for p in catalog.producers if p.name==resource.family)
        if producer.state!='registered' or (resource.name,resource.digest) not in producer.routes:raise GateError('UnverifiedProducerCatalog')
        try:version=resource.current_digest()
        except Exception as e:raise GateError('UnverifiedProducerCatalog') from e
        if type(version) is not str or version!=producer.adapter_digest:raise GateError('UnverifiedProducerCatalog')
        if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=PROTOCOL_DIGEST:raise GateError('ProtocolChanged')
        with resource.backend.opened() as nsfd:
            s=os.fstat(nsfd);namespace=dict(device=s.st_dev,inode=s.st_ino)
            name=self.name(resource,namespace);saved=self.ledger.read(fd,name)
            state=resource.backend.state(nsfd,resource.name,resource.digest)
            base=dict(schema=1,owner=current,family=resource.family,name=resource.name,route_digest=resource.digest,adapter_digest=version,protocol_digest=PROTOCOL_DIGEST,namespace=namespace)
            if saved is None:
                if state['state']!='available':raise GateError('UnownedInhibition')
                row=dict(base,original=state['stamp'] if resource.family=='dbus-activation' else None,effect=None,phase='intent',revision=1)
            else:
                row=decode(saved)
                if any(row[k]!=v for k,v in base.items()):raise GateError('OwnershipConflict')
                if resource.family=='dbus-activation' and state['stamp']!=row['original']:raise GateError('ResourceChanged')
                if row['phase']=='fenced' and (state['state']!='fenced' or state['stamp']!=row['effect']):raise GateError('ResourceChanged')
            plan=Plan(uid,operation,key,encode(row),self.ledger.fingerprint([saved]),json.dumps(state,sort_keys=True).encode())
            yield plan,resource,nsfd,name,saved,state,fd
    @contextmanager
    def _snapshot(self,uid,operation,key,exclusive=False):
        with self._locked(uid,exclusive) as args:
            iterator=self._capture(uid,operation,key,*args)
            try:yield next(iterator)
            finally:iterator.close()
    def plan(self,uid,operation,key):
        def work():
            with self._snapshot(uid,operation,key) as capture:return capture[0]
        return self.owner._storage(work)
    def execute(self,plan,authorize):
        if type(plan) is not Plan:raise GateError('InvalidPlan')
        def work():
            with self._snapshot(plan.uid,plan.operation,plan.key) as capture:
                if capture[0]!=plan:raise GateError('Conflict')
            self.owner._authorize(authorize,decode(plan.entry))
            with self._snapshot(plan.uid,plan.operation,plan.key,True) as capture:
                fresh,resource,nsfd,name,saved,state,ledger_fd=capture
                if fresh!=plan:raise GateError('Conflict')
                row=decode(plan.entry)
                if row['phase']=='fenced':return 'OwnedFilesystemInhibitionNoQuiescence'
                if saved is None:
                    # _snapshot holds the shared namespace's stable ledger EX.
                    self.ledger.atomic(ledger_fd,name,encode(row))
                self.crash('intent-synced')
                resource.backend.apply(nsfd,resource.name,resource.digest);self.crash('effect-synced')
                after=resource.backend.state(nsfd,resource.name,resource.digest)
                if after['state']!='fenced' or (resource.family=='dbus-activation' and after['stamp']!=row['original']):raise GateError('ResourceChanged')
                done=dict(row,phase='fenced',revision=2,effect=after['stamp'])
                self.ledger.atomic(ledger_fd,name,encode(done));self.crash('fenced-journal-synced')
                return 'OwnedFilesystemInhibitionNoQuiescence'
        return self.owner._storage(work)
    def resume(self,uid,operation,key,authorize):return self.execute(self.plan(uid,operation,key),authorize)
    def inspect(self,uid,operation,key):return decode(self.plan(uid,operation,key).entry)['phase']
