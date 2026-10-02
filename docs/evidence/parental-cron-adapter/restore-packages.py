"""Remove only the three introduced packages and compare exact RPM tuples."""
from common import *
assert not Path('/etc/pam.d/crond').exists()
assert run(['systemctl','show','cron.service','-p','MainPID','--value'])['stdout'].strip()=='0'
before=set((BASE/'packages-before.txt').read_text().splitlines())
current=set(run(['rpm','-qa','--qf','%{NAME}|%{VERSION}|%{RELEASE}|%{ARCH}\n'])['stdout'].splitlines())
assert not before-current and {l.split('|')[0] for l in current-before}=={'cron','cronie','debianutils'}
commands=[run(['rpm','-e','--test','cronie','cron','debianutils']),run(['systemctl','disable','cron.service']),run(['rpm','-e','cronie','cron','debianutils']),run(['systemctl','daemon-reload'])]
after=set(run(['rpm','-qa','--qf','%{NAME}|%{VERSION}|%{RELEASE}|%{ARCH}\n'])['stdout'].splitlines())
row=dict(passed=before==after,commands=commands,exact_package_tuples_restored=before==after)
(BASE/'packages-restored.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
