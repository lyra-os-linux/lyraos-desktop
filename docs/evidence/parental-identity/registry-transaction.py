"""Disposable proof helper for durable registry transitions; not a system service."""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import uuid

HEADER = b'LYRA-ID-REGISTRY-V1\n'
MAX_FILE = 8192
GENERATION = re.compile(r'[0-9a-f]{32}\Z')
NAME = re.compile(r'[a-z_][a-z0-9_-]{0,62}\Z')
STATES = {'active', 'tombstone', 'blocked', 'provisioning', 'transitioning', 'recovering'}
CRASH_EXIT = 91


class StoreError(RuntimeError):
    pass


def validate_record(row):
    expected = {'state', 'user', 'uid', 'gid', 'group', 'generation'}
    if not isinstance(row, dict) or set(row) != expected:
        raise StoreError('invalid record fields')
    if row['state'] not in STATES or not NAME.fullmatch(row['user']) or not NAME.fullmatch(row['group']):
        raise StoreError('invalid state or account name')
    for key in ('uid', 'gid'):
        if type(row[key]) is not int or not 0 < row[key] < 2**32 - 1:
            raise StoreError('invalid Unix ID')
    if not isinstance(row['generation'], str) or not GENERATION.fullmatch(row['generation']):
        raise StoreError('invalid generation')


def encode_registry(rows):
    lines = [HEADER]
    seen = set()
    for row in rows:
        validate_record(row)
        if row['generation'] in seen:
            raise StoreError('duplicate generation')
        seen.add(row['generation'])
        lines.append('|'.join(str(row[k]) for k in ('state', 'user', 'uid', 'gid', 'group', 'generation')).encode() + b'\n')
    if not rows:
        raise StoreError('empty registry')
    return b''.join(lines)


def decode_registry(data):
    if not data.startswith(HEADER) or not data.endswith(b'\n') or b'\0' in data or len(data) > MAX_FILE:
        raise StoreError('invalid registry framing')
    rows, seen = [], set()
    for raw in data[len(HEADER):].splitlines():
        parts = raw.decode('ascii').split('|')
        if len(parts) != 6:
            raise StoreError('invalid registry row')
        state, user, uid, gid, group, generation = parts
        if not uid.isdecimal() or not gid.isdecimal():
            raise StoreError('invalid registry IDs')
        row = {'state': state, 'user': user, 'uid': int(uid), 'gid': int(gid),
               'group': group, 'generation': generation}
        validate_record(row)
        if generation in seen:
            raise StoreError('duplicate generation')
        seen.add(generation)
        rows.append(row)
    if not rows:
        raise StoreError('empty registry')
    return rows


