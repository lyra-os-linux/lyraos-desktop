"""Native user@.service admission in the disposable parental VM only.

Copy transition.py, pam-guard.c and bindings.py from the previous stages to
the /root paths below. No recipe or published package uses this fixture.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, '/root')
from transition import Gate, Busy, DIRECTORY, processes

spec = importlib.util.spec_from_file_location('bindings', '/root/identity-bindings.py')
bindings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bindings)
BINDING = dict(user='parentaltest', uid=1003, gid=1004, group='parentaltest')
CONTEXT = 'lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
gate = Gate(BINDING)  # Checks root, kernel marker and disposable disk serial.
gate.check_identity()
PAM = Path('/etc/pam.d/systemd-user')
VENDOR = Path('/usr/lib/pam.d/systemd-user')
MODULE = Path('/usr/lib64/security/pam_lyra_transition_fixture.so')
STATE = DIRECTORY / '1003.state'
LOCK = DIRECTORY / '1003.lock'
checks, cleanup = [], []
result = dict(kind='native-systemd-user-admission', full_account_protection=False,
              checks=checks, cleanup=cleanup)


def run(args, check=True):
    p = subprocess.run(args, capture_output=True, text=True, timeout=60)
    row = dict(rc=p.returncode, stdout=p.stdout, stderr=p.stderr)
    if check and p.returncode:
        raise RuntimeError((args, row))
    return row


def record(name, **details):
    row = dict(name=name, passed=True, **details)
    checks.append(row)
    print(json.dumps(row), flush=True)


def show(uid):
    output = run(['systemctl', 'show', f'user@{uid}.service', '-p', 'MainPID',
                  '-p', 'ActiveState', '-p', 'Result', '-p', 'ExecMainStatus'])['stdout']
    return dict(line.split('=', 1) for line in output.splitlines())


def stop(uid):
    run(['systemctl', 'stop', f'user@{uid}.service'])
    assert show(uid)['MainPID'] == '0'


def start(name, uid=1003, allowed=True):
    if show(uid)['ActiveState'] == 'failed':
        run(['systemctl', 'reset-failed', f'user@{uid}.service'])
    launched = run(['systemctl', 'start', f'user@{uid}.service'], check=False)
    state = show(uid)
    if allowed:
        assert launched['rc'] == 0 and state['ActiveState'] == 'active', (launched, state)
        pid = int(state['MainPID'])
        context = Path(f'/proc/{pid}/attr/current').read_text().strip('\x00\n ')
        assert (context == CONTEXT) if uid == 1003 else ':unconfined_t:' in context, context
        record(name, unit=state, context=context)
    else:
        assert launched['rc'] != 0 and state['MainPID'] == '0', (launched, state)
        assert state['ExecMainStatus'] == '224', state  # systemd EXIT_PAM, not a generic exec failure.
        record(name, unit=state, command=launched)


def recover():
    assert not processes(1003)
    with gate.transition():
        pass


def lease_holders():
    """Read kernel fd/inode evidence, independent of the /proc UID safety check."""
    identity = LOCK.stat()
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            for fd in (proc / 'fd').iterdir():
                try:
                    info = fd.stat()
                except FileNotFoundError:
                    continue
                if (info.st_dev, info.st_ino) == (identity.st_dev, identity.st_ino):
                    found.append(dict(pid=int(proc.name), fd=fd.name,
                                      comm=(proc / 'comm').read_text().strip(),
                                      context=(proc / 'attr/current').read_text().strip('\x00\n ')))
        except FileNotFoundError:
            continue
    return found


assert run(['getenforce'])['stdout'].strip() == 'Permissive'
assert all(show(uid)['MainPID'] == '0' for uid in (1003, 1002))
assert not MODULE.exists() and not DIRECTORY.exists()
original = PAM.read_bytes() if PAM.exists() else None
vendor_hash = hashlib.sha256(VENDOR.read_bytes()).hexdigest()
try:
    run(['gcc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror', '-O2',
         '/root/transition-pam-guard.c', '-o', str(MODULE), '-lpam', '-lselinux'])
    DIRECTORY.mkdir(mode=0o700)
    gate.initialize()
    recover()
    PAM.write_text(VENDOR.read_text() + '\n' + bindings.render([BINDING]).replace(
        'pam_lyra_identity_fixture.so', 'pam_lyra_transition_fixture.so'))
    PAM.chmod(0o644)
    run(['restorecon', '-R', str(DIRECTORY), str(PAM), str(MODULE)])
    run(['setenforce', '1'])
    start('supervised-active')
    start('ordinary-active', 1002)
    holders = lease_holders()
    assert any(row['comm'] == '(sd-pam)' for row in holders), holders
    with gate.directory() as directory:
        try:
            with gate.locked(directory, '.lock'):
                raise AssertionError('active PAM lease was lost')
        except Busy:
            record('native-sd-pam-retains-lease', holders=holders)
    pid = show(1003)['MainPID']
    try:
        with gate.transition():
            raise AssertionError('transition entered with active manager')
    except Busy:
        assert STATE.read_bytes() == b'blocked\n'
        assert show(1003)['MainPID'] == pid
        record('active-manager-prevents-transition-and-remains-alive', pid=pid)
    stop(1002)
    start('ordinary-during-persistent-block', 1002)
    stop(1003)
    assert not lease_holders()
    record('manager-stop-releases-lease')
    start('stopping-manager-does-not-clear-block', allowed=False)
    recover()
    start('explicit-recovery-admits-supervised')
    # The vendor reload path reexecs the manager; its PAM keeper must survive.
    run(['systemctl', 'reload', 'user@1003.service'])
    assert show(1003)['ActiveState'] == 'active'
    with gate.directory() as directory:
        try:
            with gate.locked(directory, '.lock'):
                raise AssertionError('reload lost PAM lease')
        except Busy:
            record('vendor-reexec-retains-lease', holders=lease_holders())
    stop(1003)
    stop(1002)

    for fault in ('missing-state', 'corrupt-state', 'missing-module', 'permissive'):
        state_data = STATE.read_bytes()
        saved_module = MODULE.with_suffix('.manager-saved')
        try:
            if fault == 'missing-state': STATE.unlink()
            elif fault == 'corrupt-state': STATE.write_bytes(b'active\n')
            elif fault == 'missing-module': MODULE.rename(saved_module)
            else: run(['setenforce', '0'])
            start(fault + '-supervised-denied', allowed=False)
            start(fault + '-ordinary-preserved', 1002)
            stop(1002)
        finally:
            if saved_module.exists(): saved_module.rename(MODULE)
            STATE.write_bytes(state_data)
            STATE.chmod(0o600)
            run(['restorecon', str(STATE)])
            run(['setenforce', '1'])
        recover()  # Failed pam_open_session must not leak leases.
    start('final-supervised-recovered')
    start('final-ordinary-preserved', 1002)
    result['journal'] = run(['journalctl', '-b', '-u', 'user@1003.service', '-n', '80', '--no-pager'])['stdout']
    result['versions'] = run(['rpm', '-q', 'systemd', 'pam', 'selinux-policy-targeted'])['stdout']
    result['passed'] = True
finally:
    def clean(name, action):
        try:
            action()
            cleanup.append(dict(name=name, passed=True))
        except Exception as error:
            cleanup.append(dict(name=name, passed=False, error=str(error)))
    for uid in (1003, 1002):
        clean(f'stop-manager-{uid}', lambda uid=uid: stop(uid))
    clean('restore-permissive', lambda: run(['setenforce', '0']))
    clean('restore-pam', lambda: PAM.write_bytes(original) if original is not None else PAM.unlink(missing_ok=True))
    clean('remove-module', lambda: MODULE.unlink(missing_ok=True))
    if DIRECTORY.exists():
        for file in DIRECTORY.iterdir():
            clean('remove-' + file.name, lambda file=file: file.unlink())
        clean('remove-state-directory', DIRECTORY.rmdir)
    result['vendor_preserved'] = hashlib.sha256(VENDOR.read_bytes()).hexdigest() == vendor_hash
    result['override_restored'] = PAM.read_bytes() == original if original is not None else not PAM.exists()
    result['fixture_removed'] = not MODULE.exists() and not DIRECTORY.exists()
    result['passed'] = bool(result.get('passed') and all(row['passed'] for row in cleanup)
        and result['vendor_preserved'] and result['override_restored'] and result['fixture_removed'])
    Path('/root/manager-systemd-result.json').write_text(json.dumps(result, indent=2) + '\n')
assert result['passed'], result
