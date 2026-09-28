"""Native fixture only. No real login entry point is modified."""
import importlib.util
import json
import os
from pathlib import Path
import pwd
import grp
import signal
import subprocess
import time

assert os.geteuid() == 0
assert 'lyra.parental-identity-test=1' in Path('/proc/cmdline').read_text().split()
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'
signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(143)))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


transition = load('transition', '/root/transition.py')
bindings = load('bindings', '/root/identity-bindings.py')
MODULE = Path('/usr/lib64/security/pam_lyra_transition_fixture.so')
PAM = Path('/etc/pam.d/lyra-transition-probe')
DIRECTORY = transition.DIRECTORY
PROBE = '/opt/lyra-parental-probe/probe'
CONTEXT = 'lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
children, checks, cleanup = [], [], []
result = dict(kind='experimental-admission-transition', full_account_protection=False,
              checks=checks, cleanup=cleanup)


def cmd(args):
    return subprocess.run(args, capture_output=True, text=True, check=True, timeout=90).stdout


def record(name, **details):
    row = dict(name=name, passed=True, **details)
    checks.append(row)
    print(json.dumps(row), flush=True)


def account(name):
    p = pwd.getpwnam(name)
    return dict(user=name, uid=p.pw_uid, gid=p.pw_gid, group=grp.getgrgid(p.pw_gid).gr_name)


def test(name, user='identitytest', expected=70, approved=False):
    args = [PROBE] if approved else ['/usr/bin/python3', '-c', 'print("PAYLOAD_EXECUTED")']
    p = subprocess.run(['python3', '/root/transition-pam-probe.py', user, *args],
                       capture_output=True, text=True, timeout=20)
    assert p.returncode == expected, (name, p.returncode, p.stdout, p.stderr)
    entry = json.loads(p.stdout.splitlines()[0])
    assert bool(entry['pam_open_rc']) == (expected == 70), (name, entry)
    if expected:
        assert 'PAYLOAD_EXECUTED' not in p.stdout
    elif approved:
        assert f'uid={pwd.getpwnam(user).pw_uid} context={CONTEXT}' in p.stdout
    else:
        assert 'PAYLOAD_EXECUTED' in p.stdout
    if expected == 126:
        assert '"exec_errno": 13' in p.stdout
    record(name, rc=p.returncode, stdout=p.stdout, stderr=p.stderr)


