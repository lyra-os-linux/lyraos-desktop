"""Pinned main-process observation; read-only, no coverage or revocation authority."""
from contextlib import contextmanager
from dataclasses import dataclass
import re
from coordinator import GateError
from reference import Reference

@dataclass(frozen=True)
class Observation:
    pid: int
    start_ticks: int
    uids: tuple
    gids: tuple
    groups: tuple
    capabilities: tuple
    executable: tuple
    argv: tuple
    cgroup: str


def runtime(rows, canonical):
    if type(rows) is not dict or set(rows) != {'MainPID', 'ControlGroup'}:
        raise GateError('UnverifiedRuntime')
    for name, signature in (('MainPID', 'u'), ('ControlGroup', 's')):
        row = rows[name]
        if type(row) is not dict or set(row) != {'type', 'data'} or row['type'] != signature:
            raise GateError('UnverifiedRuntime')
    pid = rows['MainPID']['data']; group = rows['ControlGroup']['data']
    if type(pid) is not int or not 0 < pid < 2**31:
        raise GateError('UnverifiedRuntime')
    if type(group) is not str or group != '/system.slice/' + canonical:
        raise GateError('UnsupportedRuntime')
    return pid, '0::' + group


def validate(reference, row, pid, cgroup):
    if type(row) is not Observation or row.pid != pid or type(row.pid) is not int or type(row.start_ticks) is not int or row.start_ticks <= 0:
        raise GateError('UnverifiedRuntime')
    config = reference.configuration
    for values, expected in ((row.uids, (config.identity.uid,)*4), (row.gids, (config.configured_gid,)*4), (row.groups, (config.configured_gid,)), (row.capabilities, (0,)*3)):
        if type(values) is not tuple or any(type(n) is not int for n in values) or values != expected:
            raise GateError('UnsupportedRuntimeCredentials')
    fingerprints = dict(reference.fingerprints)
    stamp = fingerprints.get(config.executable)
    if type(stamp) is not tuple or len(stamp) != 9 or any(type(n) is not int for n in stamp[:8]) or type(stamp[-1]) is not str or not re.fullmatch('[0-9a-f]{64}', stamp[-1]):
        raise GateError('UnverifiedExecutable')
    if type(row.executable) is not tuple or row.executable != (stamp[0], stamp[1], stamp[-1]) or type(row.argv) is not tuple or row.argv != config.argv or row.cgroup != cgroup:
        raise GateError('UnsupportedRuntime')


class Pinned:
    def __init__(self, reference, observation, pin, backend, revalidate):
        self.reference = reference; self.observation = observation
        self._pin = pin; self._backend = backend; self._revalidate = revalidate
        self._closed = False

    def check(self):
        if self._closed:
            raise GateError('InvalidPlan')
        if self._revalidate(self.reference) != self.reference:
            raise GateError('Conflict')
        if self._backend.pid(self._pin) != self.observation.pid or self._backend.exited(self._pin):
            raise GateError('Conflict')
        pid, cgroup = runtime(self._backend.runtime(self.reference.configuration.canonical), self.reference.configuration.canonical)
        row = self._backend.read(self._pin)
        validate(self.reference, row, pid, cgroup)
        if row != self.observation or self._backend.exited(self._pin):
            raise GateError('Conflict')
        if self._revalidate(self.reference) != self.reference:
            raise GateError('Conflict')
        return row


@contextmanager
def capture(reference, backend, revalidate):
    pin = None; result = None
    try:
        if type(reference) is not Reference or revalidate(reference) != reference:
            raise GateError('InvalidPlan')
        pid, cgroup = runtime(backend.runtime(reference.configuration.canonical), reference.configuration.canonical)
        pin = backend.pin(pid)
        if backend.pid(pin) != pid or backend.exited(pin):
            raise GateError('Conflict')
        row = backend.read(pin)
        validate(reference, row, pid, cgroup)
        result = Pinned(reference, row, pin, backend, revalidate)
        result.check()
        yield result
    except (OSError, ValueError, UnicodeError) as e:
        raise GateError('Busy') from e
    finally:
        if result is not None: result._closed = True
        if pin is not None: backend.close(pin)
