"""Two registered job routes per UID; no arbitrary shell/descendant claim."""
from state import *
import grp,select,signal,stat,shutil
CRONPAM=Path('/etc/pam.d/crond');CRONVENDOR=Path('/usr/lib/pam.d/crond')
CRONMODULE=Path('/usr/lib64/security/pam_lyra_cron_ordinary_fixture.so')
BINARY=Path('/usr/bin/lyra-cron-adapter-fixture')
SYSTEM=Path('/etc/cron.d/lyra-cron-adapter-target');PEERSYSTEM=Path('/etc/cron.d/lyra-cron-adapter-peer')
USERS=((1002,'ordinaryuser'),(1000,'installeduser'))
SPOOL=Path('/var/spool/cron/tabs');CTX='lyra_cron_adapter_state_t'
def directory(uid):return Path(pwd.getpwuid(uid).pw_dir)/'lyra-cron-adapter'
def table(uid):return SPOOL/pwd.getpwuid(uid).pw_name

def safe(path,expected,uid=0):
    s=path.lstat();return stat.S_ISREG(s.st_mode) and s.st_uid==uid and not s.st_mode&0o022 and s.st_nlink==1 and path.read_bytes()==expected

def label():
    for p in (PROOFS,ROLES,DIRECTORY):run(['chcon','-R','-t',CTX,str(p)])

def cron_pid():return run(['systemctl','show','cron.service','-p','MainPID','--value'])['stdout'].strip()
def pid_identity(pid):
    p=Path('/proc',str(pid));text=(p/'status').read_text()
    return dict(pid=pid,uids=list(map(int,next(l.split()[1:] for l in text.splitlines() if l.startswith('Uid:')))),exe=str((p/'exe').resolve()),cgroup=(p/'cgroup').read_text().strip(),parent=int(next(l.split()[1] for l in text.splitlines() if l.startswith('PPid:'))))
def rows(uid,kind):
    p=directory(uid)/(kind+'.log')
    return [dict(uid=int(u),pid=int(pid),epoch=int(epoch)) for u,pid,epoch in (l.split() for l in p.read_text().splitlines())] if p.exists() else []
def live(row):
    p=pid_identity(row['pid']);assert p['uids']==[row['uid']]*4 and p['exe']==str(BINARY) and '/system.slice/cron.service' in p['cgroup'],p
    return p

def monitor(item):
    pid=item['parent']
    for _ in range(6):
        p=pid_identity(pid)
        if p['uids']==[0]*4 and p['exe']=='/usr/sbin/cron' and '/system.slice/cron.service' in p['cgroup'] and str(pid)!=cron_pid():return p
        pid=p['parent'];assert pid>1
    raise AssertionError('no root job monitor')

def wait_tick(uid,count):
    end=time.monotonic()+180
    while time.monotonic()<end:
        if all(len(rows(uid,k))>=count for k in ('user','system')):time.sleep(.4);return
        time.sleep(.2)
    raise AssertionError(dict(uid=uid,count=count,rows={k:rows(uid,k) for k in ('user','system')},journal=run(['journalctl','-u','cron.service','--no-pager','-o','cat'])['stdout']))

def cursor():return json.loads(run(['journalctl','-n','1','-o','json'])['stdout'])['__CURSOR']
def denied_tick(start,target_count,peer_count):
    wait_tick(1000,peer_count)
    assert all(len(rows(1002,k))==target_count for k in ('user','system'))
    log=run(['journalctl','--after-cursor='+start,'--no-pager','-o','cat'])['stdout']
    exact=[l for l in log.splitlines() if 'pam_lyra_cron_ordinary_fixture(crond:account): Experimental ordinary cron admission rejected account' in l]
    native=[l for l in log.splitlines() if '(ordinaryuser)' in l and 'FAILED to authorize user with PAM' in l]
    assert len(exact)==len(native)==2,(exact,native,log)
    return dict(journal_cursor=start,guard_rejections=exact,cron_account_errors=native,target_count=target_count,peer_count=peer_count)

