"""Read interrupted admission ownership, test actual PAM, then restore fixture."""
import sys
sys.path.insert(0,'/root/unit-stop-jobs')
from bridge import *
from fixture import *
from live_common import *
from pam import PROFILE_PATH
import subprocess
checkpoint=json.loads((BASE/'owner-state.json').read_text());assert checkpoint['old_boot']!=boot_id()
kind=checkpoint['kind'];point=checkpoint['point'];checks=[];passed=False;error=None

def snapshot():
    return {p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size,inode=p.stat().st_ino,uid=p.stat().st_uid,gid=p.stat().st_gid,mode=p.stat().st_mode&0o777,nlink=p.stat().st_nlink) for p in PROOFS.iterdir() if p.is_file()}
def raw(name):return (PROOFS/name).read_bytes() if (PROOFS/name).exists() else None
def attempt(action):
    try:return dict(result=action(),code=None)
    except oc.GateError as e:return dict(result=None,code=e.code)
try:
    installed={name:dict(sha256=hashlib.sha256(Path(name).read_bytes()).hexdigest(),inode=Path(name).stat().st_ino,mode=Path(name).stat().st_mode&0o777,uid=Path(name).stat().st_uid,gid=Path(name).stat().st_gid,nlink=Path(name).stat().st_nlink) for name in checkpoint['installed_files']}
    assert installed==checkpoint['installed_files'];run(['setenforce','1'])
    record(checks,'installed-admission-sources-survive-cut',installed_files=installed)
    assert not (BASE/'owner-finally-ran').exists()
    before=snapshot();marker=raw('.deny-1002');owned=raw('.operation-1002.json');journal=raw('.withdrawal-1002.json');proof=raw('1002')
    selected=marker if kind=='marker' else owned if kind=='owner' else proof
    if kind in ('marker','owner'):
        if point in ('partial-write','temp-fsynced'):assert selected is None
        if point=='directory-fsynced':assert selected is not None
        if selected is not None:
            row=ops.decode(selected);assert row['operation']==checkpoint['operation'] and row['phase']=='intent' and row['revision']==1
        assert journal is None and proof is not None and hashlib.sha256(proof).hexdigest()==checkpoint['original_target_proof_sha256']
        if kind=='marker':assert owned is None
        else:
            assert marker is not None
            row=ops.decode(marker);assert row['operation']==checkpoint['operation'] and row['phase']=='intent'
            if owned is not None:assert ops.decode(owned)==row
    else:
        assert marker is not None and owned is not None and journal is not None
        row=ops.decode(owned);assert row['operation']==checkpoint['operation'] and row['phase']=='legacy-blocked' and row['revision']==2
        from withdrawal import decode as decode_withdrawal
        for data in (marker,journal):
            legacy=decode_withdrawal(data);assert legacy['operation']==checkpoint['operation'] and legacy['phase']=='blocked'
        if point=='directory-synced':assert proof is None
        if proof is not None:assert hashlib.sha256(proof).hexdigest()==checkpoint['original_target_proof_sha256']
    blocked=marker is not None
    record(checks,'interrupted-owner-state-is-whole-and-unacknowledged-before-marker',kind=kind,point=point,blocked=blocked,files=before,marker=json.loads(marker) if marker else None,owned=json.loads(owned) if owned else None,journal=json.loads(journal) if journal else None,proof_present=proof is not None,quiescence_claimed=False)
    inspected=attempt(lambda:factory().inspect(1002))
    assert inspected==(dict(result='BlockedRecoveryRequired',code=None) if blocked else dict(result=None,code='RecoveryRequired'))
    assert snapshot()==before;record(checks,'inspection-is-read-only',outcome=inspected)
    calls=[]
    def deny(row):
        unlocked_authority();calls.append(row);return False
    wrong=attempt(lambda:factory().resume(1002,'f'*32 if checkpoint['operation']!='f'*32 else 'e'*32,deny))
    assert wrong['code']==('Conflict' if blocked else 'RecoveryRequired') and not calls and snapshot()==before
    record(checks,'different-operation-refused-before-authorization',outcome=wrong)
    denied=attempt(lambda:factory().resume(1002,checkpoint['operation'],deny))
    assert denied['code']==('Denied' if blocked else 'RecoveryRequired') and len(calls)==(1 if blocked else 0) and snapshot()==before
    record(checks,'fresh-denial-or-missing-marker-preserves-all-state',outcome=denied,authorization_calls=calls)
    run(['systemctl','start','user@1000.service']);assert context(1000).startswith('unconfined_u:unconfined_r:unconfined_t:')
    assert hashlib.sha256((PROOFS/'1000').read_bytes()).hexdigest()==checkpoint['peer_proof_sha256']
    record(checks,'peer-proof-preserved-and-new-admission-succeeds',unit=show(1000),context=context(1000))
    if blocked:
        deny_attempt(checks,'durable-marker-denies-target-pam-even-if-proof-exists')
    else:
        run(['systemctl','start','user@1002.service']);assert context(1002).startswith('unconfined_u:unconfined_r:unconfined_t:')
        record(checks,'uncommitted-withdrawal-preserves-original-admission',unit=show(1002),context=context(1002),withdrawal_acknowledged=False)
    assert snapshot()==before;record(checks,'pam-attempts-do-not-promote-temporary-or-recreate-proof',files=snapshot())
    passed=True
except BaseException as e:error=repr(e);raise
finally:
    Path('/run/lyra-owner-cut-ready.json').unlink(missing_ok=True)
    cleanup=subprocess.run(['python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=140)
    for p in (Path('/usr/libexec/lyra-unit-stop-jobs-probe'),Path('/usr/libexec/lyra-unit-stop-jobs-drop-stop'),Path(PROFILE_PATH)):p.unlink(missing_ok=True)
    result=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,old_boot=checkpoint['old_boot'],new_boot=boot_id(),metadata=checkpoint['metadata'],cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,full_account_protection=False,global_coverage_qualified=False,production_daemon_qualified=False,physical_power_loss_tested=False,producer_quiescence_qualified=False)
    (BASE/'owner-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=result['passed'],checks=len(checks),cleanup_rc=cleanup.returncode)));assert cleanup.returncode==0,cleanup.stderr
