from boot_common import *
checks=[];meta=config();current=boot_id()
assert current!=meta['initial_boot_id']
hook=BASE/('hook-'+current+'.json');end=time.monotonic()+30
while not hook.exists() and time.monotonic()<end:time.sleep(.2)
row=json.loads(hook.read_text())
assert row['enforcing']=='Enforcing' and run(['getenforce'])['stdout'].strip()=='Enforcing'
assert row['files_before']==meta['before_reboot_files'] and row['files_after']==row['files_before']
assert row['source_sha256']==meta['source_sha256']['recover-at-boot.py']
record(checks,'durable-state-survives-kernel-reboot',files=persistent(),boot_id=current)
status=run(['systemctl','show',UNIT.name,'-p','ExecMainStatus','--value'])['stdout'].strip()
if meta['fault']:
    assert not row['inspect_executed'] and status=='42' and current!=meta['first_verified_boot_id']
else:
    assert row['inspect_executed'] and status=='0' and row['outcome']=='BlockedRecoveryRequired'
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
store=factory();operation=meta['operation'];before=persistent()
peer_files=meta['before_reboot_files']['proofs']['1000'];peer_catalog=meta['before_reboot_files']['catalog']['1000.json']
if not meta['fault']:
    assert (PROOFS/'1002').exists() and ops.decode((PROOFS/'.operation-1002.json').read_bytes())['phase']=='legacy-blocked'
    expect('Conflict',lambda:store.resume(1002,'0'*32,lambda _:(_ for _ in ()).throw(AssertionError('prompted'))))
    expect('Denied',lambda:store.resume(1002,operation,lambda _:False));assert persistent()==before
    record(checks,'wrong-operation-and-denied-authorization-preserve-postboot-state')
    catalog=json.loads((CATALOG/'1002.json').read_text());changed=dict(catalog,revision=catalog['revision']+1);publish(1002,changed)
    proof_before=state()
    expect('Conflict',lambda:store.resume(1002,operation,lambda _:(_ for _ in ()).throw(AssertionError('prompted'))));assert state()==proof_before
    publish(1002,catalog);assert persistent()==before
    record(checks,'changed-catalog-refuses-recovery-before-prompt',fixture_catalog_restored_explicitly=True)
    calls=[]
    def authorize(row):calls.append(row);return True
    assert store.resume(1002,operation,authorize)=='AdmissionWithdrawnNoQuiescence' and len(calls)==1
    done=ops.decode((PROOFS/'.operation-1002.json').read_bytes());assert ops.same_owner(done,meta['expected_owner']) and done['phase']=='retired' and done['revision']==3
    assert not (PROOFS/'1002').exists() and show(PEER)['MainPID']==peer['MainPID']
    after=persistent();assert after['proofs']['1000']==peer_files and after['catalog']['1000.json']==peer_catalog
    record(checks,'authorized-postboot-resume-retains-owner-and-barrier',owner=done,files=after,authorization_calls=len(calls),peer_pid=peer['MainPID'])
    deny_attempt(checks,'post-retirement-target-denied-peer-preserved')
    meta.update(first_verified_boot_id=current,fault=True,before_reboot_files=persistent());save(meta)
else:
    assert current!=meta['first_verified_boot_id']
    calls=[]
    def authorize(row):calls.append(row);return True
    assert store.resume(1002,operation,authorize)=='AdmissionWithdrawnNoQuiescence' and len(calls)==1
    assert persistent()==before and show(PEER)['MainPID']==peer['MainPID']
    assert before['proofs']['1000']==peer_files and before['catalog']['1000.json']==peer_catalog
    record(checks,'post-failed-hook-authorized-retry-readonly-peer-preserved',files=persistent(),authorization_calls=len(calls),peer_pid=peer['MainPID'])
save_result('verified-fault' if row['fault'] else 'verified-readonly',checks,metadata=meta,kernel_reboot_tested=True,
    whole_classification_qualified=False,all_producer_quiescence=False,producer_revocation_tested=False,
    production_journal_qualified=False,global_monotonic_revision_qualified=False,anti_rollback_qualified=False,
    real_nss_mutations_tested=False,power_loss_tested=False)
