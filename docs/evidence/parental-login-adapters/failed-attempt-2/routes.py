"""Native login drivers; fixture credentials remain only in VM memory/stdin."""
import importlib.util,sys,socketserver,threading
spec=importlib.util.spec_from_file_location('login_common','/root/login-adapters/login-common.py')
lc=importlib.util.module_from_spec(spec);sys.modules[spec.name]=lc;spec.loader.exec_module(lc)
from login_common import *
children=[];checks=[];echo=None;invocation=None

def ssh_options():
    return ['-F','/dev/null','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(PRIVATE/'known_hosts'),'-o','ConnectTimeout=5','-i',str(PRIVATE/'client-key')]

def ssh_log():return run(['journalctl','_SYSTEMD_INVOCATION_ID='+invocation,'--no-pager','-o','cat'])['stdout']

def exact_ssh_denial(before):
    log=ssh_log();assert log.startswith(before);fresh=log[len(before):]
    assert 'pam_lyra_ordinary_ssh_fixture(sshd:account): Experimental ordinary SSH admission rejected account' in fresh,fresh
    assert 'Access denied for user ordinaryuser by PAM account configuration' in fresh,fresh
    return fresh

def remote(user,allowed,name):
    before=ssh_log();r=run(['ssh',*ssh_options(),user+'@127.0.0.1',"printf 'LYRA_%s\\n' ENTRY_OK; id -u; id -Z"],check=False)
    assert (r['rc']==0 and 'LYRA_ENTRY_OK' in r['stdout'])==allowed,r
    if allowed:assert str(pwd.getpwnam(user).pw_uid) in r['stdout'].splitlines() and ':unconfined_t:' in r['stdout']
    else:assert r['rc']==255 and 'LYRA_ENTRY_OK' not in r['stdout']
    record(checks,name,**r,rejection=exact_ssh_denial(before) if not allowed else None)

def persistent_command(user):
    p=subprocess.Popen(['ssh',*ssh_options(),user+'@127.0.0.1',"printf 'LYRA_%s\\n' COMMAND_READY; exec sleep 600"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);children.append(p)
    assert select.select([p.stdout],[],[],15)[0] and p.stdout.readline().strip()=='LYRA_COMMAND_READY'
    return p

class Echo(socketserver.BaseRequestHandler):
    def handle(self):self.request.sendall(self.request.recv(256))
def start_echo():
    global echo
    echo=socketserver.ThreadingTCPServer(('127.0.0.1',0),Echo);echo.daemon_threads=True
    threading.Thread(target=echo.serve_forever,daemon=True).start()
def exchange(port):
    try:
        with socket.create_connection(('127.0.0.1',port),timeout=.3) as c:c.sendall(b'LYRA_PROBE');return c.recv(256)==b'LYRA_PROBE'
    except OSError:return False

def tunnel(user,allowed,name):
    before=ssh_log()
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    p=subprocess.Popen(['ssh',*ssh_options(),'-N','-o','ExitOnForwardFailure=yes','-L',f'127.0.0.1:{port}:127.0.0.1:{echo.server_address[1]}',user+'@127.0.0.1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);children.append(p)
    end=time.monotonic()+10;forwarded=False
    while time.monotonic()<end and p.poll() is None:
        if exchange(port):forwarded=True;break
        time.sleep(.05)
    assert forwarded==allowed
    if not allowed:
        out,err=p.communicate(timeout=5);assert p.returncode==255
        record(checks,name,rc=p.returncode,forwarded=False,rejection=exact_ssh_denial(before))
    else:record(checks,name,forwarded=True)
    return p,port

def mux():
    control=PRIVATE/'mux'
    p=subprocess.Popen(['ssh',*ssh_options(),'-M','-S',str(control),'-N','ordinaryuser@127.0.0.1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);children.append(p)
    end=time.monotonic()+10
    while time.monotonic()<end and p.poll() is None:
        if control.exists() and run(['ssh',*ssh_options(),'-S',str(control),'-O','check','ordinaryuser@127.0.0.1'],check=False)['rc']==0:return p,control
        time.sleep(.05)
    raise AssertionError('multiplex did not start')
def mux_command(control,allowed,name):
    before=ssh_log();r=run(['ssh',*ssh_options(),'-S',str(control),'ordinaryuser@127.0.0.1',"printf 'LYRA_%s\\n' MUX_COMMAND"],check=False)
    assert (r['rc']==0 and 'LYRA_MUX_COMMAND' in r['stdout'])==allowed,r
    if not allowed:assert r['rc']==255
    record(checks,name,**r,rejection=exact_ssh_denial(before) if not allowed else None)

def sftp_denied():
    before=ssh_log();out=PRIVATE/'sftp-download';batch=PRIVATE/'sftp-batch';batch.write_text('get /etc/os-release '+str(out)+'\n')
    r=run(['sftp',*ssh_options(),'-b',str(batch),'ordinaryuser@127.0.0.1'],check=False)
    assert r['rc']!=0 and not out.exists()
    record(checks,'new-sftp-denied',**r,rejection=exact_ssh_denial(before))

def session_processes(uid):
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            if os.readlink(p/'exe')==str(SESSION):
                matches=[x for x in account_scope_processes(uid) if x['pid']==int(p.name)]
                if not matches:continue
                row=matches[0]
                row['context']=(p/'attr/current').read_text().strip('\x00\n ');found.append(row)
        except FileNotFoundError:pass
    return found

def gdm_login(user,password,allowed,name):
    uid=pwd.getpwnam(user).pw_uid
    assert not session_processes(uid)
    end=time.monotonic()+30;address=None
    while time.monotonic()<end:
        log=run(['journalctl','-b','-u','gdm.service','--no-pager','-o','cat'])['stdout']
        addresses=re.findall(r'D-Bus server for greeters listening on (\S+)',log)
        if addresses and 'GdmDisplay: session registered: yes' in log:address=addresses[-1];break
        time.sleep(.1)
    assert address,log
    cursor=json.loads(run(['journalctl','-n','1','-o','json'])['stdout'])['__CURSOR']
    gdm=pwd.getpwnam('gdm')
    def drop():os.setgroups([]);os.setgid(gdm.pw_gid);os.setuid(gdm.pw_uid)
    p=subprocess.Popen(['python3','-c',(BASE/'password-client.py').read_text(),address,user],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec_fn=drop);children.append(p)
    events=[];buffer=b'';selector=selectors.DefaultSelector();selector.register(p.stdout,selectors.EVENT_READ);denial=None;observed=None
    try:
        end=time.monotonic()+40
        while time.monotonic()<end:
            for key,_ in selector.select(.1):
                chunk=os.read(key.fd,65536);assert chunk,('client closed',events,p.stderr.read())
                buffer+=chunk
                while b'\n' in buffer:
                    line,buffer=buffer.split(b'\n',1);row=json.loads(line);events.append(row)
                    assert row['event'] not in ('error','timeout'),row
                    if row['event']=='password-prompt':
                        p.stdin.write((json.dumps({'answer':password})+'\n').encode());p.stdin.flush()
            current=session_processes(uid)
            log=run(['journalctl','-b','--after-cursor='+cursor,'--no-pager','-o','cat'])['stdout']
            signals=[x.get('name') for x in events if x['event']=='signal']
            if allowed and current and 'SessionOpened' in signals:observed=current;break
            if not allowed:
                assert not current
                cause='pam_lyra_withdrawal_fixture(gdm-password:session): Experimental withdrawal admission rejected session'
                if cause in log and 'ConversationStopped' in signals:denial=log;observed=[];break
        assert observed is not None,(events,log)
        if allowed:assert all(x['uids']==(uid,)*4 and ':unconfined_t:' in x['context'] for x in observed),observed
        else:assert not any(x.get('name')=='SessionOpened' for x in events)
        assert password not in log
        worker=None
        if allowed:
            rows=[json.loads(line) for line in run(['journalctl','-b','--after-cursor='+cursor,'--no-pager','-o','json'])['stdout'].splitlines()]
            worker_pids={int(x['_PID']) for x in rows if f'pam_unix(gdm-password:session): session opened for user {user}(' in x.get('MESSAGE','')}
            assert len(worker_pids)==1,worker_pids
            worker=worker_pids.pop()
            assert os.readlink(Path('/proc',str(worker),'exe'))==str(WORKER)
        record(checks,name,processes=observed,rejection=denial,events=events,worker_pid=worker)
        return worker
    finally:
        selector.close()
        if p.poll() is None:p.kill()
        p.wait(timeout=10)
