from boot_common import *
checks=[];meta=config();current=boot_id()
assert current!=meta['initial_boot_id']
hook=BASE/('hook-'+current+'.json');end=time.monotonic()+30
while not hook.exists() and time.monotonic()<end:time.sleep(.2)
row=json.loads(hook.read_text());status=run(['systemctl','show',UNIT.name,'-p','ExecMainStatus','--value'])['stdout'].strip()
assert row['enforcing']=='Enforcing' and run(['getenforce'])['stdout'].strip()=='Enforcing'
assert row['files_before']==row['files_after']==meta['before_reboot_files']==persistent()
assert row['source_sha256']==meta['source_sha256']['recover-at-boot.py']
record(checks,'owner-ledger-inodes-catalog-proofs-and-retirements-survive-kernel-reboot',files=persistent(),boot_id=current,records=records())
if meta['fault']:
    assert not row['inspect_executed'] and status=='42' and current!=meta['first_verified_boot_id']
else:
    assert row['inspect_executed'] and status=='0' and row['owner']=='AdmissionWithdrawnNoQuiescence' and row['records']==meta['before_reboot_records']
record(checks,'failed-hook-does-not-repair-or-authorize' if meta['fault'] else 'boot-hook-inspects-without-completion-or-authorization',hook=row,status=status)
end=time.monotonic()+30
while time.monotonic()<end:
    if show(1002)['ExecMainStatus']=='224' and show(1000)['ActiveState']=='active':break
    time.sleep(.2)
target_unit=show(1002);journal=run(['journalctl','-b','-u','user@1002.service','--no-pager','-o','cat'])['stdout']
assert target_unit['MainPID']=='0' and target_unit['ExecMainStatus']=='224'
assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in journal
record(checks,'target-linger-auto-admission-denied',unit=target_unit,journal=journal)
peer=show(1000);assert peer['ActiveState']=='active' and int(peer['MainPID'])>0
assert context(1000).startswith('unconfined_u:unconfined_r:unconfined_t:')
record(checks,'unrelated-ordinary-linger-auto-admitted',unit=peer,context=context(1000))
current_broker=broker();assert current_broker['boot_id']!=meta['initial_broker']['boot_id']
meta['broker_pid']=current_broker['pid'];save(meta)
record(checks,'new-boot-shared-broker-running',broker=current_broker,initial_broker=meta['initial_broker'])
assert {PREFIX+s for s in PEERS}<=activatable() and not ({PREFIX+s for s in TARGET}&activatable())
record(checks,'retired-target-routes-absent-peer-routes-activatable-after-boot',activatable=sorted(n for n in activatable() if n.startswith(PREFIX)))
for s in TARGET:
    assert not owner(s)
    record(checks,'persisted-retirement-denies-activation-'+s,command=blocked_probe(s))
assert not uid_processes(1002)
record(checks,'zero-target-processes-after-four-activation-denials',processes=uid_processes(1002))
peer_baseline={s:probe(s) for s in PEERS}
record(checks,'peer-exec-and-systemd-routes-activate-with-persistent-vendor-units',owners=peer_baseline,broker=broker(),peer_pid=peer['MainPID'])
assert peer_baseline['PeerUnit']['unit_state']['FragmentPath']==str(UNITS/unit_name('PeerUnit'))
deny_attempt(checks,'manual-pam-retry-denied-peer-preserved')
gate=owned_factory();operation=meta['operation'];before=persistent();key=('dbus-activation',PREFIX+TARGET[3])
expect('Conflict',lambda:gate.resume(1002,'0'*32,key,lambda _:(_ for _ in ()).throw(AssertionError('prompted'))))
expect('Denied',lambda:gate.resume(1002,operation,key,lambda _:False));assert persistent()==before
record(checks,'wrong-operation-and-denied-resource-resume-preserve-all-state')
catalog_row=json.loads((ic.CATALOG/'1002.json').read_text());ic.publish(1002,dict(catalog_row,revision=2));changed=persistent()
expect('Conflict',lambda:gate.resume(1002,operation,key,lambda _:(_ for _ in ()).throw(AssertionError('prompted'))));assert persistent()==changed
ic.publish(1002,catalog_row);after_catalog=persistent()
assert after_catalog['proofs']==before['proofs'] and after_catalog['ledger']==before['ledger'] and after_catalog['retirements']==before['retirements']
record(checks,'stale-catalog-refuses-resource-resume-before-prompt',explicit_root_catalog_restore=True)
effects=[];authorizations=[];adapter=live_adapter(effects,authorizations)
if not meta['fault']:
    assert records()[TARGET[3]]['phase']=='intent'
    expect('UnverifiedAdmission',lambda:adapter.inhibit(target()));assert not effects and not authorizations
    record(checks,'postboot-pending-owner-still-refuses-live-inhibit-without-reload')
    calls=[]
    def authorize_pending(r):unlocked_authority();calls.append(r);return True
    old=persistent();assert gate.resume(1002,operation,key,authorize_pending)=='OwnedFilesystemInhibitionNoQuiescence' and len(calls)==1
    done=persistent();assert done['proofs']==old['proofs'] and done['catalog']==old['catalog'] and done['retirements']==old['retirements']
    assert len([n for n in done['ledger'] if done['ledger'][n]!=old['ledger'][n]])==1
    assert all(r['phase']=='fenced' for r in records().values())
    record(checks,'fresh-authorized-pending-resume-commits-only-journal-preserving-definition-inode',authorization_calls=len(calls),before=old,files=done,records=records())
