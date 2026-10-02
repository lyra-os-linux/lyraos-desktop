"""Offline verification of two real kernel boots and ordinary-account isolation."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for name,h in v['sha256'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==h,name
p=read('prepared.json');a=read('verified-readonly.json');b=read('verified-fault.json')
assert [len(x['checks']) for x in (p,a,b)]==[4,7,6]
assert all(x['passed'] and all(c['passed'] for c in x['checks']) for x in (p,a,b))
assert len({p['boot_id'],a['boot_id'],b['boot_id']})==3
assert p['metadata']['initial_boot_id']==p['boot_id']
for name,h in p['metadata']['source_sha256'].items():
    target={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','barrier-writer.py':'../parental-registry-barrier/writer.py'}.get(name,name)
    assert hashlib.sha256((P/target).read_bytes()).hexdigest()==h,name
initial=p['metadata']['before_reboot_files']
assert '1002' in initial and '1000' in initial and '.deny-1002' in initial and '.withdrawal-1002.json' not in initial
assert p['checks'][2]['worker_rc']==91 and int(p['checks'][2]['peer_pid'])>0 and int(p['checks'][2]['target_pid'])>0
for artifact,fault in ((a,False),(b,True)):
    for flag in ('full_account_protection','whole_classification_qualified','all_producer_quiescence','real_nss_mutations_tested','power_loss_tested'):assert artifact[flag] is False
    c={x['name']:x for x in artifact['checks']}
    files=c['durable-state-survives-kernel-reboot']['files']
    hookrow=c['hook-fault-no-metadata-change' if fault else 'hook-inspects-without-reenrollment']
    hook=hookrow['hook'];assert hookrow['status']==('42' if fault else '0')
    assert hook['boot_id']==artifact['boot_id'] and hook['fault']==fault and hook['inspect_executed']==(not fault)
    assert hook['files_before']==hook['files_after']==files and hook['enforcing']=='Enforcing'
    assert hook['source_sha256']==p['metadata']['source_sha256']['recover-at-boot.py']
    assert files==a['metadata']['before_reboot_files'] if fault else files==initial
    assert files['1000']==initial['1000'] and files['.deny-1002']==initial['.deny-1002']
    for uid in (1000,1002,1003):assert files[f'.gate-{uid}.lock']==initial[f'.gate-{uid}.lock']
    for st in files.values():assert st['mode']==0o600 and st['uid']==0 and st['nlink']==1
    denied=c['target-linger-auto-admission-denied']
    assert denied['unit']['MainPID']=='0' and denied['unit']['ExecMainStatus']=='224'
    assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in denied['journal']
    peer=c['unrelated-ordinary-linger-auto-admitted'];assert peer['unit']['ActiveState']=='active' and int(peer['unit']['MainPID'])>0
    assert peer['context'].startswith('unconfined_u:unconfined_r:unconfined_t:')
    for x in artifact['checks']:
        if 'peer_pid' in x:assert x['peer_pid']==peer['unit']['MainPID']
        if 'unit' in x and x['name']!='unrelated-ordinary-linger-auto-admitted':
            assert x['unit']['MainPID']=='0' and x['unit']['ExecMainStatus']=='224'
        if 'peer_context' in x:assert x['peer_context']==peer['context']
        if 'files' in x:assert x['files']['1000']==initial['1000']
retired=a['checks'][5]['files'];assert '1002' not in retired and '.withdrawal-1002.json' in retired
assert retired==a['metadata']['before_reboot_files']==b['checks'][0]['files']==b['checks'][-1]['files']
cleanup=read('cleanup.json');restored=read('restored.json')
assert cleanup['passed'] and all(x['passed'] for x in cleanup['cleanup']) and all(cleanup['restored'].values())
assert restored['passed'] and all(x=='0' for x in restored['units'].values()) and all(restored['absent_paths'].values())
assert not restored['processes'] and not restored['sessions'].strip() and restored['enforce']=='Permissive'
assert all(restored[x] for x in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
assert not restored['complete_kernel_audit']
assert v['native_checks']==17 and v['real_kernel_reboots']==2 and v['python_tests']==294 and v['python_suite_exit_code']==0
assert v['qemu_exit_codes']==[0,0,0] and v['poweroff_rc']==0 and not v['production_changed'] and not v['power_loss_tested']
assert all(x['rc']==0 for x in v['executions'])
print('PASS: 17 controles, 2 reinícios reais; conta comum independente preservada')
