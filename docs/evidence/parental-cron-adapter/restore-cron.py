"""Read-only fixture/policy/process inspection, before or after RPM removal."""
from fixture import *
paths=(CRONPAM,CRONMODULE,BINARY,SYSTEM,PEERSYSTEM,*[table(uid) for uid,n in USERS],*[directory(uid) for uid,n in USERS])
absent={str(p):not p.exists() and not p.is_symlink() for p in paths}
processes=[]
for p in Path('/proc').iterdir():
    if not p.name.isdecimal():continue
    try:
        exe=str((p/'exe').resolve());cg=(p/'cgroup').read_text().strip()
        if exe in (str(BINARY),'/usr/sbin/cron') or '/system.slice/cron.service' in cg:processes.append(dict(pid=int(p.name),exe=exe,cgroup=cg))
    except FileNotFoundError:pass
policy=run(['semodule','-l'])['stdout'];policy_absent=all(line.split()[0]!='cron-state' for line in policy.splitlines())
meta=config();common=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in meta['common_pam_sha256'].items())
row=dict(passed=all(absent.values()) and not processes and policy_absent and common,absent=absent,processes=processes,policy_absent=policy_absent,common_preserved=common,cron_pid=cron_pid())
assert row['cron_pid']=='0';(BASE/'cron-restored-independent.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