class RegistryStore:
    def __init__(self, directory, crash_at=None):
        if os.geteuid() != 0:
            raise StoreError('must run as root in the disposable VM')
        self.directory = Path(directory)
        self.crash_at = crash_at
        self._check_directory()

    def _check_directory(self):
        fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            st = os.fstat(fd)
            if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077:
                raise StoreError('state directory must be root-owned mode 0700 or stricter')
        finally:
            os.close(fd)

    @contextlib.contextmanager
    def _locked(self, nonblocking=False, shared=False):
        dfd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            lockfd = os.open('.transaction.lock', os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW,
                             0o600, dir_fd=dfd)
            st = os.fstat(lockfd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077 or st.st_nlink != 1:
                raise StoreError('unsafe lock file')
            try:
                operation = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
                fcntl.flock(lockfd, operation | (fcntl.LOCK_NB if nonblocking else 0))
            except BlockingIOError as error:
                raise StoreError('busy: an admitted PAM session or another transaction holds the lock') from error
            yield dfd
        finally:
            if 'lockfd' in locals():
                os.close(lockfd)
            os.close(dfd)

    def _crash(self, point):
        if self.crash_at == point:
            os._exit(CRASH_EXIT)

    @staticmethod
    def _atomic(dfd, name, data, crash=None):
        tmp = f'.{name}.{uuid.uuid4().hex}.tmp'
        fd = -1
        try:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                         0o600, dir_fd=dfd)
            view = memoryview(data)
            while view:
                count = os.write(fd, view)
                if count <= 0:
                    raise OSError('short write to temporary state file')
                view = view[count:]
            os.fsync(fd)
            if crash:
                crash('temp-synced')
            os.close(fd); fd = -1
            os.replace(tmp, name, src_dir_fd=dfd, dst_dir_fd=dfd)
            os.fsync(dfd)
            if crash:
                crash('published')
        except BaseException:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(tmp, dir_fd=dfd)
            except FileNotFoundError:
                pass
            raise

    def _read(self, dfd, name, limit=MAX_FILE):
        fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=dfd)
        try:
            st = os.fstat(fd)
            if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077 or
                    st.st_nlink != 1 or st.st_size <= 0 or st.st_size > limit):
                raise StoreError(f'unsafe {name}')
            data = os.read(fd, st.st_size)
            if len(data) != st.st_size:
                raise StoreError(f'short read from {name}')
            return data
        finally:
            os.close(fd)

    def _rows(self, dfd):
        return decode_registry(self._read(dfd, 'identity-registry'))

    def _write_rows(self, dfd, rows, point=None):
        self._atomic(dfd, 'identity-registry', encode_registry(rows),
                     (lambda phase: self._crash(f'{point}-{phase}')) if point else None)

    def _journal(self, dfd):
        try:
            obj = json.loads(self._read(dfd, 'identity-journal', 4096))
        except FileNotFoundError:
            return None
        if (not isinstance(obj, dict) or obj.get('schema') != 1 or
                obj.get('phase') not in {'prepared', 'blocked', 'tombstoned', 'committed', 'recovering'} or
                not isinstance(obj.get('transaction'), str) or
                not GENERATION.fullmatch(obj.get('old_generation', ''))):
            raise StoreError('invalid transaction journal')
        new = obj.get('new_generation')
        if new is not None and not GENERATION.fullmatch(new):
            raise StoreError('invalid journal target generation')
        return obj

    def _write_journal(self, dfd, obj, point=None):
        data = (json.dumps(obj, sort_keys=True, separators=(',', ':')) + '\n').encode()
        self._atomic(dfd, 'identity-journal', data,
                     (lambda phase: self._crash(f'{point}-{phase}')) if point else None)

    def _remove_journal(self, dfd, point=None):
        os.unlink('identity-journal', dir_fd=dfd)
        os.fsync(dfd)
        if point:
            self._crash(point)

    @staticmethod
    def _remove_stale_temps(dfd):
        pattern = re.compile(r'\.(?:identity-registry|identity-journal)\.[0-9a-f]{32}\.tmp\Z')
        removed = False
        for name in os.listdir(dfd):
            if pattern.fullmatch(name):
                os.unlink(name, dir_fd=dfd)
                removed = True
        if removed:
            os.fsync(dfd)

    def seed(self, rows):
        with self._locked() as dfd:
            try:
                os.stat('identity-registry', dir_fd=dfd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise StoreError('registry already exists')
            self._write_rows(dfd, rows)

    def begin(self, old_generation):
        # Fail Busy instead of waiting behind an admitted PAM session.
        with self._locked(nonblocking=True) as dfd:
            if self._journal(dfd) is not None:
                raise StoreError('transaction already pending')
            rows = self._rows(dfd)
            old = next((r for r in rows if r['generation'] == old_generation), None)
            if old is None or old['state'] != 'active':
                raise StoreError('old generation is not active')
            journal = {'schema': 1, 'transaction': uuid.uuid4().hex,
                       'phase': 'prepared', 'old_generation': old_generation,
                       'new_generation': None}
            self._write_journal(dfd, journal, 'journal-prepared')
            old['state'] = 'transitioning'
            self._write_rows(dfd, rows, 'registry-blocked')
            journal['phase'] = 'blocked'
            self._write_journal(dfd, journal, 'journal-blocked')

    def tombstone(self, old_generation):
        with self._locked() as dfd:
            journal = self._journal(dfd)
            if journal is None or journal['old_generation'] != old_generation or journal['phase'] != 'blocked':
                raise StoreError('no blocked transaction for this generation')
            rows = self._rows(dfd)
            old = next((r for r in rows if r['generation'] == old_generation), None)
            if old is None or old['state'] != 'transitioning':
                raise StoreError('old generation is not blocked')
            old['state'] = 'tombstone'
            self._write_rows(dfd, rows, 'registry-tombstone')
            journal['phase'] = 'tombstoned'
            self._write_journal(dfd, journal, 'journal-tombstoned')

    def publish(self, old_generation, new_record):
        validate_record(new_record)
        if new_record['state'] != 'active':
            raise StoreError('new enrollment must be active')
        with self._locked() as dfd:
            journal = self._journal(dfd)
            if journal is None or journal['old_generation'] != old_generation or journal['phase'] != 'tombstoned':
                raise StoreError('old generation has no durable tombstone')
            rows = self._rows(dfd)
            old = next((r for r in rows if r['generation'] == old_generation), None)
            if old is None or old['state'] != 'tombstone':
                raise StoreError('old generation is not tombstoned')
            if any(r['generation'] == new_record['generation'] for r in rows):
                raise StoreError('new generation already exists')
            journal['new_generation'] = new_record['generation']
            self._write_journal(dfd, journal)
            rows.append(dict(new_record))
            self._write_rows(dfd, rows, 'registry-new-active')
            journal['phase'] = 'committed'
            self._write_journal(dfd, journal, 'journal-committed')
            self._remove_journal(dfd, 'journal-removed')

    def recover(self):
        with self._locked() as dfd:
            self._remove_stale_temps(dfd)
            journal = self._journal(dfd)
            if journal is None:
                return 'clean'
            rows = self._rows(dfd)
            old = next((r for r in rows if r['generation'] == journal['old_generation']), None)
            new = next((r for r in rows if r['generation'] == journal.get('new_generation')), None)
            if journal['phase'] == 'committed' and old and old['state'] == 'tombstone' and new and new['state'] == 'active':
                self._remove_journal(dfd)
                return 'committed'
            # Incomplete transactions are made non-active; recovery never enrolls.
            for row in (old, new):
                if row is not None and row['state'] != 'tombstone':
                    row['state'] = 'recovering'
            self._write_rows(dfd, rows)
            journal['phase'] = 'recovering'
            self._write_journal(dfd, journal)
            return 'blocked'

    def snapshot(self):
        with self._locked(shared=True) as dfd:
            return self._rows(dfd), self._journal(dfd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['seed', 'begin', 'tombstone', 'publish', 'recover', 'snapshot'])
    parser.add_argument('directory')
    parser.add_argument('value', nargs='?')
    parser.add_argument('--record-json')
    parser.add_argument('--crash-at')
    args = parser.parse_args()
    store = RegistryStore(args.directory, args.crash_at)
    if args.command == 'seed':
        store.seed(json.loads(args.value))
        out = 'seeded'
    elif args.command == 'begin':
        store.begin(args.value); out = 'begun'
    elif args.command == 'tombstone':
        store.tombstone(args.value); out = 'tombstoned'
    elif args.command == 'publish':
        store.publish(args.value, json.loads(args.record_json)); out = 'published'
    elif args.command == 'recover':
        out = store.recover()
    else:
        out = json.dumps(store.snapshot(), sort_keys=True)
    print(out)


if __name__ == '__main__':
    main()
