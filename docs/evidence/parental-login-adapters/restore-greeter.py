"""Additional read-only GDM greeter lifetime check, dedicated VM only."""
from common import *
import sys
spec=importlib.util.spec_from_file_location('login_common',BASE/'login-common.py')
lc=importlib.util.module_from_spec(spec);sys.modules[spec.name]=lc;spec.loader.exec_module(lc)
uid=config()['gdm_uid']
processes=lc.account_scope_processes(uid)
logind_absent=run(['loginctl','show-user',str(uid)],check=False)['rc']!=0
row=dict(passed=not processes and logind_absent,gdm_uid=uid,scope_processes=processes,logind_absent=logind_absent)
(BASE/'greeter-restored.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
