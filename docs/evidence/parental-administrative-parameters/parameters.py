"""Typed sealed laboratory parameters. No GUI secrets or production ABI."""
from dataclasses import dataclass
import hashlib
import json


@dataclass(frozen=True)
class Parameters:
    full_name: str
    groups: tuple
    is_admin: bool

    def public(self):
        return dict(full_name=self.full_name, groups=[dict(name=n, gid=g) for n, g in self.groups],
                    is_admin=self.is_admin)

    def digest(self):
        return hashlib.sha256(json.dumps(self.public(), sort_keys=True,
                                        separators=(',', ':')).encode()).hexdigest()


def parse(model, method, values, resolve_group):
    require = model.require
    require(type(values) is dict, 'InvalidParameters')
    if set(values) & {'password', 'photo'}:
        raise model.Error('UnsupportedOperation')
    require(type(method) is str and method in ('UpdateUser', 'SetAdmin'), 'UnsupportedOperation')
    require(set(values) == ({'is_admin'} if method == 'SetAdmin' else {'full_name', 'groups', 'is_admin'}),
            'InvalidParameters')
    require(type(values['is_admin']) is bool, 'InvalidParameters')
    admin = values['is_admin']
    name = ''
    if method == 'UpdateUser':
        name = values['full_name']
        require(type(name) is str and bool(name.strip()) and len(name) <= 128 and
                not any(ord(ch) < 32 or ord(ch) == 127 or ch == ':' for ch in name), 'InvalidParameters')
        groups = values['groups']
        require(type(groups) is list and len(groups) <= 64 and
                all(model.matches(model.NAME, g) for g in groups), 'InvalidParameters')
        require(len(set(groups)) == len(groups), 'InvalidParameters')
        require(admin or 'wheel' not in groups, 'InvalidParameters')
        groups = set(groups)
        if admin:
            groups.add('wheel')
    else:
        groups = {'wheel'}  # typed add/remove of wheel, not replacement of all groups
    require(len(groups) <= 64, 'InvalidParameters')
    pairs = []
    for group in sorted(groups):
        try:
            gid = resolve_group(group)
        except Exception as exc:
            raise model.Error('InvalidParameters') from exc
        require(type(gid) is int and 0 < gid < 2**32-1, 'InvalidParameters')
        pairs.append((group, gid))
    return Parameters(name, tuple(pairs), admin)


def revalidate(model, params, resolve_group):
    for name, expected in params.groups:
        try:
            observed = resolve_group(name)
        except Exception as exc:
            raise model.Error('Conflict') from exc
        model.require(type(observed) is int and observed == expected, 'Conflict')


@dataclass(frozen=True)
class Plan:
    base: object
    parameters: Parameters
    parameter_digest: str


class SealedGuard:
    def __init__(self, base_guard, resolve_group):
        self.base = base_guard
        self.model = base_guard.model
        self.resolve_group = resolve_group
        self._plans = {}

    def plan(self, sender, association, revision, method, values):
        # Capability precedes group/catalog lookups, even for invalid targets.
        self.base.planner._caller(sender, association)
        params = parse(self.model, method, values, self.resolve_group)
        base = self.base.plan(sender, association, revision, method)
        plan = Plan(base, params, params.digest())
        self._plans = {k: v for k, v in self._plans.items() if k in self.base._plans}
        self._plans[base.admission.identifier] = plan
        return plan

    def execute(self, sender, identifier, authorize, adapter):
        plan = self._plans.get(identifier)
        self.model.require(plan is not None, 'Denied')
        # Parent validates sender/capability/identity before invoking callbacks.
        def auth(payload):
            revalidate(self.model, plan.parameters, self.resolve_group)
            payload['parameters'] = plan.parameters.public()
            payload['parameter_digest'] = plan.parameter_digest
            allowed = authorize(payload)
            if allowed is True:
                revalidate(self.model, plan.parameters, self.resolve_group)
            return allowed

        def effect(method, account):
            self.model.require(method == plan.base.method and
                               account == plan.base.admission.account and
                               plan.parameters.digest() == plan.parameter_digest, 'Conflict')
            revalidate(self.model, plan.parameters, self.resolve_group)
            adapter(method, account, plan.parameters)
        try:
            return self.base.execute(sender, identifier, auth, effect)
        finally:
            if identifier not in self.base._plans:
                self._plans.pop(identifier, None)


def command(model, method, account, params):
    """Build a fixed argv, never execute it. Account comes from server catalog."""
    model.require(type(params) is Parameters, 'InvalidParameters')
    model.require(model.matches(model.NAME, account.identity.user), 'InvalidIdentity')
    values = dict(is_admin=params.is_admin)
    if method == 'UpdateUser':
        values.update(full_name=params.full_name, groups=[n for n, _ in params.groups])
    parsed = parse(model, method, values, lambda n: dict(params.groups).get(n))
    model.require(parsed == params, 'InvalidParameters')
    if method == 'UpdateUser':
        return ('/usr/sbin/usermod', '-c', params.full_name, '-G',
                ','.join(n for n, _ in params.groups), '--', account.identity.user)
    if params.is_admin:
        return ('/usr/sbin/usermod', '-aG', 'wheel', '--', account.identity.user)
    return ('/usr/bin/gpasswd', '-d', account.identity.user, 'wheel')
