"""Restore only the PAM, registry, linger and unit fixtures in this VM."""
from common import *
import shutil,sys
from fixture import remove_cron,restored_cron
remove_cron()
(BASE/'cron-restored.json').write_text(json.dumps(restored_cron(),indent=2)+'\n')
meta=config();cleanup=[]
run(['setenforce','0'])
def clean(name,action):
    try:action();cleanup.append(dict(name=name,passed=True))
    except Exception as error:cleanup.append(dict(name=name,passed=False,error=str(error)))
for name,uid in (('parentaltest',1003),('ordinaryuser',1002),('installeduser',1000)):
    if Path('/var/lib/systemd/linger',name).exists():clean('disable-linger-'+name,lambda name=name:run(['loginctl','disable-linger',name]))
    run(['loginctl','terminate-user',name],check=False)
    clean('stop-manager-'+name,lambda uid=uid:stop(uid))
    clean('stop-runtime-'+name,lambda uid=uid:run(['systemctl','stop',f'user-runtime-dir@{uid}.service']))
    end=time.monotonic()+20
    while uid_processes(uid) and time.monotonic()<end:time.sleep(.1)
    assert not uid_processes(uid)
    clean('drain-logind-'+name,lambda uid=uid,name=name:drain(uid,name))
if UNIT.exists():clean('disable-recovery-fixture',lambda:run(['systemctl','disable','--now',UNIT.name]))
clean('restore-permissive',lambda:run(['setenforce','0']))
def restore_pam():
    original=(BASE/'original-pam').read_bytes();assert hashlib.sha256(original).hexdigest()==meta['original_pam_sha256']
    PAM.write_bytes(original);PAM.chmod(meta['original_pam_mode']);run(['restorecon',str(PAM)])
clean('restore-original-pam',restore_pam)
clean('remove-fixture-module',lambda:MODULE.unlink(missing_ok=True))
for path in (Path('/var/lib/lyra-parental-roles-test'),Path('/var/lib/lyra-ordinary-attestation-test')):
    if path.exists():clean('remove-'+path.name,lambda path=path:shutil.rmtree(path))
if DIRECTORY.exists():clean('remove-fixture-registry',lambda:shutil.rmtree(DIRECTORY))
clean('remove-fixture-unit',lambda:UNIT.unlink(missing_ok=True))
clean('daemon-reload',lambda:run(['systemctl','daemon-reload']))
run(['systemctl','reset-failed',UNIT.name,'user@1003.service','user@1002.service'],check=False)
restored=dict(pam=hashlib.sha256(PAM.read_bytes()).hexdigest()==meta['original_pam_sha256'],pam_mode=PAM.stat().st_mode&0o777==meta['original_pam_mode'],
    vendor=hashlib.sha256(VENDOR.read_bytes()).hexdigest()==meta['vendor_sha256'],
    accounts=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in meta['account_sha256'].items()),
    removed=not any(p.exists() for p in (DIRECTORY,MODULE,UNIT,Path('/etc/systemd/system/multi-user.target.wants',UNIT.name))),
    linger_removed=not any(Path('/var/lib/systemd/linger',n).exists() for n in ('parentaltest','ordinaryuser','installeduser')),
    managers_stopped=all(show(uid)['MainPID']=='0' and not uid_processes(uid) for uid in (1000,1002,1003)),
    permissive=run(['getenforce'])['stdout'].strip()=='Permissive')
row=dict(passed=all(x['passed'] for x in cleanup) and all(restored.values()),cleanup=cleanup,restored=restored,boot_id=boot_id())
(BASE/'cleanup.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
if '--reset' in sys.argv:CONFIG.unlink();(BASE/'original-pam').unlink()
