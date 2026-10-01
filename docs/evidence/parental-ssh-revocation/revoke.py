"""Disposable SSH revocation via native logind, with pidfd completion evidence.

Only acts after a durable v2 barrier. Does not send custom signals to root,
restart the shared listener, stop arbitrary producers or change account IDs.
"""
import os
from pathlib import Path
import select
import subprocess
import time

EXECUTABLES = {'/usr/libexec/ssh/sshd-auth', '/usr/libexec/ssh/sshd-session'}

def fixture():
    assert os.geteuid() == 0
    assert {'lyra.parental-selinux-test=1', 'lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
    assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'

def process(pid):
    directory = Path('/proc') / str(pid)
    stat = (directory / 'stat').read_text()
    fields = stat[stat.rfind(')') + 2:].split()
    uids = tuple(int(v) for v in next(line.split()[1:] for line in
                 (directory / 'status').read_text().splitlines() if line.startswith('Uid:')))
    return dict(pid=pid, ppid=int(fields[1]), starttime=int(fields[19]), state=fields[0],
                uids=uids, executable=os.readlink(directory / 'exe'),
                context=(directory / 'attr/current').read_text().strip('\x00\n '),
                cgroup=(directory / 'cgroup').read_text().strip(),
                cmdline=(directory / 'cmdline').read_bytes().replace(b'\0', b' ').decode())

def holders(path):
    identity = path.stat()
    found = []
    for directory in Path('/proc').iterdir():
        if not directory.name.isdecimal(): continue
        try:
            for fd in (directory / 'fd').iterdir():
                try: info = fd.stat()
                except FileNotFoundError: continue
                if (info.st_dev, info.st_ino) == (identity.st_dev, identity.st_ino):
                    found.append(process(int(directory.name)))
                    break
        except FileNotFoundError: pass
    return found

def revoke(uid, generation, directory, unit, listener):
    fixture()
    assert isinstance(uid, int) and uid > 0
    assert len(generation) == 32 and all(c in '0123456789abcdef' for c in generation)
    assert unit == 'lyra-parental-revoke-sshd.service' and listener > 1
    assert (directory / f'.barrier-{generation}').exists()
    lease_holders = holders(directory / f'.lease-{generation}.lock')
    assert lease_holders, 'no tracked SSH transport; do not claim revocation'
    pins = []
    try:
        for row in lease_holders:
            assert row['pid'] != listener and row['executable'] in EXECUTABLES, row
            assert f'/user.slice/user-{uid}.slice/session-' in row['cgroup'], row
            assert row['uids'] in ((0, 0, 0, 0), (uid, uid, uid, uid)), row
            binary = Path(row['executable']).stat()
            assert binary.st_uid == 0 and not binary.st_mode & 0o022
            pin = os.pidfd_open(row['pid']); pins.append(pin)
            current = process(row['pid'])
            for key in ('starttime','ppid','uids','executable','context','cgroup'):
                assert current[key] == row[key], (row, current)
        # Native logind terminates the account's sessions and user manager. Root
        # SSH monitors are included in the session scope; pidfds verify their exit.
        completed = subprocess.run(['loginctl','terminate-user',str(uid)],
                                   capture_output=True,text=True,timeout=30)
        assert completed.returncode == 0, completed.stderr
        deadline = time.monotonic() + 10
        while any(not select.select([pin], [], [], 0)[0] for pin in pins):
            assert time.monotonic() < deadline, 'tracked SSH transport did not exit; keep barrier'
            time.sleep(.02)
        assert not holders(directory / f'.lease-{generation}.lock'), 'lease still held; keep barrier'
        return dict(holders_before=lease_holders, pidfds=True, pidfds_exited=len(pins),
                    logind_rc=completed.returncode, custom_signals=False)
    finally:
        for pin in pins: os.close(pin)
