"""Native user manager/lingering proof with generation registry, only in VM.

Uses vendor systemd-user PAM plus the experimental guard. No login, logout,
GDM, credential prompt or production account lifecycle is simulated here.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import secrets
import subprocess
import time

assert os.geteuid() == 0
assert {'lyra.parental-selinux-test=1', 'lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'

DIRECTORY = Path('/var/lib/lyra-parental-test')
PAM = Path('/etc/pam.d/systemd-user')
VENDOR = Path('/usr/lib/pam.d/systemd-user')
MODULE = Path('/usr/lib64/security/pam_lyra_identity_registry_fixture.so')
SAVED_MODULE = MODULE.with_suffix('.lifetime-saved')
GUARD = Path('/root/identity-pam-registry-guard.c')
WRITER = Path('/root/identity-registry-transaction.py')
CONTEXT = 'lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
IDENTITY = dict(user='parentaltest', uid=1003, gid=1004, group='parentaltest')
checks, cleanup = [], []
result = dict(kind='native-generation-registry-user-manager-lingering',
              full_account_protection=False, login_logout_tested=False,
              checks=checks, cleanup=cleanup)
spec = importlib.util.spec_from_file_location('registry_transaction', WRITER)
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)


def run(argv, check=True):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    row = dict(rc=p.returncode, stdout=p.stdout, stderr=p.stderr)
    if check and p.returncode:
        raise RuntimeError((argv, row))
    return row


def record(name, passed=True, **detail):
    row = dict(name=name, passed=bool(passed), **detail)
    checks.append(row)
    print(json.dumps(row), flush=True)
    assert passed, row


def show(uid):
    data = run(['systemctl', 'show', f'user@{uid}.service', '-p', 'MainPID',
                '-p', 'ActiveState', '-p', 'Result', '-p', 'ExecMainStatus'])['stdout']
    return dict(line.split('=', 1) for line in data.splitlines())


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
        context = Path(f"/proc/{state['MainPID']}/attr/current").read_text().strip('\x00\n ')
        assert (context == CONTEXT) if uid == 1003 else ':unconfined_t:' in context, context
        record(name, unit=state, context=context)
    else:
        assert launched['rc'] != 0 and state['MainPID'] == '0' and state['ExecMainStatus'] == '224', (launched, state)
        record(name, unit=state, command=launched)


def holders():
    identity = (DIRECTORY / '.transaction.lock').stat()
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


def busy(name, generation):
    rows_before, journal_before = store.snapshot()
    try:
        store.begin(generation)
    except writer.StoreError as error:
        assert str(error).startswith('busy:'), str(error)
        message = str(error)
    else:
        raise AssertionError('exclusive transaction admitted while manager is live')
    rows_after, journal_after = store.snapshot()
    assert (rows_after, journal_after) == (rows_before, journal_before)
    lease_holders = holders()
    assert any(row['comm'] == '(sd-pam)' for row in lease_holders), lease_holders
    record(name, error=message, holders=lease_holders,
           registry_unchanged=True, new_admission_still_active=True)


def install_pam(generation):
    text = VENDOR.read_text() + '\n'
    text += ('session [success=1 default=ignore] pam_succeed_if.so quiet '
             'user != parentaltest uid ne 1003 gid ne 1004\n')
    text += ('session required pam_lyra_identity_registry_fixture.so '
             f'account=active|parentaltest|1003|1004|parentaltest|{generation}\n')
    PAM.write_text(text)
    PAM.chmod(0o644)
    run(['restorecon', str(PAM)])


def wait_active(uid, seconds=20):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        state = show(uid)
        if state['ActiveState'] == 'active':
            return state
        if state['ActiveState'] == 'failed':
            raise AssertionError(('linger manager failed', state))
        time.sleep(0.2)
    raise AssertionError(('linger did not start manager', show(uid)))


def uid_processes(uid):
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            status = (proc / 'status').read_text().splitlines()
            ids = next(line.split()[1:] for line in status if line.startswith('Uid:'))
            if str(uid) in ids:
                found.append(dict(pid=int(proc.name), comm=(proc / 'comm').read_text().strip()))
        except FileNotFoundError:
            continue
    return found


def logind_sessions():
    found = []
    for line in run(['loginctl', 'list-sessions', '--no-legend'])['stdout'].splitlines():
        sid = line.split()[0]
        data = run(['loginctl', 'show-session', sid, '-p', 'Id', '-p', 'User',
                    '-p', 'Name', '-p', 'Class', '-p', 'Service', '-p', 'State'])['stdout']
        found.append(dict(item.split('=', 1) for item in data.splitlines()))
    return found


def wait_logind_cleanup(uid, user):
    end = time.monotonic() + 20
    while time.monotonic() < end:
        state = run(['systemctl', 'show', f'user-runtime-dir@{uid}.service', '-p', 'ActiveState'])['stdout']
        known = run(['loginctl', 'show-user', user], check=False)['rc'] == 0
        if not known and state.strip() == 'ActiveState=inactive' and not uid_processes(uid):
            return
        time.sleep(0.2)
    raise AssertionError(('logind has not drained fixture user', uid, state, known))


assert run(['getenforce'])['stdout'].strip() == 'Permissive'
assert all(show(uid)['MainPID'] == '0' and not uid_processes(uid) for uid in (1003, 1002))
assert not run(['loginctl', 'list-sessions', '--no-legend'])['stdout'].strip()
assert all(not (Path('/var/lib/systemd/linger') / user).exists() for user in ('parentaltest', 'ordinaryuser'))
assert not MODULE.exists() and not SAVED_MODULE.exists() and not DIRECTORY.exists()
pw = pwd.getpwnam('parentaltest')
assert (pw.pw_uid, pw.pw_gid) == (1003, 1004)
original_pam = PAM.read_bytes() if PAM.exists() else None
original_mode = PAM.stat().st_mode & 0o777 if PAM.exists() else None
vendor_hash = hashlib.sha256(VENDOR.read_bytes()).hexdigest()
account_hashes = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in ('/etc/passwd', '/etc/group')}
gen_a, gen_b = secrets.token_hex(16), secrets.token_hex(16)
module_created = state_created = pam_changed = linger_attempted = False
cursor = next(line.removeprefix('-- cursor: ') for line in
              run(['journalctl', '-n', '0', '--show-cursor', '--no-pager'])['stdout'].splitlines()
              if line.startswith('-- cursor: '))

try:
    run(['gcc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror', '-O2', str(GUARD), '-o', str(MODULE), '-lpam', '-lselinux'])
    module_created = True
    MODULE.chmod(0o755)
    run(['restorecon', str(MODULE)])
    DIRECTORY.mkdir(mode=0o700)
    state_created = True
    run(['restorecon', str(DIRECTORY)])
    store = writer.RegistryStore(DIRECTORY)
    store.seed([dict(state='active', **IDENTITY, generation=gen_a)])
    pam_changed = True
    install_pam(gen_a)
    result['source_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (GUARD, WRITER, Path(__file__))}
    result['module_sha256'] = hashlib.sha256(MODULE.read_bytes()).hexdigest()
    run(['setenforce', '1'])
    start('generation-a-native-manager-admitted')
    start('ordinary-native-manager-preserved', 1002)
    busy('sd-pam-keeps-generation-lease', gen_a)
    stop(1003)
    record('stop-releases-generation-lease', passed=not holders() and not uid_processes(1003))
    store.begin(gen_a)
    start('transitioning-denies-native-manager', allowed=False)
    stop(1002)
    start('ordinary-during-transitioning-preserved', 1002)
    store.tombstone(gen_a)
    start('tombstone-denies-old-native-generation', allowed=False)
    store.publish(gen_a, dict(state='active', **IDENTITY, generation=gen_b))
    start('old-pam-generation-denied-after-new-enrollment', allowed=False)
    install_pam(gen_b)
    start('new-generation-native-manager-admitted')
    stop(1003)
    # An exclusive writer must produce a PAM denial, not an unbounded wait.
    with store._locked(nonblocking=True):
        start('exclusive-writer-lock-denies-native-pam-without-wait', allowed=False)
        stop(1002)
        start('ordinary-preserved-during-exclusive-writer-lock', 1002)
    start('native-manager-recovers-after-writer-lock-released')
    stop(1003)

    linger_attempted = True
    run(['loginctl', 'enable-linger', 'parentaltest'])
    state = wait_active(1003)
    sessions = logind_sessions()
    properties = run(['loginctl', 'show-user', 'parentaltest', '-p', 'Linger', '-p', 'State', '-p', 'Sessions'])['stdout']
    # systemd-user PAM can register Class=manager; that is not a user login.
    record('linger-has-no-interactive-or-remote-login-session',
           passed=all(s['Class'] == 'manager' and s['User'] in ('1003', '1002') for s in sessions)
                  and 'Linger=yes' in properties,
           sessions=sessions, logind=properties)
    assert Path(f"/proc/{state['MainPID']}/attr/current").read_text().strip('\x00\n ') == CONTEXT
    record('linger-starts-supervised-manager-without-login-session', unit=state, logind=properties)
    busy('linger-with-no-login-sessions-still-prevents-transition', gen_b)
    run(['systemctl', 'reload', 'user@1003.service'])
    assert show(1003)['ActiveState'] == 'active'
    busy('linger-reexec-retains-generation-lease', gen_b)
    assert show(1002)['ActiveState'] == 'active'
    record('ordinary-manager-remains-active-during-linger')
    run(['loginctl', 'disable-linger', 'parentaltest'])
    # Observe logind behavior; disabling linger alone is not a stop contract.
    record('disable-linger-recorded-without-assuming-process-exit',
           unit=show(1003), uid_processes=uid_processes(1003),
           logind=run(['loginctl', 'show-user', 'parentaltest', '-p', 'Linger', '-p', 'State', '-p', 'Sessions'], check=False))
    stop(1003)
    assert not uid_processes(1003) and not holders()
    record('explicit-stop-leaves-no-fixture-process-or-lease')
    stop(1002)
    wait_logind_cleanup(1003, 'parentaltest')
    wait_logind_cleanup(1002, 'ordinaryuser')
    record('logind-runtime-and-user-records-drained-before-restart')

    registry = DIRECTORY / 'identity-registry'
    for fault in ('missing-registry', 'corrupt-registry', 'missing-module', 'permissive'):
        saved = registry.read_bytes()
        try:
            if fault == 'missing-registry': registry.unlink()
            elif fault == 'corrupt-registry': registry.write_bytes(b'corrupt\n')
            elif fault == 'missing-module': MODULE.rename(SAVED_MODULE)
            else: run(['setenforce', '0'])
            start(fault + '-supervised-denied', allowed=False)
            start(fault + '-ordinary-preserved', 1002)
            stop(1002)
        finally:
            if SAVED_MODULE.exists(): SAVED_MODULE.rename(MODULE)
            registry.write_bytes(saved)
            registry.chmod(0o600)
            run(['restorecon', str(registry)])
            run(['setenforce', '1'])
        assert not holders(), ('denied PAM leaked lease', fault)
    start('final-supervised-native-recovered')
    start('final-ordinary-native-preserved', 1002)
    result['passed'] = True
finally:
    def clean(name, action):
        try:
            action()
            cleanup.append(dict(name=name, passed=True))
        except Exception as error:
            cleanup.append(dict(name=name, passed=False, error=str(error)))
    if linger_attempted:
        clean('disable-fixture-linger', lambda: run(['loginctl', 'disable-linger', 'parentaltest']))
    for uid in (1003, 1002):
        clean(f'stop-manager-{uid}', lambda uid=uid: stop(uid))
    clean('restore-permissive', lambda: run(['setenforce', '0']))
    if pam_changed:
        def restore_pam():
            if original_pam is None:
                PAM.unlink(missing_ok=True)
            else:
                PAM.write_bytes(original_pam)
                PAM.chmod(original_mode)
                run(['restorecon', str(PAM)])
        clean('restore-pam-override', restore_pam)
    if module_created:
        clean('remove-fixture-module', lambda: MODULE.unlink(missing_ok=True))
        clean('remove-saved-fixture-module', lambda: SAVED_MODULE.unlink(missing_ok=True))
    if state_created:
        def remove_state():
            for file in DIRECTORY.iterdir():
                file.unlink()
            DIRECTORY.rmdir()
        clean('remove-fixture-registry', remove_state)
    result['journal'] = run(['journalctl', '--after-cursor', cursor, '-u', 'user@1003.service', '-u', 'user@1002.service', '--no-pager'], check=False)
    result['versions'] = run(['rpm', '-q', 'systemd', 'pam', 'selinux-policy-targeted'], check=False)
    result['restored'] = dict(
        pam_bytes=PAM.read_bytes() == original_pam if original_pam is not None else not PAM.exists(),
        pam_mode=(PAM.stat().st_mode & 0o777) == original_mode if original_pam is not None else not PAM.exists(),
        vendor_pam=hashlib.sha256(VENDOR.read_bytes()).hexdigest() == vendor_hash,
        account_files=all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest for p, digest in account_hashes.items()),
        fixture_removed=not DIRECTORY.exists() and not MODULE.exists() and not SAVED_MODULE.exists(),
        linger_removed=not (Path('/var/lib/systemd/linger') / 'parentaltest').exists(),
        managers_stopped=all(show(uid)['MainPID'] == '0' for uid in (1003, 1002)),
        fixture_processes_gone=all(not uid_processes(uid) for uid in (1003, 1002)),
        permissive=run(['getenforce'])['stdout'].strip() == 'Permissive')
    result['passed'] = bool(result.get('passed') and all(row['passed'] for row in cleanup)
                            and all(result['restored'].values()) and result['journal']['rc'] == 0)
    Path('/root/identity-native-registry-manager-result.json').write_text(json.dumps(result, indent=2) + '\n')
assert result['passed'], result
