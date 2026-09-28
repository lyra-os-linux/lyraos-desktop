"""VM-only admission transition primitive, not an account administration API.

Uses persistent denial plus cooperative PAM leases. All real entry points must
participate before this can authorize account changes in production. Never
removes users, kills processes or automatically reopens after a failure.
"""
import contextlib
import fcntl
import grp
import os
from pathlib import Path
import pwd
import re
import stat
import uuid

DIRECTORY = Path('/etc/security/lyra-parental-transition-fixture')
NAME = re.compile(r'[a-z_][a-z0-9_-]{0,62}\Z')


def active_record(binding):
    if not isinstance(binding, dict) or set(binding) != {'user', 'uid', 'gid', 'group'}:
        raise ValueError('invalid binding')
    if any(not isinstance(binding[k], str) or not NAME.fullmatch(binding[k]) for k in ('user', 'group')):
        raise ValueError('invalid name')
    if any(type(binding[k]) is not int or not 0 < binding[k] < 2**32 - 1 for k in ('uid', 'gid')):
        raise ValueError('invalid ID')
    return f"active={binding['user']}:{binding['uid']}:{binding['gid']}:{binding['group']}\n".encode()


def process_owners(status):
    rows = [line.split()[1:] for line in status.splitlines() if line.startswith('Uid:')]
    if len(rows) != 1 or len(rows[0]) != 4 or any(not v.isascii() or not v.isdecimal() for v in rows[0]):
        raise ValueError('unreadable process identity')
    return tuple(int(v) for v in rows[0])


def processes(uid, proc=Path('/proc')):
    found = []
    for entry in proc.iterdir():
        if not entry.name.isascii() or not entry.name.isdecimal():
            continue
        try:
            owners = process_owners((entry / 'status').read_text())
        except FileNotFoundError:
            continue  # Process exited; other read/parse errors must abort.
        if uid in owners:
            found.append(int(entry.name))
    return sorted(found)


def trusted(fd, directory=False):
    info = os.fstat(fd)
    kind = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    if not kind or info.st_uid != 0 or info.st_mode & 0o022:
        raise PermissionError('untrusted fixture gate')


class Busy(RuntimeError):
    pass


class Gate:
    def __init__(self, binding):
        self.record = active_record(binding)
        if os.geteuid() != 0:
            raise PermissionError('root only')
        if 'lyra.parental-identity-test=1' not in Path('/proc/cmdline').read_text().split():
            raise RuntimeError('not a disposable fixture boot')
        if Path('/sys/block/vda/serial').read_text().strip() != 'lyra-admission-test':
            raise RuntimeError('wrong disposable disk')
        self.binding = dict(binding)
        self.key = str(binding['uid'])

    @contextlib.contextmanager
    def directory(self):
        fd = os.open(DIRECTORY, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            trusted(fd, directory=True)
            yield fd
        finally:
            os.close(fd)

    def write_state(self, directory, value):
        temporary = f'.{self.key}.{uuid.uuid4().hex}.tmp'
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                     0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
            os.rename(temporary, self.key + '.state', src_dir_fd=directory, dst_dir_fd=directory)
            os.fsync(directory)
        finally:
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass

    def initialize(self):
        """Fresh fixture only; never replace the inodes used for locking."""
        with self.directory() as directory:
            for suffix in ('.lock', '.writer'):
                fd = os.open(self.key + suffix, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o600, dir_fd=directory)
                os.fsync(fd)
                os.close(fd)
            self.write_state(directory, b'blocked\n')

    @contextlib.contextmanager
    def locked(self, directory, suffix):
        fd = os.open(self.key + suffix, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=directory)
        try:
            trusted(fd)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise Busy('PAM session or transition still active') from error
            yield
        finally:
            os.close(fd)

    def check_idle(self):
        active = processes(self.binding['uid'])
        if active:
            raise Busy(f'account still owns processes: {active}')

    def check_identity(self):
        p = pwd.getpwnam(self.binding['user'])
        actual = dict(user=p.pw_name, uid=p.pw_uid, gid=p.pw_gid, group=grp.getgrgid(p.pw_gid).gr_name)
        if actual != self.binding:
            raise RuntimeError('account identity changed during transition')

    @contextlib.contextmanager
    def transition(self):
        """Pre-commit failure keeps denial; successful exit verifies then opens.

        This prototype requires a stable name/UID/GID/private-group tuple. It
        deliberately cannot commit an identity migration or supervision removal.
        """
        with self.directory() as directory, self.locked(directory, '.writer'):
            self.write_state(directory, b'blocked\n')
            with self.locked(directory, '.lock'):
                self.check_identity()
                self.check_idle()
                yield
                self.check_identity()
                self.check_idle()
                try:
                    self.write_state(directory, self.record)
                except OSError:
                    # A failed directory fsync can follow a successful rename.
                    # Restore denial if storage still accepts writes. Failure of
                    # both writes is an unresolved storage fault, not a claimed
                    # successful recovery; production activation is not supported.
                    self.write_state(directory, b'blocked\n')
                    raise
