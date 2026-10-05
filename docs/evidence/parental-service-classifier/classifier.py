"""Read-only laboratory catalog and server-owned planning. No production API.

Trusted controller supplies transport/capability/NSS/adapter observations.
Local revisions and digests detect conflicts, not rollback. No writer, enrollment,
PAM installation, Polkit, Unix mutation, or certificate of producer coverage.
"""
from dataclasses import dataclass
import fcntl
import hashlib
import json
import math
import os
import re
import secrets
import stat

LIMIT = 65536
NAME = re.compile(r'[a-z_][a-z0-9_-]{0,62}\Z')
TOKEN = re.compile(r'[0-9a-f]{32}\Z')
HASH = re.compile(r'[0-9a-f]{64}\Z')
STATES = {'active', 'provisioning', 'transitioning', 'recovering', 'tombstone'}


class Error(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code='InvalidCatalog'):
    if not condition:
        raise Error(code)


def positive(value):
    return type(value) is int and 0 < value < 2**63


def matches(pattern, value):
    return type(value) is str and pattern.fullmatch(value) is not None


@dataclass(frozen=True)
class Identity:
    user: str
    uid: int
    gid: int
    group: str


def identity(row):
    require(type(row) is dict and set(row) == {'user', 'uid', 'gid', 'group'})
    require(all(type(row[k]) is int and 0 < row[k] < 2**32-1 for k in ('uid', 'gid')))
    require(all(matches(NAME, row[k]) for k in ('user', 'group')))
    return Identity(**row)


@dataclass(frozen=True)
class Account:
    association: str
    generation: str
    identity: Identity
    revision: int
    kind: str
    state: str
    operation: str
    barrier: bool
    policy: str
    adapters: tuple


@dataclass(frozen=True)
class Catalog:
    revision: int
    accounts: tuple
    digest: str


def decode(data):
    """Strict bounded schema; all returned values deeply immutable."""
    require(type(data) is bytes and 0 < len(data) <= LIMIT)

    def unique(pairs):
        row = {}
        for key, value in pairs:
            require(key not in row)
            row[key] = value
        return row

    try:
        row = json.loads(data.decode('utf-8'), object_pairs_hook=unique,
                         parse_constant=lambda _: require(False))
        require(type(row) is dict and set(row) == {'schema', 'revision', 'accounts'})
        require(type(row['schema']) is int and row['schema'] == 1 and positive(row['revision']))
        require(type(row['accounts']) is list and len(row['accounts']) <= 128)
        accounts = []
        for item in row['accounts']:
            require(type(item) is dict and set(item) == {
                'association', 'generation', 'identity', 'revision', 'kind',
                'state', 'operation', 'barrier', 'policy', 'adapters'})
            require(matches(TOKEN, item['association']) and matches(TOKEN, item['generation']))
            require(positive(item['revision']) and item['revision'] <= row['revision'])
            require(type(item['kind']) is str and item['kind'] in ('ordinary', 'supervised'))
            require(type(item['state']) is str and item['state'] in STATES)
            require(type(item['operation']) is str and
                    (item['operation'] == '' or matches(TOKEN, item['operation'])))
            require(type(item['barrier']) is bool and type(item['adapters']) is dict)
            require(len(item['adapters']) <= 32)
            require(all(matches(NAME, k) and matches(HASH, v)
                        for k, v in item['adapters'].items()))
            if item['kind'] == 'ordinary':
                require(item['policy'] == '' and not item['adapters'])
            else:
                require(matches(HASH, item['policy']) and bool(item['adapters']))
            if item['state'] == 'active' and not item['barrier']:
                require(item['operation'] == '')
            else:
                require(matches(TOKEN, item['operation']))
            accounts.append(Account(item['association'], item['generation'],
                                    identity(item['identity']), item['revision'],
                                    item['kind'], item['state'], item['operation'],
                                    item['barrier'], item['policy'],
                                    tuple(sorted(item['adapters'].items()))))
        # Conflicting ownership anywhere invalidates this closed lab catalog.
        # Tombstone/UID reuse is deliberately unsupported, never deduplicated.
        for key in (lambda a: a.association, lambda a: a.generation,
                    lambda a: a.identity.uid, lambda a: a.identity.user):
            require(len({key(a) for a in accounts}) == len(accounts))
        canonical = json.dumps(row, sort_keys=True, separators=(',', ':')).encode()
        return Catalog(row['revision'], tuple(accounts), hashlib.sha256(canonical).hexdigest())
    except Error:
        raise
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
        raise Error('InvalidCatalog') from exc


