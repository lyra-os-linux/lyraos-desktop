"""Experimental ordinary withdrawal composed with mandatory producer gates.

No Unix mutation, enrollment, publication or removal of negative authority.
Adapters and authorization are trusted test objects, never client objects.
"""
from dataclasses import dataclass
from coordinator import REQUIRED,GateError

@dataclass(frozen=True)
class Target:
    uid:int
    operation:str
    proof_hash:str

class OrdinaryCoordinator:
    def __init__(self,withdrawal,withdrawal_error,adapters):
        self.withdrawal=withdrawal;self.withdrawal_error=withdrawal_error
        self.adapters=dict(adapters)
    def _storage(self,action):
        try:return action()
        except GateError:raise
        except self.withdrawal_error as e:
            code=str(e)
            if code not in {'Denied','Conflict','Busy','Unknown','RecoveryRequired','InvalidPlan','InvalidOperation','InvalidIdentity'}:
                code='StorageFailure'
            raise GateError(code) from e
        except Exception as e:raise GateError('StorageFailure') from e
    @staticmethod
    def _authorize(authorize,payload,revoke):
        try:return authorize(payload,revoke)
        except Exception as e:raise GateError('AuthorizationFailure') from e
    def plan(self,uid,operation):return self._storage(lambda:self.withdrawal.plan(uid,operation))
    def block_and_check(self,plan,authorize,revoke=False):
        self._storage(lambda:self.withdrawal.begin(plan,lambda p:self._authorize(authorize,p,revoke)))
        return self._check(Target(plan.uid,plan.operation,plan.proof_hash),revoke)
    def resume_and_check(self,uid,operation,authorize,revoke=False):
        verified=[]
        def grant(row):
            target=Target(row['uid'],row['operation'],row['proof_hash'])
            result=self._authorize(authorize,dict(row),revoke)
            if result is True:verified.append(target)
            return result
        self._storage(lambda:self.withdrawal.resume(uid,operation,grant))
        if len(verified)!=1:raise GateError('Denied')
        return self._check(verified[0],revoke)
    def state(self,uid):return self._storage(lambda:self.withdrawal.inspect(uid))
    def _blocked(self,target):
        if self.state(target.uid)!='BlockedUntilAuthorizedRecovery':raise GateError('UnverifiedClassification')
    def _check(self,target,revoke):
        self._blocked(target)
        if REQUIRED-self.adapters.keys():raise GateError('UnsupportedProducer')
        try:
            for name in sorted(REQUIRED):
                if self.adapters[name].inhibit(target) is not True:raise GateError('UnsupportedProducer')
            if revoke:
                for name in sorted(REQUIRED):
                    if self.adapters[name].revoke(target) is not True:raise GateError('Busy')
            for name in sorted(REQUIRED):
                if self.adapters[name].quiescent(target) is not True:raise GateError('UnverifiedQuiescence')
            for name in sorted(REQUIRED):
                if self.adapters[name].inhibited(target) is not True:raise GateError('UnsupportedProducer')
        except GateError:raise
        except Exception as e:raise GateError('AdapterFailure') from e
        self._blocked(target)
        # Callback scope only. This result NEVER permits Unix mutation/publication.
        return 'CheckedWithinAdapterScope'
