"""Native login/SSH test, restricted to the marked disposable guest.

Credentials are generated inside the guest, never returned, and removed with
the fixture accounts. No real host accounts or SSH service are modified.
"""
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pty
import pwd
import grp
import re
import secrets
import select
import shutil
import signal
import socket
import socketserver
import subprocess
import termios
import threading
import time

assert os.geteuid() == 0
assert 'lyra.parental-identity-test=1' in Path('/proc/cmdline').read_text().split()
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'
signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(143)))
SOURCE = Path('/root/entry-evidence/parental-entries/policy.py')
spec = importlib.util.spec_from_file_location('entry_policy', SOURCE)
policy = importlib.util.module_from_spec(spec); spec.loader.exec_module(policy)
PRIVATE = Path('/run/lyra-entry-fixture')
KEYS = Path('/etc/ssh/lyra-entry-keys')
HOSTKEY = Path('/etc/ssh/ssh_host_lyra_entry_key')
CONFIG = Path('/etc/ssh/lyra-entry-fixture.conf')
UNIT = 'lyra-parental-entry-sshd.service'
NAMES = ['clirestricted', 'clicontrol']
passwords = {name: secrets.token_urlsafe(24) for name in NAMES}
checks, cleanup, children, created, groups = [], [], [], [], []
result = dict(kind='native-login-and-openssh-account-denial', full_account_protection=False,
              checks=checks, cleanup=cleanup)
original_pam = {name: Path('/etc/pam.d', name).read_bytes() if Path('/etc/pam.d', name).exists() else None
                for name in ('login', 'sshd')}
assert all(value is None for value in original_pam.values()), 'unexpected existing local override'
vendor = {name: Path('/usr/lib/pam.d', name).read_text() for name in original_pam}
result['vendor_sha256'] = {name: hashlib.sha256(value.encode()).hexdigest() for name, value in vendor.items()}


def safe(text):
    for password in passwords.values(): text = text.replace(password, '<redacted>')
    return text


