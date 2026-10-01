"""Native SSH revocation test; marked disposable VM only, no host changes."""
import hashlib, importlib.util, json, os, pwd, grp, re, secrets, shutil, signal
import socket, socketserver, subprocess, threading, time, pty, select, termios, errno
from pathlib import Path
from ssh_revoke import holders, revoke, process
assert os.geteuid() == 0
assert {'lyra.parental-selinux-test=1','lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'
PRIVATE = Path('/run/lyra-revoke-fixture')
KEYS = Path('/etc/ssh/lyra-revoke-keys')
HOSTKEY = Path('/etc/ssh/ssh_host_lyra_revoke_key')
CONFIG = Path('/etc/ssh/lyra-revoke-fixture.conf')
UNIT = 'lyra-parental-revoke-sshd.service'
DIRECTORY = Path('/var/lib/lyra-parental-test')
MODULE = Path('/usr/lib64/security/pam_lyra_ssh_registry_fixture.so')
PAM = Path('/etc/pam.d/sshd')
GUARD = Path('/root/ssh-pam-account-guard.c')
WRITER = Path('/root/barrier-writer.py')
POLICY = Path('/root/lyra-ssh-registry.cil')
NAMES = ['clirestricted','clicontrol']
passwords = {name: secrets.token_urlsafe(24) for name in NAMES}
checks, cleanup, children, created, groups = [], [], [], [], []
result = dict(kind='native-ssh-generation-revocation', full_account_protection=False,
              checks=checks, cleanup=cleanup, full_gnome_session_tested=False)
spec=importlib.util.spec_from_file_location('writer',WRITER)
writer=importlib.util.module_from_spec(spec);spec.loader.exec_module(writer)
vendor = Path('/usr/lib/pam.d/sshd').read_text()
original_pam = PAM.read_bytes() if PAM.exists() else None
original_mode = PAM.stat().st_mode & 0o777 if PAM.exists() else None
initial_enforcing = subprocess.run(['getenforce'],capture_output=True,text=True,check=True).stdout.strip()
assert initial_enforcing == 'Permissive'
assert not any(path.exists() for path in (PRIVATE,KEYS,HOSTKEY,HOSTKEY.with_suffix('.pub'),CONFIG,DIRECTORY,MODULE))
assert not set(NAMES) & {p.pw_name for p in pwd.getpwall()}
assert not set(NAMES) & {g.gr_name for g in grp.getgrall()}
assert not any(Path('/home',name).exists() for name in NAMES)
assert original_pam is None
before_accounts = {name: (pwd.getpwnam(name).pw_uid,pwd.getpwnam(name).pw_gid) for name in ('parentaltest','ordinaryuser')}
generation = secrets.token_hex(16)
echo = None; server_started = policy_installed = state_created = module_created = False
invocation = None
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


def ssh_options():
    return ['-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(PRIVATE/'known_hosts'),
            '-o', 'ConnectTimeout=5', '-i', str(PRIVATE/'client-key')]


def remote(name, allowed, label):
    before = server_log() if not allowed else None
    p = cmd(['ssh', *ssh_options(), name+'@127.0.0.1', "printf 'LYRA_%s\\n' ENTRY_OK; id -u; id -Z"], check=False, timeout=15)
    assert (p.returncode == 0 and 'LYRA_ENTRY_OK' in p.stdout) == allowed, (label, p.returncode, p.stdout, p.stderr)
    if not allowed: assert p.returncode == 255 and 'LYRA_ENTRY_OK' not in p.stdout, (label, p.stdout, p.stderr)
    record(label, rc=p.returncode, stdout=p.stdout, stderr=p.stderr,
           account_rejection=denial_since(before) if not allowed else None)
    if not allowed: time.sleep(penalty_delay)


def sftp(name, allowed, label):
    before = server_log() if not allowed else None
    output = PRIVATE/'download'
    output.unlink(missing_ok=True)
    batch = PRIVATE/'sftp-batch'; batch.write_text('get /etc/os-release ' + str(output) + '\n')
    p = cmd(['sftp', *ssh_options(), '-b', str(batch), name+'@127.0.0.1'], check=False, timeout=15)
    if allowed:
        assert p.returncode == 0 and output.read_bytes() == Path('/etc/os-release').read_bytes(), (label, p.stderr)
    else:
        assert p.returncode != 0 and not output.exists(), (label, p.stdout, p.stderr)
    record(label, rc=p.returncode, downloaded=output.exists(), stderr=p.stderr,
           account_rejection=denial_since(before) if not allowed else None)
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
    before = server_log() if not allowed else None
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
            record(label, rc=process.returncode, forwarded=False, stderr=stderr,account_rejection=denial_since(before))
            time.sleep(penalty_delay)
        else:
            record(label, forwarded=True, no_shell_channel=True)
        if keep: return process, local
    finally:
        if not keep and process.poll() is None:
            process.terminate(); process.wait(timeout=10)



def label_registry():
    cmd(['chcon','-R','-t','lyra_ssh_registry_state_t',str(DIRECTORY)])

def install_pam(gen):
    r=roster[0]
    fragment=(f"account requisite pam_lyra_ssh_registry_fixture.so account=active|{r['user']}|{r['uid']}|{r['gid']}|{r['group']}|{gen}\n")
    PAM.write_text('#%PAM-1.0\n'+fragment+vendor.removeprefix('#%PAM-1.0\n'));PAM.chmod(0o644)
    cmd(['restorecon',str(PAM)])

def server_log():
    args=['journalctl','--no-pager','-o','cat']
    args += ['_SYSTEMD_INVOCATION_ID='+invocation] if invocation else ['-u',UNIT]
    return cmd(args,check=False).stdout

def denial_since(before):
    # One credential attempt at a time; old ordinary transports remain idle.
    # Require the fixture guard's account cause and OpenSSH's account rejection,
    # not just rc255, a missing socket or an IP penalty.
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        current=server_log();assert current.startswith(before)
        fresh=current[len(before):].splitlines()
        cause=[i for i,line in enumerate(fresh) if 'pam_lyra_ssh_registry_fixture(sshd:account): Experimental SSH registry admission rejected account' in line]
        failure=[i for i,line in enumerate(fresh) if f'Access denied for user {NAMES[0]} by PAM account configuration' in line]
        if len(cause)==len(failure)==1:
            assert cause[0]<failure[0]
            return dict(lines=[fresh[cause[0]],fresh[failure[0]]],cause='fixture-registry-account',
                        user=NAMES[0],sequential_attempt=True)
        time.sleep(.02)
    raise AssertionError(dict(reason='no exact PAM account rejection for this attempt',fresh=fresh))

def persistent_command(name):
    child=subprocess.Popen(['ssh',*ssh_options(),name+'@127.0.0.1',
                            "printf 'LYRA_%s\\n' COMMAND_READY; exec sleep 600"],
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    children.append(child)
    assert select.select([child.stdout],[],[],15)[0], 'command did not start'
    assert child.stdout.readline().strip()=='LYRA_COMMAND_READY'
    return child

def prompt_pending():
    # PTY keeps a real SSH password conversation paused without exporting it.
    pid, master=pty.fork()
    if pid==0:
        os.execv('/usr/bin/ssh',['ssh',*[option.replace('BatchMode=yes','BatchMode=no') for option in ssh_options()],'-o','PubkeyAuthentication=no',
            '-o','BatchMode=no','-o','PreferredAuthentications=password','-o','NumberOfPasswordPrompts=1',
            NAMES[0]+'@127.0.0.1',"printf 'LYRA_%s\\n' PENDING_EXECUTED"])
    output=bytearray();status=None
    try:
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            if select.select([master],[],[],.1)[0]:
                output.extend(os.read(master,65536))
            if b'password:' in output.lower():break
        else:raise AssertionError(safe(output.decode(errors='replace')))
        assert not termios.tcgetattr(master)[3]&termios.ECHO
        return pid,master,output
    except BaseException:
        os.kill(pid,signal.SIGKILL);os.waitpid(pid,0);os.close(master);raise

def answer_pending(pid,master,output,allowed=False):
    before = server_log() if not allowed else None
    try:
        os.write(master,(passwords[NAMES[0]]+'\n').encode())
        deadline=time.monotonic()+15;status=None
        while time.monotonic()<deadline:
            if select.select([master],[],[],.1)[0]:
                try: chunk=os.read(master,65536)
                except OSError as error:
                    if error.errno!=errno.EIO:raise
                    chunk=b''
                output.extend(chunk)
            done,child_status=os.waitpid(pid,os.WNOHANG)
            if done:status=child_status;break
        assert status is not None and os.waitstatus_to_exitcode(status)==(0 if allowed else 255)
        assert (b'LYRA_PENDING_EXECUTED' in output)==allowed
        record('baseline-password-ssh-admitted' if allowed else 'pending-password-after-barrier-denied',rc=os.waitstatus_to_exitcode(status),
               transcript=safe(output.decode(errors='replace')),
               account_rejection=denial_since(before) if not allowed else None)
        if not allowed:time.sleep(penalty_delay)
    finally:
        try:os.kill(pid,signal.SIGKILL)
        except ProcessLookupError:pass
        try:os.waitpid(pid,0)
        except ChildProcessError:pass
        os.close(master)

def multiplex_master():
    control = PRIVATE / 'restricted-mux'
    child = subprocess.Popen(['ssh', *ssh_options(), '-M', '-S', str(control), '-N', NAMES[0]+'@127.0.0.1'],
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    children.append(child)
    deadline=time.monotonic()+10
    while time.monotonic()<deadline and child.poll() is None:
        if control.exists():
            checked=cmd(['ssh',*ssh_options(),'-S',str(control),'-O','check',NAMES[0]+'@127.0.0.1'],check=False)
            if checked.returncode==0:
                record('baseline-multiplexed-transport-admitted',rc=checked.returncode)
                return child,control
        time.sleep(.05)
    raise AssertionError('multiplex master did not start')

def multiplex_command(control,label,allowed):
    before = server_log() if not allowed else None
    child=cmd(['ssh',*ssh_options(),'-S',str(control),NAMES[0]+'@127.0.0.1',
               "printf 'LYRA_%s\\n' MUX_COMMAND"],check=False,timeout=15)
    assert (child.returncode==0 and 'LYRA_MUX_COMMAND' in child.stdout)==allowed
    if not allowed:assert child.returncode==255 and 'LYRA_MUX_COMMAND' not in child.stdout
    record(label,rc=child.returncode,stdout=child.stdout,stderr=child.stderr,
           account_rejection=denial_since(before) if not allowed else None)
    if not allowed:time.sleep(penalty_delay)

pending=None
try:
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
    cmd(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(GUARD),'-o',str(MODULE),'-lpam','-lselinux']); module_created=True
    cmd(['restorecon',str(MODULE)])
    DIRECTORY.mkdir(mode=0o700); state_created=True
    store=writer.RegistryStore(DIRECTORY)
    store.seed([dict(state='active',**roster[0],generation=generation)])
    cmd(['semodule','-i',str(POLICY)]); policy_installed=True
    label_registry()
    install_pam(generation)
    CONFIG.write_text(f'''Port 22
ListenAddress 127.0.0.1
HostKey {HOSTKEY}
PidFile {PRIVATE}/sshd.pid
AuthorizedKeysFile {KEYS}/%u
UsePAM yes
PubkeyAuthentication yes
PasswordAuthentication yes
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


    result['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (Path(__file__),GUARD,WRITER,POLICY,Path('/root/ssh_revoke.py'))}
    result['module_sha256']=hashlib.sha256(MODULE.read_bytes()).hexdigest()
    remote(NAMES[0],True,'baseline-active-ssh-admitted')
    remote(NAMES[1],True,'baseline-ordinary-ssh-admitted')
    pending=prompt_pending();answer_pending(*pending,allowed=True);pending=None
    existing,port=tunnel(NAMES[0],True,'baseline-no-shell-target-tunnel',keep=True)
    ordinary,ordinary_port=tunnel(NAMES[1],True,'baseline-no-shell-ordinary-tunnel',keep=True)
    logind=cmd(['loginctl','list-sessions','--no-legend']).stdout
    # -N means no shell channel, not necessarily no PAM/logind session.
    result['no_shell_tunnel_logind_sessions']=logind
    before_holders=holders(DIRECTORY/f'.lease-{generation}.lock')
    record('no-shell-tunnel-lease-inventory',holders=before_holders,logind_sessions=logind,
           lease_retained=bool(before_holders))
    mux,control=multiplex_master()
    target_command=persistent_command(NAMES[0]);ordinary_command=persistent_command(NAMES[1])
    record('baseline-both-persistent-commands-admitted')
    pending=prompt_pending()
    record('password-conversation-paused-before-barrier')
    try:store.begin(generation)
    except writer.StoreError as error:
        assert str(error).startswith('busy:');busy=True
    else:busy=False
    label_registry()
    assert busy, 'live SSH transports must retain the generation lease'
    assert (DIRECTORY/f'.barrier-{generation}').exists()
    assert existing.poll() is None and exchange(port)
    assert ordinary.poll() is None and exchange(ordinary_port)
    record('durable-barrier-alone-does-not-revoke-old-tunnel',forwarded=True,busy=busy)
    multiplex_command(control,'old-multiplex-can-open-channel-until-transport-revoked',True)
    revocation=revoke(roster[0]['uid'],generation,DIRECTORY,UNIT,server_pid)
    deadline=time.monotonic()+10
    while time.monotonic()<deadline and (existing.poll() is None or target_command.poll() is None):time.sleep(.05)
    mux.wait(timeout=10)
    assert existing.poll() is not None and target_command.poll() is not None and mux.returncode!=0
    assert not exchange(port) and not holders(DIRECTORY/f'.lease-{generation}.lock')
    record('target-transports-and-command-revoked',**revocation,forwarded=False,
           logind_terminated=True,
           tunnel_rc=existing.returncode,command_rc=target_command.returncode,mux_rc=mux.returncode)
    assert ordinary.poll() is None and exchange(ordinary_port) and ordinary_command.poll() is None
    assert cmd(['systemctl','show','-p','MainPID','--value',UNIT]).stdout.strip()==str(server_pid)
    record('ordinary-connections-and-shared-listener-preserved',forwarded=True,listener_pid=server_pid)
    assert os.waitpid(pending[0],os.WNOHANG)==(0,0), 'pending authentication unexpectedly killed'
    record('pending-authentication-survives-logind-until-account-recheck')
    answer_pending(*pending);pending=None
    multiplex_command(control,'old-multiplex-cannot-open-channel-after-revocation',False)
    remote(NAMES[0],False,'new-command-after-revocation-denied')
    sftp(NAMES[0],False,'new-sftp-after-revocation-denied')
    tunnel(NAMES[0],False,'new-no-shell-tunnel-after-revocation-denied')
    remote(NAMES[1],True,'ordinary-new-command-after-revocation-admitted')
    store.begin(generation);store.tombstone(generation)
    next_gen=secrets.token_hex(16)
    store.publish(generation,dict(state='active',**roster[0],generation=next_gen));label_registry()
    remote(NAMES[0],False,'old-pam-generation-after-enrollment-denied')
    install_pam(next_gen)
    remote(NAMES[0],True,'explicit-new-generation-after-revocation-admitted')
    tunnel(NAMES[0],True,'explicit-new-generation-no-shell-tunnel-admitted')
    assert ordinary.poll() is None and exchange(ordinary_port)
    record('ordinary-existing-tunnel-survives-entire-transition')
    result['ssh_account_denials']=[line for line in server_log().splitlines() if 'PAM account' in line or 'rejected account' in line]
    assert any('Experimental SSH registry admission rejected account' in line for line in result['ssh_account_denials'])
    result['passed']=True
except BaseException as error:
    result['error']=safe(str(error));print('SSH_REVOCATION_FAILED: '+result['error'],flush=True);raise
finally:
    def clean(name,action):
        try:action();cleanup.append(dict(name=name,passed=True))
        except Exception as error:cleanup.append(dict(name=name,passed=False,error=safe(str(error))))
    if pending:
        pid,master,_=pending
        clean('kill-pending-client',lambda:os.kill(pid,signal.SIGKILL))
        clean('reap-pending-client',lambda:os.waitpid(pid,0))
        clean('close-pending-pty',lambda:os.close(master))
    for child in children:
        if child.poll() is None:
            clean('stop-client',child.terminate)
            clean('wait-client',lambda child=child:child.wait(timeout=10))
    if echo:echo.shutdown();echo.server_close()
    if server_started:
        result['server_journal']=safe(server_log())
        clean('stop-fixture-sshd',lambda:cmd(['systemctl','stop',UNIT]))
    clean('restore-selinux-mode',lambda:cmd(['setenforce','0']))
    if original_pam is None:clean('remove-pam-override',lambda:PAM.unlink(missing_ok=True))
    else:
        def restore_pam():PAM.write_bytes(original_pam);PAM.chmod(original_mode)
        clean('restore-pam-override',restore_pam)
    for name in created:
        uid=pwd.getpwnam(name).pw_uid
        cmd(['loginctl','terminate-user',name],check=False)
        clean('stop-manager-'+name,lambda uid=uid:cmd(['systemctl','stop',f'user@{uid}.service',f'user-runtime-dir@{uid}.service']))
        for _ in range(100):
            if cmd(['pgrep','-u',str(uid)],check=False).returncode!=0:break
            time.sleep(.05)
        clean('remove-'+name,lambda name=name:cmd(['userdel','-r',name]))
    for name in groups:
        if name in {g.gr_name for g in grp.getgrall()}:clean('remove-group-'+name,lambda name=name:cmd(['groupdel',name]))
    for path in (CONFIG,HOSTKEY,HOSTKEY.with_suffix('.pub'),MODULE):
        clean('remove-'+path.name,lambda path=path:path.unlink(missing_ok=True))
    for directory in (PRIVATE,KEYS,DIRECTORY):
        if directory.exists():clean('remove-'+directory.name,lambda directory=directory:shutil.rmtree(directory))
    if policy_installed:clean('remove-registry-policy',lambda:cmd(['semodule','-r','lyra-ssh-registry']))
    result['original_accounts_preserved']=before_accounts=={name:(pwd.getpwnam(name).pw_uid,pwd.getpwnam(name).pw_gid) for name in before_accounts}
    result['vendor_restored']=not PAM.exists() and Path('/usr/lib/pam.d/sshd').read_text()==vendor
    result['fixtures_removed']=not set(NAMES)&{p.pw_name for p in pwd.getpwall()} and not any(path.exists() for path in (PRIVATE,KEYS,HOSTKEY,HOSTKEY.with_suffix('.pub'),CONFIG,DIRECTORY,MODULE))
    result['enforce_restored']=cmd(['getenforce']).stdout.strip()==initial_enforcing
    result['passed']=bool(result.get('passed') and all(c['passed'] for c in cleanup) and all(result[k] for k in ('original_accounts_preserved','vendor_restored','fixtures_removed','enforce_restored')))
    assert not any(secret in json.dumps(result) for secret in passwords.values()),'secret in evidence'
    Path('/root/ssh-revocation-result.json').write_text(safe(json.dumps(result,indent=2))+'\n')
assert result['passed'],'cleanup failed'
