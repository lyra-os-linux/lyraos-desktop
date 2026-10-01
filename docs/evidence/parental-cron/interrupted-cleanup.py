from pathlib import Path
import subprocess,pwd,grp,os,signal,time,shutil
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
assert 'lyra.parental-identity-test=1' in Path('/proc/cmdline').read_text().split()
names=[('cronfixture',31300,41300),('croncontrol',31301,41301)]
Path('/etc/cron.d/lyra-parental-fixture').unlink(missing_ok=True)
for name,uid,gid in names:
    if name in {p.pw_name for p in pwd.getpwall()}:
        account=pwd.getpwnam(name);assert (account.pw_uid,account.pw_gid)==(uid,gid)
    else:assert uid not in {p.pw_uid for p in pwd.getpwall()}
    subprocess.run(['crontab','-u',name,'-r'],capture_output=True)
subprocess.run(['systemctl','stop','cron.service'],check=True)
subprocess.run(['setenforce','0'],check=True)
for name,uid,gid in names:
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():continue
        try:
            actual=int(next(x.split()[1] for x in (proc/'status').read_text().splitlines() if x.startswith('Uid:')))
            if actual==uid and (proc/'exe').resolve()==Path('/usr/bin/lyra-cron-identity-fixture'):os.kill(int(proc.name),signal.SIGTERM)
        except FileNotFoundError:pass
    for _ in range(100):
        if subprocess.run(['pgrep','-u',str(uid)],capture_output=True).returncode:break
        time.sleep(.05)
    assert subprocess.run(['pgrep','-u',str(uid)],capture_output=True).returncode
    if name in {p.pw_name for p in pwd.getpwall()}:subprocess.run(['userdel',name],check=True)
    if name in {g.gr_name for g in grp.getgrall()}:subprocess.run(['groupdel',name],check=True)
for path in ['/home/cronfixture','/home/croncontrol','/var/lib/lyra-parental-test']:
    if Path(path).exists():shutil.rmtree(path)
for path in ['/etc/pam.d/crond','/usr/lib64/security/pam_lyra_producer_registry_fixture.so','/usr/bin/lyra-cron-identity-fixture']:Path(path).unlink(missing_ok=True)
subprocess.run(['semodule','-r','lyra-cron-registry'],check=True)
print('Interrupted fixture removed')