def cmd(args, input=None, check=True, timeout=45):
    p = subprocess.run(args, input=input, capture_output=True, text=True, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(safe(f'{args[0]} failed ({p.returncode}): {p.stdout}\n{p.stderr}'))
    return p


def record(name, **values):
    row = dict(name=name, passed=True, **values)
    row = json.loads(safe(json.dumps(row)))
    checks.append(row); print(json.dumps(row), flush=True)


def account(name):
    p = pwd.getpwnam(name)
    return dict(user=name, uid=p.pw_uid, gid=p.pw_gid, group=grp.getgrgid(p.pw_gid).gr_name)


def install_policy(roster):
    for name, original in vendor.items():
        path = Path('/etc/pam.d', name)
        temporary = path.with_suffix('.lyra-new')
        temporary.write_text(policy.compose(original, roster)); temporary.chmod(0o644)
        cmd(['restorecon', str(temporary)])
        temporary.replace(path); cmd(['restorecon', str(path)])


def native_login(name, allowed, label):
    pid, master = pty.fork()
    if pid == 0:
        os.execve('/usr/bin/login', ['login', name], dict(PATH='/usr/bin:/bin', TERM='dumb', LANG='C', LC_ALL='C'))
    output = bytearray(); sent_password = sent_command = False; status = None
    deadline = time.monotonic() + 20
    try:
        while time.monotonic() < deadline:
            if select.select([master], [], [], .1)[0]:
                try: chunk = os.read(master, 65536)
                except OSError as error:
                    if error.errno == errno.EIO: break
                    raise
                if not chunk: break
                output.extend(chunk)
            if not sent_password and b'Password:' in output:
                assert not termios.tcgetattr(master)[3] & termios.ECHO, 'password prompt unexpectedly echoes'
                os.write(master, (passwords[name] + '\n').encode()); sent_password = True
            if sent_password and not sent_command and output.endswith((b'$ ', b'# ', b'> ')):
                # The echoed command does not contain the expanded success marker.
                os.write(master, b"printf 'LYRA_%s\\n' ENTRY_OK; id -u; id -Z; exit\n")
                sent_command = True
            done, child_status = os.waitpid(pid, os.WNOHANG)
            if done: status = child_status; break
        if status is None:
            for _ in range(100):
                done, child_status = os.waitpid(pid, os.WNOHANG)
                if done: status = child_status; break
                time.sleep(.02)
        observed = b'LYRA_ENTRY_OK' in output
        assert sent_password and observed == allowed, (label, safe(output.decode(errors='replace')))
        if allowed: assert status is not None and os.waitstatus_to_exitcode(status) == 0
        if not allowed:
            assert b'Permission denied' in output or b'Login incorrect' in output or b'Authentication failure' in output, safe(output.decode(errors='replace'))
        record(label, allowed=allowed, authenticated_shell=observed,
               transcript=safe(output.decode(errors='replace')),
               exit_code=os.waitstatus_to_exitcode(status) if status is not None else None)
    finally:
        if status is None:
            try: os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError: pass
            try: os.waitpid(pid, 0)
            except ChildProcessError: pass
        os.close(master)


def ssh_options():
    return ['-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(PRIVATE/'known_hosts'),
            '-o', 'ConnectTimeout=5', '-i', str(PRIVATE/'client-key')]


def remote(name, allowed, label):
    p = cmd(['ssh', *ssh_options(), name+'@127.0.0.1', "printf 'LYRA_%s\\n' ENTRY_OK; id -u; id -Z"], check=False, timeout=15)
    assert (p.returncode == 0 and 'LYRA_ENTRY_OK' in p.stdout) == allowed, (label, p.returncode, p.stdout, p.stderr)
    if not allowed: assert p.returncode == 255 and 'LYRA_ENTRY_OK' not in p.stdout, (label, p.stdout, p.stderr)
    record(label, rc=p.returncode, stdout=p.stdout, stderr=p.stderr)
    if not allowed: time.sleep(penalty_delay)


def sftp(name, allowed, label):
    output = PRIVATE/'download'
    output.unlink(missing_ok=True)
    batch = PRIVATE/'sftp-batch'; batch.write_text('get /etc/os-release ' + str(output) + '\n')
    p = cmd(['sftp', *ssh_options(), '-b', str(batch), name+'@127.0.0.1'], check=False, timeout=15)
    if allowed:
        assert p.returncode == 0 and output.read_bytes() == Path('/etc/os-release').read_bytes(), (label, p.stderr)
    else:
        assert p.returncode != 0 and not output.exists(), (label, p.stdout, p.stderr)
    record(label, rc=p.returncode, downloaded=output.exists(), stderr=p.stderr)
    if not allowed: time.sleep(penalty_delay)


class Echo(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.sendall(self.request.recv(256))


def free_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); return probe.getsockname()[1]


def exchange(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=.3) as connection:
            connection.sendall(b'LYRA_TUNNEL_PROBE')
            return connection.recv(256) == b'LYRA_TUNNEL_PROBE'
    except OSError:
        return False


def tunnel(name, allowed, label, keep=False):
    local = free_port()
    process = subprocess.Popen(['ssh', *ssh_options(), '-N', '-o', 'ExitOnForwardFailure=yes',
        '-L', f'127.0.0.1:{local}:127.0.0.1:{echo.server_address[1]}', name+'@127.0.0.1'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    children.append(process)
    try:
        deadline = time.monotonic() + 10
        passed = False
        while time.monotonic() < deadline and process.poll() is None:
            if exchange(local): passed = True; break
            time.sleep(.05)
        assert passed == allowed, (label, process.poll())
        if not allowed:
            stdout, stderr = process.communicate(timeout=5)
            assert process.returncode == 255, (label, stdout, stderr)
            record(label, rc=process.returncode, forwarded=False, stderr=stderr)
            time.sleep(penalty_delay)
        else:
            record(label, forwarded=True, no_session=True)
        if keep: return process, local
    finally:
        if not keep and process.poll() is None:
            process.terminate(); process.wait(timeout=10)


assert not any(path.exists() for path in [PRIVATE, KEYS, HOSTKEY, HOSTKEY.with_suffix('.pub'), CONFIG])
assert not set(NAMES) & {p.pw_name for p in pwd.getpwall()}
assert not set(NAMES) & {g.gr_name for g in grp.getgrall()}
assert not any(Path('/home', name).exists() for name in NAMES)
initial_enforcing = cmd(['getenforce']).stdout.strip(); assert initial_enforcing == 'Permissive'
before_accounts = {name: account(name) for name in ('parentaltest', 'ordinaryuser')}
echo = None; server_started = False; invocation = None


def server_log():
    args = ['journalctl', '--no-pager', '-o', 'cat']
    args += ['_SYSTEMD_INVOCATION_ID=' + invocation] if invocation else ['-u', UNIT]
    return cmd(args, check=False).stdout
try:
    cmd(['systemctl', 'disable', '--now', 'sshd.service'])  # newly installed in this VM only
    PRIVATE.mkdir(mode=0o700); KEYS.mkdir(mode=0o755)
    cmd(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(PRIVATE/'client-key')])
    cmd(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(HOSTKEY)])
    public = (PRIVATE/'client-key.pub').read_text()
    host_public = HOSTKEY.with_suffix('.pub').read_text().split()
    (PRIVATE/'known_hosts').write_text('127.0.0.1 ' + ' '.join(host_public[:2]) + '\n')
    for offset, name in enumerate(NAMES):
        uid = next(i for i in range(31000 + offset, 32000) if i not in {p.pw_uid for p in pwd.getpwall()})
        gid = next(i for i in range(41000 + offset, 42000) if i not in {g.gr_gid for g in grp.getgrall()})
        cmd(['groupadd', '-g', str(gid), name]); groups.append(name)
        cmd(['useradd', '-m', '-u', str(uid), '-g', str(gid), '-s', '/bin/bash', name]); created.append(name)
        cmd(['chpasswd'], input=name + ':' + passwords[name] + '\n')
        (KEYS/name).write_text(public); (KEYS/name).chmod(0o644)
        cmd(['restorecon', '-R', '/home/' + name])
    roster = [account(NAMES[0])]; result['bindings'] = roster
    CONFIG.write_text(f'''Port 22
ListenAddress 127.0.0.1
HostKey {HOSTKEY}
PidFile {PRIVATE}/sshd.pid
AuthorizedKeysFile {KEYS}/%u
UsePAM yes
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
StrictModes yes
AllowUsers {' '.join(NAMES)}
AllowTcpForwarding yes
X11Forwarding no
Subsystem sftp internal-sftp
LogLevel VERBOSE
''')
    CONFIG.chmod(0o600)
    cmd(['restorecon', '-R', str(KEYS), str(HOSTKEY), str(HOSTKEY.with_suffix('.pub')), str(CONFIG)])
    cmd(['/usr/sbin/sshd', '-t', '-f', str(CONFIG)])
    effective = cmd(['/usr/sbin/sshd', '-T', '-f', str(CONFIG)]).stdout
    assert 'usepam yes\n' in effective
    penalty = next(line for line in effective.splitlines() if line.startswith('persourcepenalties '))
    duration = re.search(r'\bauthfail:(\d+(?:\.\d+)?)(?:s)?(?:\s|$)', penalty)
    assert duration and 0 < float(duration[1]) <= 10, penalty
    penalty_delay = float(duration[1]) + 1
    result['penalty_spacing_seconds'] = penalty_delay
    result['effective_sshd'] = '\n'.join(line for line in effective.splitlines() if line.split()[0] in
        {'usepam', 'listenaddress', 'port', 'allowusers', 'allowtcpforwarding', 'passwordauthentication', 'pubkeyauthentication', 'subsystem', 'persourcepenalties'})
    cmd(['setenforce', '1'])
    cmd(['systemd-run', '--unit=' + UNIT, '--property=KillMode=control-group', '/usr/sbin/sshd', '-D', '-e', '-f', str(CONFIG)])
    server_started = True
    invocation = cmd(['systemctl', 'show', '-p', 'InvocationID', '--value', UNIT]).stdout.strip()
    assert re.fullmatch('[a-f0-9]{32}', invocation)
    result['server_invocation'] = invocation
    for _ in range(100):
        try:
            with socket.create_connection(('127.0.0.1', 22), timeout=.2): break
        except OSError: time.sleep(.05)
    else: raise RuntimeError('fixture sshd did not start')
    server_pid = int(cmd(['systemctl', 'show', '-p', 'MainPID', '--value', UNIT]).stdout)
    result['sshd_context'] = Path(f'/proc/{server_pid}/attr/current').read_text().strip('\x00\n ')
    echo = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Echo)
    echo.daemon_threads = True
    threading.Thread(target=echo.serve_forever, daemon=True).start()

    for name in NAMES:
        native_login(name, True, 'baseline-login-' + name)
        remote(name, True, 'baseline-ssh-' + name)
    sftp(NAMES[0], True, 'baseline-sftp-restricted-fixture')
    existing, port = tunnel(NAMES[0], True, 'baseline-forward-before-policy', keep=True)

    install_policy(roster)
    assert existing.poll() is None and exchange(port)
    record('existing-forward-survives-policy-change', qualification='known-revocation-gap', forwarded=True)
    existing.terminate(); existing.wait(timeout=10)
    for name in NAMES:
        allowed = name == NAMES[1]
        native_login(name, allowed, 'policy-login-' + name)
        remote(name, allowed, 'policy-ssh-' + name)
        sftp(name, allowed, 'policy-sftp-' + name)
        tunnel(name, allowed, 'policy-no-session-forward-' + name)
    cmd(['setenforce', '0'])
    try:
        remote(NAMES[0], False, 'permissive-ssh-still-denied')
        native_login(NAMES[0], False, 'permissive-login-still-denied')
        remote(NAMES[1], True, 'permissive-ordinary-preserved')
    finally: cmd(['setenforce', '1'])
    old_gid = roster[0]['gid']
    cmd(['usermod', '-g', str(account(NAMES[1])['gid']), NAMES[0]])
    try:
        remote(NAMES[0], False, 'primary-gid-drift-still-denied')
        remote(NAMES[1], True, 'ordinary-gid-drift-preserved')
    finally: cmd(['usermod', '-g', str(old_gid), NAMES[0]])
    for name in original_pam: Path('/etc/pam.d', name).unlink()
    native_login(NAMES[0], True, 'restored-vendor-login')
    remote(NAMES[0], True, 'restored-vendor-ssh')
    sftp(NAMES[0], True, 'restored-vendor-sftp')
    tunnel(NAMES[0], True, 'restored-vendor-forward')
    log = server_log()
    result['ssh_account_denials'] = [line for line in log.splitlines() if 'PAM account' in line or 'Access denied' in line]
    assert any(NAMES[0] in line for line in result['ssh_account_denials']), result['ssh_account_denials']
    result['passed'] = True
