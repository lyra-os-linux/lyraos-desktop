"""Durable admission-withdrawal ownership; no enrollment or producer revocation.

First durable intent occupies the marker already denied by the historical PAM
reader. Resume requires fresh authorization and the same inventory binding.
Local phases/revisions are not global monotonic or anti-rollback authority.
"""
from dataclasses import dataclass
from coordinator import GateError
from withdrawal import Plan as WithdrawalPlan,decode as decode_legacy,encode as encode_legacy
import hashlib,json,os,re

FIELDS={'schema','action','identity','operation','proof_hash','proof_snapshot','inventory_revision','inventory_digest','phase','revision'}
BINDING=FIELDS-{'phase','revision'}
PHASES={'intent':1,'legacy-blocked':2,'retired':3}
HEX=re.compile('[0-9a-f]{64}\\Z')
NAME=re.compile('[a-z_][a-z0-9_-]{0,62}\\Z')

def validate(row):
    if type(row) is not dict or set(row)!=FIELDS or type(row['schema']) is not int or row['schema']!=1 or row['action']!='withdraw-admission':raise GateError('InvalidOperationJournal')
    i=row['identity']
    if type(i) is not dict or set(i)!={'uid','user','gid','group'}:raise GateError('InvalidOperationJournal')
    if any(type(i[k]) is not int or not 0<i[k]<2**32-1 for k in ('uid','gid')) or any(type(i[k]) is not str or not NAME.fullmatch(i[k]) for k in ('user','group')):raise GateError('InvalidOperationJournal')
    if type(row['operation']) is not str or not re.fullmatch('[0-9a-f]{32}',row['operation']):raise GateError('InvalidOperationJournal')
    if any(type(row[k]) is not str or not HEX.fullmatch(row[k]) for k in ('proof_hash','proof_snapshot','inventory_digest')):raise GateError('InvalidOperationJournal')
    if type(row['inventory_revision']) is not int or not 0<row['inventory_revision']<2**63 or type(row['phase']) is not str or row['phase'] not in PHASES or type(row['revision']) is not int or PHASES[row['phase']]!=row['revision']:raise GateError('InvalidOperationJournal')
    return row

def encode(row):return (json.dumps(validate(row),sort_keys=True,separators=(',',':'))+'\n').encode()
def decode(data):
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise GateError('InvalidOperationJournal')
            d[k]=v
        return d
    try:return validate(json.loads(data,object_pairs_hook=unique))
    except GateError:raise
    except (ValueError,TypeError,UnicodeError,RecursionError) as e:raise GateError('InvalidOperationJournal') from e

def same_owner(a,b):return all(a[k]==b[k] for k in BINDING)
def legacy(row):return dict(schema=1,uid=row['identity']['uid'],operation=row['operation'],proof_hash=row['proof_hash'],phase='blocked',revision=1)

@dataclass(frozen=True)
class Plan:
    withdrawal:WithdrawalPlan
    inventory:object

