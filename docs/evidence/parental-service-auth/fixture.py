"""Root filesystem fixture adapted for isolated D-Bus/Polkit tests."""
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import grp
import shutil
import subprocess
import sys
import time
import unittest

BASE = Path('/root/lyra-service-auth-test')
DATA = BASE / 'fixtures'


def guard():
    assert os.geteuid() == 0
    cmd = Path('/proc/cmdline').read_text().split()
    assert 'lyra.parental-identity-test=1' in cmd and 'lyra.parental-selinux-test=1' in cmd
    assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'
    assert Path(__file__).resolve().parent == BASE


guard()


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


co = load('coordinator', 'coordinator.py')
w = load('withdrawal', 'withdrawal.py')
op = load('storage_operations', 'operations.py')
i = load('storage_inventory', 'inventory.py')
writer = load('storage_writer', 'writer.py')
c = load('storage_classifier', 'classifier.py')
b = load('storage_binding', 'binding.py')


def identify(uid):
    account = pwd.getpwuid(uid)
    # Limit this laboratory to a unique files-backed identity, no remote NSS.
    local = [line.split(':') for line in Path('/etc/passwd').read_text().splitlines()
             if line and int(line.split(':')[2]) == uid]
    assert len(local) == 1 and local[0][0] == account.pw_name and int(local[0][3]) == account.pw_gid
    group = grp.getgrgid(account.pw_gid)
    local_group = [line.split(':') for line in Path('/etc/group').read_text().splitlines()
                   if line and int(line.split(':')[2]) == account.pw_gid]
    assert len(local_group) == 1 and local_group[0][0] == group.gr_name
    return dict(user=account.pw_name, uid=uid, gid=account.pw_gid, group=group.gr_name)


IDENTITIES = {uid: identify(uid) for uid in (1000, 1002)}


def atomic(directory, name, payload):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        writer.RegistryStore._atomic(fd, name, payload)
    finally:
        os.close(fd)


def encode(row):
    return (json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n').encode()


def decode_proof(payload, uid):
    # Strict synthetic JSON proof, deliberately not the historical PAM format.
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out: raise w.WithdrawalError('InvalidProof')
            out[key] = value
        return out
    try:
        row = json.loads(payload, object_pairs_hook=unique)
        parsed = c.identity(row)
        if parsed.uid != uid: raise ValueError()
        return row
    except Exception as exc:
        raise w.WithdrawalError('InvalidProof') from exc


def files(directory):
    out = {}
    for p in sorted(directory.rglob('*')):
        if p.is_file() and not p.is_symlink():
            s = p.stat()
            out[str(p.relative_to(directory))] = dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                inode=s.st_ino, uid=s.st_uid, gid=s.st_gid, mode=s.st_mode & 0o777, size=s.st_size)
    return out


def system_state():
    paths = [Path('/etc/passwd'), Path('/etc/group')]
    for directory in ('/etc/pam.d', '/usr/lib/pam.d'):
        paths.extend(sorted(p for p in Path(directory).glob('*') if p.is_file()))
    return dict(files={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                selinux=subprocess.check_output(['getenforce'], text=True).strip())


@contextmanager
def exclusive(path):
    with path.open('rb') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


class Fixture:
    def __init__(self, directory, create=False):
        self.root = directory
        self.catalog_dir = directory / 'catalog'
        self.inventory_dir = directory / 'inventory'
        self.ledger = directory / 'ledger'
        self.allow = True
        self.auth_calls = 0
        self.probes = []
        if create:
            directory.mkdir(mode=0o700)
            for path in (self.catalog_dir, self.inventory_dir, self.ledger): path.mkdir(mode=0o700)
            self.catalog = dict(schema=1, revision=1, accounts=[])
            for uid, token in ((1002, 'a'), (1000, 'b')):
                self.catalog['accounts'].append(dict(association=token*32, generation=token*32,
                    identity=IDENTITIES[uid], revision=1, kind='ordinary', state='active',
                    operation='', barrier=False, policy='', adapters={}))
                inventory = dict(schema=1, identity=IDENTITIES[uid], revision=1,
                    producers={name: dict(state='registered', adapter_digest='c'*64,
                        routes=[dict(id='fixture-'+name, digest='d'*64)]) for name in co.REQUIRED})
                atomic(self.inventory_dir, f'{uid}.json', encode(inventory))
                atomic(self.inventory_dir, f'.inventory-{uid}.lock', b'')
                atomic(self.ledger, str(uid), encode(IDENTITIES[uid]))
                atomic(self.ledger, f'.gate-{uid}.lock', b'')
            atomic(self.catalog_dir, 'catalog.json', encode(self.catalog))
            atomic(self.catalog_dir, 'catalog.lock', b'')
        self.reader = c.Reader(self.catalog_dir)  # default root owner, unchanged
        self.inventory = i.Inventory(self.inventory_dir,
            lambda observed: c.Identity(**identify(observed.uid)) == c.Identity(**vars(observed)))
        self.withdrawal = w.Withdrawal(self.ledger, writer.RegistryStore._atomic, decode_proof)
        planner = c.Planner(self.reader, lambda sender: 0 if sender == ':1.20' else None,
            lambda uid, association: self.allow is True,
            lambda uid: c.Identity(**identify(uid)), time.monotonic)
        # Root here has explicit trusted technical capability. It is not guardian.
        self.bridge = b.Bridge(c, planner, op.Operations, self.withdrawal, w.WithdrawalError, self.inventory)

    def plan(self): return self.bridge.plan(':1.20', 'a'*32, 1)

    def authorize(self, payload):
        checked = []
        for path in (self.catalog_dir / 'catalog.lock', self.inventory_dir / '.inventory-1002.lock',
                     self.ledger / '.gate-1002.lock'):
            with exclusive(path): checked.append(path.name)
        self.auth_calls += 1
        self.probes.append(checked)
        return True

    def execute(self, plan, auth=None):
        return self.bridge.execute(':1.20', plan.identifier, auth or self.authorize)

    def resume(self, operation, auth=None):
        return self.bridge.resume(':1.20', 'a'*32, operation, auth or self.authorize)


