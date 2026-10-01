"""Observe native automatic linger admission after a real kernel restart."""
from common import *
checks=[];meta=config();generation=meta['generation_b'];fault=meta['fault']
assert boot_id()!=meta['initial_boot_id']
if fault:assert boot_id()!=meta['verified_boot_id']
hook_path=BASE/('hook-'+boot_id()+'.json')
end=time.monotonic()+30
while not hook_path.exists() and time.monotonic()<end:time.sleep(.1)
hook=json.loads(hook_path.read_text())
assert hook['boot_id']==boot_id() and hook['fault']==fault and hook['enforcing']=='Enforcing'
assert run(['getenforce'])['stdout'].strip()=='Enforcing'
record(checks,'new-kernel-boot-and-enforcing-recovery-hook-observed',hook=hook)
# All durable transaction bytes survive the reboot until the fixture hook runs.
assert hook['files_before']==meta['before_reboot_files']
record(checks,'durable-registry-barriers-journal-and-leases-survive-real-reboot',files=hook['files_before'])
rows,journals=writer.RegistryStore(DIRECTORY).snapshot();current=next(r for r in rows if r['generation']==generation)
assert current['state']=='recovering' and (DIRECTORY/('.barrier-'+generation)).exists()
assert meta['generation_a'] not in journals
record(checks,'recovery-does-not-enroll-or-remove-newer-barrier',row=current,journals=journals)
if fault:
    assert not hook['recovery_executed'] and hook['files_before']==hook['files_after']
    status=run(['systemctl','show',UNIT.name,'-p','ExecMainStatus','--value'])['stdout'].strip();assert status=='42',status
    record(checks,'failed-boot-recovery-keeps-durable-blocked-state',status=status)
else:
    assert hook['recovery_executed'] and hook['outcome'][generation]=='blocked'
    assert next(r for r in hook['snapshot_before'][0] if r['generation']==generation)['state']=='active'
    assert hook['snapshot_before'][1][meta['generation_a']]['phase']=='committed'
    record(checks,'older-commit-recovery-preserves-newer-orphan-barrier',outcome=hook['outcome'])
failed=wait_state(1003,'failed');assert failed['MainPID']=='0' and failed['ExecMainStatus']=='224',failed
assert not uid_processes(1003) and not holders()
log=run(['journalctl','-b','-u','user@1003.service','--no-pager','-o','cat'])['stdout']
assert 'Experimental registry-backed admission rejected session' in log,log
record(checks,'automatic-linger-manager-denied-with-exact-native-pam-cause',unit=failed,journal=log)
ordinary=wait_state(1002,'active');assert ':unconfined_t:' in context(1002)
assert Path('/var/lib/systemd/linger/ordinaryuser').exists() and Path('/var/lib/systemd/linger/parentaltest').exists()
record(checks,'ordinary-linger-manager-survives-supervised-recovery-failure',unit=ordinary,context=context(1002))
# Retry is another native PAM admission; recovery alone must not permit it.
run(['systemctl','reset-failed','user@1003.service'])
retry=run(['systemctl','start','user@1003.service'],check=False);state=show(1003)
assert retry['rc'] and state['MainPID']=='0' and state['ExecMainStatus']=='224' and not holders()
record(checks,'manual-manager-retry-stays-denied-without-explicit-enrollment',unit=state,command=retry)
save_result('verified-fault' if fault else 'verified-recovery',checks,hook=hook)
if not fault:
    meta.update(verified_boot_id=boot_id(),fault=True,before_reboot_files=file_state());save(meta)
