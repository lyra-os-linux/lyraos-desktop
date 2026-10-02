"""Experimental closed system-bus catalog; no global discovery/recovery API.

Retirement is persistent, but pending activation races and boot recovery are
not qualified. Never turn this scoped check into whole-account authority.
"""
from dataclasses import dataclass
from coordinator import GateError
import hashlib,os,re,stat,time

@dataclass(frozen=True)
class Route:
    name: str
    digest: str
    unit: str = ''

class RetiredRoutes:
    """Retain exact root-owned definitions under non-activation filenames.

    Exclusive hard-link publication plus unlink preserves the original on
    conflict and never replaces an existing retirement record. Both crash
    intermediates (two names) and absence are checked before claiming a fence.
    A conflicting destination or changed definition requires operator recovery.
    """
    def __init__(self,directory):self.directory=directory
    @staticmethod
    def names(route):
        if type(route) is not Route or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+',route.name) or not re.fullmatch('[0-9a-f]{64}',route.digest):raise GateError('InvalidRoute')
        return route.name+'.service','.lyra-withdrawn-'+route.name
    def _open(self):
        if os.geteuid()!=0:raise GateError('RootRequired')
        fd=os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        s=os.fstat(fd)
        if s.st_uid!=0 or s.st_mode&0o022:os.close(fd);raise GateError('UnsafeRoutes')
        return fd
    @staticmethod
    def _read(fd,name,links):
        try:f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,dir_fd=fd)
        except FileNotFoundError:return None
        try:
            s=os.fstat(f)
            if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o022 or s.st_nlink not in links or s.st_size>8192:raise GateError('UnsafeRoutes')
            data=os.read(f,8193)
            if len(data)>8192:raise GateError('UnsafeRoutes')
            return s.st_dev,s.st_ino,hashlib.sha256(data).hexdigest()
        finally:os.close(f)
    def inspect(self,route):
        fd=self._open()
        try:return self._inspect(fd,route)
        finally:os.close(fd)
    def _inspect(self,fd,route):
        source,dest=self.names(route)
        a=self._read(fd,source,(1,2));b=self._read(fd,dest,(1,2))
        if a is None and b is not None and b[2]==route.digest:
            if os.stat(dest,dir_fd=fd,follow_symlinks=False).st_nlink!=1:raise GateError('UnsafeRoutes')
            return 'retired'
        if a is not None and a[2]==route.digest:
            if b is None:
                if os.stat(source,dir_fd=fd,follow_symlinks=False).st_nlink!=1:raise GateError('UnsafeRoutes')
                return 'active'
            if a==b and os.stat(source,dir_fd=fd,follow_symlinks=False).st_nlink==2:return 'partial'
        raise GateError('UnverifiedProducerCatalog')
    def retire(self,routes):
        fd=self._open()
        try:
            for route in routes:
                state=self._inspect(fd,route)
                if state=='retired':continue
                source,dest=self.names(route)
                if state=='active':os.link(source,dest,src_dir_fd=fd,dst_dir_fd=fd,follow_symlinks=False)
                os.fsync(fd)
                if self._inspect(fd,route)!='partial':raise GateError('UnsafeRoutes')
                os.unlink(source,dir_fd=fd);os.fsync(fd)
                if self._inspect(fd,route)!='retired':raise GateError('UnsafeRoutes')
            return True
        finally:os.close(fd)

class DBusActivation:
    def __init__(self,classification,routes,verify_catalog,retirement,reload,
                 absent_from_bus,stop_payloads,observe,authorize,settle_seconds=25):
        if not 0<=settle_seconds<=30:raise ValueError('unbounded revocation wait')
        self.routes=tuple(routes)
        if not self.routes:raise GateError('UnsupportedProducer')
        for r in self.routes:
            if type(r) is not Route or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+',r.name) or not re.fullmatch('[0-9a-f]{64}',r.digest):raise GateError('InvalidRoute')
            if r.unit and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*\.service',r.unit):raise GateError('InvalidRoute')
        if len({r.name for r in self.routes})!=len(self.routes):raise GateError('InvalidRoute')
        self.classification=classification;self.verify_catalog=verify_catalog;self.retirement=retirement
        self.reload=reload;self.absent_from_bus=absent_from_bus;self.stop_payloads=stop_payloads
        self.observe=observe;self.authorize=authorize;self.settle_seconds=settle_seconds
    def _catalog(self):
        if self.verify_catalog(self.classification.identity,self.routes) is not True:raise GateError('UnverifiedProducerCatalog')
        for r in self.routes:self.retirement.inspect(r)
    def _fenced(self):
        if any(self.retirement.inspect(r)!='retired' for r in self.routes) or self.absent_from_bus(self.routes) is not True:raise GateError('UnverifiedAdmission')
    def _authorize(self,target,action):
        try:allowed=self.authorize(target,action,self.routes)
        except Exception as e:raise GateError('AuthorizationFailure') from e
        if allowed is not True:raise GateError('Denied')
    def inhibit(self,target):
        with self.classification.verified(target):self._catalog()
        self._authorize(target,'inhibit')
        with self.classification.verified(target):
            self._catalog()
            if self.retirement.retire(self.routes) is not True or self.reload() is not True:raise GateError('UnverifiedAdmission')
            self._catalog();self._fenced();return True
    def inhibited(self,target):
        with self.classification.verified(target):self._catalog();self._fenced();return True
    def quiescent(self,target):
        with self.classification.verified(target):
            self._catalog();self._fenced();return self.observe(self.routes) is True
    def revoke(self,target):
        self.inhibited(target);self._authorize(target,'revoke')
        with self.classification.verified(target):
            self._catalog();self._fenced()
            if self.stop_payloads(self.routes) is not True:raise GateError('Busy')
            end=time.monotonic()+self.settle_seconds
            while self.observe(self.routes) is not True:
                if time.monotonic()>=end:raise GateError('UnverifiedQuiescence')
                time.sleep(.1)
            self._catalog();self._fenced();return True
