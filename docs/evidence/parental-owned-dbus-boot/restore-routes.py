"""Separate read-only bus/path/process inspection after common restoration."""
from fixture import *
row=restored_routes()
processes=[]
for p in Path('/proc').iterdir():
    if not p.name.isdecimal():continue
    try:
        cg=(p/'cgroup').read_text().strip()
        exe=(p/'exe').resolve()
        if '/system.slice/lyra-owned-boot-dbus-' in cg or exe==BINARY:processes.append(dict(pid=int(p.name),cgroup=cg,executable=str(exe)))
    except FileNotFoundError:pass
row['processes']=processes;row['scratch_absent']=not(BASE/'retirement-scratch').exists() and not(BASE/'retirement-scratch-link').is_symlink()
row['passed']=row['passed'] and not processes and row['scratch_absent']
(BASE/'routes-restored-independent.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
