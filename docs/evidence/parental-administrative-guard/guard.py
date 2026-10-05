"""Isolated administrative dispatch guard. No Unix commands or product hook.

Controller serializes calls and supplies a trusted typed effect adapter.
Create/remove and supervised mutation have no lifecycle implementation here.
Successful dispatch does not certify producer quiescence or product enrollment.
"""
from contextlib import contextmanager
from dataclasses import dataclass

SUPPORTED = frozenset({'UpdateUser', 'SetAdmin'})


@dataclass(frozen=True)
class Plan:
    admission: object
    method: str
    inventory_digest: str
    ledger_digest: str


class Guard:
    def __init__(self, bridge):
        self.bridge = bridge
        self.model = bridge.model
        self.planner = bridge.planner
        self.inventory = bridge.inventory
        self._plans = {}

    @contextmanager
    def _held(self, admission, exclusive):
        c = self.model
        uid = admission.account.identity.uid
        with self.inventory.request(admission.sender, admission.association,
                                    admission.caller_uid, admission.catalog_digest):
            with self.inventory.locked(uid) as inv:
                snapshot = self.inventory.read_locked(inv, uid)
                w = self.bridge.operations.withdrawal
                with w.lock(uid, exclusive) as (fd, names):
                    proof, marker, journal = w.snapshot(fd, names)
                    owner = w.read(fd, self.bridge.operations.name(uid))
                    c.require(marker is None and journal is None and owner is None, 'Blocked')
                    c.require(proof is not None, 'RecoveryRequired')
                    identity = c.identity(w.decode_proof(proof, uid))
                    c.require(identity == admission.account.identity, 'InvalidIdentity')
                    c.require(self.planner._now() < admission.expires, 'Conflict')
                    self.inventory.guard()
                    yield snapshot.digest, w.fingerprint([proof, marker, journal, owner])

    def plan(self, sender, association, expected_revision, method):
        # Closed operation set. No broad removal/userdel compensation path.
        self.model.require(type(method) is str and method in SUPPORTED, 'UnsupportedOperation')
        admission = self.planner.plan(sender, association, expected_revision)
        try:
            with self._held(admission, False) as (inventory, ledger):
                plan = Plan(admission, method, inventory, ledger)
            self._plans = {k: v for k, v in self._plans.items() if k in self.planner._plans}
            self._plans[admission.identifier] = plan
            return plan
        except Exception:
            self.planner._plans.pop(admission.identifier, None)
            raise

    def _check(self, plan, state):
        self.model.require(state == (plan.inventory_digest, plan.ledger_digest), 'Conflict')

    def execute(self, sender, identifier, authorize, effect):
        admission = self.planner.validate(sender, identifier)
        plan = self._plans.get(identifier)
        self.model.require(plan is not None and plan.admission == admission, 'Denied')
        with self.bridge.running(admission.association):
            with self._held(admission, False) as state:
                self._check(plan, state)
            # All leases are released during interaction. Payload is detached,
            # contains no password/photo/free-form usermod arguments.
            request = dict(method=plan.method, association=admission.association,
                           generation=admission.generation, revision=admission.revision,
                           target=dict(user=admission.account.identity.user,
                                       uid=admission.account.identity.uid))
            try:
                allowed = authorize(request)
            except Exception as exc:
                raise self.model.Error('AuthorizationFailure') from exc
            self.model.require(allowed is True, 'Denied')
            self.planner.validate(sender, identifier)
            with self._held(admission, True) as state:
                self._check(plan, state)
                # EX withdrawal lease stays held across trusted dispatch; a
                # cooperative withdrawal cannot publish a marker in this gap.
                # The adapter MUST preserve the account's identity tuple and
                # must perform its own typed input validation and authorization.
                # Consume before dispatch, including on adapter failure: the
                # same plan must not repeat a possibly partial effect.
                self._plans.pop(identifier, None)
                self.planner._plans.pop(identifier, None)
                effect(plan.method, admission.account)
                observed = self.planner.observe_identity(admission.account.identity.uid)
                self.model.require(type(observed) is self.model.Identity and
                                   observed == admission.account.identity, 'InvalidIdentity')
            return 'OrdinaryMutationDispatched'
