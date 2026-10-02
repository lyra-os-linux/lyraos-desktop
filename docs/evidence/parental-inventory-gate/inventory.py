"""Root-owned registered inventory reader. No whole-namespace certificate issuer.

Local revision + digest detect changed catalogs, not global monotonic authority
or anti-rollback. Writers must take the stable per-UID EX lock. Root is trusted.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType
from coordinator import GateError,REQUIRED
import contextvars,fcntl,hashlib,json,os,re,stat

@dataclass(frozen=True)
class Identity:
    user:str
    uid:int
    gid:int
    group:str

@dataclass(frozen=True)
class Producer:
    name:str
    state:str
    adapter_digest:str
    routes:tuple

@dataclass(frozen=True)
class Snapshot:
    identity:Identity
    revision:int
    producers:tuple
    digest:str

HEX=re.compile('[0-9a-f]{64}\\Z')
NAME=re.compile('[a-z_][a-z0-9_-]{0,62}\\Z')
ROUTE=re.compile('[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\\Z')
def positive(value):return type(value) is int and 0<value<2**32-1

def decode(data,uid):
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise GateError('InvalidInventory')
            d[k]=v
        return d
    try:
        row=json.loads(data,object_pairs_hook=unique)
        if type(row) is not dict or set(row)!={'schema','identity','revision','producers'} or type(row['schema']) is not int or row['schema']!=1:raise ValueError()
        i=row['identity']
        if type(i) is not dict or set(i)!={'user','uid','gid','group'} or not positive(i['uid']) or not positive(i['gid']) or i['uid']!=uid:raise ValueError()
        if any(type(i[k]) is not str or not NAME.fullmatch(i[k]) for k in ('user','group')):raise ValueError()
        if type(row['revision']) is not int or not 0<row['revision']<2**63:raise ValueError()
        p=row['producers']
        if type(p) is not dict:raise ValueError()
        if set(p)-REQUIRED:raise GateError('UnknownProducer')
        if REQUIRED-set(p):raise GateError('UnsupportedProducer')
        producers=[]
        for name in sorted(REQUIRED):
            item=p[name]
            if type(item) is not dict or set(item)!={'state','adapter_digest','routes'}:raise ValueError()
            state=item['state'];digest=item['adapter_digest'];routes=item['routes']
            # There is deliberately no "complete" spelling: a config file is
            # not evidence of namespace completeness. A qualified issuer is pending.
            if state not in ('registered','unsupported'):raise GateError('UnverifiedCoverage')
            if type(digest) is not str or not HEX.fullmatch(digest) or type(routes) is not list or len(routes)>64:raise ValueError()
            if (state=='registered' and not routes) or (state=='unsupported' and routes):raise ValueError()
            pairs=[]
            for r in routes:
                if type(r) is not dict or set(r)!={'id','digest'} or type(r['id']) is not str or not ROUTE.fullmatch(r['id']) or type(r['digest']) is not str or not HEX.fullmatch(r['digest']):raise ValueError()
                pairs.append((r['id'],r['digest']))
            if len({r[0] for r in pairs})!=len(pairs):raise ValueError()
            producers.append(Producer(name,state,digest,tuple(sorted(pairs))))
        canonical=json.dumps(row,sort_keys=True,separators=(',',':')).encode()
        return Snapshot(Identity(**i),row['revision'],tuple(producers),hashlib.sha256(canonical).hexdigest())
    except GateError:raise
    except (ValueError,TypeError,KeyError,UnicodeError,RecursionError) as e:raise GateError('InvalidInventory') from e

class Inventory:
    def __init__(self,directory,verify_identity):self.directory=directory;self.verify_identity=verify_identity
    @contextmanager
    def locked(self,uid):
        if os.geteuid()!=0:raise GateError('RootRequired')
        if not positive(uid):raise GateError('InvalidIdentity')
        dfd=fd=-1
        try:
            dfd=os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
            s=os.fstat(dfd)
            if s.st_uid!=0 or s.st_mode&0o077:raise GateError('UnsafeInventory')
            fd=os.open(f'.inventory-{uid}.lock',os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,dir_fd=dfd)
            s=os.fstat(fd)
            if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o077 or s.st_nlink!=1:raise GateError('UnsafeInventory')
            try:fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
            except BlockingIOError as e:raise GateError('Busy') from e
            yield dfd
        except GateError:raise
        except FileNotFoundError as e:raise GateError('UnknownInventory') from e
        except OSError as e:raise GateError('UnsafeInventory') from e
        finally:
            if fd>=0:os.close(fd)
            if dfd>=0:os.close(dfd)
    def read_locked(self,dfd,uid):
        fd=-1
        try:
            fd=os.open(f'{uid}.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,dir_fd=dfd);s=os.fstat(fd)
            if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o077 or s.st_nlink!=1 or not 0<s.st_size<=65536:raise GateError('UnsafeInventory')
            data=os.read(fd,65537)
            if len(data)!=s.st_size:raise GateError('UnsafeInventory')
            result=decode(data,uid)
            try:verified=self.verify_identity(result.identity)
            except Exception as e:raise GateError('InvalidIdentity') from e
            if verified is not True:raise GateError('InvalidIdentity')
            return result
        except GateError:raise
        except FileNotFoundError as e:raise GateError('UnknownInventory') from e
        except OSError as e:raise GateError('UnsafeInventory') from e
        finally:
            if fd>=0:os.close(fd)
    def snapshot(self,uid):
        with self.locked(uid) as fd:return self.read_locked(fd,uid)

@dataclass(frozen=True)
class Binding:
    adapter:object
    current_digest:object
    verify_routes:object

@dataclass(frozen=True)
class Plan:
    withdrawal:object
    snapshot:Snapshot
    policy:str

class CheckedAdapter:
    def __init__(self,gate,name,adapter):self.gate=gate;self.name=name;self.adapter=adapter
    def _call(self,method,target):
        active=self.gate._active.get()
        if active is None:raise GateError('UnverifiedInventory')
        fd,plan=active
        expected=plan.withdrawal
        if (target.uid,target.operation,target.proof_hash)!=(expected.uid,expected.operation,expected.proof_hash):raise GateError('InvalidPlan')
        self.gate._check(plan,fd)
        result=getattr(self.adapter,method)(target)
        self.gate._check(plan,fd)
        return result
    def inhibit(self,target):return self._call('inhibit',target)
    def revoke(self,target):return self._call('revoke',target)
    def quiescent(self,target):return self._call('quiescent',target)
    def inhibited(self,target):return self._call('inhibited',target)

class InventoryGate:
    """Mandatory preflight around ordinary coordinator; no publication API.

    whole-account (default) never accepts registered/unsupported catalogs.
    registered-test is a trusted fixture-factory policy, not a client selector.
    Success there stays CheckedWithinRegisteredInventory, never account-active.
    """
    def __init__(self,inventory,coordinator,bindings,policy='whole-account'):
        if policy not in ('whole-account','registered-test'):raise ValueError('invalid factory policy')
        self.inventory=inventory;self.coordinator=coordinator;self.bindings=MappingProxyType(dict(bindings));self.policy=policy
        self._originals=MappingProxyType(dict(coordinator.adapters))
        self._proxies=MappingProxyType({n:CheckedAdapter(self,n,a) for n,a in self._originals.items()})
        coordinator.adapters=self._proxies
        self._active=contextvars.ContextVar('inventory-active',default=None)
    def _coverage(self,snapshot):
        if self.policy=='whole-account':raise GateError('UnverifiedCoverage')
        if any(p.state!='registered' for p in snapshot.producers):raise GateError('UnsupportedProducer')
        if set(self.bindings)!=REQUIRED or set(self.coordinator.adapters)!=REQUIRED:raise GateError('UnsupportedProducer')
        for p in snapshot.producers:
            b=self.bindings[p.name]
            if type(b) is not Binding or self.coordinator.adapters[p.name] is not self._proxies[p.name] or self._originals[p.name] is not b.adapter:raise GateError('UnverifiedAdapterBinding')
            try:
                digest=b.current_digest()
                valid=type(digest) is str and digest==p.adapter_digest and b.verify_routes(snapshot.identity,p.routes) is True
            except Exception as e:raise GateError('UnverifiedAdapterBinding') from e
            if not valid:raise GateError('UnverifiedAdapterBinding')
    def plan(self,uid,operation):
        s=self.inventory.snapshot(uid);self._coverage(s)
        return Plan(self.coordinator.plan(uid,operation),s,self.policy)
    def _valid_plan(self,plan):
        if type(plan) is not Plan or type(plan.snapshot) is not Snapshot or plan.policy!=self.policy:raise GateError('InvalidPlan')
        p=plan.withdrawal
        try:
            if not positive(p.uid) or type(p.operation) is not str or not re.fullmatch('[0-9a-f]{32}',p.operation) or type(p.proof_hash) is not str or not HEX.fullmatch(p.proof_hash) or p.uid!=plan.snapshot.identity.uid:raise GateError('InvalidPlan')
        except AttributeError as e:raise GateError('InvalidPlan') from e
    def _check(self,plan,dfd,preflight=False):
        self._valid_plan(plan)
        current=self.inventory.read_locked(dfd,plan.withdrawal.uid)
        if current!=plan.snapshot:raise GateError('Conflict')
        self._coverage(current)
        if preflight and self.coordinator.plan(plan.withdrawal.uid,plan.withdrawal.operation)!=plan.withdrawal:raise GateError('Conflict')
    def block_and_check(self,plan,authorize,revoke=False):
        self._valid_plan(plan)
        if type(revoke) is not bool:raise GateError('InvalidPlan')
        with self.inventory.locked(plan.withdrawal.uid) as fd:self._check(plan,fd,preflight=True)
        # No inventory lock is held across interactive authorization.
        try:allowed=authorize(plan,revoke)
        except Exception as e:raise GateError('AuthorizationFailure') from e
        if allowed is not True:raise GateError('Denied')
        with self.inventory.locked(plan.withdrawal.uid) as fd:
            self._check(plan,fd,preflight=True)
            # Cooperating writers cannot replace this UID's catalog while effects
            # run. Other UIDs have separate locks. External root edits are trusted
            # maintenance, not an adversarial-root security promise.
            def authorize_inner(inner,requested_revoke):
                self._check(plan,fd)
                if inner!=plan.withdrawal or requested_revoke!=revoke:raise GateError('InvalidPlan')
                return True
            token=self._active.set((fd,plan))
            try:result=self.coordinator.block_and_check(plan.withdrawal,authorize_inner,revoke)
            finally:self._active.reset(token)
            self._check(plan,fd)
            if result!='CheckedWithinAdapterScope':raise GateError('UnverifiedQuiescence')
            return 'CheckedWithinRegisteredInventory'
