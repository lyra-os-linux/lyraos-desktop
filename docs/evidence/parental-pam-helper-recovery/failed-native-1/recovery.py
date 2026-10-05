"""Same-boot, in-memory recovery of a helper captured with its live parent.

Experimental closed-profile model. Never capture a fresh orphan or relax PAM
admission. Existing Effects/StopJobs own durable intent and drain completion.
"""
from contextlib import contextmanager
import re
from coordinator import GateError
from pam import PamExecution
from jobs import StopJobs


class RetainedHelper:
    def __init__(self, execution, boot_id):
        if type(execution) is not PamExecution or execution.helpers is None or len(execution.refs) != 1:
            raise GateError('InvalidPlan')
        execution.check()
        self.execution = execution
        self.unit = next(iter(execution.refs))
        self.reference = execution.refs[self.unit].execution
        self.main = execution.guard._pins[self.unit]
        self.helper, self.observation, self.parent = execution.helpers[self.unit]
        self.boot_id = boot_id
        self.boot = boot_id()
        if type(self.boot) is not str or not re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', self.boot):
            raise GateError('UnverifiedBoot')
        self.closed = False
        execution.check()
        if boot_id() != self.boot:
            raise GateError('Conflict')

    def check(self):
        """Allow only the original live helper or its observed complete exit."""
        x = self.execution
        if self.closed or self.main._closed or x.helpers is None:
            raise GateError('InvalidPlan')
        if self.boot_id() != self.boot:
            raise GateError('RecoveryRequired')
        x.guard._fences()
        if x.sources(self.reference) != self.reference:
            raise GateError('Conflict')
        b = x.backend
        if not b.exited(self.main._pin):
            raise GateError('UnverifiedRuntime')
        rows = b.runtime(self.unit)
        if rows != {'MainPID': {'type': 'u', 'data': 0}, 'ControlGroup': {'type': 's', 'data': '/system.slice/' + self.unit}} or type(rows['MainPID']['data']) is not int:
            raise GateError('UnverifiedRuntime')
        members = x.members(self.unit)
        if type(members) is not tuple or any(type(p) is not int or p <= 0 for p in members):
            raise GateError('UnverifiedRuntime')
        if b.exited(self.helper):
            if members != ():
                raise GateError('Conflict')
        else:
            # Parent=1 is accepted only with both historical pidfds retained.
            # This is not an entry point for independently discovered orphans.
            if members != (self.observation.pid,) or b.pid(self.helper) != self.observation.pid or type(b.parent(self.helper)) is not int or b.parent(self.helper) != 1:
                raise GateError('Conflict')
            if b.read(self.helper) != self.observation or b.exited(self.helper):
                raise GateError('Conflict')
        if x.sources(self.reference) != self.reference:
            raise GateError('Conflict')
        x.guard._fences()
        if self.boot_id() != self.boot:
            raise GateError('RecoveryRequired')
        return True

    def recover(self, effects, backend, authorize, settle_seconds=0):
        self.check()
        if set(effects.routes) != {self.unit} or effects.boot_id() != self.boot:
            raise GateError('InvalidPlan')
        before = effects.read(self.unit)  # Validates the retired owner/catalog.
        if before is None and self.execution.backend.exited(self.helper):
            raise GateError('UnverifiedRuntime')  # No invented stop completion.
        try:
            allowed = authorize(dict(unit=self.unit, uid=effects.target.uid,
                                     operation=effects.target.operation,
                                     action='recover-pam-helper'))
        except Exception as error:
            raise GateError('AuthorizationFailure') from error
        if allowed is not True:
            raise GateError('Denied')
        self.check()
        if effects.read(self.unit) != before:
            raise GateError('Conflict')
        if before is None and self.execution.backend.exited(self.helper):
            raise GateError('UnverifiedRuntime')
        jobs = StopJobs(effects, RecoveryBackend(self, backend), self.check, settle_seconds)
        if before is not None:
            # Fresh authorization already happened outside journal locks.
            return jobs.reconcile(self.unit, lambda row: True)
        return jobs(['systemctl', 'stop', self.unit])


@contextmanager
def retain(execution, boot_id):
    with execution.batch():
        origin = RetainedHelper(execution, boot_id)
        try:
            yield origin
        finally:
            origin.closed = True


class RecoveryBackend:
    """Require retained pidfds as well as the backend's cgroup/job drain proof."""
    def __init__(self, origin, backend):
        self.origin = origin
        self.backend = backend

    def request(self, unit):
        if unit != self.origin.unit:
            raise GateError('UnsupportedProducer')
        self.origin.check()
        return self.backend.request(unit)

    def drained(self, unit):
        if unit != self.origin.unit:
            raise GateError('UnsupportedProducer')
        self.origin.check()
        b = self.origin.execution.backend
        if not b.exited(self.origin.main._pin) or not b.exited(self.origin.helper):
            return False
        if self.backend.drained(unit) is not True:
            return False
        self.origin.check()
        return True
