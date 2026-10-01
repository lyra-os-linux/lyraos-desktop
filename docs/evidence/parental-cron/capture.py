"""Read-only capture of the detached native cron experiment."""
import hashlib,json
from pathlib import Path
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
assert {'lyra.parental-selinux-test=1','lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
result=json.loads(Path('/root/cron-result.json').read_text());pid=int(Path('/root/cron-execution.pid').read_text())
p=Path('/proc',str(pid))
if p.exists():
    state=next(line.split()[1] for line in (p/'status').read_text().splitlines() if line.startswith('State:'))
    assert state=='Z',state
else:state='absent'
stdout=Path('/root/cron-native.stdout').read_text();stderr=Path('/root/cron-native.stderr').read_text()
checks=[json.loads(line) for line in stdout.splitlines() if line.startswith('{"name":')]
assert result['passed'] and checks==result['checks'] and not stderr
row=dict(pid=pid,final_process_state=state,result_sha256=hashlib.sha256(Path('/root/cron-result.json').read_bytes()).hexdigest(),
         stdout=stdout,stderr=stderr,passed=True)
Path('/root/cron-capture.json').write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps(row))
