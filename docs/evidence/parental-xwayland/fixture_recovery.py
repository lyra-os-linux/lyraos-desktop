"""Durable recovery for the marked disposable parental VM, never a host tool."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import uuid

ROOT = Path('/root/lyra-xwayland-recovery')
ACTIVE = ROOT / 'active.json'
MODULE = Path('/etc/selinux/targeted/active/modules/400/lyra-trusted-shell-test')
SERVICES = ['gdm', 'user@1003.service', 'auditd']


def guard():
    assert os.geteuid() == 0
    assert 'lyra.parental-selinux-test=1' in Path('/proc/cmdline').read_text().split()
    ROOT.mkdir(mode=0o700, exist_ok=True)
    assert not ROOT.is_symlink() and ROOT.stat().st_uid == 0
    assert stat.S_IMODE(ROOT.stat().st_mode) == 0o700


def run(argv, timeout=60, check=True):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError((argv, result.returncode, result.stderr))
    return result


def save(path, data):
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def snapshot(paths, generated):
    guard()
    with (ROOT / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        assert not ACTIVE.exists(), 'Pending recovery: run fixture_recovery.py first'
        assert not MODULE.exists()
        assert Path('/sys/fs/selinux/enforce').read_text().strip() == '0'
        for service in SERVICES:
            assert run(['systemctl', 'is-active', service], check=False).stdout.strip() == 'inactive'
        backup = ROOT / uuid.uuid4().hex
        backup.mkdir(mode=0o700)
        entries = []
        missing_dirs = set()
        for index, item in enumerate(dict.fromkeys(map(str, [*paths, *generated]))):
            path = Path(item)
            assert path.is_absolute() and not path.is_symlink()
            exists = path.exists()
            entry = dict(path=item, exists=exists)
            if exists:
                info = path.stat()
                assert stat.S_ISREG(info.st_mode)
                data = path.read_bytes()
                name = str(index)
                save(backup / name, data)
                entry.update(blob=name, sha256=hashlib.sha256(data).hexdigest(),
                             mode=stat.S_IMODE(info.st_mode), uid=info.st_uid, gid=info.st_gid,
                             atime=info.st_atime_ns, mtime=info.st_mtime_ns,
                             label=base64.b64encode(os.getxattr(path, 'security.selinux')).decode())
            else:
                parent = path.parent
                while not parent.exists():
                    missing_dirs.add(str(parent))
                    parent = parent.parent
            entries.append(entry)
        audit_status = dict(line.split(maxsplit=1) for line in run(['auditctl', '-s']).stdout.splitlines())
        manifest = dict(backup=str(backup), entries=entries, audit_backlog_limit=audit_status['backlog_limit'],
                        directories=sorted(missing_dirs, key=lambda p: len(Path(p).parts), reverse=True))
        data = json.dumps(manifest, indent=2).encode()
        save(backup / 'manifest.json', data)
        sync_dir(backup)
        save(ROOT / 'pending.json', data)
        os.replace(ROOT / 'pending.json', ACTIVE)
        sync_dir(ROOT)
        return str(backup)


def recover():
    guard()
    with (ROOT / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not ACTIVE.exists():
            return dict(restored=True, pending=False)
        manifest = json.loads(ACTIVE.read_text())
        backup = Path(manifest['backup'])
        assert backup.parent == ROOT and not backup.is_symlink()
        # Validate every backup before touching the live fixture.
        for entry in manifest['entries']:
            if entry['exists']:
                data = (backup / entry['blob']).read_bytes()
                assert hashlib.sha256(data).hexdigest() == entry['sha256']
        run(['systemctl', 'stop', 'gdm', 'user@1003.service'], timeout=90)
        run(['setenforce', '0'])
        run(['systemctl', 'stop', 'auditd'])
        run(['auditctl', '-b', manifest['audit_backlog_limit']])
        for service in SERVICES:
            assert run(['systemctl', 'is-active', service], check=False).stdout.strip() == 'inactive'
        log = Path('/tmp/lyra-trusted-shell-test.log')
        if log.is_file() and not log.is_symlink():
            (backup / 'session-stderr.log').write_bytes(log.read_bytes())
            Path('/root/trusted-shell-stderr.log').write_bytes(log.read_bytes())
        for entry in manifest['entries']:
            path = Path(entry['path'])
            assert not path.is_symlink()
            if entry['exists']:
                data = (backup / entry['blob']).read_bytes()
                if not path.exists() or path.read_bytes() != data:
                    path.write_bytes(data)
                os.chown(path, entry['uid'], entry['gid'])
                path.chmod(entry['mode'])
                os.setxattr(path, 'security.selinux', base64.b64decode(entry['label']))
                assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
                os.utime(path, ns=(entry['atime'], entry['mtime']))
                assert os.getxattr(path, 'security.selinux') == base64.b64decode(entry['label'])
                assert path.stat().st_mtime_ns == entry['mtime']
            else:
                path.unlink(missing_ok=True)
        for name in manifest['directories']:
            path = Path(name)
            if path.exists():
                path.rmdir()
        if MODULE.exists():
            run(['semodule', '-r', 'lyra-trusted-shell-test'], timeout=120)
        assert not MODULE.exists()
        assert not Path('/run/user/1003').exists()
        result = dict(restored=True, pending=False, backup=str(backup), files=len(manifest['entries']))
        (backup / 'restored.json').write_text(json.dumps(result, indent=2))
        ACTIVE.unlink()
        sync_dir(ROOT)
        return result


if __name__ == '__main__':
    print(json.dumps(recover(), indent=2))
