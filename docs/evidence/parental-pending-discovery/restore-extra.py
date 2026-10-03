from fixture import *
extra='lyra-discovery-dbus-unregistered.service';unit=ushow(extra)
paths=[Path('/run/systemd/transient')/extra,Path('/run/systemd/system')/extra]
row=dict(unit=unit,absent={str(p):not p.exists() and not p.is_symlink() for p in paths},passed=unit['MainPID']=='0' and all(not p.exists() and not p.is_symlink() for p in paths))
(BASE/'extra-restored-independent.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
