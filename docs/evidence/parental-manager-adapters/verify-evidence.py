"""Offline check: scoped real adapters, coverage refusal and restored VM."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
external={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','coordinator.py':'../parental-coordinator/coordinator.py','ordinary-coordinator.py':'../parental-ordinary-coordinator/ordinary-coordinator.py','barrier-writer.py':'../parental-registry-barrier/writer.py'}
r=read('result.json');failed=read('failed-attempt-1/result.json')
for result,initial in ((r,False),(failed,True)):
    for n,h in result['metadata']['source_sha256'].items():
        target='failed-attempt-1/adapters.py' if initial and n=='adapters.py' else external.get(n,n)
        assert hashlib.sha256((P/target).read_bytes()).hexdigest()==h,n
    for f in ('full_account_protection','whole_classification_qualified','all_producer_quiescence','real_nss_mutations_tested','production_adapters_qualified','monotonic_revision_qualified','power_loss_tested'):assert result[f] is False,f
assert not failed['passed'] and failed['cleanup_rc']==0 and len(failed['checks'])==6
assert int((P/'failed-attempt-1/exit-status').read_text())==1
assert 'UnverifiedQuiescence' in (P/'failed-attempt-1/stderr.log').read_text()
assert read('failed-attempt-1/cleanup.json')['passed']
assert r['passed'] and r['error'] is None and r['cleanup_rc']==0
rows=r['checks'];assert len(rows)==13 and all(x['passed'] for x in rows)
c={x['name']:x for x in rows};assert len(c)==13
peer=c['baseline-ordinary-1000']['unit']['MainPID'];old=c['baseline-ordinary-1002']['unit']['MainPID']
for uid in (1000,1002):
    x=c[f'baseline-ordinary-{uid}'];assert int(x['unit']['MainPID'])>0 and x['unit']['ActiveState']=='active'
    assert x['context'].startswith('unconfined_u:unconfined_r:unconfined_t:')
x=c['withdrawn-classification-old-manager-observed'];assert x['target_pid']==old and x['peer_pid']==peer
x=c['real-manager-revoked-peer-preserved'];assert x['target_unit']['MainPID']=='0' and not x['target_processes'] and x['peer_pid']==peer
for n in ('revoked-target-native-readmission-denied','linger-target-manual-admission-denied'):
    x=c[n];assert x['unit']['MainPID']=='0' and x['unit']['ExecMainStatus']=='224' and x['peer_pid']==peer
    assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in x['journal']
assert c['linger-cannot-reactivate-withdrawn-target']['unit']['MainPID']=='0'
x=c['peer-fresh-native-admission-preserved'];assert int(x['unit']['MainPID'])>0 and x['unit']['ActiveState']=='active'
assert x['context'].startswith('unconfined_u:unconfined_r:unconfined_t:')
for n in ('revocation-denied-preserves-old-manager','wrong-operation-no-revocation','changed-pam-no-revocation','real-revocation-idempotent-negative-authority-preserved','two-real-adapters-do-not-satisfy-all-producers'):assert c[n]['passed']
cleanup=read('cleanup.json');restored=read('restored.json')
assert cleanup['passed'] and all(x['passed'] for x in cleanup['cleanup']) and all(cleanup['restored'].values())
assert restored['passed'] and all(x=='0' for x in restored['units'].values()) and all(restored['absent_paths'].values())
assert not restored['processes'] and not restored['sessions'].strip() and restored['enforce']=='Permissive'
assert all(restored[n] for n in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
assert not restored['complete_kernel_audit']
assert v['native_checks']==13 and v['native_exit_code']==int((P/'exit-status').read_text())==0
assert not(P/'stderr.log').read_bytes() and v['stderr_empty']
assert json.loads((P/'stdout.log').read_text().splitlines()[-1])=={'passed':True,'checks':13,'cleanup_rc':0}
assert v['python_tests']==334 and v['new_python_tests']==21 and v['python_suite_exit_code']==0
suite=(P/'python-suite.txt').read_text();assert 'Ran 334 tests' in suite and '\nOK\n' in suite
assert v['poweroff_rc']==v['qemu_exit_code']==0 and not v['production_changed'] and not v['all_producers_qualified']
print('PASS: 13 controles nativos; revogação real, cobertura incompleta recusada; 334 testes')
