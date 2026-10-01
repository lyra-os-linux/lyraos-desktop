"""Remove only the three packages introduced by the disposable cron test."""
import hashlib,json,os,subprocess
from pathlib import Path
assert os.geteuid()==0
assert {'lyra.parental-selinux-test=1','lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
def run(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=120)
    row=dict(argv=args,rc=p.returncode,stdout=p.stdout,stderr=p.stderr)
    assert p.returncode==0,row
    return row
before=set(Path('/root/cron-packages-before.txt').read_text().splitlines())
current=set(run(['rpm','-qa','--qf','%{NAME}\n'])['stdout'].splitlines())
assert current-before=={'cron','cronie','debianutils'} and not before-current
assert subprocess.check_output(['systemctl','show','cron.service','-p','MainPID','--value'],text=True).strip()=='0'
assert not any(Path(p).exists() for p in ('/etc/pam.d/crond','/var/lib/lyra-parental-test','/etc/cron.d/lyra-parental-fixture','/usr/bin/lyra-cron-identity-fixture'))
result=dict(packages_before_sha256=hashlib.sha256(Path('/root/cron-packages-before.txt').read_bytes()).hexdigest(),
    introduced=sorted(current-before),commands=[])
result['commands'].append(run(['rpm','-e','--test','cronie','cron','debianutils']))
result['commands'].append(run(['systemctl','disable','cron.service']))
result['commands'].append(run(['rpm','-e','cronie','cron','debianutils']))
result['commands'].append(run(['systemctl','daemon-reload']))
after=set(run(['rpm','-qa','--qf','%{NAME}\n'])['stdout'].splitlines())
result['package_set_restored']=before==after
result['passed']=result['package_set_restored']
Path('/root/cron-packages-restored.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));assert result['passed']
