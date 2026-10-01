"""VM-only recovery hook; no account is ever enrolled or unblocked here."""
from common import *
meta=config();assert boot_id()!=meta['initial_boot_id']
before=writer.RegistryStore(DIRECTORY).snapshot();files_before=file_state()
run(['setenforce','1'])
row=dict(boot_id=boot_id(),fault=meta['fault'],snapshot_before=before,files_before=files_before,
    enforcing=run(['getenforce'])['stdout'].strip(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
if meta['fault']:
    row.update(recovery_executed=False,snapshot_after=before,files_after=file_state())
    (BASE/('hook-'+boot_id()+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True);raise SystemExit(42)
outcome=writer.RegistryStore(DIRECTORY).recover()
row.update(recovery_executed=True,outcome=outcome,snapshot_after=writer.RegistryStore(DIRECTORY).snapshot(),files_after=file_state())
(BASE/('hook-'+boot_id()+'.json')).write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps(row),flush=True)
