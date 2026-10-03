from boot_common import *
checks=[];meta=config();current=boot_id()
assert current!=meta['initial_boot_id']
hook=BASE/('hook-'+current+'.json');end=time.monotonic()+30
while not hook.exists() and time.monotonic()<end:time.sleep(.2)
row=json.loads(hook.read_text());status=run(['systemctl','show',UNIT.name,'-p','ExecMainStatus','--value'])['stdout'].strip()
assert row['enforcing']=='Enforcing' and run(['getenforce'])['stdout'].strip()=='Enforcing'
assert row['files_before']==row['files_after']==meta['before_reboot_files']==persistent()
assert row['source_sha256']==meta['source_sha256']['recover-at-boot.py']
record(checks,'owner-ledger-inodes-catalog-proofs-and-masks-survive-kernel-reboot',files=persistent(),boot_id=current,records=records())
if meta['fault']:
    assert not row['inspect_executed'] and status=='42' and current!=meta['first_verified_boot_id']
else:
    assert row['inspect_executed'] and status=='0' and row['owner']=='AdmissionWithdrawnNoQuiescence' and row['records']==meta['before_reboot_records']
record(checks,'failed-hook-does-not-repair-or-authorize' if meta['fault'] else 'boot-hook-inspects-without-completion-or-authorization',hook=row,status=status)
end=time.monotonic()+30
while time.monotonic()<end:
    if show(TARGET)['ExecMainStatus']=='224' and show(PEER)['ActiveState']=='active':break
    time.sleep(.2)
target_unit=show(TARGET);journal=run(['journalctl','-b','-u','user@1002.service','--no-pager','-o','cat'])['stdout']
assert target_unit['MainPID']=='0' and target_unit['ExecMainStatus']=='224'
assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in journal
record(checks,'target-linger-auto-admission-denied',unit=target_unit,journal=journal)
peer=show(PEER);assert peer['ActiveState']=='active' and int(peer['MainPID'])>0
assert context(PEER).startswith('unconfined_u:unconfined_r:unconfined_t:')
record(checks,'unrelated-ordinary-linger-auto-admitted',unit=peer,context=context(PEER))
peer_baseline={n:wait_active(n) for n in (PEER_UNITS[0],PEER_UNITS[1])}
assert unit_show(PEER_UNITS[2])['ActiveState']=='active'
record(checks,'peer-service-and-timer-auto-start-after-reboot',units=peer_baseline,timer=unit_show(PEER_UNITS[2]))
for n in TARGET_UNITS:
    u=unit_show(n);assert u['LoadState']=='masked' and u['MainPID']=='0' and u['ActiveState'] in ('inactive','failed')
    result=run(['systemctl','start',n],check=False)
    assert result['rc']!=0 and 'masked' in result['stderr'].lower() and unit_show(n)['MainPID']=='0'
    record(checks,'persisted-mask-blocks-boot-and-manual-start-'+n,unit=u,command=result)
assert not scoped_processes(TARGET_UNITS) and not uid_processes(1002)
record(checks,'zero-target-processes-with-peer-live',peer_pid=peer['MainPID'],target_processes=scoped_processes(TARGET_UNITS))
deny_attempt(checks,'manual-pam-retry-denied-peer-preserved')
gate=owned_factory();operation=meta['operation'];before=persistent()
expect('Conflict',lambda:gate.resume(1002,'0'*32,('system-units',TARGET_UNITS[3]),lambda _:(_ for _ in ()).throw(AssertionError('prompted'))))
expect('Denied',lambda:gate.resume(1002,operation,('system-units',TARGET_UNITS[3]),lambda _:False))
assert persistent()==before
record(checks,'wrong-operation-and-denied-resource-resume-preserve-all-state')
catalog=json.loads((ic.CATALOG/'1002.json').read_text());ic.publish(1002,dict(catalog,revision=2));changed=persistent()
expect('Conflict',lambda:gate.resume(1002,operation,('system-units',TARGET_UNITS[3]),lambda _:(_ for _ in ()).throw(AssertionError('prompted'))))
assert persistent()==changed
ic.publish(1002,catalog)
# Atomic fixture publication changes catalog inode; preserve byte binding, not claim rollback protection.
after_catalog=persistent();assert after_catalog['proofs']==before['proofs'] and after_catalog['ledger']==before['ledger'] and after_catalog['masks']==before['masks']
assert (ic.CATALOG/'1002.json').read_text()==(json.dumps(catalog,sort_keys=True)+'\n')
record(checks,'stale-catalog-refuses-resource-resume-before-prompt',explicit_root_catalog_restore=True)
commands=[];live_auth=[];adapter=live_adapter(commands,live_auth)
if not meta['fault']:
    assert records()[TARGET_UNITS[3]]['phase']=='intent'
    expect('UnverifiedAdmission',lambda:adapter.inhibit(target()));assert not commands
    record(checks,'postboot-pending-owner-still-refuses-live-inhibit-without-reload')
    calls=[]
    def authorize_pending(r):unlocked_authority();calls.append(r);return True
    old=persistent();assert gate.resume(1002,operation,('system-units',TARGET_UNITS[3]),authorize_pending)=='OwnedFilesystemInhibitionNoQuiescence' and len(calls)==1
    done=persistent();assert done['proofs']==old['proofs'] and done['catalog']==old['catalog'] and done['masks']==old['masks']
    assert len([n for n in done['ledger'] if done['ledger'][n]!=old['ledger'][n]])==1
    assert all(r['phase']=='fenced' for r in records().values())
    record(checks,'fresh-authorized-pending-resume-commits-only-journal-preserving-mask-inode',authorization_calls=len(calls),before=old,files=done,records=records())
