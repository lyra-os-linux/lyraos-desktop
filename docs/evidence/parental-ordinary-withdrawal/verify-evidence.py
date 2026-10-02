"""Verify recorded withdrawal evidence without accessing PAM or fixture state."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for name,h in v['sha256'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==h,name
r=read('result.json');cleanup=read('cleanup.json');restored=read('restored.json')
assert r['passed'] and r['cleanup_rc']==0 and r['error'] is None
for flag in ('full_account_protection','whole_classification_qualified','real_nss_mutations_tested','all_producer_quiescence','real_reboot_tested','power_loss_tested'):assert r[flag] is False,flag
for name,h in r['metadata']['source_sha256'].items():
    target={'withdrawal-pam-guard.c':'pam-guard.c','barrier-writer.py':'../parental-registry-barrier/writer.py'}.get(name,name)
    assert hashlib.sha256((P/target).read_bytes()).hexdigest()==h,name
rows=r['checks'];assert len(rows)==33 and len({x['name'] for x in rows})==33
assert all(x['passed'] for x in rows)
c={x['name']:x for x in rows}
for x in rows:
    if 'allowed' not in x:continue
    if x['allowed']:
        assert x['unit']['ActiveState']=='active' and int(x['unit']['MainPID'])>0
        assert x['context']=='lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0' if x['uid']==1003 else x['context'].startswith('unconfined_u:unconfined_r:unconfined_t:')
    else:
        assert x['uid']==1002 and x['unit']['MainPID']=='0' and x['unit']['ExecMainStatus']=='224'
        assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in x['journal']
operations=set();proof_hashes=set()
for point in ('marker-synced','journal-synced','proof-unlinked','retired-journal-synced'):
    crash=c[point+'-crash91-durable-block'];marker=crash['marker']
    assert crash['worker_rc']==91 and crash['proof_exists']==(point in {'marker-synced','journal-synced'})
    assert marker['uid']==1002 and marker['phase']=='blocked' and marker['revision']==1
    operations.add(marker['operation']);proof_hashes.add(marker['proof_hash'])
    assert not c[point+'-new-ordinary-denied']['allowed']
    assert c[point+'-reconcile-read-only-no-reenrollment']['passed']
    journal=c[point+'-authorized-resume-remains-blocked']['journal']
    assert journal['phase']=='retired' and journal['revision']==2
    assert all(journal[k]==marker[k] for k in ('operation','uid','proof_hash'))
    assert c[point+'-same-operation-idempotent-conflicting-operation-denied']['passed']
assert len(operations)==4 and len(proof_hashes)==1
for name in ('authorization-denied-no-effects','stale-proof-conflict-no-marker','concurrent-reader-prevents-withdrawal-before-effects','authorized-retry-retires-restored-proof-without-reopening'):assert c[name]['passed']
for name in ('writer-lock-denies-concurrent-new-admission','restored-old-proof-still-denied-by-marker','missing-marker-existing-journal-still-denies','corrupt-journal-still-denies-old-proof'):assert not c[name]['allowed']
old=c['old-ordinary-manager-survives-admission-withdrawal'];assert int(old['pid'])>0 and not old['quiescence_proven']
assert int(c['unrelated-supervised-manager-preserved']['pid'])>0
assert cleanup['passed'] and all(x['passed'] for x in cleanup['cleanup']) and all(cleanup['restored'].values())
assert restored['passed'] and all(x=='0' for x in restored['units'].values()) and all(restored['absent_paths'].values())
assert not restored['processes'] and not restored['sessions'].strip() and restored['enforce']=='Permissive'
assert all(restored[x] for x in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
assert not restored['complete_kernel_audit']
assert v['python_tests']==294 and v['new_python_tests']==8 and v['python_suite_exit_code']==0
assert v['poweroff_rc']==v['qemu_exit_code']==v['native_exit_code']==int((P/'exit-status').read_text())==0
assert v['stderr_empty'] and not (P/'stderr.log').read_bytes()
assert v['native_terminal_result']==json.loads((P/'stdout.log').read_text().splitlines()[-1])=={'passed':True,'checks':33,'cleanup_rc':0}
assert not v['production_changed'] and not v['all_producer_quiescence'] and not v['real_reboot_tested'] and not v['power_loss_tested']
print('PASS: 33 controles de retirada; nenhuma declaração de quiescência ou enrollment')
