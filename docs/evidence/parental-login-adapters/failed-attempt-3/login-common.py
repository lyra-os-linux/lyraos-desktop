"""Additional login fixtures and exact restoration, dedicated VM only."""
from state import *
import stat,shutil,grp,socket,selectors,re,secrets,select
SSH_UNIT='lyra-login-adapters-sshd.service'
SSH_CONFIG=Path('/etc/ssh/lyra-login-adapters.conf')
KEYS=Path('/etc/ssh/lyra-login-adapters-keys')
HOSTKEY=Path('/etc/ssh/ssh_host_lyra_login_adapters_key')
PRIVATE=Path('/run/lyra-login-adapters')
SSH_MODULE=Path('/usr/lib64/security/pam_lyra_ordinary_ssh_fixture.so')
WORKER=Path('/usr/libexec/gdm/gdm-session-worker')
PATCHED=Path('/root/gdm-official-build/daemon/gdm-session-worker')
HELPER=Path('/usr/libexec/gdm/gdm-wayland-session')
SESSION=Path('/opt/lyra-parental-probe/manager-session')
CONF=Path('/etc/gdm/custom.conf')
POLICIES=('lyra-login-state','lyra-registry-gdm')
EXTRA=(SSH_CONFIG,KEYS,HOSTKEY,HOSTKEY.with_suffix('.pub'),PRIVATE,SSH_MODULE,SESSION)
LOGIN_PATHS=tuple(map(Path,('/etc/pam.d/sshd','/etc/pam.d/gdm-password','/etc/gdm/custom.conf','/etc/shadow','/usr/libexec/gdm/gdm-session-worker','/usr/libexec/gdm/gdm-wayland-session','/usr/share/wayland-sessions/gnome.desktop','/usr/share/wayland-sessions/gnome-wayland.desktop','/var/lib/AccountsService/users/ordinaryuser','/var/lib/AccountsService/users/installeduser')))

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def backup_login(meta):
    assert not any(p.exists() for p in EXTRA)
    assert run(['systemctl','show','gdm.service','-p','MainPID','--value'])['stdout'].strip()=='0'
    assert run(['systemctl','show','sshd.service','-p','MainPID','--value'])['stdout'].strip()=='0'
    assert digest(WORKER)=='40e1387811b74adcde44b8a34f03db1d032190867e1c5f4092bb9aa1362fdab8'
    assert digest(PATCHED)=='92a976fc0e375cd41d1a9330c650241081fd09278d464662a435200cc296704f'
    assert not set(POLICIES)&{line.split()[0] for line in run(['semodule','-l'])['stdout'].splitlines()}
    meta['login_paths']={};(BASE/'backups').mkdir(mode=0o700,exist_ok=True)
    for index,p in enumerate(LOGIN_PATHS):
        row={'present':p.exists(),'backup':str(index)}
        if p.exists():
            s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_uid==0 and s.st_nlink==1
            row.update(sha256=digest(p),mode=s.st_mode&0o7777,uid=s.st_uid,gid=s.st_gid,label=os.getxattr(p,'security.selinux').hex())
            target=BASE/'backups'/str(index);target.write_bytes(p.read_bytes());target.chmod(0o600)
        meta['login_paths'][str(p)]=row
    meta['accounts_active']=run(['systemctl','is-active','accounts-daemon.service'],check=False)['rc']==0
    meta['login_vendor_sha256']={str(p):digest(p) for p in map(Path,('/usr/lib/pam.d/sshd','/usr/lib/pam.d/gdm-password'))}
    meta['diagnostic_worker_sha256']=digest(PATCHED)
    meta['gdm_uid']=pwd.getpwnam('gdm').pw_uid

def restore_login():
    meta=config()
    run(['systemctl','stop',SSH_UNIT,'gdm.service'],check=False)
    gdm_uid=meta['gdm_uid'];run(['loginctl','terminate-user',str(gdm_uid)],check=False)
    run(['systemctl','stop',f'user@{gdm_uid}.service',f'user-runtime-dir@{gdm_uid}.service'],check=False)
    run(['setenforce','0']);run(['systemctl','stop','accounts-daemon.service'])
    for ptext,row in meta['login_paths'].items():
        p=Path(ptext)
        if not row['present']:p.unlink(missing_ok=True);continue
        data=(BASE/'backups'/row['backup']).read_bytes();assert hashlib.sha256(data).hexdigest()==row['sha256']
        p.write_bytes(data);os.chown(p,row['uid'],row['gid']);p.chmod(row['mode']);os.setxattr(p,'security.selinux',bytes.fromhex(row['label']))
    for p in EXTRA:
        if p.is_dir():shutil.rmtree(p)
        else:p.unlink(missing_ok=True)
    installed={line.split()[0] for line in run(['semodule','-l'])['stdout'].splitlines()}
    for name in POLICIES:
        if name in installed:run(['semodule','-r',name])
    if meta['accounts_active']:run(['systemctl','start','accounts-daemon.service'])
    run(['systemctl','reset-failed',SSH_UNIT],check=False)
    row=login_restored(meta);(BASE/'login-restored.json').write_text(json.dumps(row,indent=2)+'\n');assert row['passed'],row

def login_restored(meta):
    files={}
    for ptext,row in meta['login_paths'].items():
        p=Path(ptext)
        if not row['present']:files[ptext]=not p.exists();continue
        s=p.lstat();files[ptext]=digest(p)==row['sha256'] and s.st_mode&0o7777==row['mode'] and (s.st_uid,s.st_gid)==(row['uid'],row['gid']) and os.getxattr(p,'security.selinux').hex()==row['label']
    vendors=all(digest(Path(p))==h for p,h in meta['login_vendor_sha256'].items())
    absent={str(p):not p.exists() for p in EXTRA}
    policies_absent=not set(POLICIES)&{line.split()[0] for line in run(['semodule','-l'])['stdout'].splitlines()}
    units={u:run(['systemctl','show',u,'-p','MainPID','--value'])['stdout'].strip() for u in ('gdm.service',SSH_UNIT,f'user@{meta["gdm_uid"]}.service',f'user-runtime-dir@{meta["gdm_uid"]}.service')}
    return dict(passed=all(files.values()) and vendors and all(absent.values()) and policies_absent and all(p=='0' for p in units.values()),files=files,vendors=vendors,absent=absent,policies_absent=bool(policies_absent),units=units)

def protected_bytes(path,expected):
    s=path.lstat()
    return stat.S_ISREG(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022 and s.st_nlink==1 and path.read_bytes()==expected

def account_scope_processes(uid):
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            uids=tuple(int(v) for v in next(line.split()[1:] for line in (p/'status').read_text().splitlines() if line.startswith('Uid:')))
            groups=[line.split(':',2)[2] for line in (p/'cgroup').read_text().splitlines()]
            prefix=f'/user.slice/user-{uid}.slice'
            if uid in uids or any(g==prefix or g.startswith(prefix+'/') for g in groups):
                found.append(dict(pid=int(p.name),uids=uids,cgroup=groups,comm=(p/'comm').read_text().strip()))
        except FileNotFoundError:pass
    return found

def observed_empty(uid):
    return show(uid)['MainPID']=='0' and run(['systemctl','show',f'user-runtime-dir@{uid}.service','-p','ActiveState','--value'])['stdout'].strip()=='inactive' and not account_scope_processes(uid) and run(['loginctl','show-user',str(uid)],check=False)['rc']!=0
