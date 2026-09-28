"""Native GDM autologin admission, using the earlier diagnostic worker.

VM-only: minimal ELF session, not a GNOME or password-authentication test.
Requires /root/{transition.py,identity-bindings.py,transition-pam-guard.c,
manager-session.c,lyra-manager-launcher.cil} plus the prior GDM build.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0, '/root')
from transition import Gate, Busy, DIRECTORY, processes

BINDING = dict(user='parentaltest', uid=1003, gid=1004, group='parentaltest')
CONTEXT = 'lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
gate = Gate(BINDING)  # Verifies root and the exact disposable disk/boot marker.
gate.check_identity()
spec = importlib.util.spec_from_file_location('bindings', '/root/identity-bindings.py')
bindings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bindings)
MODULE = Path('/usr/lib64/security/pam_lyra_transition_fixture.so')
WORKER = Path('/usr/libexec/gdm/gdm-session-worker')
PATCHED = Path('/root/gdm-official-build/daemon/gdm-session-worker')
BACKUP = Path('/root/manager-worker.backup')
HELPER = Path('/usr/libexec/gdm/gdm-wayland-session')
SESSION = Path('/opt/lyra-parental-probe/manager-session')
CONF = Path('/etc/gdm/custom.conf')
STATE = DIRECTORY / '1003.state'
LOCK = DIRECTORY / '1003.lock'
POLICY = Path('/root/lyra-manager-launcher.cil')
OFFICIAL_SHA = '40e1387811b74adcde44b8a34f03db1d032190867e1c5f4092bb9aa1362fdab8'
PATCHED_SHA = '92a976fc0e375cd41d1a9330c650241081fd09278d464662a435200cc296704f'
checks, cleanup = [], []
result = dict(kind='native-gdm-autologin-admission', full_account_protection=False,
              password_authentication_tested=False, full_gnome_session_tested=False,
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
    print(json.dumps(row), flush=True)


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


def start(name, user='parentaltest', allowed=True, missing_module=False):
    assert not session_processes()
    CONF.write_text(saved[CONF].decode().replace('[daemon]', '[daemon]\nAutomaticLoginEnable=True\nAutomaticLogin=' + user)
                    .replace('[debug]', '[debug]\nEnable=true'))
    cursor = json.loads(run(['journalctl', '-n', '1', '-o', 'json'])['stdout'])['__CURSOR']
    if value('gdm.service', 'ActiveState') == 'failed':
        run(['systemctl', 'reset-failed', 'gdm.service'])
    run(['systemctl', 'start', 'gdm.service'])
    observed = None
    for _ in range(100):
        current = session_processes()
        log = journal(cursor)
        if allowed and current:
            observed = current
            break
        denial = 'PAM unable to dlopen' if missing_module else 'Experimental supervised admission rejected session'
        if not allowed and any('gdm-autologin][' in line and denial in line for line in log.splitlines()):
            assert not current, current
            observed = []
            break
        time.sleep(.1)
    assert observed is not None, dict(name=name, journal=journal(cursor), processes=session_processes())
    if allowed:
        time.sleep(.3)
        assert session_processes() == observed, 'session exited after admission'
        uid = 1003 if user == 'parentaltest' else 1002
        assert all(row['uids'] == [uid] * 4 for row in observed), observed
        assert all(row['context'] == CONTEXT if uid == 1003 else ':unconfined_t:' in row['context'] for row in observed)
    record(name, processes=observed, journal=journal(cursor),
           sessions=run(['loginctl', 'list-sessions', '--no-legend'])['stdout'])


def stop():
    run(['systemctl', 'stop', 'gdm.service'])
    for uid in (1003, 1002):
        run(['loginctl', 'terminate-user', str(uid)], check=False)  # Absent session is allowed.
    run(['systemctl', 'stop', 'user@1003.service', 'user@1002.service'])
    for _ in range(100):
        if not processes(1003) and not processes(1002):
            break
        time.sleep(.05)
    assert not processes(1003) and not processes(1002)
    assert not session_processes()


def recover():
    with gate.transition():
        pass


assert run(['getenforce'])['stdout'].strip() == 'Permissive'
assert all(value(unit, 'MainPID') == '0' for unit in ('gdm.service', 'user@1003.service', 'user@1002.service'))
assert not any(p.exists() for p in (MODULE, DIRECTORY, BACKUP, SESSION))
assert digest(WORKER) == OFFICIAL_SHA and digest(PATCHED) == PATCHED_SHA
assert not any(line.split()[0] == 'lyra-manager-launcher' for line in run(['semodule', '-l'])['stdout'].splitlines())
paths = [Path('/etc/pam.d/systemd-user'), Path('/etc/pam.d/gdm-autologin'), CONF,
         Path('/usr/share/wayland-sessions/gnome.desktop'), Path('/usr/share/wayland-sessions/gnome-wayland.desktop'),
         Path('/var/lib/AccountsService/users/parentaltest'), Path('/var/lib/AccountsService/users/ordinaryuser')]
saved = {p: p.read_bytes() if p.exists() else None for p in paths}
helper_label = os.getxattr(HELPER, 'security.selinux')
vendor_hashes = {str(p): digest(p) for p in (Path('/usr/lib/pam.d/gdm-autologin'), Path('/usr/lib/pam.d/systemd-user'))}
accounts_active = value('accounts-daemon.service', 'ActiveState') == 'active'
installed = False
shutil.copy2(WORKER, BACKUP)
try:
    run(['gcc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror', '-O2',
         '/root/transition-pam-guard.c', '-o', str(MODULE), '-lpam', '-lselinux'])
    run(['gcc', '-Wall', '-Wextra', '-Werror', '-O2', '/root/manager-session.c', '-o', str(SESSION)])
    run(['chcon', '-t', 'lyra_parental_probe_exec_t', str(SESSION)])
    DIRECTORY.mkdir(mode=0o700)
    gate.initialize()
    recover()
    fragment = bindings.render([BINDING]).replace('pam_lyra_identity_fixture.so', 'pam_lyra_transition_fixture.so')
    for name in ('systemd-user', 'gdm-autologin'):
        target = Path('/etc/pam.d/' + name)
        target.write_text(Path('/usr/lib/pam.d/' + name).read_text() + '\n' + fragment)
        target.chmod(0o644)
    for entry in paths[3:5]:
        entry.write_text('[Desktop Entry]\nName=Admission fixture\nExec=' + str(SESSION) + '\nTryExec=' + str(SESSION)
                         + '\nType=Application\nDesktopNames=LYRA\nX-GDM-SessionRegisters=false\n')
    run(['semodule', '-i', str(POLICY)])
    installed = True
    run(['chcon', '-t', 'lyra_manager_launcher_exec_t', str(HELPER)])
    shutil.copy2(PATCHED, WORKER)
    run(['restorecon', '-R', str(DIRECTORY), str(MODULE), str(WORKER), '/etc/pam.d/gdm-autologin'])
    run(['setenforce', '1'])
    start('supervised-autologin-active')
    holders = lease_holders()
    assert any('gdm-session-worker [pam/gdm-autologin]' in row['cmdline'] for row in holders), holders
    assert any(row['comm'] == '(sd-pam)' for row in holders), holders
    record('gdm-worker-and-sd-pam-retain-leases', holders=holders)
    prior = session_processes()
    try:
        with gate.transition():
            raise AssertionError('unsafe transition entered')
    except Busy:
        assert STATE.read_bytes() == b'blocked\n' and session_processes() == prior
        record('active-gdm-session-prevents-transition-and-remains-alive')
    stop()
    assert not lease_holders()
    record('gdm-stop-releases-leases')
    start('new-gdm-session-denied-after-block', allowed=False)
    stop()
    start('ordinary-gdm-preserved-during-block', user='ordinaryuser')
    stop()
    recover()
    start('explicit-recovery-admits-gdm')
    stop()
    for fault in ('missing-state', 'missing-module', 'permissive'):
        state_data = STATE.read_bytes()
        saved_module = MODULE.with_suffix('.manager-saved')
        try:
            if fault == 'missing-state': STATE.unlink()
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
            run(['restorecon', str(STATE)])
            run(['setenforce', '1'])
        recover()
    start('final-gdm-supervised-recovered')
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
    clean('stop-fixture-sessions', stop)
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
        clean('remove-launcher-policy', lambda: run(['semodule', '-r', 'lyra-manager-launcher']))
    result['vendor_preserved'] = all(digest(Path(p)) == sha for p, sha in vendor_hashes.items())
    result['official_worker_restored'] = digest(WORKER) == OFFICIAL_SHA
    result['helper_label_restored'] = os.getxattr(HELPER, 'security.selinux') == helper_label
    result['files_restored'] = all(p.read_bytes() == data if data is not None else not p.exists() for p, data in saved.items())
    result['fixture_removed'] = not any(p.exists() for p in (MODULE, SESSION, DIRECTORY, BACKUP))
    result['passed'] = bool(result.get('passed') and all(row['passed'] for row in cleanup)
        and all(result[k] for k in ('vendor_preserved', 'official_worker_restored', 'helper_label_restored', 'files_restored', 'fixture_removed')))
    Path('/root/manager-gdm-result.json').write_text(json.dumps(result, indent=2) + '\n')
assert result['passed'], result
