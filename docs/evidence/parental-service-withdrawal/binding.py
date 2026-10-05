"""Isolated bridge to historical Operations; no production service/Polkit.

Trusted controller serializes bridge calls. Canonical catalog writers cooperate
with its stable lock. Transport/capability/NSS/auth callbacks remain test inputs.
No changes to historical writer, journals, phases or atomic publication.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
import stat


@dataclass(frozen=True)
class Snapshot:
    identity: object
    revision: int
    digest: str


class BoundInventory:
    """Catalog SH -> existing inventory lock -> withdrawal lock (Operations).

    Bind catalog/generation to the existing persisted inventory_digest. This is
    a lab composition, not a global revision authority or coverage certificate.
    """
    def __init__(self, model, planner, inventory):
        self.model = model
        self.planner = planner
        self.source = inventory
        self.scope = ContextVar('parental_withdrawal_scope', default=None)

    @contextmanager
    def request(self, sender, association, caller_uid, catalog_digest=None):
        token = self.scope.set((sender, association, caller_uid, catalog_digest))
        try:
            yield
        finally:
            self.scope.reset(token)

    def guard(self):
        scope = self.scope.get()
        self.model.require(scope is not None, 'Denied')
        sender, association, uid, _ = scope
        self.model.require(self.planner._caller(sender, association) == uid, 'Denied')
        return scope

    @contextmanager
    def locked(self, uid):
        c = self.model
        self.guard()
        reader = self.planner.reader
        dfd = lock = -1
        try:
            dfd = os.open(reader.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            ds = os.fstat(dfd)
            c.require(ds.st_uid == reader.owner and not ds.st_mode & 0o077, 'UnsafeCatalog')
            lock = os.open('catalog.lock', os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=dfd)
            ls = os.fstat(lock)
            c.require(stat.S_ISREG(ls.st_mode) and ls.st_uid == reader.owner and
                      stat.S_IMODE(ls.st_mode) == 0o600 and ls.st_nlink == 1, 'UnsafeCatalog')
            try:
                fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise c.Error('Busy') from exc
            catalog = reader.snapshot()
            current = os.stat('catalog.lock', dir_fd=dfd, follow_symlinks=False)
            c.require((current.st_dev, current.st_ino) == (ls.st_dev, ls.st_ino), 'UnsafeCatalog')
            with self.source.locked(uid) as source_fd:
                yield catalog, source_fd
        except FileNotFoundError as exc:
            raise c.Error('RecoveryRequired') from exc
        except OSError as exc:
            raise c.Error('UnsafeCatalog') from exc
        finally:
            for fd in (lock, dfd):
                if fd >= 0:
                    os.close(fd)

    def account(self, catalog, uid):
        c = self.model
        _, association, _, expected = self.guard()
        if expected is not None:
            c.require(catalog.digest == expected, 'Conflict')
        account = next((a for a in catalog.accounts if a.association == association), None)
        c.require(account is not None and account.identity.uid == uid, 'Conflict')
        c.require(account.kind == 'ordinary', 'UnsupportedOperation')
        c.classify(catalog, uid, self.planner.observe_identity)
        return account

    def read_locked(self, fd, uid):
        catalog, source_fd = fd
        account = self.account(catalog, uid)
        source = self.source.read_locked(source_fd, uid)
        c = self.model
        observed = c.Identity(**{k: getattr(source.identity, k) for k in ('user', 'uid', 'gid', 'group')})
        c.require(observed == account.identity, 'InvalidIdentity')
        c.require(c.positive(source.revision) and c.matches(c.HASH, source.digest), 'Conflict')
        binding = dict(schema=1, catalog=catalog.digest, association=account.association,
                       generation=account.generation, account_revision=account.revision,
                       inventory_revision=source.revision, inventory_digest=source.digest)
        digest = hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        return Snapshot(observed, source.revision, digest)


class Bridge:
    def __init__(self, model, planner, operations_factory, withdrawal, withdrawal_error, inventory):
        self.model = model
        self.planner = planner
        self.inventory = BoundInventory(model, planner, inventory)
        self.operations = operations_factory(withdrawal, withdrawal_error, self.inventory)
        self._plans = {}
        self._running = set()

    @contextmanager
    def running(self, association):
        self.model.require(association not in self._running, 'Busy')
        self._running.add(association)
        try:
            yield
        finally:
            self._running.remove(association)

    def plan(self, sender, association, expected_revision):
        plan = self.planner.plan(sender, association, expected_revision)
        try:
            with self.inventory.request(sender, association, plan.caller_uid, plan.catalog_digest):
                operation = self.operations.plan(plan.account.identity.uid, plan.identifier)
            self._plans = {k: v for k, v in self._plans.items() if k in self.planner._plans}
            self._plans[plan.identifier] = operation
            return plan
        except Exception:
            self.planner._plans.pop(plan.identifier, None)
            raise

    def execute(self, sender, identifier, authorize):
        plan = self.planner.validate(sender, identifier)
        operation = self._plans.get(identifier)
        self.model.require(operation is not None, 'Denied')
        with self.running(plan.association):
            with self.inventory.request(sender, plan.association, plan.caller_uid, plan.catalog_digest):
                def auth(record):
                    self.planner.validate(sender, identifier)
                    allowed = authorize(dict(action='withdraw-admission', association=plan.association,
                                             generation=plan.generation, revision=plan.revision,
                                             effect=plan.effect, owner=record))
                    if allowed is True:
                        self.planner.validate(sender, identifier)
                    return allowed
                result = self.operations.begin(operation, auth)
            self._plans.pop(identifier, None)
            self.planner._plans.pop(identifier, None)
            return result

    def resume(self, sender, association, operation_id, authorize):
        uid = self.planner._caller(sender, association)  # capability before lookup
        catalog = self.planner.reader.snapshot()
        account = next((a for a in catalog.accounts if a.association == association), None)
        self.model.require(account is not None, 'RecoveryRequired')
        with self.running(association):
            with self.inventory.request(sender, association, uid, catalog.digest):
                def auth(record):
                    self.inventory.guard()
                    allowed = authorize(dict(action='withdraw-admission', association=association,
                                             generation=account.generation, revision=account.revision,
                                             effect='deny-new-admission-only', owner=record))
                    if allowed is True:
                        self.inventory.guard()
                    return allowed
                return self.operations.resume(account.identity.uid, operation_id, auth)

    def inspect_admission(self, sender, association):
        """Lab diagnostic; negative canonical ledger overrides positive catalog."""
        uid = self.planner._caller(sender, association)
        catalog = self.planner.reader.snapshot()
        account = next((a for a in catalog.accounts if a.association == association), None)
        self.model.require(account is not None, 'RecoveryRequired')
        with self.inventory.request(sender, association, uid, catalog.digest):
            with self.inventory.locked(account.identity.uid) as inv:
                self.inventory.read_locked(inv, account.identity.uid)
                w = self.operations.withdrawal
                with w.lock(account.identity.uid, False) as (fd, names):
                    proof, marker, journal = w.snapshot(fd, names)
                    owner = w.read(fd, self.operations.name(account.identity.uid))
                    self.model.require(marker is None and journal is None and owner is None, 'Blocked')
                    self.model.require(proof is not None, 'RecoveryRequired')
                    decoded = w.decode_proof(proof, account.identity.uid)
                    self.model.require(self.model.identity(decoded) == account.identity, 'InvalidIdentity')
                    return 'OrdinaryEligible'
