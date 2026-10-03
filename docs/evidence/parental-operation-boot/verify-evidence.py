"""Offline verification of scoped owner persistence across two real reboots."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
p=read('prepared.json');a=read('verified-readonly.json');b=read('verified-fault.json')
assert [len(x['checks']) for x in (p,a,b)]==[4,9,6]
assert all(x['passed'] and all(c['passed'] for c in x['checks']) for x in (p,a,b))
assert len({p['boot_id'],a['boot_id'],b['boot_id']})==3 and p['metadata']['initial_boot_id']==p['boot_id']
external={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','barrier-writer.py':'../parental-registry-barrier/writer.py','operations.py':'../parental-operation-journal/operations.py','inventory.py':'../parental-inventory-gate/inventory.py','coordinator.py':'../parental-coordinator/coordinator.py','ordinary-coordinator.py':'../parental-ordinary-coordinator/ordinary-coordinator.py','manager_adapters.py':'../parental-manager-adapters/adapters.py'}
for n,h in p['metadata']['source_sha256'].items():assert hashlib.sha256((P/external.get(n,n)).read_bytes()).hexdigest()==h,n
initial=p['metadata']['before_reboot_files'];proofs=initial['proofs']
assert all(n in proofs for n in ('1000','1002','.deny-1002','.withdrawal-1002.json','.operation-1002.json'))
assert p['checks'][2]['child_rc']==91 and p['checks'][2]['owner']['phase']=='legacy-blocked' and p['checks'][2]['owner']['revision']==2
for artifact,fault in ((a,False),(b,True)):
    assert artifact['kernel_reboot_tested'] is True
    for f in ('full_account_protection','whole_classification_qualified','all_producer_quiescence','producer_revocation_tested','production_journal_qualified','global_monotonic_revision_qualified','anti_rollback_qualified','real_nss_mutations_tested','power_loss_tested'):assert artifact[f] is False,f
    c={x['name']:x for x in artifact['checks']}
    files=c['durable-state-survives-kernel-reboot']['files']
    hookrow=c['hook-fault-no-metadata-change' if fault else 'hook-inspects-without-reenrollment'];hook=hookrow['hook']
    assert hookrow['status']==('42' if fault else '0') and hook['fault']==fault and hook['inspect_executed']==(not fault)
    assert hook['files_before']==hook['files_after']==files and hook['boot_id']==artifact['boot_id'] and hook['enforcing']=='Enforcing'
    assert hook['source_sha256']==p['metadata']['source_sha256']['recover-at-boot.py']
    if not fault:assert hook['outcome']=='BlockedRecoveryRequired'
    assert files==(a['metadata']['before_reboot_files'] if fault else initial)
    assert files['catalog']==initial['catalog'] and files['proofs']['1000']==proofs['1000'] and files['proofs']['.deny-1002']==proofs['.deny-1002']
    for uid in (1000,1002,1003):assert files['proofs'][f'.gate-{uid}.lock']==proofs[f'.gate-{uid}.lock']
    for part in files.values():
        for st in part.values():assert st['mode']==0o600 and st['uid']==st['gid']==0 and st['nlink']==1
    peer=c['unrelated-ordinary-linger-auto-admitted'];pid=peer['unit']['MainPID']
    assert peer['unit']['ActiveState']=='active' and int(pid)>0 and peer['context'].startswith('unconfined_u:unconfined_r:unconfined_t:')
    for x in artifact['checks']:
        if 'peer_pid' in x:assert x['peer_pid']==pid
        if 'unit' in x and x['name']!='unrelated-ordinary-linger-auto-admitted':
            assert x['unit']['MainPID']=='0' and x['unit']['ExecMainStatus']=='224'
            assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in x['journal']
        if 'files' in x:assert x['files']['proofs']['1000']==proofs['1000'] and x['files']['catalog']==initial['catalog']
ca={x['name']:x for x in a['checks']};done=ca['authorized-postboot-resume-retains-owner-and-barrier']
assert ca['wrong-operation-and-denied-authorization-preserve-postboot-state']['passed'] and ca['changed-catalog-refuses-recovery-before-prompt']['passed']
owner=done['owner'];expected=p['metadata']['expected_owner']
assert {k:x for k,x in owner.items() if k not in ('phase','revision')}=={k:x for k,x in expected.items() if k not in ('phase','revision')}
assert owner['phase']=='retired' and owner['revision']==3 and done['authorization_calls']==1
retired=done['files'];assert '1002' not in retired['proofs']
assert retired==a['metadata']['before_reboot_files']==b['checks'][0]['files']==b['checks'][-1]['files']
assert b['checks'][-1]['authorization_calls']==1
c=read('cleanup.json');assert c['passed'] and all(x['passed'] for x in c['cleanup']) and all(c['restored'].values())
for n in ('inventory-restored.json','inventory-restored-independent.json'):
    x=read(n);assert x['passed'] and x.get('directory_absent',x.get('inventory_directory_absent')) is True
r=read('restored.json');assert r['passed'] and all(x=='0' for x in r['units'].values()) and all(r['absent_paths'].values())
assert not r['processes'] and not r['sessions'].strip() and r['enforce']=='Permissive' and not r['complete_kernel_audit']
assert all(r[f] for f in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
assert v['native_checks']==19 and v['real_kernel_reboots']==2 and v['failed_native_attempts']==0
assert v['qemu_exit_codes']==[0,0,0] and v['poweroff_rc']==0 and not v['production_changed']
assert v['python_baseline_tests']==455 and v['python_baseline_reused'] is True
assert 'Ran 455 tests' in (P/'../parental-operation-journal/python-suite.txt').read_text()
assert all(x['rc']==0 and not x['stderr'] for x in v['executions'])
print('PASS: 19 controles, 2 reinícios reais; owner e bloqueio preservados')
