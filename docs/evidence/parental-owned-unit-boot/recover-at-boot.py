"""VM-only enforcing/read-only inspection; never authorize, resume or repair."""
from boot_common import *
meta=config();assert boot_id()!=meta['initial_boot_id']
before=persistent();run(['setenforce','1'])
row=dict(boot_id=boot_id(),fault=meta['fault'],files_before=before,enforcing=run(['getenforce'])['stdout'].strip(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
if meta['fault']:
    row.update(inspect_executed=False,files_after=persistent())
    (BASE/('hook-'+boot_id()+'.json')).write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True);raise SystemExit(42)
row.update(inspect_executed=True,owner=factory().inspect(1002),records=records(),files_after=persistent())
assert row['owner']=='AdmissionWithdrawnNoQuiescence' and row['records']==meta['before_reboot_records'] and row['files_after']==before
(BASE/('hook-'+boot_id()+'.json')).write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True)
