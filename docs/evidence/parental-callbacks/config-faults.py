"""Native fail-closed checks; call only while the disposable Shell module is loaded."""
from pathlib import Path
import json, os, stat, subprocess
assert 'lyra.parental-selinux-test=1' in Path('/proc/cmdline').read_text().split()
profile=Path('/etc/dconf/profile/lyra-supervised-test')
database=Path('/etc/dconf/db/lyra-supervised-test')
runtime=Path('/run/user/1003')
launcher='/usr/libexec/lyra/trusted-shell-test'
assert Path('/sys/fs/selinux/enforce').read_text().strip()=='1'
original={p:(p.read_bytes(),p.stat().st_uid,p.stat().st_gid,stat.S_IMODE(p.stat().st_mode))
          for p in [profile,database]}
made_runtime=False
records=[]
def restore():
    for p,(data,uid,gid,mode) in original.items():
        p.write_bytes(data);os.chown(p,uid,gid);p.chmod(mode)
def check(name,expected,ordinary=False):
    cmd=['runuser','-u','ordinaryuser' if ordinary else 'parentaltest','--']
    if not ordinary:cmd+=['runcon','system_u:system_r:lyra_parental_probe_t:s0','/opt/lyra-parental-probe/probe']
    cmd+=[launcher]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=10)
    records.append(dict(name=name,rc=r.returncode,stdout=r.stdout,stderr=r.stderr))
    assert r.returncode==126 and expected in r.stderr,records[-1]
try:
    # Keep paths in place to preserve their SELinux labels across faults.
    database.chmod(0o666)
    check('writable-administrator-database','missing or untrusted administrator configuration')
    restore()
    os.chown(database,1003,1004)
    check('non-root-administrator-database','missing or untrusted administrator configuration')
    restore()
    if not runtime.exists():
        runtime.mkdir(mode=0o700);os.chown(runtime,1003,1004)
        subprocess.run(['chcon','-t','user_tmp_t',str(runtime)],check=True)
        made_runtime=True
    assert runtime.is_dir() and not runtime.is_symlink() and runtime.stat().st_uid==1003
    profile.write_text('user-db:user\n')
    check('profile-does-not-apply-locks','desktop restrictions are not locked and effective')
    restore()
    database.write_bytes(b'invalid dconf database\n')
    check('corrupt-administrator-database','desktop restrictions are not locked and effective')
    restore()
    check('ordinary-account-cannot-enter-shell-domain','not in trusted shell domain',ordinary=True)
    subprocess.run(['setenforce','0'],check=True)
    check('permissive-mode-refused','SELinux is not enforcing')
finally:
    subprocess.run(['setenforce','1'],check=True)
    restore()
    Path('/root/trusted-shell-config-faults.json').write_text(json.dumps(records,indent=2)+'\n')
    if made_runtime:
        # dconf creates a change-notification file even when values are only read.
        for item in [runtime/'dconf/user',runtime/'dconf',runtime]:
            if not item.exists():continue
            assert not item.is_symlink() and item.stat().st_uid==1003
            if item.is_dir():item.rmdir()
            else:item.unlink()
print(json.dumps(records,indent=2))
