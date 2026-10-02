"""Temporary signed RPM installation in the marked disposable VM only."""
from common import *
assert run(['getenforce'])['stdout'].strip()=='Permissive'
assert run(['rpm','-q','cron','cronie','debianutils'],check=False)['rc']!=0
before=run(['rpm','-qa','--qf','%{NAME}|%{VERSION}|%{RELEASE}|%{ARCH}\n'])['stdout'];(BASE/'packages-before.txt').write_text(before)
assert not {'cron','cronie','debianutils'}&{l.split('|')[0] for l in before.splitlines()}
paths=[Path('/root')/n for n in ('cron-4.2-160100.2.3.x86_64.rpm','cronie-1.7.2-160100.2.3.x86_64.rpm','debianutils-5.4-160100.2.1.x86_64.rpm')]
sigs=run(['rpm','--checksig',*map(str,paths)]);assert sigs['stdout'].count('digests signatures OK')==3,sigs
install=run(['rpm','-Uvh',*map(str,paths)])
run(['systemctl','stop','cron.service']);run(['systemctl','disable','cron.service'])
after=run(['rpm','-qa','--qf','%{NAME}|%{VERSION}|%{RELEASE}|%{ARCH}\n'])['stdout']
b=set(before.splitlines());a=set(after.splitlines());assert not b-a and {l.split('|')[0] for l in a-b}=={'cron','cronie','debianutils'}
row=dict(passed=True,introduced=sorted(a-b),signatures=sigs,installation=install,rpm_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},before_sha256=hashlib.sha256(before.encode()).hexdigest())
(BASE/'installation.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row))
