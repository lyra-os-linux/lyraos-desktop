"""Read-only namespace change guard for trusted factories; no coverage issuer.

Only declared source trees are covered. Publishers must use the same permanent
lock. Root maintenance outside that protocol is not an adversarial-root promise.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import fcntl, hashlib, os, stat
from coordinator import GateError

@dataclass(frozen=True)
class Entry:
    path: str
    stamp: tuple
    digest: str

@dataclass(frozen=True)
class Snapshot:
    roots: tuple
    entries: tuple
    authority: tuple

class Namespace:
    def __init__(self, roots, lock, *, owner=0, ancestor_owners=(0,), entries=4096, bytes_limit=16*1024*1024, depth=16):
        roots=tuple(str(p) for p in roots)
        if not roots or len(set(roots))!=len(roots):raise GateError('InvalidInventory')
        for path in (*roots,str(lock)):
            if not path.startswith('/') or str(Path(path))!=path or '..' in Path(path).parts:raise GateError('InvalidInventory')
        ordered=tuple(sorted(roots))
        if any(b.startswith(a.rstrip('/')+'/') for a in ordered for b in ordered if a!=b):raise GateError('InvalidInventory')
        if any(str(lock)==r or str(lock).startswith(r.rstrip('/')+'/') for r in roots):raise GateError('InvalidInventory')
        if type(owner) is not int or owner<0 or any(type(n) is not int or n<=0 for n in (entries,bytes_limit,depth)):raise GateError('InvalidInventory')
        if len(roots)>entries:raise GateError('ProducerNamespaceLimit')
        if type(ancestor_owners) is not tuple or any(type(u) is not int or u<0 for u in ancestor_owners):raise GateError('InvalidInventory')
        self.ancestor_owners=frozenset((*ancestor_owners,owner))
        self.roots=ordered;self.lock=str(lock);self.owner=owner
        self.limit=entries;self.bytes_limit=bytes_limit;self.depth=depth

    def safe(self,s,directory=False,ancestor=False):
        owners=self.ancestor_owners if ancestor else (self.owner,)
        if s.st_uid not in owners or s.st_mode&0o022:raise GateError('UnsafeProducerNamespace')
        if directory:
            if not stat.S_ISDIR(s.st_mode):raise GateError('UnsafeProducerNamespace')
        elif not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:raise GateError('UnsafeProducerNamespace')

    def open_absolute(self,path,directory=False):
        fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
        try:
            self.safe(os.fstat(fd),directory=True,ancestor=True)
            parts=Path(path).parts[1:]
            for index,name in enumerate(parts):
                isdir=index<len(parts)-1 or directory
                flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK
                if isdir:flags|=os.O_DIRECTORY
                child=os.open(name,flags,dir_fd=fd)
                os.close(fd);fd=child
                self.safe(os.fstat(fd),directory=isdir,ancestor=index<len(parts)-1)
            return fd
        except BaseException:
            os.close(fd);raise

    @staticmethod
    def stamp(s):
        return (s.st_dev,s.st_ino,s.st_uid,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)

    def collect(self):
        rows=[];budget=0
        def names_at(fd):
            names=[]
            with os.scandir(fd) as stream:
                for entry in stream:
                    names.append(entry.name)
                    if len(names)>self.limit:raise GateError('ProducerNamespaceLimit')
            return sorted(names)
        def walk(fd,path,level):
            nonlocal budget
            if level>self.depth:raise GateError('ProducerNamespaceLimit')
            before=os.fstat(fd);self.safe(before,directory=True)
            names=names_at(fd);rows.append(Entry(path,self.stamp(before),''))
            if len(rows)+len(names)>self.limit:raise GateError('ProducerNamespaceLimit')
            for name in names:
                # No filename or extension allowlist: unknown sources are included.
                s=os.stat(name,dir_fd=fd,follow_symlinks=False)
                isdir=stat.S_ISDIR(s.st_mode);self.safe(s,directory=isdir)
                flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC
                if isdir:flags|=os.O_DIRECTORY
                child=os.open(name,flags,dir_fd=fd)
                try:
                    if self.stamp(os.fstat(child))!=self.stamp(s):raise GateError('Conflict')
                    full=path.rstrip('/')+'/'+name
                    if isdir:walk(child,full,level+1)
                    else:
                        if budget+s.st_size>self.bytes_limit:raise GateError('ProducerNamespaceLimit')
                        chunks=[];remaining=s.st_size+1
                        while remaining:
                            data=os.read(child,min(65536,remaining))
                            if not data:break
                            chunks.append(data);remaining-=len(data)
                        content=b''.join(chunks);budget+=len(content)
                        if len(content)!=s.st_size or self.stamp(os.fstat(child))!=self.stamp(s):raise GateError('Conflict')
                        rows.append(Entry(full,self.stamp(s),hashlib.sha256(content).hexdigest()))
                        if len(rows)>self.limit:raise GateError('ProducerNamespaceLimit')
                    if self.stamp(os.stat(name,dir_fd=fd,follow_symlinks=False))!=self.stamp(s):raise GateError('Conflict')
                finally:os.close(child)
            if names_at(fd)!=names or self.stamp(os.fstat(fd))!=self.stamp(before):raise GateError('Conflict')
        try:
            for root in self.roots:
                fd=self.open_absolute(root,directory=True)
                try:walk(fd,root,0)
                finally:os.close(fd)
            lock=self.open_absolute(self.lock)
            try:authority=(self.lock,self.stamp(os.fstat(lock)))
            finally:os.close(lock)
            return Snapshot(self.roots,tuple(rows),authority)
        except GateError:raise
        except OSError as e:raise GateError('UnverifiedProducerNamespace') from e

    def snapshot(self):
        first=self.collect()
        if self.collect()!=first:raise GateError('Conflict')
        return first

    @contextmanager
    def locked(self):
        fd=-1
        try:
            fd=self.open_absolute(self.lock)
            original=self.stamp(os.fstat(fd))
            try:fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
            except BlockingIOError as e:raise GateError('Busy') from e
            def verify():
                check=self.open_absolute(self.lock)
                try:
                    if self.stamp(os.fstat(check))!=original:raise GateError('Conflict')
                finally:os.close(check)
            verify();yield verify;verify()
        except GateError:raise
        except OSError as e:raise GateError('UnverifiedProducerNamespace') from e
        finally:
            if fd>=0:os.close(fd)

    def check(self,expected):
        if type(expected) is not Snapshot or expected.roots!=self.roots:raise GateError('InvalidPlan')
        if self.snapshot()!=expected:raise GateError('Conflict')
        return expected

    def plan(self):
        with self.locked():return self.snapshot()

    def execute(self,expected,authorize,effects):
        # Internal factory callbacks only; no publication, enrollment or unblock.
        with self.locked():self.check(expected)
        try:allowed=authorize(expected)
        except Exception as e:raise GateError('AuthorizationFailure') from e
        if allowed is not True:raise GateError('Denied')
        with self.locked() as verify_lock:
            self.check(expected)
            results=[]
            for effect in effects:
                verify_lock();self.check(expected)
                results.append(effect())
                verify_lock();self.check(expected)
            return tuple(results)
