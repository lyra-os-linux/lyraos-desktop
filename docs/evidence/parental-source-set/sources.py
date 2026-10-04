"""Declared source-set fence, including optional absence and exact trusted aliases.

No graph resolver, broker policy evaluator or coverage issuer. Factory config is
trusted; root publishers must use the permanent namespace lock.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib,os,stat
from namespace import Namespace,Entry
from coordinator import GateError
@dataclass(frozen=True)
class Sources:
    specification:tuple
    entries:tuple
    missing:tuple
    ancestry:tuple
    aliases:tuple
    authority:tuple
class SourceSet(Namespace):
    def __init__(self,directories,files,optional_files,lock,aliases=(),**kwargs):
        super().__init__(directories,lock,**kwargs)
        self.files=tuple(sorted(str(x) for x in files));self.optional=frozenset(str(x) for x in optional_files)
        self.aliases=tuple(sorted(aliases))
        if len(self.files)>128 or len(set(self.files))!=len(self.files) or not self.optional<=set(self.files) or len(self.aliases)>16:raise GateError('InvalidInventory')
        for path in self.files:
            if not path.startswith('/') or str(Path(path))!=path or '..' in Path(path).parts or path==self.lock:raise GateError('InvalidInventory')
        if len({x[0] for x in self.aliases})!=len(self.aliases):raise GateError('InvalidInventory')
        for path,target in self.aliases:
            if type(path) is not str or not path.startswith('/') or str(Path(path))!=path or '..' in Path(path).parts or type(target) is not str or not target or '..' in Path(target).parts:raise GateError('InvalidInventory')
        self.specification=(self.roots,self.files,tuple(sorted(self.optional)),self.aliases)
    @staticmethod
    def identity(s):return s.st_dev,s.st_ino,s.st_uid,s.st_mode
    def probe(self,path,directory,optional):
        fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC);parts=Path(path).parts[1:];ancestry=[];prefix='/'
        try:
            self.safe(os.fstat(fd),directory=True,ancestor=True)
            for index,name in enumerate(parts):
                parent=os.fstat(fd);ancestry.append((prefix,self.identity(parent)))
                isdir=index<len(parts)-1 or directory
                flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK
                if isdir:flags|=os.O_DIRECTORY
                try:child=os.open(name,flags,dir_fd=fd)
                except FileNotFoundError:
                    if not optional:raise GateError('UnverifiedProducerNamespace')
                    return False,(path,prefix,tuple(parts[index:]),self.stamp(parent)),tuple(ancestry)
                os.close(fd);fd=child;self.safe(os.fstat(fd),directory=isdir,ancestor=index<len(parts)-1)
                prefix=prefix.rstrip('/')+'/'+name
            return True,None,tuple(ancestry)
        finally:os.close(fd)
    def alias_observations(self):
        rows=[]
        for path,target in self.aliases:
            parent=str(Path(path).parent);name=Path(path).name;fd=self.open_absolute(parent,directory=True)
            try:
                s=os.stat(name,dir_fd=fd,follow_symlinks=False)
                if not stat.S_ISLNK(s.st_mode) or s.st_uid!=self.owner or os.readlink(name,dir_fd=fd)!=target:raise GateError('UnsupportedProducerAlias')
                rows.append((path,target,self.stamp(s),self.identity(os.fstat(fd))))
            finally:os.close(fd)
        return tuple(rows)
    def collect(self):
        missing=[];ancestry=[];present=[];rows=[];budget=0
        try:
            aliases=self.alias_observations()
            for path in self.roots:
                exists,absent,parents=self.probe(path,True,True);ancestry.extend(parents)
                if exists:present.append(path)
                else:missing.append(absent)
            if present:
                tree=Namespace(present,self.lock,owner=self.owner,ancestor_owners=tuple(self.ancestor_owners),entries=self.limit,bytes_limit=self.bytes_limit,depth=self.depth).collect()
                rows.extend(tree.entries);budget=sum(row.stamp[5] for row in rows if row.digest)
            for path in self.files:
                exists,absent,parents=self.probe(path,False,path in self.optional);ancestry.extend(parents)
                if not exists:missing.append(absent);continue
                if any(path.startswith(root.rstrip('/')+'/') for root in present):continue
                fd=self.open_absolute(path)
                try:
                    s=os.fstat(fd)
                    if budget+s.st_size>self.bytes_limit:raise GateError('ProducerNamespaceLimit')
                    chunks=[];remaining=s.st_size+1
                    while remaining:
                        data=os.read(fd,min(65536,remaining))
                        if not data:break
                        chunks.append(data);remaining-=len(data)
                    data=b''.join(chunks)
                    if len(data)!=s.st_size or self.stamp(os.fstat(fd))!=self.stamp(s):raise GateError('Conflict')
                    budget+=len(data);rows.append(Entry(path,self.stamp(s),hashlib.sha256(data).hexdigest()))
                finally:os.close(fd)
            if len(rows)+len(missing)>self.limit:raise GateError('ProducerNamespaceLimit')
            fd=self.open_absolute(self.lock)
            try:authority=(self.lock,self.stamp(os.fstat(fd)))
            finally:os.close(fd)
            if self.alias_observations()!=aliases:raise GateError('Conflict')
            return Sources(self.specification,tuple(rows),tuple(missing),tuple(ancestry),aliases,authority)
        except GateError:raise
        except OSError as e:raise GateError('UnverifiedProducerNamespace') from e
    def check(self,expected):
        if type(expected) is not Sources or expected.specification!=self.specification:raise GateError('InvalidPlan')
        if self.snapshot()!=expected:raise GateError('Conflict')
        return expected
