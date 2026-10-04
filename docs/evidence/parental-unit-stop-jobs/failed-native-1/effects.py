"""Scoped stop-effect journal bound to the existing negative operation owner.

Separate stable effect lock avoids upgrading the adapter's classification SH.
No admission changes, retry submission, enrollment or global monotonic claim.
"""
from contextlib import contextmanager
from pathlib import Path
import hashlib,json,re
from coordinator import GateError
import operation_journal as operations
PROTOCOL_DIGEST=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
FIELDS={'schema','owner','unit','route_digest','protocol_digest','boot_id','phase','revision','job'}
PHASES={'intent':1,'accepted':2,'uncertain':2,'observed-drained':3}
HEX=re.compile('[0-9a-f]{64}\\Z')
JOB=re.compile('/org/freedesktop/systemd1/job/[1-9][0-9]*\\Z')
def validate(row):
    if type(row) is not dict or set(row)!=FIELDS or type(row['schema']) is not int or row['schema']!=1:raise GateError('InvalidStopJournal')
    operations.validate(row['owner'])
    if row['owner']['phase']!='retired':raise GateError('InvalidStopJournal')
    if type(row['unit']) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\.(service|timer)',row['unit']):raise GateError('InvalidStopJournal')
    if any(type(row[k]) is not str or not HEX.fullmatch(row[k]) for k in ('route_digest','protocol_digest')):raise GateError('InvalidStopJournal')
    if type(row['boot_id']) is not str or not re.fullmatch('[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}',row['boot_id']):raise GateError('InvalidStopJournal')
    if type(row['phase']) is not str or row['phase'] not in PHASES or type(row['revision']) is not int or row['revision']!=PHASES[row['phase']]:raise GateError('InvalidStopJournal')
    job=row['job']
    if job is not None and (type(job) is not str or not JOB.fullmatch(job)):raise GateError('InvalidStopJournal')
    if row['phase']=='intent' and job is not None or row['phase']=='accepted' and job is None:raise GateError('InvalidStopJournal')
    return row
def encode(row):return (json.dumps(validate(row),sort_keys=True,separators=(',',':'))+'\n').encode()
def decode(data):
    def unique(pairs):
        row={}
        for k,v in pairs:
            if k in row:raise GateError('InvalidStopJournal')
            row[k]=v
        return row
    try:return validate(json.loads(data,object_pairs_hook=unique))
    except GateError:raise
    except (ValueError,TypeError,UnicodeError,RecursionError) as e:raise GateError('InvalidStopJournal') from e

class Effects:
    def __init__(self,owner,storage,target,routes,boot_id):
        self.owner=owner;self.storage=storage;self.target=target;self.routes=dict(routes);self.boot_id=boot_id
        if not self.routes or len(self.routes)>64:raise GateError('UnsupportedProducer')
    @staticmethod
    def name(unit):return '.stop-'+hashlib.sha256(unit.encode()).hexdigest()+'.json'
    @contextmanager
    def locked(self,unit,exclusive=False):
        if unit not in self.routes:raise GateError('UnsupportedProducer')
        t=self.target
        def opened():
            with self.owner.inventory.locked(t.uid) as inv:
                with self.owner.withdrawal.lock(t.uid,False) as (proof,names):
                    current,_=self.owner._owner(proof,names,t.uid)
                    if (current['identity']['uid'],current['operation'],current['proof_hash'])!=(t.uid,t.operation,t.proof_hash) or current['phase']!='retired':raise GateError('Conflict')
                    self.owner._inventory(current,inv)
                    snapshot=self.owner.inventory.read_locked(inv,t.uid)
                    producer=next(p for p in snapshot.producers if p.name=='system-units')
                    if producer.state!='registered' or (unit,self.routes[unit]) not in producer.routes:raise GateError('UnverifiedProducerCatalog')
                    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=PROTOCOL_DIGEST:raise GateError('ProtocolChanged')
                    with self.storage.lock(t.uid,exclusive) as (fd,_):
                        raw=self.storage.read(fd,self.name(unit));row=decode(raw) if raw is not None else None
                        if row is not None:
                            if row['owner']!=current or row['unit']!=unit or row['route_digest']!=self.routes[unit] or row['protocol_digest']!=PROTOCOL_DIGEST:raise GateError('Conflict')
                            if row['boot_id']!=self.boot_id():raise GateError('RecoveryRequired')
                        yield fd,current,row
        iterator=opened()
        try:yield next(iterator)
        except OSError as e:raise GateError('StorageFailure') from e
        finally:iterator.close()
    def read(self,unit):
        def work():
            with self.locked(unit) as (_,_,row):return row
        return self.owner._storage(work)
    def begin(self,unit):
        def work():
            with self.locked(unit,True) as (fd,current,row):
                if row is not None:raise GateError('RecoveryRequired')
                row=dict(schema=1,owner=current,unit=unit,route_digest=self.routes[unit],protocol_digest=PROTOCOL_DIGEST,boot_id=self.boot_id(),phase='intent',revision=1,job=None)
                self.storage.atomic(fd,self.name(unit),encode(row));return row
        return self.owner._storage(work)
    def advance(self,expected,phase,job=None):
        validate(expected)
        def work():
            with self.locked(expected['unit'],True) as (fd,_,row):
                if row!=expected:raise GateError('Conflict')
                if phase in ('accepted','uncertain') and row['phase']!='intent' or phase=='observed-drained' and row['phase'] not in ('intent','accepted','uncertain'):raise GateError('RecoveryRequired')
                if phase not in ('accepted','uncertain','observed-drained'):raise GateError('InvalidStopJournal')
                result=dict(row,phase=phase,revision=PHASES[phase],job=job if phase in ('accepted','uncertain') else row['job'])
                self.storage.atomic(fd,self.name(row['unit']),encode(result));return result
        return self.owner._storage(work)
