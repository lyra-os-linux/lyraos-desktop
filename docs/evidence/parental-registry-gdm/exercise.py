"""VM-only generation-registry admission through native GDM password PAM.

Reuses the PR140 greeter client, diagnostic worker and minimal ELF session.
Requires root files registry-gdm-evidence.py, lyra-registry-gdm.cil,
identity-pam-registry-guard.c, identity-registry-transaction.py,
transition.py (process inventory only), manager-session.c and password-client.py.
"""
import grp
import hashlib
import importlib.util
import json
import os
import pwd
import re
import secrets
import selectors
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0, '/root')
from transition import processes

assert os.geteuid() == 0
assert {'lyra.parental-selinux-test=1', 'lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'
DIRECTORY = Path('/var/lib/lyra-parental-test')

BINDING = dict(user='parentaltest', uid=1003, gid=1004, group='parentaltest')
CONTEXT = 'lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
account = pwd.getpwnam(BINDING['user'])
assert (account.pw_uid, account.pw_gid, grp.getgrgid(account.pw_gid).gr_name) == (1003, 1004, 'parentaltest')
spec = importlib.util.spec_from_file_location('registry_transaction', '/root/identity-registry-transaction.py')
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)
generation = secrets.token_hex(16)
spec = importlib.util.spec_from_file_location('gdm_evidence', '/root/registry-gdm-evidence.py')
gdm_evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gdm_evidence)
MODULE = Path('/usr/lib64/security/pam_lyra_identity_registry_fixture.so')
WORKER = Path('/usr/libexec/gdm/gdm-session-worker')
PATCHED = Path('/root/gdm-official-build/daemon/gdm-session-worker')
BACKUP = Path('/root/manager-worker.backup')
HELPER = Path('/usr/libexec/gdm/gdm-wayland-session')
SESSION = Path('/opt/lyra-parental-probe/manager-session')
CONF = Path('/etc/gdm/custom.conf')
STATE = DIRECTORY / 'identity-registry'
LOCK = DIRECTORY / '.transaction.lock'
POLICY = Path('/root/lyra-registry-gdm.cil')
OFFICIAL_SHA = '40e1387811b74adcde44b8a34f03db1d032190867e1c5f4092bb9aa1362fdab8'
PATCHED_SHA = '92a976fc0e375cd41d1a9330c650241081fd09278d464662a435200cc296704f'
GDM = pwd.getpwnam('gdm')
CLIENT = Path('/root/password-client.py').read_text()
SHADOW = Path('/etc/shadow')
old_shadow = SHADOW.read_bytes()
passwords = {user: secrets.token_hex(24) for user in ('parentaltest', 'ordinaryuser')}
children = []
checks, cleanup = [], []
result = dict(kind='native-gdm-password-generation-registry-admission', full_account_protection=False,
              password_authentication_tested=True, full_gnome_session_tested=False,
              official_worker_sha256=OFFICIAL_SHA, diagnostic_worker_sha256=PATCHED_SHA,
              checks=checks, cleanup=cleanup)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, check=True):
    p = subprocess.run(args, capture_output=True, text=True, timeout=90)
    row = dict(rc=p.returncode, stdout=p.stdout, stderr=p.stderr)
    if check and p.returncode:
        raise RuntimeError((args, row))
    return row


def record(name, **details):
    row = dict(name=name, passed=True, **details)
    checks.append(row)
    assert not any(secret in json.dumps(row) for secret in passwords.values())
    print(json.dumps(dict(name=name, passed=True)), flush=True)


def value(unit, property):
    return run(['systemctl', 'show', unit, '-p', property, '--value'])['stdout'].strip()


def session_processes():
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            if os.readlink(proc / 'exe') == str(SESSION):
                found.append(dict(pid=int(proc.name), context=(proc / 'attr/current').read_text().strip('\x00\n '),
                                  uids=[int(v) for v in next(line for line in (proc / 'status').read_text().splitlines()
                                                           if line.startswith('Uid:')).split()[1:]]))
        except FileNotFoundError:
            continue
    return found


