"""Offline inspection of composed gate, concurrent writers and restored VM."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for name,h in v['sha256'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==h,name
r=read('result.json');cleanup=read('cleanup.json');restored=read('restored.json')
assert r['passed'] and r['cleanup_rc']==0 and r['error'] is None
for flag in ('full_account_protection','whole_classification_qualified','all_producer_quiescence','real_nss_mutations_tested','production_adapters_qualified','monotonic_revision_qualified','power_loss_tested'):assert r[flag] is False,flag
for name,h in r['metadata']['source_sha256'].items():
    target={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','coordinator.py':'../parental-coordinator/coordinator.py','barrier-writer.py':'../parental-registry-barrier/writer.py'}.get(name,name)
    assert hashlib.sha256((P/target).read_bytes()).hexdigest()==h,name
rows=r['checks'];assert len(rows)==16 and len({x['name'] for x in rows})==16 and all(x['passed'] for x in rows)
c={x['name']:x for x in rows}
for name in ('baseline-ordinary-1000','baseline-ordinary-1002','held-target-lock-other-uid-plan-and-native-admission-independent'):
    x=c[name];assert x['unit']['ActiveState']=='active' and int(x['unit']['MainPID'])>0
    assert x['context'].startswith('unconfined_u:unconfined_r:unconfined_t:')
old=c['missing-producers-blocked-but-old-manager-still-active'];assert int(old['pid'])>0 and int(old['peer_pid'])>0 and not old['quiescence_proven']
assert old['peer_pid']==c['baseline-ordinary-1000']['unit']['MainPID']
assert c['coordinator-denied-no-storage-effects']['passed'] and c['zero-target-processes-still-require-all-producers']['passed']
all_operations=set();digests=set()
for round_no in range(3):
    race=c[f'race-{round_no}-one-operation-persisted'];ready=race['ready'];workers=race['workers']
    assert race['worker_rc']==[0,0] and len(ready)==len(workers)==2
    assert ready[0]['digest']==ready[1]['digest'] and ready[0]['proof_hash']==ready[1]['proof_hash']
    assert {x['operation'] for x in ready}=={x['operation'] for x in workers}
    assert all(x['digest']==ready[0]['digest'] and x['proof_hash']==ready[0]['proof_hash'] and x['uid']==1002 for x in workers)
    win=[x for x in workers if x['code']=='UnsupportedProducer'];lose=[x for x in workers if x['code'] in {'Busy','Conflict'}]
    assert len(win)==len(lose)==1
    marker=race['marker'];journal=race['journal']
    assert marker['uid']==journal['uid']==1002 and marker['operation']==journal['operation']==win[0]['operation']
    assert marker['proof_hash']==journal['proof_hash']==ready[0]['proof_hash']
    assert (marker['phase'],marker['revision'])==('blocked',1) and (journal['phase'],journal['revision'])==('retired',2)
    assert race['peer_pid']==old['peer_pid']
    all_operations.update(x['operation'] for x in workers);digests.add(ready[0]['digest'])
    assert c[f'race-{round_no}-loser-rejected-winner-retry-blocked']['passed']
assert len(all_operations)==6 and len(digests)==1
for name in ['post-gate-new-admission-denied-peer-preserved']+[f'race-{i}-new-target-denied-peer-preserved' for i in range(3)]:
    x=c[name];assert x['unit']['MainPID']=='0' and x['unit']['ExecMainStatus']=='224' and x['peer_pid']==old['peer_pid']
    assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in x['journal']
    assert x['peer_context'].startswith('unconfined_u:unconfined_r:unconfined_t:')
assert cleanup['passed'] and all(x['passed'] for x in cleanup['cleanup']) and all(cleanup['restored'].values())
assert restored['passed'] and all(x=='0' for x in restored['units'].values()) and all(restored['absent_paths'].values())
assert not restored['processes'] and not restored['sessions'].strip() and restored['enforce']=='Permissive'
assert all(restored[x] for x in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
assert not restored['complete_kernel_audit']
assert v['python_tests']==313 and v['new_python_tests']==19 and v['python_suite_exit_code']==0
assert v['native_checks']==16 and v['concurrent_races']==3 and v['native_exit_code']==int((P/'exit-status').read_text())==0
assert v['poweroff_rc']==v['qemu_exit_code']==0 and v['stderr_empty'] and not(P/'stderr.log').read_bytes()
assert v['native_terminal_result']==json.loads((P/'stdout.log').read_text().splitlines()[-1])=={'passed':True,'checks':16,'cleanup_rc':0}
assert not v['production_changed'] and not v['production_adapters_qualified']
print('PASS: 16 controles, 3 disputas; cobertura ausente continua bloqueante')