def start(mode):
    child = subprocess.Popen(['python3', '/root/transition-pam-probe.py', 'identitytest', PROBE],
        env=dict(os.environ, LYRA_FIXTURE_MODE=mode), stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    children.append(child)
    line = json.loads(child.stdout.readline())
    assert line == {'pam_started': True} if mode == 'delayed' else line['pam_open_rc'] == 0, line
    return child


def send(child, value):
    child.stdin.write(value + '\n'); child.stdin.flush()


def busy(name, gate):
    try:
        with gate.transition():
            raise AssertionError('unsafe transition was entered')
    except transition.Busy as error:
        record(name, reason=str(error))


def recover(gate):
    with gate.transition():
        pass


assert not MODULE.exists() and not PAM.exists() and not DIRECTORY.exists()
assert 'identitytest' not in {p.pw_name for p in pwd.getpwall()}
assert 'identitytest' not in {g.gr_name for g in grp.getgrall()}
before = {name: account(name) for name in ('parentaltest', 'ordinaryuser')}
initial_enforcing = cmd(['getenforce']).strip()
assert initial_enforcing == 'Permissive'
uid = next(i for i in range(21000, 22000) if i not in {p.pw_uid for p in pwd.getpwall()})
gid = next(i for i in range(23000, 24000) if i not in {g.gr_gid for g in grp.getgrall()})
created_group = created_user = mapped = False
units = []
try:
    cmd(['gcc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror', '-O2',
         '/root/transition-pam-guard.c', '-o', str(MODULE), '-lpam', '-lselinux'])
    cmd(['groupadd', '-g', str(gid), 'identitytest']); created_group = True
    cmd(['useradd', '-M', '-u', str(uid), '-g', str(gid), 'identitytest']); created_user = True
    cmd(['semanage', 'login', '-a', '-s', 'lyra_parental_u', '-r', 's0', 'identitytest']); mapped = True
    roster = [account('parentaltest'), account('identitytest')]
    result['bindings'] = roster
    DIRECTORY.mkdir(mode=0o700)
    first, gate = [transition.Gate(item) for item in roster]
    for item in (first, gate):
        item.initialize()
    # Existing-account control, not an enrollment claim about the original fixture.
    with first.directory() as directory:
        first.write_state(directory, first.record)
    recover(gate)
    state = DIRECTORY / f'{uid}.state'
    lock = DIRECTORY / f'{uid}.lock'
    PAM.write_text('session required pam_selinux.so close\nsession required pam_selinux.so open nottys\n' +
                   bindings.render(roster).replace('pam_lyra_identity_fixture.so', 'pam_lyra_transition_fixture.so'))
    PAM.chmod(0o644); MODULE.chmod(0o755)
    cmd(['restorecon', '-R', str(DIRECTORY), str(PAM), str(MODULE)])
    cmd(['setenforce', '1'])
    for user in ('parentaltest', 'identitytest'):
        test('approved-' + user, user, 0, True)
        test('python-denied-' + user, user, 126)
    test('ordinary-healthy', 'ordinaryuser', 0)

    with gate.transition():
        test('during-transition-denied')
        test('other-supervised-during-transition', 'parentaltest', 0, True)
        test('ordinary-during-transition', 'ordinaryuser', 0)
        busy('concurrent-writer-refused', gate)
    test('after-transition-approved', expected=0, approved=True)

    for mode in ('hold', 'end', 'fork-end'):
        child = start(mode)
        busy(mode + '-live-pam-lease', gate)
        test(mode + '-new-session-denied')
        send(child, 'close')
        if mode == 'fork-end':
            assert json.loads(child.stdout.readline()) == {'child_pam_end': True}
            busy('child-pam-end-preserves-parent-lease', gate)
            send(child, 'close')
        assert child.wait(timeout=15) == 0, child.stderr.read()
        recover(gate)
        test(mode + '-recovered', expected=0, approved=True)

    child = start('delayed')
    try:
        with gate.transition():
            raise RuntimeError('injected operation failure')
    except RuntimeError as error:
        assert str(error) == 'injected operation failure'
    assert state.read_bytes() == b'blocked\n'
    send(child, 'open')
    output, error = child.communicate(timeout=15)
    assert child.returncode == 70 and json.loads(output.splitlines()[0])['pam_open_rc'] != 0
    record('preexisting-pam-handle-observes-persistent-block', rc=child.returncode, stdout=output, stderr=error)
    recover(gate)

    code = "import json,signal; from transition import Gate; g=Gate(json.loads(" + repr(json.dumps(roster[1])) + "));\nwith g.transition():\n print('leased',flush=True)\n signal.pause()"
    child = subprocess.Popen(['python3', '-u', '-c', code], cwd='/root', stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    children.append(child)
    assert child.stdout.readline().strip() == 'leased'
    child.kill(); assert child.wait(timeout=15) == -signal.SIGKILL
    assert state.read_bytes() == b'blocked\n'
    test('sigkill-leaves-admission-blocked')
    test('ordinary-after-writer-sigkill', 'ordinaryuser', 0)
    recover(transition.Gate(roster[1]))
    test('fresh-controller-recovers-after-sigkill', expected=0, approved=True)

    unit = 'lyra-parental-transition-orphan.service'; units.append(unit)
    cmd(['systemd-run', '--unit=' + unit, '--uid=' + str(uid), '/usr/bin/sleep', 'infinity'])
    for _ in range(100):
        pid = int(cmd(['systemctl', 'show', '-p', 'MainPID', '--value', unit]).strip())
        if pid and uid in transition.process_owners(Path(f'/proc/{pid}/status').read_text()):
            break
        time.sleep(.05)
    else:
        raise AssertionError('fixture process did not start')
    assert '/system.slice/' + unit in Path(f'/proc/{pid}/cgroup').read_text()
    logout = subprocess.run(['loginctl', 'terminate-user', str(uid)], capture_output=True, text=True, timeout=15)
    assert Path(f'/proc/{pid}').exists()
    record('process-outside-logind-survives-terminate-user', pid=pid, logout_rc=logout.returncode)
    busy('remaining-process-refuses-transition', gate)
    assert Path(f'/proc/{pid}').exists()
    test('remaining-process-new-admission-denied')
    test('ordinary-with-other-process-remaining', 'ordinaryuser', 0)
    cmd(['systemctl', 'stop', unit]); units.remove(unit)
    recover(gate)
    test('after-process-stopped-approved', expected=0, approved=True)

    try:
        try:
            with gate.transition():
                cmd(['usermod', '-g', str(before['ordinaryuser']['gid']), 'identitytest'])
        except RuntimeError as error:
            assert 'identity changed' in str(error)
            record('identity-change-refuses-commit')
        else:
            raise AssertionError('identity change was accepted')
        assert state.read_bytes() == b'blocked\n'
        test('changed-identity-stays-denied')
    finally:
        cmd(['usermod', '-g', str(gid), 'identitytest'])
    test('restoring-identity-alone-does-not-open')
    recover(gate)

    original_write = gate.write_state
    def fail_after_active_write(directory, value):
        original_write(directory, value)
        if value == gate.record:
            raise OSError('injected error after active publication')
    gate.write_state = fail_after_active_write
    try:
        try:
            recover(gate)
        except OSError as error:
            assert str(error) == 'injected error after active publication'
        else:
            raise AssertionError('injected storage error was ignored')
        assert state.read_bytes() == b'blocked\n'
        test('failed-final-publication-restores-block')
        test('ordinary-after-final-publication-error', 'ordinaryuser', 0)
    finally:
        gate.write_state = original_write
    recover(gate)

    for name, value in [('corrupt', b'active\n'), ('other-identity', first.record), ('trailing-data', gate.record + b'x')]:
        state.write_bytes(value)
        test('gate-' + name)
        test('ordinary-gate-' + name, 'ordinaryuser', 0)
        recover(gate)
    state.chmod(0o666)
    try:
        test('writable-state-denied')
        test('ordinary-writable-state', 'ordinaryuser', 0)
    finally:
        state.chmod(0o600)
    backup = state.with_suffix('.saved')
    state.rename(backup)
    try:
        test('missing-state-denied')
        test('ordinary-missing-state', 'ordinaryuser', 0)
        state.symlink_to(backup.name)
        test('symlink-state-denied')
        state.unlink()
        os.link(backup, state)
        test('hardlink-state-denied')
        state.unlink()
    finally:
        if state.is_symlink(): state.unlink()
        backup.replace(state)
    backup = lock.with_suffix('.saved')
    lock.rename(backup)
    try:
        test('missing-lease-file-denied')
        test('ordinary-missing-lease-file', 'ordinaryuser', 0)
    finally:
        backup.rename(lock)
    DIRECTORY.chmod(0o777)
    try:
        test('writable-directory-denied')
        test('ordinary-writable-directory', 'ordinaryuser', 0)
    finally:
        DIRECTORY.chmod(0o700)
    cmd(['setenforce', '0'])
    try:
        test('permissive-still-denied')
        recover(gate)  # failed open_session must not leak its lease
        record('failed-selinux-check-releases-lease')
    finally:
        cmd(['setenforce', '1'])
    test('final-approved', expected=0, approved=True)
    test('final-python-denied', expected=126)
    test('final-ordinary', 'ordinaryuser', 0)
    result['passed'] = True
finally:
    def clean(name, action):
        try:
            action(); cleanup.append(dict(name=name, passed=True))
        except Exception as error:
            cleanup.append(dict(name=name, passed=False, error=str(error)))
    for child in children:
        if child.poll() is None:
            clean('kill-fixture-helper', child.kill)
            clean('reap-fixture-helper', lambda: child.wait(timeout=15))
    for unit in units:
        clean('stop-' + unit, lambda unit=unit: cmd(['systemctl', 'stop', unit]))
    clean('restore-permissive', lambda: cmd(['setenforce', '0']))
    if mapped: clean('remove-fixture-mapping', lambda: cmd(['semanage', 'login', '-d', 'identitytest']))
    if created_user: clean('remove-fixture-account', lambda: cmd(['userdel', 'identitytest']))
    if created_group and 'identitytest' in {g.gr_name for g in grp.getgrall()}:
        clean('remove-fixture-group', lambda: cmd(['groupdel', 'identitytest']))
    clean('remove-fixture-pam', lambda: PAM.unlink(missing_ok=True))
    clean('remove-fixture-module', lambda: MODULE.unlink(missing_ok=True))
    if DIRECTORY.exists():
        for file in DIRECTORY.iterdir():
            clean('remove-' + file.name, lambda file=file: file.unlink())
        clean('remove-fixture-directory', DIRECTORY.rmdir)
    result['original_accounts_preserved'] = before == {name: account(name) for name in before}
    result['fixture_removed'] = not (PAM.exists() or MODULE.exists() or DIRECTORY.exists() or
        'identitytest' in {p.pw_name for p in pwd.getpwall()} or 'identitytest' in {g.gr_name for g in grp.getgrall()})
    result['passed'] = bool(result.get('passed') and all(c['passed'] for c in cleanup)
        and result['original_accounts_preserved'] and result['fixture_removed'])
    Path('/root/transition-results.json').write_text(json.dumps(result, indent=2) + '\n')
assert result['passed'], result
