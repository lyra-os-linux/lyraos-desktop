"""Run beyond the VM command channel's 120-second cap, logging to files."""
import json,os,subprocess
from pathlib import Path
assert os.geteuid()==0
assert {'lyra.parental-selinux-test=1','lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
assert not Path('/etc/pam.d/crond').exists() and not Path('/var/lib/lyra-parental-test').exists()
Path('/root/cron-result.json').unlink(missing_ok=True)
with Path('/root/cron-native.stdout').open('w') as out,Path('/root/cron-native.stderr').open('w') as err:
    p=subprocess.Popen(['/usr/bin/python3','/root/cron-exercise.py'],cwd='/root',stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
Path('/root/cron-execution.pid').write_text(str(p.pid)+'\n')
print(json.dumps(dict(pid=p.pid,stdout='/root/cron-native.stdout',stderr='/root/cron-native.stderr')))