def lease_holders():
    inode = LOCK.stat()
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
                if (info.st_dev, info.st_ino) == (inode.st_dev, inode.st_ino):
                    found.append(dict(pid=int(proc.name), fd=fd.name,
                                      comm=(proc / 'comm').read_text().strip(),
                                      cmdline=(proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode()))
        except FileNotFoundError:
            continue
    return found


def journal(cursor):
    return run(['journalctl', '-b', '--after-cursor=' + cursor, '--no-pager', '-o', 'short'])['stdout']


def start(name, user='parentaltest', allowed=True, missing_module=False,
          block_at_prompt=False, wrong_password=False):
    assert not session_processes()
    CONF.write_text(saved[CONF].decode().replace('[daemon]', '[daemon]\nAutomaticLoginEnable=False')
                    .replace('[debug]', '[debug]\nEnable=true'))
    cursor = json.loads(run(['journalctl', '-n', '1', '-o', 'json'])['stdout'])['__CURSOR']
    if value('gdm.service', 'ActiveState') == 'failed':
        run(['systemctl', 'reset-failed', 'gdm.service'])
    run(['systemctl', 'start', 'gdm.service'])
    manager_pid = int(value('gdm.service', 'MainPID'))
    for _ in range(200):
        log = journal(cursor)
        addresses = list(dict.fromkeys(re.findall(r'D-Bus server for greeters listening on (\S+)', log)))
        if addresses and 'GdmDisplay: session registered: yes' in log:
            break
        time.sleep(.1)
    else:
        raise AssertionError(dict(reason='native greeter did not become ready', journal=log))
    # The greeter itself is a successfully started session. Its startup must
    # precede the cursor used to evaluate the account's password conversation.
    cursor = json.loads(run(['journalctl', '-n', '1', '-o', 'json'])['stdout'])['__CURSOR']

    def drop():
        os.setgroups([])
        os.setgid(GDM.pw_gid)
        os.setuid(GDM.pw_uid)
    child = subprocess.Popen(['python3', '-c', CLIENT, addresses[0], user],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=drop)
    children.append(child)
    selector = selectors.DefaultSelector()
    selector.register(child.stdout, selectors.EVENT_READ)
    buffer = b''
    events = []
    prompts = 0
    observed = denial = None
    answer = secrets.token_hex(24) if wrong_password else passwords[user]
    deadline = time.monotonic() + 40
    try:
        while time.monotonic() < deadline:
            for key, _ in selector.select(.1):
                chunk = os.read(key.fd, 65536)
                assert chunk, dict(reason='protocol client exited early', events=events)
                buffer += chunk
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    row = json.loads(line)
                    events.append(row)
                    assert row['event'] not in ('error', 'timeout'), row
                    if row['event'] == 'connected':
                        assert row['uid'] == GDM.pw_uid
                    if row['event'] == 'password-prompt':
                        prompts += 1
                        assert prompts == 1, 'unexpected second credential request'
                        if block_at_prompt:
                            store.begin(generation)
                            label_registry()
                            rows, pending = store.snapshot()
                            assert pending['phase'] == 'blocked'
                            assert next(r for r in rows if r['generation'] == generation)['state'] == 'transitioning'
                            events.append(dict(event='transitioning-before-password-answer', generation=generation))
                        child.stdin.write((json.dumps(dict(answer=answer)) + '\n').encode())
                        child.stdin.flush()
                        events.append(dict(event='password-answer-sent', correct=not wrong_password))
            current = session_processes()
            log = journal(cursor)
            if allowed and current:
                observed = current
                break
            if not allowed:
                assert not current, current
                if wrong_password:
                    signals = [r.get('name') for r in events if r['event'] == 'signal']
                    failed_auth = any('gdm-password][' in line and 'pam_unix(gdm-password:auth): authentication failure' in line for line in log.splitlines())
                    if failed_auth and 'VerificationFailed' in signals and 'ConversationStopped' in signals:
                        denial = dict(kind='password-authentication-failed')
                else:
                    denial = gdm_evidence.rejection(log, manager_pid, user, missing_module, service='gdm-password')
                if denial:
                    observed = []
                    break
        assert observed is not None and prompts == 1, dict(name=name, events=events, journal=journal(cursor))
        signals = [r.get('name') for r in events if r['event'] == 'signal']
        if allowed:
            assert 'VerificationComplete' in signals and 'SessionOpened' in signals, events
            time.sleep(.3)
            assert session_processes() == observed
            uid = 1003 if user == 'parentaltest' else 1002
            assert all(row['uids'] == [uid] * 4 for row in observed)
            assert all(row['context'] == CONTEXT if uid == 1003 else ':unconfined_t:' in row['context'] for row in observed)
        else:
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                assert not session_processes()
                time.sleep(.05)
            log = journal(cursor)
            assert value('gdm.service', 'MainPID') == str(manager_pid)
            assert not any(f' gdm[{manager_pid}]: ' in line and "Emitting 'session-started' signal" in line for line in log.splitlines())
            if wrong_password:
                assert 'VerificationComplete' not in signals and 'SessionOpened' not in signals
            else:
                worker = f" gdm-password][{denial['worker_pid']}]: "
                assert any(worker in line and 'GdmSessionWorker: state AUTHENTICATED' in line for line in log.splitlines())
                assert any(worker in line and 'GdmSessionWorker: state AUTHORIZED' in line for line in log.splitlines())
                assert gdm_evidence.rejection(log, manager_pid, user, missing_module, service='gdm-password')
        assert answer not in journal(cursor), 'credential unexpectedly logged'
        record(name, user=user, generation=generation, processes=observed, rejection=denial, client_events=events,
               journal=journal(cursor), post_rejection_observation_seconds=2 if not allowed else None)
    finally:
        selector.close()
        if child.poll() is None:
            child.kill()
        child.wait(timeout=10)
        for stream in (child.stdin, child.stdout, child.stderr):
            stream.close()


def stop():
    run(['systemctl', 'stop', 'gdm.service'])
    for uid in (1003, 1002, GDM.pw_uid):
        run(['loginctl', 'terminate-user', str(uid)], check=False)  # Absent session is allowed.
    run(['systemctl', 'stop', 'user@1003.service', 'user@1002.service', f'user@{GDM.pw_uid}.service'])
    for _ in range(100):
        if not processes(1003) and not processes(1002):
            break
        time.sleep(.05)
    assert not processes(1003) and not processes(1002)
    assert not session_processes()


def label_registry():
    # Fixture-only labeling; the writer does not implement product MAC labels.
    run(['chcon', '-R', '-t', 'lyra_registry_state_t', str(DIRECTORY)])


def install_pam():
    fragment = ('session [success=1 default=ignore] pam_succeed_if.so quiet '
                'user != parentaltest uid ne 1003 gid ne 1004\n'
                'session required pam_lyra_identity_registry_fixture.so '
                f'account=active|parentaltest|1003|1004|parentaltest|{generation}\n')
    for name in ('systemd-user', 'gdm-password'):
        target = Path('/etc/pam.d/' + name)
        target.write_text(Path('/usr/lib/pam.d/' + name).read_text() + '\n' + fragment)
        target.chmod(0o644)
        run(['restorecon', str(target)])


def recover():
    # Explicit fixture re-enrollment, never silently reactivate old generation.
    global generation
    assert not processes(1003) and not lease_holders()
    rows, pending = store.snapshot()
    assert pending is not None and pending['old_generation'] == generation
    if pending['phase'] == 'blocked':
        store.tombstone(generation)
    new_generation = secrets.token_hex(16)
    store.publish(generation, dict(state='active', **BINDING, generation=new_generation))
    generation = new_generation
    label_registry()
    install_pam()


assert run(['getenforce'])['stdout'].strip() == 'Permissive'
assert all(value(unit, 'MainPID') == '0' for unit in ('gdm.service', 'user@1003.service', 'user@1002.service'))
assert not any(p.exists() for p in (MODULE, DIRECTORY, BACKUP, SESSION))
assert digest(WORKER) == OFFICIAL_SHA and digest(PATCHED) == PATCHED_SHA
assert not any(line.split()[0] == 'lyra-registry-gdm' for line in run(['semodule', '-l'])['stdout'].splitlines())
paths = [Path('/etc/pam.d/systemd-user'), Path('/etc/pam.d/gdm-password'), CONF,
         Path('/usr/share/wayland-sessions/gnome.desktop'), Path('/usr/share/wayland-sessions/gnome-wayland.desktop'),
         Path('/var/lib/AccountsService/users/parentaltest'), Path('/var/lib/AccountsService/users/ordinaryuser')]
saved = {p: p.read_bytes() if p.exists() else None for p in paths}
helper_label = os.getxattr(HELPER, 'security.selinux')
vendor_hashes = {str(p): digest(p) for p in (Path('/usr/lib/pam.d/gdm-password'), Path('/usr/lib/pam.d/systemd-user'))}
accounts_active = value('accounts-daemon.service', 'ActiveState') == 'active'
installed = False
shutil.copy2(WORKER, BACKUP)
try:
    secret_input = ''.join(user + ':' + password + '\n' for user, password in passwords.items())
    subprocess.run(['chpasswd'], input=secret_input, text=True, check=True, capture_output=True)
    del secret_input
    run(['gcc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror', '-O2',
         '/root/identity-pam-registry-guard.c', '-o', str(MODULE), '-lpam', '-lselinux'])
    run(['gcc', '-Wall', '-Wextra', '-Werror', '-O2', '/root/manager-session.c', '-o', str(SESSION)])
    run(['chcon', '-t', 'lyra_parental_probe_exec_t', str(SESSION)])
    DIRECTORY.mkdir(mode=0o700)
    store = writer.RegistryStore(DIRECTORY)
    store.seed([dict(state='active', **BINDING, generation=generation)])
    install_pam()
    for entry in paths[3:5]:
        entry.write_text('[Desktop Entry]\nName=Admission fixture\nExec=' + str(SESSION) + '\nTryExec=' + str(SESSION)
                         + '\nType=Application\nDesktopNames=LYRA\nX-GDM-SessionRegisters=false\n')
    run(['semodule', '-i', str(POLICY)])
    installed = True
    run(['chcon', '-t', 'lyra_manager_launcher_exec_t', str(HELPER)])
    shutil.copy2(PATCHED, WORKER)
    run(['restorecon', '-R', str(DIRECTORY), str(MODULE), str(WORKER), '/etc/pam.d/gdm-password'])
    label_registry()
    result['source_sha256'] = {Path(p).name: digest(Path(p)) for p in ('/root/identity-pam-registry-guard.c', '/root/identity-registry-transaction.py', '/root/registry-gdm-evidence.py', '/root/password-client.py', '/root/manager-session.c', '/root/transition.py', str(POLICY), __file__)}
    run(['setenforce', '1'])
    start('supervised-password-active')
    holders = lease_holders()
    assert any('gdm-session-worker [pam/gdm-password]' in row['cmdline'] for row in holders), holders
    assert any(row['comm'] == '(sd-pam)' for row in holders), holders
    record('gdm-worker-and-sd-pam-retain-leases', holders=holders)
    prior = session_processes()
    before = store.snapshot()
    try:
        store.begin(generation)
    except writer.StoreError as error:
        assert str(error).startswith('busy:')
        assert store.snapshot() == before and session_processes() == prior
        record('active-gdm-session-retains-generation-and-prevents-transition', error=str(error))
    else:
        raise AssertionError('unsafe transition entered')
    stop()
    assert not lease_holders()
    record('gdm-stop-releases-generation-leases')
    store.begin(generation)
    label_registry()
    start('transitioning-denies-new-gdm-session', allowed=False)
    stop()
    start('ordinary-gdm-preserved-during-transitioning', user='ordinaryuser')
    stop()
    store.tombstone(generation)
    label_registry()
    start('tombstone-denies-old-gdm-generation', allowed=False)
    stop()
    new_generation = secrets.token_hex(16)
    store.publish(generation, dict(state='active', **BINDING, generation=new_generation))
    label_registry()
    start('old-pam-generation-denied-after-enrollment', allowed=False)
    stop()
    generation = new_generation
    install_pam()
    start('explicit-new-generation-admits-gdm')
    stop()
    for fault in ('missing-state', 'corrupt-state', 'missing-module', 'permissive'):
        state_data = STATE.read_bytes()
        saved_module = MODULE.with_suffix('.manager-saved')
        try:
            if fault == 'missing-state': STATE.unlink()
            elif fault == 'corrupt-state': STATE.write_bytes(b'corrupt\n')
            elif fault == 'missing-module': MODULE.rename(saved_module)
            else: run(['setenforce', '0'])
            start(fault + '-gdm-supervised-denied', allowed=False, missing_module=fault == 'missing-module')
            stop()
            start(fault + '-gdm-ordinary-preserved', user='ordinaryuser')
            stop()
        finally:
            if saved_module.exists(): saved_module.rename(MODULE)
            STATE.write_bytes(state_data)
            STATE.chmod(0o600)
            label_registry()
            run(['setenforce', '1'])
    start('final-gdm-supervised-recovered')
    stop()
    # A PAM handle started before the persistent block must recheck on open.
    start('password-conversation-before-block-denied', allowed=False, block_at_prompt=True)
    stop()
    recover()
    start('password-after-pending-conversation-recovery')
    stop()
    start('wrong-password-supervised-denied', allowed=False, wrong_password=True)
    stop()
    start('correct-password-after-auth-failure')
    stop()
    result['versions'] = run(['rpm', '-q', 'gdm', 'systemd', 'pam', 'selinux-policy-targeted'])['stdout']
    result['passed'] = True
finally:
    def clean(name, action):
        try:
            action()
            cleanup.append(dict(name=name, passed=True))
        except Exception as error:
            cleanup.append(dict(name=name, passed=False, error=str(error)))
    for child in children:
        if child.poll() is None:
            clean('stop-protocol-client', child.kill)
            clean('reap-protocol-client', lambda child=child: child.wait(timeout=10))
    clean('stop-fixture-sessions', stop)
    clean('restore-test-passwords', lambda: SHADOW.write_bytes(old_shadow))
    clean('restore-permissive', lambda: run(['setenforce', '0']))
    clean('stop-accounts-before-restoration', lambda: run(['systemctl', 'stop', 'accounts-daemon.service']))
    clean('restore-official-worker', lambda: shutil.copy2(BACKUP, WORKER))
    clean('restore-helper-label', lambda: os.setxattr(HELPER, 'security.selinux', helper_label))
    for p, data in saved.items():
        clean('restore-' + str(p), lambda p=p, data=data: p.unlink(missing_ok=True) if data is None else p.write_bytes(data))
    if accounts_active:
        clean('restore-accounts-daemon', lambda: run(['systemctl', 'start', 'accounts-daemon.service']))
    if digest(WORKER) == OFFICIAL_SHA:
        clean('remove-worker-backup', BACKUP.unlink)
    for p in (MODULE, SESSION):
        clean('remove-' + str(p), lambda p=p: p.unlink(missing_ok=True))
    if DIRECTORY.exists():
        for p in DIRECTORY.iterdir():
            clean('remove-' + str(p), lambda p=p: p.unlink())
        clean('remove-state-directory', DIRECTORY.rmdir)
    if installed:
        clean('remove-launcher-policy', lambda: run(['semodule', '-r', 'lyra-registry-gdm']))
    result['vendor_preserved'] = all(digest(Path(p)) == sha for p, sha in vendor_hashes.items())
    result['official_worker_restored'] = digest(WORKER) == OFFICIAL_SHA
    result['helper_label_restored'] = os.getxattr(HELPER, 'security.selinux') == helper_label
    result['files_restored'] = all(p.read_bytes() == data if data is not None else not p.exists() for p, data in saved.items())
    result['passwords_restored'] = SHADOW.read_bytes() == old_shadow
    result['fixture_removed'] = not any(p.exists() for p in (MODULE, SESSION, DIRECTORY, BACKUP))
    result['managers_stopped'] = all(value(unit, 'MainPID') == '0' for unit in ('gdm.service', 'user@1003.service', 'user@1002.service', f'user@{GDM.pw_uid}.service'))
    result['permissive_restored'] = run(['getenforce'])['stdout'].strip() == 'Permissive'
    result['fixture_processes_gone'] = not processes(1003) and not processes(1002)
    result['passed'] = bool(result.get('passed') and all(row['passed'] for row in cleanup)
        and all(result[k] for k in ('vendor_preserved', 'official_worker_restored', 'helper_label_restored', 'files_restored', 'fixture_removed', 'passwords_restored', 'managers_stopped', 'permissive_restored', 'fixture_processes_gone')))
    assert not any(secret in json.dumps(result) for secret in passwords.values()), 'credential present in exported evidence'
    Path('/root/registry-gdm-result.json').write_text(json.dumps(result, indent=2) + '\n')
assert result['passed'], result
