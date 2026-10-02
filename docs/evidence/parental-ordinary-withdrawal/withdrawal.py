"""Root-only experimental admission withdrawal, not enrollment or quiescence.

Stable per-UID lock shared with the fixture PAM reader. Callback authorization
is trusted test injection, not Polkit. No proof/marker restoration method.
"""
import contextlib,dataclasses,fcntl,hashlib,json,os,re,stat

class WithdrawalError(RuntimeError):pass

@dataclasses.dataclass(frozen=True)
class Plan:
    uid:int
    operation:str
    digest:str
    proof_hash:str

HEX=re.compile(r'[0-9a-f]{32}\Z')

def validate_journal(row):
    if type(row) is not dict or set(row)!={'schema','uid','operation','proof_hash','phase','revision'}:
        raise WithdrawalError('InvalidJournal')
    if row['schema']!=1 or type(row['schema']) is not int or type(row['uid']) is not int or not 0<row['uid']<2**32-1:
        raise WithdrawalError('InvalidJournal')
    if type(row['operation']) is not str or not HEX.fullmatch(row['operation']):raise WithdrawalError('InvalidJournal')
    if type(row['proof_hash']) is not str or not re.fullmatch('[0-9a-f]{64}',row['proof_hash']):raise WithdrawalError('InvalidJournal')
    if type(row['revision']) is not int or (row['phase'],row['revision']) not in [('blocked',1),('retired',2)]:
        raise WithdrawalError('InvalidJournal')
    return row

def encode(row):return (json.dumps(validate_journal(row),sort_keys=True,separators=(',',':'))+'\n').encode()

def decode(data):
    def unique(pairs):
        row={}
        for k,v in pairs:
            if k in row:raise WithdrawalError('InvalidJournal')
            row[k]=v
        return row
    try:return validate_journal(json.loads(data,object_pairs_hook=unique))
    except (ValueError,UnicodeError,TypeError) as e:raise WithdrawalError('InvalidJournal') from e

class Withdrawal:
    def __init__(self,directory,atomic,decode_proof,crash_at=None):
        if os.geteuid()!=0:raise WithdrawalError('RootRequired')
        self.directory=directory;self.atomic=atomic;self.decode_proof=decode_proof;self.crash_at=crash_at
    def crash(self,point):
        if self.crash_at==point:os._exit(91)
    @staticmethod
    def names(uid):
        if type(uid) is not int or not 0<uid<2**32-1:raise WithdrawalError('InvalidIdentity')
        return str(uid),f'.deny-{uid}',f'.withdrawal-{uid}.json',f'.gate-{uid}.lock'
    @contextlib.contextmanager
    def lock(self,uid,exclusive):
        names=self.names(uid)
        dfd=os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        fd=-1
        try:
            s=os.fstat(dfd)
            if s.st_uid!=0 or s.st_mode&0o077:raise WithdrawalError('UnsafeDirectory')
            fd=os.open(names[3],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,dir_fd=dfd)
            s=os.fstat(fd)
            if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o077 or s.st_nlink!=1:raise WithdrawalError('UnsafeLock')
            try:fcntl.flock(fd,(fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)|fcntl.LOCK_NB)
            except BlockingIOError as e:raise WithdrawalError('Busy') from e
            yield dfd,names
        finally:
            if fd>=0:os.close(fd)
            os.close(dfd)
    @staticmethod
    def read(dfd,name):
        try:fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,dir_fd=dfd)
        except FileNotFoundError:return None
        try:
            s=os.fstat(fd)
            if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o077 or s.st_nlink!=1 or not 0<s.st_size<=8192:
                raise WithdrawalError('UnsafeState')
            data=os.read(fd,s.st_size)
            if len(data)!=s.st_size:raise WithdrawalError('ShortRead')
            return data
        finally:os.close(fd)
    def snapshot(self,dfd,names):return [self.read(dfd,n) for n in names[:3]]
    @staticmethod
    def fingerprint(parts):return hashlib.sha256(json.dumps([p.hex() if p is not None else None for p in parts]).encode()).hexdigest()
    def plan(self,uid,operation):
        if type(operation) is not str or not HEX.fullmatch(operation):raise WithdrawalError('InvalidOperation')
        with self.lock(uid,False) as (dfd,names):
            proof,marker,journal=self.snapshot(dfd,names)
            if marker is not None or journal is not None:raise WithdrawalError('RecoveryRequired')
            if proof is None:raise WithdrawalError('Unknown')
            self.decode_proof(proof,uid)
            return Plan(uid,operation,self.fingerprint([proof,marker,journal]),hashlib.sha256(proof).hexdigest())
    def begin(self,plan,authorize):
        if type(plan) is not Plan:raise WithdrawalError('InvalidPlan')
        with self.lock(plan.uid,False) as (dfd,names):
            if self.fingerprint(self.snapshot(dfd,names))!=plan.digest:raise WithdrawalError('Conflict')
        if authorize(plan) is not True:raise WithdrawalError('Denied')
        with self.lock(plan.uid,True) as (dfd,names):
            proof,marker,journal=self.snapshot(dfd,names)
            if self.fingerprint([proof,marker,journal])!=plan.digest:raise WithdrawalError('Conflict')
            self.decode_proof(proof,plan.uid)
            if hashlib.sha256(proof).hexdigest()!=plan.proof_hash:raise WithdrawalError('Conflict')
            row=dict(schema=1,uid=plan.uid,operation=plan.operation,proof_hash=plan.proof_hash,phase='blocked',revision=1)
            self.atomic(dfd,names[1],encode(row));self.crash('marker-synced')
            self.atomic(dfd,names[2],encode(row));self.crash('journal-synced')
            return self.retire(dfd,names,row)
    def retire(self,dfd,names,row):
        proof=self.read(dfd,names[0])
        if proof is not None:
            if hashlib.sha256(proof).hexdigest()!=row['proof_hash']:raise WithdrawalError('Conflict')
            self.decode_proof(proof,row['uid']);os.unlink(names[0],dir_fd=dfd);os.fsync(dfd)
        self.crash('proof-unlinked')
        row=dict(row,phase='retired',revision=2)
        self.atomic(dfd,names[2],encode(row));self.crash('retired-journal-synced')
        return 'AdmissionBlockedProofRetiredNoQuiescence'
    def resume(self,uid,operation,authorize):
        with self.lock(uid,False) as (dfd,names):
            before=self.snapshot(dfd,names)
            if before[1] is None:raise WithdrawalError('RecoveryRequired')
            row=decode(before[1])
            if row['uid']!=uid or row['operation']!=operation:raise WithdrawalError('Conflict')
            if before[2] is not None:
                journal=decode(before[2])
                if any(journal[k]!=row[k] for k in ('uid','operation','proof_hash')):raise WithdrawalError('Conflict')
            digest=self.fingerprint(before)
        if authorize(row) is not True:raise WithdrawalError('Denied')
        with self.lock(uid,True) as (dfd,names):
            if self.fingerprint(self.snapshot(dfd,names))!=digest:raise WithdrawalError('Conflict')
            return self.retire(dfd,names,row)
    def inspect(self,uid):
        # Read-only boot/recovery status. Never recreate an ordinary proof.
        with self.lock(uid,False) as (dfd,names):
            proof,marker,journal=self.snapshot(dfd,names)
            if marker is not None or journal is not None:return 'BlockedUntilAuthorizedRecovery'
            return 'ExistingOrdinaryProofNeedsVerification' if proof is not None else 'Unknown'
