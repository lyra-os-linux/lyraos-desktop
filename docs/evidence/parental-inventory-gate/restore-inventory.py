"""Independent read-only check that fixture inventory authority was removed."""
import json,os
from pathlib import Path
assert os.geteuid()==0
assert {'lyra.parental-selinux-test=1','lyra.parental-identity-test=1'}<=set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
p=Path('/var/lib/lyra-producer-inventory-test')
row=dict(passed=not p.exists() and not p.is_symlink(),inventory_directory_absent=not p.exists() and not p.is_symlink())
Path('/root/inventory-gate/inventory-restored-independent.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
