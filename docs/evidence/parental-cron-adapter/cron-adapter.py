"""Closed registered cron scope fenced by already installed account admission.

No crontab deletion or shared daemon restart. Root-selected callbacks bind the
actual PAM route/catalog and trusted payloads; no generic command-tree claim.
"""
from dataclasses import dataclass
from coordinator import GateError
import re,time

@dataclass(frozen=True)
class Job:
    name: str
    kind: str
    digest: str

class Cron:
    def __init__(self,classification,jobs,verify_catalog,verify_admission,
                 stop_payloads,observe,authorize,settle_seconds=25):
        if not 0<=settle_seconds<=30:raise ValueError('unbounded revocation wait')
        self.jobs=tuple(jobs)
        if not self.jobs:raise GateError('UnsupportedProducer')
        for j in self.jobs:
            if type(j) is not Job or j.kind not in ('user','system') or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',j.name) or not re.fullmatch('[0-9a-f]{64}',j.digest):raise GateError('InvalidJob')
        if len({(j.kind,j.name) for j in self.jobs})!=len(self.jobs):raise GateError('InvalidJob')
        self.classification=classification;self.verify_catalog=verify_catalog;self.verify_admission=verify_admission
        self.stop_payloads=stop_payloads;self.observe=observe;self.authorize=authorize;self.settle_seconds=settle_seconds
    def _verified(self):
        if self.verify_catalog(self.classification.identity,self.jobs) is not True:raise GateError('UnverifiedProducerCatalog')
        if self.verify_admission(self.classification.identity,self.jobs) is not True:raise GateError('UnverifiedAdmission')
    def inhibit(self,target):
        # Negative authority was persisted by withdrawal; guard was installed
        # before baseline. This method verifies the fence, never installs it late.
        with self.classification.verified(target):self._verified();return True
    inhibited=inhibit
    def quiescent(self,target):
        with self.classification.verified(target):self._verified();return self.observe(self.jobs) is True
    def revoke(self,target):
        self.inhibited(target)
        try:allowed=self.authorize(target,self.jobs)
        except Exception as e:raise GateError('AuthorizationFailure') from e
        if allowed is not True:raise GateError('Denied')
        with self.classification.verified(target):
            self._verified()
            if self.stop_payloads(self.classification.identity,self.jobs) is not True:raise GateError('Busy')
            end=time.monotonic()+self.settle_seconds
            while self.observe(self.jobs) is not True:
                if time.monotonic()>=end:raise GateError('UnverifiedQuiescence')
                time.sleep(.1)
            self._verified();return True
