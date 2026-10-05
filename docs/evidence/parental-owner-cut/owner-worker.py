"""Pause the existing admission owner at real publication/unlink syscalls."""
import sys
sys.path.insert(0,'/root/unit-stop-jobs')
from bridge import *
from fixture import *
from live_common import *
import signal
operation,point,kind=sys.argv[1:]
assert kind in ('marker','owner','proof')
assert point in ('partial-write','temp-fsynced','renamed','directory-fsynced','unlinked','directory-synced')
owner=factory();plan=owner.plan(1002,operation)
real_atomic=owner.withdrawal.atomic
real_write,real_fsync,real_replace,real_unlink=os.write,os.fsync,os.replace,os.unlink
trace=dict(pid=os.getpid(),kind=kind,point=point,authorization_calls=0)
counts=dict(writes=0,file_fsync=0,renames=0,directory_fsync=0,unlinks=0)
def snapshot():
    return {p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size,inode=p.stat().st_ino,uid=p.stat().st_uid,gid=p.stat().st_gid,mode=p.stat().st_mode&0o777,nlink=p.stat().st_nlink) for p in PROOFS.iterdir() if p.is_file()}
def pause(stage,name,payload_size=None):
    path=PROOFS/name
    canonical=json.loads(path.read_text()) if path.exists() else None
    row=dict(trace,stage=stage,name=name,counts=dict(counts),canonical=canonical,files=snapshot(),payload_size=payload_size,writer_sha256=hashlib.sha256(Path(writer.__file__).read_bytes()).hexdigest())
    Path('/run/lyra-owner-cut-ready.tmp').write_text(json.dumps(row)+'\n')
    real_replace('/run/lyra-owner-cut-ready.tmp','/run/lyra-owner-cut-ready.json')
    os.kill(os.getpid(),signal.SIGSTOP)
    raise AssertionError('writer resumed unexpectedly')
def atomic(fd,name,data):
    selected='.deny-1002' if kind=='marker' else '.operation-1002.json'
    if kind=='proof' or name!=selected:return real_atomic(fd,name,data)
    # Catch the FIRST publication only; begin never returns from this pause.
    assert not (PROOFS/name).exists()
    def write(handle,view):
        if point=='partial-write' and counts['writes']==0:
            count=real_write(handle,view[:len(view)//2]);counts['writes']+=1
            assert 0<count<len(view);pause(point,name,len(data))
        count=real_write(handle,view);counts['writes']+=1;return count
    def fsync(handle):
        result=real_fsync(handle)
        if handle==fd:
            counts['directory_fsync']+=1
            if point=='directory-fsynced':pause(point,name,len(data))
        else:
            counts['file_fsync']+=1
            if point=='temp-fsynced':pause(point,name,len(data))
        return result
    def replace(*args,**kwargs):
        result=real_replace(*args,**kwargs);counts['renames']+=1
        if point=='renamed':pause(point,name,len(data))
        return result
    os.write,os.fsync,os.replace=write,fsync,replace
    try:return real_atomic(fd,name,data)
    finally:os.write,os.fsync,os.replace=real_write,real_fsync,real_replace
owner.withdrawal.atomic=atomic
unlink_fd=None
def unlink(name,*args,**kwargs):
    global unlink_fd
    result=real_unlink(name,*args,**kwargs)
    if kind=='proof' and name=='1002' and kwargs.get('dir_fd') is not None:
        assert Path('/proc/self/fd',str(kwargs['dir_fd'])).readlink()==PROOFS
        unlink_fd=kwargs['dir_fd'];counts['unlinks']+=1
        if point=='unlinked':pause(point,'1002')
    return result
def fsync(handle):
    result=real_fsync(handle)
    if kind=='proof' and unlink_fd is not None and handle==unlink_fd:
        counts['directory_fsync']+=1
        if point=='directory-synced':pause(point,'1002')
    return result
if kind=='proof':os.unlink,os.fsync=unlink,fsync
def authorize(row):
    unlocked_authority();trace['authorization_calls']+=1
    assert row['operation']==operation and row['identity']['uid']==1002
    return True
try:
    owner.begin(plan,authorize)
    raise AssertionError('boundary not reached')
finally:
    (BASE/'owner-finally-ran').write_text('unexpected unwind')
