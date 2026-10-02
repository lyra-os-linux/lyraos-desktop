"""Two workers meet inside authorization, before either exclusive mutation."""
from bridge import *
import time
uid=1002;operation=sys.argv[1];release=BASE/sys.argv[2];g=gate();plan=g.plan(uid,operation)
def authorize(p,revoke):
    (BASE/('ready-'+operation+'.json')).write_text(json.dumps(dict(uid=p.uid,operation=p.operation,digest=p.digest,proof_hash=p.proof_hash)))
    end=time.monotonic()+25
    while not release.exists() and time.monotonic()<end:time.sleep(.01)
    assert release.exists(),'race release timeout'
    return True
try:g.block_and_check(plan,authorize)
except oc.GateError as e:code=e.code
else:raise AssertionError('missing producer coverage passed')
row=dict(uid=uid,operation=operation,digest=plan.digest,proof_hash=plan.proof_hash,code=code)
(BASE/('race-'+operation+'.json')).write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True)
