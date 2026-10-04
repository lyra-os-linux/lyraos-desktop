"""Independent absence of probe, backup mask and preservation of original sources."""
from common import *
paths=('/usr/libexec/lyra-unit-stop-jobs-probe','/usr/libexec/lyra-unit-stop-jobs-drop-stop','/var/lib/lyra-unit-stop-effects-test',str(BASE/'saved-mask'))
prior=json.loads(Path('/root/systemd-reference-test/result.json').read_text())
files={path:value[-1] for ref in prior['references'] for path,value in ref['fingerprints']}
row=dict(absent={p:not Path(p).exists() and not Path(p).is_symlink() for p in paths},previous_sources_and_accounts_preserved=all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in files.items()),full_filesystem_rollback_claimed=False,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
row['passed']=all(row['absent'].values()) and row['previous_sources_and_accounts_preserved']
(BASE/'extra-restored.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
