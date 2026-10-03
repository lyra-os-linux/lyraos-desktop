"""Offline checks: scoped unit ownership and masks through two kernel reboots."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
external={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','barrier-writer.py':'../parental-registry-barrier/writer.py','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','coordinator.py':'../parental-coordinator/coordinator.py','ordinary-coordinator.py':'../parental-ordinary-coordinator/ordinary-coordinator.py','manager_adapters.py':'../parental-manager-adapters/adapters.py','operations.py':'../parental-operation-journal/operations.py','inventory.py':'../parental-inventory-gate/inventory.py','ownership.py':'../parental-owned-inhibitions/ownership.py','integration.py':'../parental-owned-live/integration.py','unit-adapter.py':'../parental-unit-adapter/unit-adapter.py','dbus-adapter.py':'../parental-dbus-adapter/dbus-adapter.py'}
p=read('prepared.json');a=read('verified-readonly.json');b=read('verified-fault.json')
assert len({r['boot_id'] for r in (p,a,b)})==3 and p['metadata']['initial_boot_id']==p['boot_id']
for r,count,tag in ((p,6,'prepare'),(a,20,'verify-readonly'),(b,17,'verify-fault')):
    assert r['passed'] and not r['full_account_protection'] and len(r['checks'])==count and all(c['passed'] for c in r['checks'])
    assert int((P/(tag+'-exit-status')).read_text())==0 and not (P/(tag+'-stderr.log')).read_bytes()
    logged=[json.loads(line) for line in (P/(tag+'-stdout.log')).read_text().splitlines()]
    assert logged==r['checks']
    for n,h in r['metadata']['source_sha256'].items():assert hashlib.sha256((P/external.get(n,n)).read_bytes()).hexdigest()==h,n
initial=p['metadata']['before_reboot_files'];initial_records=p['metadata']['before_reboot_records'];names=tuple(initial_records)
assert len(names)==4 and [x['phase'] for x in initial_records.values()]==['fenced']*3+['intent']
pc={c['name']:c for c in p['checks']};crash=pc['effect-synced-crash91-pending-owner-with-four-physical-masks']
assert crash['child']['rc']==91 and not crash['child']['stderr'] and crash['records']==initial_records and crash['authorization_callbacks_outside_all_locks']
assert len(initial['ledger'])==5 and '.gate-1.lock' in initial['ledger'] and '1002' not in initial['proofs']
assert all(initial['masks'][n]['target']=='/dev/null' for n in names)
owner=next(iter(initial_records.values()))['owner']
for name,row in initial_records.items():
    assert row['name']==name and row['family']=='system-units' and row['owner']==owner
    assert row['protocol_digest']==p['metadata']['source_sha256']['ownership.py'] and row['adapter_digest']==p['metadata']['source_sha256']['unit-adapter.py']
    assert row['route_digest']==initial['vendor'][name]['sha256']
    if row['phase']=='fenced':assert row['effect']['inode']==initial['masks'][name]['inode']
    else:assert row['effect'] is None and row['revision']==1
assert owner['phase']=='retired' and owner['revision']==3 and owner['operation']==p['metadata']['operation'] and owner['proof_hash']==p['metadata']['proof_hash']
for r,fault in ((a,False),(b,True)):
    assert r['kernel_reboot_tested'] and r['ownership_ledger_reboot_qualified'] and r['boot_mask_recovery_qualified']
    for f in ('full_account_protection','whole_classification_qualified','all_producer_quiescence','dbus_boot_qualified','production_adapters_qualified','global_monotonic_revision_qualified','anti_rollback_qualified','real_nss_mutations_tested','power_loss_tested','early_boot_coverage_qualified','pending_activation_races_qualified'):assert r[f] is False,f
    c={x['name']:x for x in r['checks']}
    snapshot=c['owner-ledger-inodes-catalog-proofs-and-masks-survive-kernel-reboot']['files']
    hookcheck=c['failed-hook-does-not-repair-or-authorize' if fault else 'boot-hook-inspects-without-completion-or-authorization'];hook=hookcheck['hook']
    assert hook['files_before']==hook['files_after']==snapshot==(a['metadata']['before_reboot_files'] if fault else initial)
    assert hook['boot_id']==r['boot_id'] and hook['enforcing']=='Enforcing' and hook['fault']==fault and hook['inspect_executed']==(not fault)
    assert hookcheck['status']==('42' if fault else '0') and hook['source_sha256']==p['metadata']['source_sha256']['recover-at-boot.py']
    if not fault:assert hook['records']==initial_records and hook['owner']=='AdmissionWithdrawnNoQuiescence'
    peer=c['unrelated-ordinary-linger-auto-admitted'];pid=peer['unit']['MainPID']
    assert int(pid)>0 and peer['unit']['ActiveState']=='active' and peer['context'].startswith('unconfined_u:unconfined_r:unconfined_t:')
    for x in r['checks']:
        if 'peer_pid' in x:assert x['peer_pid']==pid
        if x['name'] in ('target-linger-auto-admission-denied','manual-pam-retry-denied-peer-preserved'):
            assert x['unit']['MainPID']=='0' and x['unit']['ExecMainStatus']=='224'
            assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in x['journal']
        if 'files' in x:
            for section in ('proofs','masks','registry','roles','vendor','wants','hook_sha256'):assert x['files'][section]==snapshot[section],(section,x['name'])
            assert x['files']['catalog']['1000.json']==initial['catalog']['1000.json']
            for lock in ('.inventory-1000.lock','.inventory-1002.lock'):assert x['files']['catalog'][lock]==initial['catalog'][lock]
    for n in names:
        x=c['persisted-mask-blocks-boot-and-manual-start-'+n]
        assert x['unit']['LoadState']=='masked' and x['unit']['MainPID']=='0' and x['command']['rc']!=0 and 'masked' in x['command']['stderr'].lower()
    assert not c['zero-target-processes-with-peer-live']['target_processes']
    assert c['wrong-operation-and-denied-resource-resume-preserve-all-state']['passed']
    assert c['stale-catalog-refuses-resource-resume-before-prompt']['explicit_root_catalog_restore']
    x=c['peer-service-and-timer-auto-start-after-reboot'];assert x['timer']['ActiveState']=='active' and all(int(u['MainPID'])>0 and '/system.slice/' in u['ControlGroup'] for u in x['units'].values())
    x=c['peer-timer-reactivates-with-target-still-fenced'];assert x['old_pid']!=x['new_unit']['MainPID']
    x=c['live-reload-validates-persisted-owner-and-loaded-masks-without-rewriting'];assert x['commands']==[['systemctl','daemon-reload']]
ca={x['name']:x for x in a['checks']};cb={x['name']:x for x in b['checks']}
x=ca['fresh-authorized-pending-resume-commits-only-journal-preserving-mask-inode'];old=x['before'];done=x['files']
assert x['authorization_calls']==1 and old['masks']==done['masks'] and old['proofs']==done['proofs'] and old['catalog']==done['catalog']
assert len([n for n in old['ledger'] if old['ledger'][n]!=done['ledger'][n]])==1
assert old['ledger']['.gate-1.lock']==done['ledger']['.gate-1.lock']
for n,r in x['records'].items():
    assert r['owner']==owner and r['phase']=='fenced' and r['revision']==2 and r['effect']['inode']==initial['masks'][n]['inode']
assert ca['postboot-lost-mask-refused-without-automatic-repair']['ledger']=={n:{k:st[k] for k in ('sha256','inode')} for n,st in done['ledger'].items()}
assert a['metadata']['before_reboot_files']['ledger']==done['ledger']
# The separate historical whole-coordinator probe resumes its legacy journal
# before refusing missing families. It replaces only that inode, same bytes.
next_proofs=a['metadata']['before_reboot_files']['proofs']
assert set(next_proofs)==set(initial['proofs'])
for n,st in next_proofs.items():
    if n=='.withdrawal-1002.json':
        assert {k:v for k,v in st.items() if k!='inode'}=={k:v for k,v in initial['proofs'][n].items() if k!='inode'}
        assert st['inode']!=initial['proofs'][n]['inode']
    else:assert st==initial['proofs'][n]
x=cb['after-failed-hook-four-authorized-completed-retries-readonly'];assert x['authorization_calls']==4
assert x['files']['ledger']==done['ledger'] and x['records']==a['metadata']['before_reboot_records']
for name in ('cleanup.json','restored.json','ownership-restored.json','ownership-restored-independent.json','units-restored.json','units-restored-independent.json'):assert read(name)['passed'],name
c=read('cleanup.json');assert all(x['passed'] for x in c['cleanup']) and all(c['restored'].values())
r=read('restored.json');assert all(x=='0' for x in r['units'].values()) and all(r['absent_paths'].values()) and not r['processes'] and not r['sessions'].strip() and r['enforce']=='Permissive' and not r['complete_kernel_audit']
assert all(r[f] for f in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
r=read('ownership-restored-independent.json');assert all(r['absent'].values())
r=read('units-restored-independent.json');assert all(r['absent'].values()) and all(r['boot_wants_absent'].values()) and not r['cgroup_leaks'] and not r['scope_processes']
assert v['native_checks']==43 and v['real_kernel_reboots']==2 and v['failed_native_attempts']==0 and v['native_exit_codes']==[0,0,0]
assert v['qemu_exit_codes']==[0,0,0] and v['poweroff_rc']==0 and not v['production_changed']
assert v['python_baseline_tests']==496 and v['python_baseline_reused'] and 'Ran 496 tests' in (P/'../parental-owned-live/python-suite.txt').read_text()
assert all(x['rc']==0 and not x['stderr'] for x in v['executions'])
print('PASS: 43 controles, 2 reinícios reais; owner, máscaras e bloqueio preservados')