else:
    calls=[];old=persistent()
    def authorize_done(r):unlocked_authority();calls.append(r);return True
    for n in TARGET_UNITS:assert gate.resume(1002,operation,('system-units',n),authorize_done)=='OwnedFilesystemInhibitionNoQuiescence'
    assert len(calls)==4 and persistent()==old
    record(checks,'after-failed-hook-four-authorized-completed-retries-readonly',authorization_calls=len(calls),files=persistent(),records=records())
old=persistent();assert adapter.inhibited(target()) and adapter.quiescent(target()) and not commands
assert adapter.inhibit(target()) and commands==[['systemctl','daemon-reload']] and adapter.quiescent(target())
assert persistent()==old and live_auth[-1]=='inhibit'
assert show(PEER)['MainPID']==peer['MainPID'] and unit_show(PEER_UNITS[0])['MainPID']==peer_baseline[PEER_UNITS[0]]['MainPID']
record(checks,'live-reload-validates-persisted-owner-and-loaded-masks-without-rewriting',commands=commands,files=persistent(),peer_pid=peer['MainPID'])
if not meta['fault']:
    # Lose the inode by rename; live facade must not repair even though no target runs.
    name=TARGET_UNITS[0];mask=MASKS_DIR/name;backup=BASE/'saved-mask';mask.rename(backup);run(['systemctl','daemon-reload'])
    ledger_before=ledger_state();old_commands=len(commands)
    expect('ResourceChanged',lambda:adapter.quiescent(target()))
    expect('ResourceChanged',lambda:adapter.inhibit(target()))
    assert len(commands)==old_commands and not mask.is_symlink() and ledger_state()==ledger_before and not uid_processes(1002)
    record(checks,'postboot-lost-mask-refused-without-automatic-repair',ledger=ledger_state())
    backup.rename(mask);run(['systemctl','daemon-reload']);assert adapter.inhibited(target()) and adapter.quiescent(target())
    record(checks,'explicit-root-restores-original-mask-inode',files=persistent())
old_pid=unit_show(PEER_UNITS[1])['MainPID'];run(['systemctl','stop',PEER_UNITS[1]]);new=wait_active(PEER_UNITS[1],old_pid)
assert show(PEER)['MainPID']==peer['MainPID'] and unit_show(PEER_UNITS[0])['MainPID']==peer_baseline[PEER_UNITS[0]]['MainPID']
record(checks,'peer-timer-reactivates-with-target-still-fenced',old_pid=old_pid,new_unit=new,peer_pid=peer['MainPID'])
time.sleep(.7);assert not scoped_processes(TARGET_UNITS) and not uid_processes(1002)
expect('UnsupportedProducer',lambda:oc.OrdinaryCoordinator(make(),WithdrawalError,{'classification':adapter.classification,'system-units':adapter}).resume_and_check(1002,operation,lambda p,r:True))
record(checks,'boot-scoped-units-still-refuse-whole-account-coverage')
if not meta['fault']:
    meta.update(first_verified_boot_id=current,fault=True,before_reboot_files=persistent(),before_reboot_records=records());save(meta)
save_result('verified-fault' if row['fault'] else 'verified-readonly',checks,metadata=meta,kernel_reboot_tested=True,
    ownership_ledger_reboot_qualified=True,boot_mask_recovery_qualified=True,whole_classification_qualified=False,
    all_producer_quiescence=False,dbus_boot_qualified=False,production_adapters_qualified=False,
    global_monotonic_revision_qualified=False,anti_rollback_qualified=False,real_nss_mutations_tested=False,power_loss_tested=False,
    early_boot_coverage_qualified=False,pending_activation_races_qualified=False)
