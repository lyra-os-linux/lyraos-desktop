from state import *
checks=[];meta=config();current=boot_id()
assert current!=meta['initial_boot_id']
hook=BASE/('hook-'+current+'.json');end=time.monotonic()+30
while not hook.exists() and time.monotonic()<end:time.sleep(.2)
row=json.loads(hook.read_text())
assert row['enforcing']=='Enforcing' and run(['getenforce'])['stdout'].strip()=='Enforcing'
assert row['files_before']==meta['before_reboot_files'] and row['files_after']==row['files_before']
assert row['source_sha256']==meta['source_sha256']['recover-at-boot.py']
record(checks,'durable-state-survives-kernel-reboot',files=state(),boot_id=current)
status=run(['systemctl','show',UNIT.name,'-p','ExecMainStatus','--value'])['stdout'].strip()
if meta['fault']:
    assert not row['inspect_executed'] and status=='42' and current!=meta['first_verified_boot_id']
else:
    assert row['inspect_executed'] and status=='0' and row['outcome']=='BlockedUntilAuthorizedRecovery'
record(checks,'hook-fault-no-metadata-change' if meta['fault'] else 'hook-inspects-without-reenrollment',hook=row,status=status)
end=time.monotonic()+30
while time.monotonic()<end:
    if show(TARGET)['ExecMainStatus']=='224' and show(PEER)['ActiveState']=='active':break
    time.sleep(.2)
target=show(TARGET);journal=run(['journalctl','-b','-u','user@1002.service','--no-pager','-o','cat'])['stdout']
assert target['MainPID']=='0' and target['ExecMainStatus']=='224'
assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in journal
record(checks,'target-linger-auto-admission-denied',unit=target,journal=journal)
peer=show(PEER);assert peer['ActiveState']=='active' and int(peer['MainPID'])>0
assert context(PEER).startswith('unconfined_u:unconfined_r:unconfined_t:')
record(checks,'unrelated-ordinary-linger-auto-admitted',unit=peer,context=context(PEER))
deny_attempt(checks,'manual-target-retry-denied-peer-pid-preserved')
store=make();operation=meta['operation']
if not meta['fault']:
    assert (PROOFS/'1002').exists() and not (PROOFS/'.withdrawal-1002.json').exists()
    before=state()
    try:store.resume(1002,operation,lambda _:False)
    except WithdrawalError as e:assert str(e)=='Denied'
    else:raise AssertionError('denied authorization proceeded')
    assert state()==before
    assert store.resume(1002,operation,lambda _:True)=='AdmissionBlockedProofRetiredNoQuiescence'
    assert not (PROOFS/'1002').exists() and decode((PROOFS/'.withdrawal-1002.json').read_bytes())['revision']==2
    assert show(PEER)['MainPID']==peer['MainPID']
    record(checks,'authorized-postboot-resume-retires-only-target-proof',files=state(),peer_pid=peer['MainPID'])
    deny_attempt(checks,'post-retirement-target-denied-peer-preserved')
    meta.update(first_verified_boot_id=current,fault=True,before_reboot_files=state());save(meta)
else:
    before=state();assert store.resume(1002,operation,lambda _:True)=='AdmissionBlockedProofRetiredNoQuiescence'
    assert state()==before and show(PEER)['MainPID']==peer['MainPID']
    record(checks,'post-failed-hook-authorized-retry-idempotent-peer-preserved',files=state(),peer_pid=peer['MainPID'])
save_result('verified-fault' if row['fault'] else 'verified-readonly',checks,metadata=meta,
    whole_classification_qualified=False,all_producer_quiescence=False,
    real_nss_mutations_tested=False,power_loss_tested=False)