class Reader:
    """Read only canonical catalog under pre-existing stable SH lock.

    Directory's ancestry is trusted by the laboratory controller. Writers must
    take EX on the same inode; this reader cannot certify a noncooperating root.
    owner defaults to root; explicit other owner is only for unprivileged tests.
    """
    def __init__(self, directory, owner=0):
        self.directory = directory
        self.owner = owner

    def snapshot(self):
        dfd = lock = fd = -1
        try:
            dfd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            ds = os.fstat(dfd)
            require(ds.st_uid == self.owner and not ds.st_mode & 0o077, 'UnsafeCatalog')
            for name in ('catalog.lock', 'catalog.json'):
                opened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=dfd)
                if name == 'catalog.lock':
                    lock = opened
                else:
                    fd = opened
                s = os.fstat(opened)
                require(stat.S_ISREG(s.st_mode) and s.st_uid == self.owner and
                        stat.S_IMODE(s.st_mode) == 0o600 and s.st_nlink == 1, 'UnsafeCatalog')
                if name == 'catalog.lock':
                    try:
                        fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
                    except BlockingIOError as exc:
                        raise Error('Busy') from exc
            require(0 < s.st_size <= LIMIT, 'UnsafeCatalog')
            data = bytearray()
            while len(data) <= LIMIT:
                part = os.read(fd, min(4096, LIMIT + 1 - len(data)))
                if not part:
                    break
                data.extend(part)
            require(len(data) == s.st_size, 'UnsafeCatalog')
            return decode(bytes(data))
        except Error:
            raise
        except FileNotFoundError as exc:
            raise Error('RecoveryRequired') from exc
        except OSError as exc:
            raise Error('UnsafeCatalog') from exc
        finally:
            for opened in (fd, lock, dfd):
                if opened >= 0:
                    os.close(opened)


def classify(catalog, uid, observe_identity, required=(), observe_adapters=None):
    """Eligibility only; upstream channel/enforcement still must authorize."""
    require(type(uid) is int and 0 < uid < 2**32-1, 'InvalidIdentity')
    account = next((a for a in catalog.accounts if a.identity.uid == uid), None)
    require(account is not None, 'RecoveryRequired')
    require(not account.barrier and account.state == 'active', 'Blocked')
    try:
        observed = observe_identity(uid)
    except Exception as exc:
        raise Error('InvalidIdentity') from exc
    require(type(observed) is Identity and observed == account.identity, 'InvalidIdentity')
    if account.kind == 'ordinary':
        return 'OrdinaryEligible'
    require(bool(required) and set(dict(account.adapters)) == set(required), 'UnsupportedProducer')
    try:
        observed = observe_adapters(account) if observe_adapters is not None else None
    except Exception as exc:
        raise Error('UnsupportedProducer') from exc
    # Trusted adapter observation must include exact generation and policy.
    require(type(observed) is tuple and observed ==
            (account.generation, account.policy, account.adapters), 'UnsupportedProducer')
    return 'SupervisedEligible'


@dataclass(frozen=True)
class Plan:
    identifier: str
    sender: str
    caller_uid: int
    association: str
    generation: str
    revision: int
    catalog_digest: str
    account: Account
    expires: float
    effect: str = 'deny-new-admission-only'


class Planner:
    """In-memory plans; transport and capabilities are trusted lab adapters.

    No interactive auth or writes. validate is not execute/authorization.
    A new planner loses plans rather than reconstructing authority on restart.
    """
    def __init__(self, reader, resolve_sender, capable, observe_identity, clock):
        self.reader = reader
        self.resolve_sender = resolve_sender
        self.capable = capable
        self.observe_identity = observe_identity
        self.clock = clock
        self._plans = {}

    def _caller(self, sender, association):
        require(type(sender) is str and re.fullmatch(r':[0-9]+\.[0-9]+', sender), 'Denied')
        require(matches(TOKEN, association), 'Denied')
        try:
            uid = self.resolve_sender(sender)
        except Exception as exc:
            raise Error('Denied') from exc
        require(type(uid) is int and 0 <= uid < 2**32-1, 'Denied')
        try:
            allowed = self.capable(uid, association)
        except Exception as exc:
            raise Error('Denied') from exc
        require(allowed is True, 'Denied')
        return uid

    def _now(self):
        now = self.clock()
        require(type(now) in (int, float) and math.isfinite(now), 'InvalidClock')
        return now

    def plan(self, sender, association, expected_revision):
        uid = self._caller(sender, association)  # before any target lookup
        require(positive(expected_revision), 'Conflict')
        catalog = self.reader.snapshot()
        account = next((a for a in catalog.accounts if a.association == association), None)
        require(account is not None, 'RecoveryRequired')
        require(account.revision == expected_revision, 'Conflict')
        # Planning supports ordinary admission withdrawal first; supervised
        # coverage and its policy-change protocol are not qualified here.
        require(account.kind == 'ordinary', 'UnsupportedOperation')
        classify(catalog, account.identity.uid, self.observe_identity)
        now = self._now()
        self._plans = {k: p for k, p in self._plans.items() if p.expires > now}
        require(len(self._plans) < 128, 'Busy')
        token = secrets.token_hex(16)
        result = Plan(token, sender, uid, association, account.generation,
                      account.revision, catalog.digest, account, now + 60.0)
        self._plans[token] = result
        return result

    def validate(self, sender, identifier):
        require(matches(TOKEN, identifier), 'Denied')
        plan = self._plans.get(identifier)
        require(plan is not None and plan.sender == sender, 'Denied')
        require(self._caller(sender, plan.association) == plan.caller_uid, 'Denied')
        require(self._now() < plan.expires, 'Conflict')
        catalog = self.reader.snapshot()
        require(catalog.digest == plan.catalog_digest, 'Conflict')
        classify(catalog, plan.account.identity.uid, self.observe_identity)
        require(self._caller(sender, plan.association) == plan.caller_uid, 'Denied')
        return plan  # still no authority to mutate anything
