"""Root fixture publisher; no machine-wide producer discovery/coverage issuer."""
from state import *
import grp,stat,shutil,fcntl
CATALOG=Path('/var/lib/lyra-producer-inventory-test')
def identity(i):
    a=pwd.getpwnam(i.user);u=pwd.getpwuid(i.uid);g=grp.getgrnam(i.group);gg=grp.getgrgid(i.gid)
    return (a.pw_name,a.pw_uid,a.pw_gid,u.pw_name,g.gr_gid,gg.gr_name)==(i.user,i.uid,i.gid,i.user,i.gid,i.group)
def secure(p,expected):
    s=p.lstat();return stat.S_ISREG(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022 and s.st_nlink==1 and p.read_bytes()==expected

def manifest(uid,digest,guard):
    name='ordinaryuser' if uid==1002 else 'installeduser';gid=1003 if uid==1002 else 1001
    producers={n:dict(state='unsupported',adapter_digest='0'*64,routes=[]) for n in ('classification','gdm','user-manager','ssh','system-units','dbus-activation','cron')}
    producers['classification']=dict(state='registered',adapter_digest=digest,routes=[dict(id='ordinary-attestation',digest=guard)])
    producers['user-manager']=dict(state='registered',adapter_digest=digest,routes=[dict(id=f'user-{uid}',digest=guard)])
    return dict(schema=1,identity=dict(user=name,uid=uid,gid=gid,group=name),revision=1,producers=producers)

def publish(uid,row):
    # Cooperating publisher locks this UID exclusively, never replaces lock inode.
    dfd=os.open(CATALOG,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fd=-1
    try:
        fd=os.open(f'.inventory-{uid}.lock',os.O_RDONLY|os.O_NOFOLLOW,dir_fd=dfd);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        writer.RegistryStore._atomic(dfd,f'{uid}.json',(json.dumps(row,sort_keys=True)+'\n').encode())
    finally:
        if fd>=0:os.close(fd)
        os.close(dfd)

def create_inventory():
    assert not CATALOG.exists();CATALOG.mkdir(mode=0o700)
    for uid in (1000,1002):
        fd=os.open(CATALOG/f'.inventory-{uid}.lock',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.fsync(fd);os.close(fd)
    fd=os.open(CATALOG,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)

def remove_inventory():
    if CATALOG.exists():shutil.rmtree(CATALOG)

def inventory_removed():return dict(passed=not CATALOG.exists(),directory_absent=not CATALOG.exists())
