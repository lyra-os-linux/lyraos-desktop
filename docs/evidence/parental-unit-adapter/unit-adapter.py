"""Registered system-unit inhibition/revocation, experimental root authority.

No general unit discovery, enrollment, unmasking, or account mutation API.
Persistent masks fence only a root-selected, verified closed unit catalog.
"""
from dataclasses import dataclass
from coordinator import GateError
import os,re,stat,time

@dataclass(frozen=True)
class Unit:
    name: str
    kind: str
    service: str = ''

class Masks:
    def __init__(self, directory):
        self.directory=directory
    def _open(self):
        if os.geteuid()!=0:raise GateError('RootRequired')
        fd=os.open(self.directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        s=os.fstat(fd)
        if s.st_uid!=0 or s.st_mode&0o022:os.close(fd);raise GateError('UnsafeMasks')
        return fd
    @staticmethod
    def _name(name):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*\.(service|timer)',name):
            raise GateError('InvalidUnit')
    @staticmethod
    def _masked(fd,name):
        try:s=os.stat(name,dir_fd=fd,follow_symlinks=False)
        except FileNotFoundError:return False
        return stat.S_ISLNK(s.st_mode) and s.st_uid==0 and s.st_nlink==1 and os.readlink(name,dir_fd=fd)=='/dev/null'
    def masked(self,name):
        self._name(name);fd=self._open()
        try:return self._masked(fd,name)
        finally:os.close(fd)
    def install(self,names):
        fd=self._open()
        try:
            for name in names:
                self._name(name)
                try:os.symlink('/dev/null',name,dir_fd=fd)
                except FileExistsError:
                    if not self._masked(fd,name):raise GateError('UnsafeMasks')
                os.fsync(fd)
                if not self._masked(fd,name):raise GateError('UnsafeMasks')
            return True
        finally:os.close(fd)

class SystemUnits:
    def __init__(self, classification, units, verify_catalog, masks, execute,
                 loaded_masked, observe, authorize, settle_seconds=25):
        if not 0<=settle_seconds<=30:raise ValueError('unbounded revocation wait')
        self.units=tuple(units)
        if not self.units or any(type(u) is not Unit for u in self.units):raise GateError('UnsupportedProducer')
        if len({u.name for u in self.units})!=len(self.units):raise GateError('InvalidUnit')
        services={u.name for u in self.units if u.kind=='service'}
        if not services:raise GateError('UnsupportedProducer')
        for u in self.units:
            Masks._name(u.name)
            if u.kind not in ('service','timer') or not u.name.endswith('.'+u.kind):raise GateError('InvalidUnit')
            if u.kind=='timer' and u.service not in services:raise GateError('UnsupportedProducer')
            if u.kind=='service' and u.service:raise GateError('InvalidUnit')
        self.classification=classification;self.verify_catalog=verify_catalog;self.masks=masks
        self.execute=execute;self.loaded_masked=loaded_masked;self.observe=observe
        self.authorize=authorize;self.settle_seconds=settle_seconds
    def _catalog(self):
        if self.verify_catalog(self.classification.identity,self.units) is not True:
            raise GateError('UnverifiedProducerCatalog')
    def _masks(self):
        if not all(self.masks.masked(u.name) is True and self.loaded_masked(u.name) is True for u in self.units):
            raise GateError('UnverifiedAdmission')
    def _authorize(self,target,action):
        try:allowed=self.authorize(target,action,self.units)
        except Exception as error:raise GateError('AuthorizationFailure') from error
        if allowed is not True:raise GateError('Denied')
    def inhibit(self,target):
        with self.classification.verified(target):self._catalog()
        self._authorize(target,'inhibit')
        with self.classification.verified(target):
            self._catalog()
            # A partial failure keeps installed masks and negative authority.
            if self.masks.install(tuple(u.name for u in self.units)) is not True:raise GateError('UnverifiedAdmission')
            if self.execute(['systemctl','daemon-reload'])['rc']!=0:raise GateError('UnverifiedAdmission')
            self._catalog();self._masks()
            return True
    def inhibited(self,target):
        with self.classification.verified(target):self._catalog();self._masks();return True
    def quiescent(self,target):
        with self.classification.verified(target):
            self._catalog();self._masks()
            return self.observe(self.units) is True
    def revoke(self,target):
        self.inhibited(target)
        self._authorize(target,'revoke')
        with self.classification.verified(target):
            self._catalog();self._masks()
            for kind in ('timer','service'):
                for unit in self.units:
                    if unit.kind==kind and self.execute(['systemctl','stop',unit.name])['rc']!=0:
                        raise GateError('Busy')
            end=time.monotonic()+self.settle_seconds
            while self.observe(self.units) is not True:
                if time.monotonic()>=end:raise GateError('UnverifiedQuiescence')
                time.sleep(.1)
            self._catalog();self._masks()
            return True
