from common import *
paths=('/var/lib/lyra-owned-boot-ledger-test','/var/lib/lyra-producer-inventory-test')
row=dict(passed=not any(Path(p).exists() or Path(p).is_symlink() for p in paths),absent={p:not Path(p).exists() and not Path(p).is_symlink() for p in paths})
(BASE/'ownership-restored-independent.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