class Operations:
    def __init__(self,withdrawal,withdrawal_error,inventory,crash_at=None):
        self.withdrawal=withdrawal;self.withdrawal_error=withdrawal_error;self.inventory=inventory;self.crash_at=crash_at
    def crash(self,point):
        if self.crash_at==point:os._exit(91)
    def _storage(self,fn):
        try:return fn()
        except GateError:raise
        except self.withdrawal_error as e:
            code=str(e)
            if code not in ('Busy','Conflict','RecoveryRequired','InvalidIdentity','InvalidOperation','Unknown','Denied'):code='StorageFailure'
            raise GateError(code) from e
        except OSError as e:raise GateError('StorageFailure') from e
    @staticmethod
    def name(uid):return f'.operation-{uid}.json'
    def _parts(self,fd,names,uid):return self.withdrawal.snapshot(fd,names)+[self.withdrawal.read(fd,self.name(uid))]
    def _identity(self,proof,identity):
        row=self.withdrawal.decode_proof(proof,identity['uid'])
        if any(row[k]!=identity[k] for k in ('uid','user','gid','group')):raise GateError('InvalidIdentity')
    def _record(self,plan):
        p=plan.withdrawal;s=plan.inventory
        return validate(dict(schema=1,action='withdraw-admission',identity=dict(uid=s.identity.uid,user=s.identity.user,gid=s.identity.gid,group=s.identity.group),operation=p.operation,proof_hash=p.proof_hash,proof_snapshot=p.digest,inventory_revision=s.revision,inventory_digest=s.digest,phase='intent',revision=1))
    def _inventory(self,record,fd):
        s=self.inventory.read_locked(fd,record['identity']['uid'])
        if dict(uid=s.identity.uid,user=s.identity.user,gid=s.identity.gid,group=s.identity.group)!=record['identity'] or (s.revision,s.digest)!=(record['inventory_revision'],record['inventory_digest']):raise GateError('Conflict')
    @staticmethod
    def _authorize(authorize,payload):
        # A detached copy prevents callbacks from modifying verified ownership.
        try:allowed=authorize(json.loads(json.dumps(payload)))
        except Exception as e:raise GateError('AuthorizationFailure') from e
        if allowed is not True:raise GateError('Denied')
    def plan(self,uid,operation):
        def work():
            with self.inventory.locked(uid) as inv:
                snapshot=self.inventory.read_locked(inv,uid)
                with self.withdrawal.lock(uid,False) as (fd,names):
                    if self.withdrawal.read(fd,self.name(uid)) is not None:raise GateError('RecoveryRequired')
                plan=self.withdrawal.plan(uid,operation)
                with self.withdrawal.lock(uid,False) as (fd,names):
                    proof,marker,journal=self.withdrawal.snapshot(fd,names)
                    if self.withdrawal.fingerprint([proof,marker,journal])!=plan.digest:raise GateError('Conflict')
                    self._identity(proof,dict(uid=snapshot.identity.uid,user=snapshot.identity.user,gid=snapshot.identity.gid,group=snapshot.identity.group))
                return Plan(plan,snapshot)
        return self._storage(work)
    def _fresh(self,plan,inv,fd,names,record):
        self._inventory(record,inv)
        proof,marker,journal,owned=self._parts(fd,names,plan.withdrawal.uid)
        if owned is not None or self.withdrawal.fingerprint([proof,marker,journal])!=plan.withdrawal.digest:raise GateError('Conflict')
        if proof is None or hashlib.sha256(proof).hexdigest()!=record['proof_hash']:raise GateError('Conflict')
        self._identity(proof,record['identity'])
    def begin(self,plan,authorize):
        if type(plan) is not Plan or type(plan.withdrawal) is not WithdrawalPlan:raise GateError('InvalidPlan')
        record=self._record(plan);uid=plan.withdrawal.uid
        if uid!=record['identity']['uid']:raise GateError('InvalidPlan')
        def work():
            with self.inventory.locked(uid) as inv:
                with self.withdrawal.lock(uid,False) as (fd,names):self._fresh(plan,inv,fd,names,record)
            self._authorize(authorize,record)
            with self.inventory.locked(uid) as inv:
                with self.withdrawal.lock(uid,True) as (fd,names):
                    self._fresh(plan,inv,fd,names,record)
                    # The legacy PAM guard rejects marker presence regardless of
                    # its payload schema, so this first fsynced intent is a fence.
                    self.withdrawal.atomic(fd,names[1],encode(record));self.crash('intent-marker-synced')
                    return self._finish(fd,names,record,inv)
        return self._storage(work)
    def _finish(self,fd,names,record,inv):
        self._inventory(record,inv)
        uid=record['identity']['uid']
        owned=self.withdrawal.read(fd,self.name(uid))
        current=decode(owned) if owned is not None else None
        if current is not None and not same_owner(current,record):raise GateError('Conflict')
        if current is None:
            self.withdrawal.atomic(fd,self.name(uid),encode(record))
            current=record
        self.crash('owned-intent-synced')
        old=legacy(record)
        marker=self.withdrawal.read(fd,names[1])
        if marker!=encode_legacy(old):self.withdrawal.atomic(fd,names[1],encode_legacy(old))
        self.crash('legacy-marker-synced')
        journal=self.withdrawal.read(fd,names[2])
        if journal is None:
            self.withdrawal.atomic(fd,names[2],encode_legacy(old));journal=encode_legacy(old)
        self.crash('legacy-journal-synced')
        if current['revision']<2:
            current=dict(record,phase='legacy-blocked',revision=2)
            self.withdrawal.atomic(fd,self.name(uid),encode(current))
        self.crash('owned-blocked-synced')
        # Already retired legacy journals never regress to blocked on resume.
        # Historical retirement retains its two fsync crash hooks unchanged.
        if decode_legacy(journal)['phase']!='retired':self.withdrawal.retire(fd,names,old)
        self._inventory(record,inv)
        if current['revision']<3:
            done=dict(record,phase='retired',revision=3)
            self.withdrawal.atomic(fd,self.name(uid),encode(done))
        self.crash('owned-retired-synced')
        return 'AdmissionWithdrawnNoQuiescence'
    def _owner(self,fd,names,uid):
        proof,marker,journal,owned=self._parts(fd,names,uid)
        if marker is None:raise GateError('RecoveryRequired')
        try:intent=decode(marker)
        except GateError:
            intent=None
            try:old=decode_legacy(marker)
            except Exception as e:raise GateError('InvalidOperationJournal') from e
            if (old['uid'],old['phase'],old['revision'])!=(uid,'blocked',1) or owned is None:raise GateError('RecoveryRequired')
            record=decode(owned)
            if (old['uid'],old['operation'],old['proof_hash'])!=(record['identity']['uid'],record['operation'],record['proof_hash']):raise GateError('Conflict')
        else:
            if intent['identity']['uid']!=uid or intent['phase']!='intent' or journal is not None:raise GateError('RecoveryRequired')
            record=intent
            if owned is not None:
                other=decode(owned)
                if not same_owner(record,other) or other['phase']!='intent':raise GateError('Conflict')
        if record['identity']['uid']!=uid:raise GateError('Conflict')
        oldjournal=None
        if journal is not None:
            try:oldjournal=decode_legacy(journal)
            except Exception as e:raise GateError('InvalidOperationJournal') from e
            if (oldjournal['uid'],oldjournal['operation'],oldjournal['proof_hash'])!=(uid,record['operation'],record['proof_hash']):raise GateError('Conflict')
        if record['phase']!='intent' and oldjournal is None:raise GateError('RecoveryRequired')
        if proof is not None:
            if record['phase']=='retired' or (oldjournal is not None and oldjournal['phase']=='retired'):raise GateError('RecoveryRequired')
            if hashlib.sha256(proof).hexdigest()!=record['proof_hash']:raise GateError('Conflict')
            self._identity(proof,record['identity'])
        if record['phase']=='retired' and (oldjournal is None or oldjournal['phase']!='retired'):raise GateError('RecoveryRequired')
        return record,self.withdrawal.fingerprint([proof,marker,journal,owned])
    def inspect(self,uid):
        # Read-only. Corruption produces an error, never an ordinary fallback.
        def work():
            with self.withdrawal.lock(uid,False) as (fd,names):
                r,_=self._owner(fd,names,uid)
                return 'AdmissionWithdrawnNoQuiescence' if r['phase']=='retired' else 'BlockedRecoveryRequired'
        return self._storage(work)
    def resume(self,uid,operation,authorize):
        if type(operation) is not str or not re.fullmatch('[0-9a-f]{32}',operation):raise GateError('InvalidOperation')
        def work():
            with self.inventory.locked(uid) as inv:
                with self.withdrawal.lock(uid,False) as (fd,names):
                    record,before=self._owner(fd,names,uid)
                    if record['operation']!=operation:raise GateError('Conflict')
                    self._inventory(record,inv)
            self._authorize(authorize,record)
            with self.inventory.locked(uid) as inv:
                with self.withdrawal.lock(uid,True) as (fd,names):
                    current,after=self._owner(fd,names,uid)
                    if before!=after or current!=record:raise GateError('Conflict')
                    self._inventory(record,inv)
                    if record['phase']=='retired':return 'AdmissionWithdrawnNoQuiescence'
                    # Keep the complete owner record even when recovering after
                    # a partial legacy publication. Never replace another owner.
                    return self._finish(fd,names,record,inv)
        return self._storage(work)
