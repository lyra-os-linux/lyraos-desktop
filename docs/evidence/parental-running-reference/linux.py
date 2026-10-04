"""Trusted marked-VM backend; kernel /proc and systemd D-Bus, no stop method."""
from pathlib import Path
import hashlib, os, select, stat
from dataclasses import dataclass
from running import Observation
from coordinator import GateError

@dataclass(frozen=True)
class Pin:
    descriptor: int
    directory: int
    requested: int

class Linux:
    def __init__(self, runtime):
        assert os.geteuid() == 0
        assert {'lyra.parental-identity-test=1', 'lyra.parental-selinux-test=1'} <= set(Path('/proc/cmdline').read_text().split())
        assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'
        self.runtime = runtime

    def pin(self, pid):
        descriptor = os.pidfd_open(pid)
        try:
            directory = os.open('/proc/' + str(pid), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            return Pin(descriptor, directory, pid)
        except BaseException:
            os.close(descriptor); raise

    def pid(self, pin):
        rows = [line.split()[1:] for line in Path('/proc/self/fdinfo/' + str(pin.descriptor)).read_text().splitlines() if line.startswith('Pid:')]
        if len(rows) != 1 or len(rows[0]) != 1: raise GateError('UnverifiedRuntime')
        return int(rows[0][0])

    def exited(self, pin):
        return bool(select.select([pin.descriptor], [], [], 0)[0])

    def close(self, pin):
        try: os.close(pin.directory)
        finally: os.close(pin.descriptor)

    def data(self, pin, name, limit=65536):
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=pin.directory)
        try:
            result = bytearray()
            while True:
                chunk = os.read(fd, min(4096, limit + 1 - len(result)))
                if not chunk: return bytes(result)
                result.extend(chunk)
                if len(result) > limit: raise GateError('UnsupportedRuntime')
        finally: os.close(fd)

    def read(self, pin):
        fields = {}
        for line in self.data(pin, 'status').decode().splitlines():
            if ':' in line:
                name, value = line.split(':', 1); fields[name] = value.split()
        uids = tuple(map(int, fields['Uid'])); gids = tuple(map(int, fields['Gid']))
        groups = tuple(sorted(map(int, fields['Groups'])))
        caps = tuple(int(fields[name][0], 16) for name in ('CapPrm', 'CapEff', 'CapAmb'))
        raw = self.data(pin, 'cmdline', 65536)
        if not raw or not raw.endswith(b'\0'): raise GateError('UnsupportedRuntime')
        argv = tuple(s.decode() for s in raw[:-1].split(b'\0'))
        ticks = int(self.data(pin, 'stat').decode().rsplit(')', 1)[1].split()[19])
        cgroup = self.data(pin, 'cgroup').decode().strip()
        # exe is a kernel /proc magic symlink; this is not a client-supplied path.
        fd = os.open('exe', os.O_RDONLY | os.O_CLOEXEC, dir_fd=pin.directory)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > 32*1024*1024: raise GateError('UnsupportedRuntime')
            data = bytearray()
            while True:
                chunk = os.read(fd, 65536)
                if not chunk: break
                data.extend(chunk)
                if len(data) > 32*1024*1024: raise GateError('UnsupportedRuntime')
            after = os.fstat(fd)
            def stamp(s): return (s.st_dev, s.st_ino, s.st_uid, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if len(data) != before.st_size or stamp(before) != stamp(after): raise GateError('Conflict')
            executable = before.st_dev, before.st_ino, hashlib.sha256(data).hexdigest()
        finally: os.close(fd)
        return Observation(pin.requested, ticks, uids, gids, groups, caps, executable, argv, cgroup)
