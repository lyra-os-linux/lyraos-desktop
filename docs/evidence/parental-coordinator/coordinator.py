"""Experimental transition gate. No transport, Polkit, NSS mutation or publication.

Callers/adapters are trusted controller objects, never objects from a GUI.
Snapshot digests detect stale plans; they are NOT a monotonic revision protocol.
The caller must serialize coordinator mutations. Root outside it is trusted.
"""
from dataclasses import dataclass
import hashlib
import json

REQUIRED = frozenset({'classification', 'gdm', 'user-manager', 'ssh',
                      'system-units', 'dbus-activation', 'cron'})


class GateError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Plan:
    generation: str
    snapshot: str


def fingerprint(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def classify(identity, protected, ordinary):
    """Trusted fixture rosters only: Unknown never becomes Ordinary.

    This is a policy decision model, not a replacement for a persistent kernel
    classification source. Loss of rosters returns Unknown for everyone.
    """
    keys = ('user', 'uid', 'gid', 'group')
    if (not isinstance(identity, dict) or set(identity) != set(keys) or
            any(type(identity[k]) is not int or identity[k] <= 0 for k in ('uid', 'gid')) or
            any(not isinstance(identity[k], str) or not identity[k] for k in ('user', 'group'))):
        return 'Unknown'
    # Any collision with a protected attribute keeps the protected route.
    matches = [p for p in protected if any(p[k] == identity[k] for k in keys)]
    if matches:
        if len(matches) != 1 or any(matches[0][k] != identity[k] for k in keys):
            return 'Blocked'
        return 'Supervised'
    return 'Ordinary' if identity in ordinary else 'Unknown'


class Coordinator:
    def __init__(self, store, busy_error, adapters):
        self.store = store
        self.busy_error = busy_error
        self.adapters = dict(adapters)

    def plan(self, generation):
        snapshot = self.store.snapshot()
        rows, journals = snapshot
        row = next((r for r in rows if r['generation'] == generation), None)
        if row is None or row['state'] not in {'active', 'transitioning'}:
            raise GateError('RecoveryRequired')
        return Plan(generation, fingerprint(snapshot))

    def block_and_check(self, plan, authorize, revoke=False):
        if type(plan) is not Plan:
            raise GateError('InvalidPlan')
        if fingerprint(self.store.snapshot()) != plan.snapshot:
            raise GateError('Conflict')
        # A real service must resolve peers and Polkit; this injected controller
        # authorization is only for isolated tests. Recheck after a prompt.
        if authorize(plan, revoke) is not True:
            raise GateError('Denied')
        if fingerprint(self.store.snapshot()) != plan.snapshot:
            raise GateError('Conflict')
        try:
            self.store.begin(plan.generation)
        except self.busy_error as error:
            if not str(error).startswith('busy: generation has admitted sessions;'):
                raise GateError('StorageFailure') from error
            # begin has already persisted the barrier/journal before lease Busy.
        try:
            missing = REQUIRED - self.adapters.keys()
            if missing:
                raise GateError('UnsupportedProducer')
            for name in sorted(REQUIRED):
                # Every adapter must confirm current inhibition, not a cache.
                if self.adapters[name].inhibit(plan.generation) is not True:
                    raise GateError('UnsupportedProducer')
            if revoke:
                for name in sorted(REQUIRED):
                    if self.adapters[name].revoke(plan.generation) is not True:
                        raise GateError('Busy')
            for name in sorted(REQUIRED):
                if self.adapters[name].quiescent(plan.generation) is not True:
                    raise GateError('UnverifiedQuiescence')
            # Revalidate after draining, while inhibition remains installed.
            for name in sorted(REQUIRED):
                if self.adapters[name].inhibited(plan.generation) is not True:
                    raise GateError('UnsupportedProducer')
            self.store.begin(plan.generation)  # Exclusive lease check again.
        except GateError:
            raise
        except self.busy_error as error:
            raise GateError('Busy') from error
        except Exception as error:
            raise GateError('AdapterFailure') from error
        # Deliberately no tombstone, publication or Unix mutation method here.
        # Success checks the supplied adapter implementations, not their coverage
        # of a real machine. Synthetic adapters must not be called qualification.
        return 'CheckedWithinAdapterScope'

    def reconcile(self):
        self.store.recover()
        rows, _ = self.store.snapshot()
        if any(r['state'] not in {'active', 'tombstone'} for r in rows):
            return 'BlockedUntilAuthorizedRecovery'
        if any(r['state'] == 'active' for r in rows):
            return 'ExistingAssociationNeedsVerification'
        return 'Tombstoned'
