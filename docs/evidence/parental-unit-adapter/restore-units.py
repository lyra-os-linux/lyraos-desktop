"""Independent registered-unit and cgroup removal check, dedicated VM only."""
from fixture import *
row=units_removed();leaks=[]
for p in Path('/proc').iterdir():
    if not p.name.isdecimal():continue
    try:
        groups=[x.split(':',2)[2] for x in (p/'cgroup').read_text().splitlines()]
        if any(c=='/system.slice/'+n or c.startswith('/system.slice/'+n+'/') for c in groups for n in ALL_UNITS):leaks.append(dict(pid=int(p.name),groups=groups))
    except FileNotFoundError:pass
row.update(cgroup_leaks=leaks,scratch_absent=not(BASE/'mask-controls-scratch').exists() and not(BASE/'mask-controls-alias').is_symlink())
row['passed']=row['passed'] and not leaks and row['scratch_absent']
(BASE/'units-restored-independent.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