except BaseException as error:
    result['error'] = safe(str(error))
    print('ENTRY_TEST_FAILED: ' + result['error'], flush=True)
    raise
finally:
    def clean(name, action):
        try: action(); cleanup.append(dict(name=name, passed=True))
        except Exception as error: cleanup.append(dict(name=name, passed=False, error=safe(str(error))))
    for child in children:
        if child.poll() is None:
            clean('stop-client', child.terminate)
            clean('wait-client', lambda child=child: child.wait(timeout=10))
    if echo:
        echo.shutdown(); echo.server_close()
    if server_started:
        result['server_journal'] = safe(server_log())
        clean('stop-fixture-sshd', lambda: cmd(['systemctl', 'stop', UNIT]))
    clean('restore-permissive', lambda: cmd(['setenforce', '0']))
    for name in original_pam:
        clean('restore-vendor-' + name, lambda name=name: Path('/etc/pam.d', name).unlink(missing_ok=True))
    for name in created:
        cmd(['loginctl', 'terminate-user', name], check=False)
        for _ in range(100):
            present = cmd(['pgrep', '-u', str(pwd.getpwnam(name).pw_uid)], check=False).returncode == 0
            if not present: break
            time.sleep(.05)
        clean('remove-' + name, lambda name=name: cmd(['userdel', '-r', name]))
    for name in groups:
        if name in {g.gr_name for g in grp.getgrall()}:
            clean('remove-group-' + name, lambda name=name: cmd(['groupdel', name]))
    for path in (CONFIG, HOSTKEY, HOSTKEY.with_suffix('.pub')):
        clean('remove-' + path.name, lambda path=path: path.unlink(missing_ok=True))
    for directory in (PRIVATE, KEYS):
        if directory.exists(): clean('remove-' + directory.name, lambda directory=directory: shutil.rmtree(directory))
    result['original_accounts_preserved'] = before_accounts == {name: account(name) for name in before_accounts}
    result['pam_vendor_restored'] = all(not Path('/etc/pam.d', name).exists() and
        Path('/usr/lib/pam.d', name).read_text() == vendor[name] for name in original_pam)
    result['fixture_accounts_removed'] = not set(NAMES) & {p.pw_name for p in pwd.getpwall()}
    result['passed'] = bool(result.get('passed') and all(c['passed'] for c in cleanup) and
        result['original_accounts_preserved'] and result['pam_vendor_restored'] and result['fixture_accounts_removed'])
    Path('/root/entry-results.json').write_text(safe(json.dumps(result, indent=2)) + '\n')
assert result['passed'], 'fixture cleanup failed'