else:
    calls=[];old=persistent()
    def authorize_done(r):unlocked_authority();calls.append(r);return True
    for s in TARGET:assert gate.resume(1002,operation,('dbus-activation',PREFIX+s),authorize_done)=='OwnedFilesystemInhibitionNoQuiescence'
    assert len(calls)==4 and persistent()==old
    record(checks,'after-failed-hook-four-authorized-completed-retries-readonly',authorization_calls=len(calls),files=persistent(),records=records())
old=persistent();assert adapter.inhibited(target()) and adapter.quiescent(target()) and not effects
assert adapter.inhibit(target()) and effects==['reload-config'] and adapter.quiescent(target())
assert persistent()==old and authorizations==['inhibit'] and broker()==current_broker
assert show(1000)['MainPID']==peer['MainPID'] and all(probe(s)['pid']==peer_baseline[s]['pid'] for s in PEERS)
record(checks,'live-reload-validates-retirements-without-rewriting-or-restarting-broker',effects=effects.copy(),files=persistent(),broker=broker(),peer_pid=peer['MainPID'])
if not meta['fault']:
    # A root fixture externally publishes an active name for the same inode.
    # Reader must refuse, never retire it automatically or rewrite its owner.
    s='TargetColdExec';active=service_path(s);os.link(retired_path(s),active)
    old_effects=effects.copy();ledger_before=ledger_state()
    expect('ResourceChanged',lambda:adapter.quiescent(target()))
    expect('ResourceChanged',lambda:adapter.inhibit(target()))
    assert effects==old_effects and ledger_state()==ledger_before and active.exists() and not uid_processes(1002)
    record(checks,'externally-reintroduced-active-definition-refused-without-auto-retirement',ledger=ledger_state(),active_inode=active.stat().st_ino)
    active.unlink();assert adapter.inhibited(target()) and adapter.quiescent(target())
    record(checks,'explicit-root-removes-divergence-original-retirement-inode-preserved',files=persistent())
for s in TARGET:blocked_probe(s)
assert not uid_processes(1002) and broker()==current_broker
assert show(1000)['MainPID']==peer['MainPID'] and all(probe(s)['pid']==peer_baseline[s]['pid'] for s in PEERS)
record(checks,'target-stays-nonactivatable-peer-owners-and-broker-preserved',owners={s:probe(s) for s in PEERS},broker=broker(),peer_pid=peer['MainPID'])
# Direct scope check avoids the legacy resume's same-byte journal replacement.
partial=oc.OrdinaryCoordinator(make(),WithdrawalError,{'classification':adapter.classification,'dbus-activation':adapter});before=persistent()
expect('UnsupportedProducer',lambda:partial._check(target(),False));assert persistent()==before
record(checks,'boot-scoped-dbus-refuses-whole-account-without-legacy-resume',files=persistent())
if not meta['fault']:
    meta.update(first_verified_boot_id=current,fault=True,before_reboot_files=persistent(),before_reboot_records=records());save(meta)
save_result('verified-fault' if row['fault'] else 'verified-readonly',checks,metadata=meta,kernel_reboot_tested=True,
    ownership_ledger_reboot_qualified=True,boot_route_recovery_qualified=True,whole_classification_qualified=False,
    all_producer_quiescence=False,whole_dbus_namespace_qualified=False,production_adapters_qualified=False,
    global_monotonic_revision_qualified=False,anti_rollback_qualified=False,real_nss_mutations_tested=False,power_loss_tested=False,
    early_boot_coverage_qualified=False,pending_activation_races_qualified=False,postboot_payload_revocation_qualified=False)
