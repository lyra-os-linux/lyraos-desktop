"""Experimental ordinary-withdrawal adapters; only systemd-user admission scope.

Root-selected dependencies, identity and PAM installation are trusted inputs.
There is no publication, NSS mutation, or ordinary-role reactivation operation.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from coordinator import GateError
from withdrawal import decode

@dataclass(frozen=True)
class Identity:
    user: str
    uid: int
    gid: int
    group: str

class Classification:
    def __init__(self, storage, identity, verify_identity, verify_installation):
        self.storage = storage
        self.identity = identity
        self.verify_identity = verify_identity
        self.verify_installation = verify_installation

    def _verify(self, target, dfd, names):
        if type(target.uid) is not int or target.uid <= 0 or target.uid != self.identity.uid:
            raise GateError('InvalidIdentity')
        if self.verify_identity(self.identity) is not True:
            raise GateError('InvalidIdentity')
        if self.verify_installation() is not True:
            raise GateError('UnverifiedAdmission')
        marker = self.storage.read(dfd, names[1])
        journal = self.storage.read(dfd, names[2])
        if marker is None or journal is None:
            raise GateError('UnverifiedClassification')
        m, j = decode(marker), decode(journal)
        expected = (target.uid, target.operation, target.proof_hash)
        if any((row['uid'], row['operation'], row['proof_hash']) != expected for row in (m, j)):
            raise GateError('Conflict')
        if (m['phase'], m['revision'], j['phase'], j['revision']) != ('blocked', 1, 'retired', 2):
            raise GateError('RecoveryRequired')
        if self.storage.read(dfd, names[0]) is not None:
            raise GateError('UnverifiedClassification')

    @contextmanager
    def verified(self, target):
        if type(target.uid) is not int or target.uid <= 0 or target.uid != self.identity.uid:
            raise GateError('InvalidIdentity')
        try:
            with self.storage.lock(target.uid, False) as (dfd, names):
                self._verify(target, dfd, names)
                yield
                self._verify(target, dfd, names)
        except GateError:
            raise
        except Exception as error:
            raise GateError('UnverifiedClassification') from error

    def inhibited(self, target):
        with self.verified(target):
            return True

    inhibit = inhibited
    quiescent = inhibited  # classification snapshot only, never process quiescence
    revoke = inhibited     # has no process effects

class UserManager:
    def __init__(self, classification, execute, observe, authorize_revocation):
        self.classification = classification
        self.execute = execute
        self.observe = observe
        self.authorize_revocation = authorize_revocation

    def inhibited(self, target):
        return self.classification.inhibited(target)

    inhibit = inhibited

    def quiescent(self, target):
        with self.classification.verified(target):
            return self.observe(target.uid) is True

    def revoke(self, target):
        # Authorize before taking a snapshot lock; revalidate after the callback.
        self.classification.inhibited(target)
        try:
            allowed = self.authorize_revocation(target)
        except Exception as error:
            raise GateError('AuthorizationFailure') from error
        if allowed is not True:
            raise GateError('Denied')
        with self.classification.verified(target):
            uid = self.classification.identity.uid
            # terminate-user can fail when logind already has no user object.
            result = self.execute(['loginctl', 'terminate-user', str(uid)])
            if result['rc'] != 0 and self.observe(uid) is not True:
                raise GateError('Busy')
            for unit in (f'user@{uid}.service', f'user-runtime-dir@{uid}.service'):
                if self.execute(['systemctl', 'stop', unit])['rc'] != 0:
                    raise GateError('Busy')
            if self.observe(uid) is not True:
                raise GateError('UnverifiedQuiescence')
            return True