def create_cron():
    assert not any(p.exists() or p.is_symlink() for p in (CRONPAM,CRONMODULE,BINARY,SYSTEM,PEERSYSTEM,*[table(uid) for uid,n in USERS],*[directory(uid) for uid,n in USERS]))
    meta=config();meta['cron_vendor_sha256']=hashlib.sha256(CRONVENDOR.read_bytes()).hexdigest()
    meta['common_pam_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/etc/pam.d').glob('common-*') if p.is_file()};save(meta)
    run(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(BASE/'cron-ordinary-guard.c'),'-o',str(CRONMODULE),'-lpam','-lselinux']);CRONMODULE.chmod(0o755);run(['restorecon',str(CRONMODULE)])
    run(['gcc','-Wall','-Wextra','-Werror','-O2',str(BASE/'payload.c'),'-o',str(BINARY)]);run(['restorecon',str(BINARY)])
    run(['semodule','-i',str(BASE/'cron-state.cil')]);label()
    CRONPAM.write_bytes(b'account requisite pam_lyra_cron_ordinary_fixture.so\n'+CRONVENDOR.read_bytes());CRONPAM.chmod(0o644);run(['restorecon',str(CRONPAM)])
    sources={str(CRONPAM):CRONPAM.read_bytes(),str(CRONMODULE):CRONMODULE.read_bytes(),str(CRONVENDOR):CRONVENDOR.read_bytes(),str(BINARY):BINARY.read_bytes()}
    labels=[]
    for uid,user in USERS:
        home=directory(uid);home.mkdir(mode=0o700);os.chown(home,uid,pwd.getpwuid(uid).pw_gid);run(['restorecon','-R',str(home)])
        temp=BASE/(user+'.table');temp.write_text(f'MAILTO=""\n* * * * * {BINARY} {home}/user.log\n');run(['crontab','-u',user,str(temp)]);temp.unlink()
        before=run(['ls','-Z',str(table(uid))])['stdout'].strip();run(['restorecon',str(table(uid))]);labels.append(dict(uid=uid,before=before,after=run(['ls','-Z',str(table(uid))])['stdout'].strip()))
        p=SYSTEM if uid==1002 else PEERSYSTEM;p.write_text(f'MAILTO=""\n* * * * * {user} {BINARY} {home}/system.log\n');p.chmod(0o644);run(['restorecon',str(p)])
        sources[str(table(uid))]=table(uid).read_bytes();sources[str(p)]=p.read_bytes()
    (BASE/'spool-labels.json').write_text(json.dumps(labels,indent=2)+'\n');return sources

def catalog(identity,jobs,sources):
    expected={('user',identity.user),('system',SYSTEM.name)}
    if {(j.kind,j.name) for j in jobs}!=expected:return False
    if {p.name for p in SYSTEM.parent.glob('lyra-cron-adapter-target*')}!={SYSTEM.name}:return False
    for j in jobs:
        p=table(identity.uid) if j.kind=='user' else SYSTEM
        if not safe(p,sources[str(p)]) or hashlib.sha256(p.read_bytes()).hexdigest()!=j.digest:return False
    a=pwd.getpwnam(identity.user);g=grp.getgrnam(identity.group)
    return (a.pw_uid,a.pw_gid,g.gr_gid)==(identity.uid,identity.gid,identity.gid)

def admission(identity,jobs,sources):
    return all(safe(Path(p),sources[p]) for p in map(str,(CRONPAM,CRONMODULE,CRONVENDOR,BINARY))) and all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in config()['common_pam_sha256'].items()) and run(['getenforce'])['stdout'].strip()=='Enforcing' and CTX in run(['ls','-Zd',str(PROOFS)])['stdout']

def signal_payloads(identity,jobs,items,pins):
    if len(items)!=len(pins):return False
    for item,pin in zip(items,pins):
        if select.select([pin],[],[],0)[0]:continue
        now=pid_identity(item['pid'])
        if now!=item or now['uids']!=[identity.uid]*4 or now['exe']!=str(BINARY):return False
        signal.pidfd_send_signal(pin,signal.SIGTERM)
    return True

def observe(jobs,payload_pins,monitor_pins):
    return not uid_processes(1002) and all(select.select([p],[],[],0)[0] for p in payload_pins+monitor_pins)

def remove_cron():
    for uid,user in USERS:
        if table(uid).exists():run(['crontab','-u',user,'-r'])
    SYSTEM.unlink(missing_ok=True);PEERSYSTEM.unlink(missing_ok=True)
    # Daemon stopped only during final fixture cleanup, never target revocation.
    run(['systemctl','stop','cron.service'])
    for uid,user in USERS:
        for row in uid_processes(uid):
            try:
                item=pid_identity(row['pid'])
                if item['exe']!=str(BINARY):continue
                fd=os.pidfd_open(item['pid'])
                try:signal.pidfd_send_signal(fd,signal.SIGTERM)
                finally:os.close(fd)
            except ProcessLookupError:pass
        if directory(uid).exists():shutil.rmtree(directory(uid))
    CRONPAM.unlink(missing_ok=True);CRONMODULE.unlink(missing_ok=True);BINARY.unlink(missing_ok=True)
    run(['semodule','-r','cron-state'],check=False)

def restored_cron():
    paths=(CRONPAM,CRONMODULE,BINARY,SYSTEM,PEERSYSTEM,*[table(uid) for uid,n in USERS],*[directory(uid) for uid,n in USERS])
    absent={str(p):not p.exists() and not p.is_symlink() for p in paths};meta=config()
    common=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in meta.get('common_pam_sha256',{}).items())
    # Native cleanup precedes package removal, so vendor must still be present.
    vendor=hashlib.sha256(CRONVENDOR.read_bytes()).hexdigest()==meta['cron_vendor_sha256'] if 'cron_vendor_sha256' in meta else True
    return dict(passed=all(absent.values()) and cron_pid()=='0' and common and vendor,absent=absent,cron_pid=cron_pid(),common_preserved=common,vendor_preserved=vendor)
