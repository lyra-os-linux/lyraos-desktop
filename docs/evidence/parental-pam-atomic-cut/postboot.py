"""Validate a real new boot before bounded cleanup of the reserved VM fixture."""
import sys
sys.path.insert(0,'/root/unit-stop-jobs')
from bridge import *
from fixture import *
from live_common import *
from pam import PROFILE_PATH
import shutil,subprocess
EFFECT_DIR=Path('/var/lib/lyra-unit-stop-effects-test')
checkpoint=json.loads((BASE/'atomic-state.json').read_text())
assert checkpoint['old_boot']!=boot_id()
n=checkpoint['unit'];checks=[];passed=False;error=None

def artifacts():
    files={str(path):dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),inode=path.stat().st_ino,mode=path.stat().st_mode&0o777,uid=path.stat().st_uid,gid=path.stat().st_gid,nlink=path.stat().st_nlink) for directory in (PROOFS,LEDGER) for path in directory.iterdir() if path.is_file()}
    mask=MASKS_DIR/n;st=mask.lstat()
    return dict(files=files,mask=dict(path=str(mask),inode=st.st_ino,uid=st.st_uid,gid=st.st_gid,mode=st.st_mode,link=os.readlink(mask)))
try:
    installed_files={name:dict(sha256=hashlib.sha256(Path(name).read_bytes()).hexdigest(),inode=Path(name).stat().st_ino,mode=Path(name).stat().st_mode&0o777,uid=Path(name).stat().st_uid,gid=Path(name).stat().st_gid,nlink=Path(name).stat().st_nlink) for name in checkpoint['installed_files']}
    assert installed_files==checkpoint['installed_files']
    record(checks,'postcut-installed-pam-and-unit-sources-intact',installed_files=installed_files)
    run(['setenforce','1'])
    assert artifacts()==checkpoint['artifacts']
    assert not (BASE/'crash-finally-ran').exists()
    # The canonical journal may persist intent or accepted before directory fsync.
    effect_file=next(EFFECT_DIR.glob('.stop-*.json'))
    canonical=json.loads(effect_file.read_text())
    assert canonical['boot_id']==checkpoint['old_boot'] and canonical['owner']['operation']==checkpoint['operation']
    expected={'partial-write':('intent',),'temp-fsynced':('intent',),'renamed':('intent','accepted'),'directory-fsynced':('accepted',)}[checkpoint['point']]
    assert canonical['phase'] in expected
    before_effects={p.name:p.read_bytes() for p in EFFECT_DIR.iterdir() if p.is_file()}
    record(checks,'interrupted-atomic-write-retains-whole-old-or-new-canonical-journal',point=checkpoint['point'],canonical=canonical,files={name:dict(size=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in before_effects.items()})

    assert unit_show(n)['LoadState']=='masked' and unit_show(n)['MainPID']=='0'
    assert not uid_processes(1002) and not scoped_processes((n,))
    record(checks,'real-new-boot-keeps-old-accepted-effect-and-negative-artifacts',old_boot=checkpoint['old_boot'],new_boot=boot_id(),artifacts=artifacts(),unit=unit_show(n),protected_proof_missing=not (PROOFS/'1002').exists())
    consumers=[]
    for mode in ('deny','allow'):
        response=run(['python3',str(BASE/'postboot-consumer.py'),checkpoint['operation'],checkpoint['proof_hash'],mode])
        row=json.loads(response['stdout']);assert row['code']=='RecoveryRequired' and row['outcome']=='blocked'
        assert not row['authorization_calls'] and not row['ipc_requests'] and not row['inherited_pidfds'] and row['result'] is None and row['empty'] is True
        assert artifacts()==checkpoint['artifacts']
        assert {p.name:p.read_bytes() for p in EFFECT_DIR.iterdir() if p.is_file()}==before_effects
        consumers.append(row)
        record(checks,'cross-boot-'+mode+'-refused-before-authorization-without-job-reuse',consumer=row)
    assert consumers[0]['pid']!=consumers[1]['pid']
    denied=run(['systemctl','start',n],check=False);assert denied['rc']!=0 and 'masked' in denied['stderr'].lower()
    record(checks,'persistent-owned-mask-refuses-postboot-producer-start')
    # Fixture maintenance preserves the exact mask inode for causal PAM testing.
    mask=MASKS_DIR/n;backup=BASE/'saved-mask';assert not backup.exists()
    mask.rename(backup)
    try:
        run(['systemctl','daemon-reload']);denied=run(['systemctl','start',n],check=False);unit=unit_show(n)
        assert denied['rc']!=0 and unit['MainPID']=='0' and unit['ExecMainStatus']=='224'
    finally:backup.rename(mask);run(['systemctl','daemon-reload'])
    assert artifacts()==checkpoint['artifacts'] and not uid_processes(1002)
    record(checks,'withdrawn-pam-admission-still-rejected-after-real-reboot',unit=unit)
    # Proof preservation across boots is distinct from old peer process liveness.
    assert hashlib.sha256((PROOFS/'1000').read_bytes()).hexdigest()==checkpoint['peer_proof_sha256']
    run(['systemctl','start','user@1000.service']);assert context(1000).startswith('unconfined_u:unconfined_r:unconfined_t:')
    record(checks,'peer-proof-preserved-and-fresh-peer-admission-succeeds',peer_pid=show(1000)['MainPID'],peer_context=context(1000),old_peer_pid_reused_as_authority=False)
    before=artifacts();deny_attempt(checks,'withdrawn-user-manager-still-rejected-in-new-boot');assert artifacts()==before
    passed=True
except BaseException as exception:
    error=repr(exception);raise
finally:
    Path('/run/lyra-pam-close-hold-test').unlink(missing_ok=True)
    Path('/run/lyra-atomic-cut-ready.json').unlink(missing_ok=True)
    cleanup=subprocess.run(['python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=140)
    for path in (Path('/usr/libexec/lyra-unit-stop-jobs-probe'),Path('/usr/libexec/lyra-unit-stop-jobs-drop-stop'),Path(PROFILE_PATH),BASE/'crash-properties.json'):path.unlink(missing_ok=True)
    if EFFECT_DIR.exists():
        (BASE/'atomic-effect-state.json').write_text(json.dumps({p.name:p.read_text() for p in EFFECT_DIR.iterdir()},indent=2)+'\n');shutil.rmtree(EFFECT_DIR)
    result=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,old_boot=checkpoint['old_boot'],new_boot=boot_id(),cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,metadata=checkpoint['metadata'],full_account_protection=False,global_coverage_qualified=False,production_daemon_qualified=False,cross_boot_recovery_authorized=False,physical_power_loss_tested=False,abrupt_vm_stop_tested=True)
    (BASE/'atomic-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=result['passed'],checks=len(checks),cleanup_rc=cleanup.returncode)));assert cleanup.returncode==0,cleanup.stderr
