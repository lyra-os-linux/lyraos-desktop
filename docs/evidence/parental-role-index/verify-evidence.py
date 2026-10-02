"""Verify recorded role-index admission evidence without touching PAM."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for name,h in v['sha256'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==h,name
failed=read('failed-result.json')
assert not failed['passed'] and failed['cleanup_rc']==0 and len(failed['checks'])==18
assert hashlib.sha256((P/'failed-native.py').read_bytes()).hexdigest()==failed['metadata']['source_sha256']['native.py']
assert read('failed-cleanup.json')['passed'] and read('failed-restored.json')['passed']
r=read('result.json');cleanup=read('cleanup.json');restored=read('restored.json')
assert r['passed'] and r['cleanup_rc']==0 and r['error'] is None
for flag in ['full_account_protection','whole_classification_qualified','missing_classifier_preserves_ordinary','real_nss_mutations_tested']:
    assert r[flag] is False,flag
for name,h in r['metadata']['source_sha256'].items():
    target={'roles-pam-guard.c':'pam-guard.c','barrier-writer.py':'../parental-registry-barrier/writer.py'}.get(name,name)
    assert hashlib.sha256((P/target).read_bytes()).hexdigest()==h,name
rows=r['checks'];assert len(rows)==20 and len({x['name'] for x in rows})==20
assert all(x['passed'] for x in rows)
for x in rows:
    if x['allowed']:
        assert x['unit']['ActiveState']=='active' and int(x['unit']['MainPID'])>0
        assert x['context']=='lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0' if x['uid']==1003 else ':unconfined_t:' in x['context']
    else:
        assert x['unit']['MainPID']=='0' and x['unit']['ExecMainStatus']=='224'
        assert 'pam_lyra_role_registry_fixture(systemd-user:session): Experimental role-index admission rejected session' in x['journal']
c={x['name']:x for x in rows}
for fault in ['missing-state','corrupt-state','missing-protected-role','wrong-ordinary-role','partial-role-identity']:
    assert not c[fault+'-protected-denied']['allowed']
    assert c[fault+'-ordinary-preserved']['allowed']
for fault in ['missing-index','corrupt-index','unsafe-index-mode']:
    assert not c[fault+'-protected-denied']['allowed']
    assert not c[fault+'-ordinary-denied-availability-gap']['allowed']
assert cleanup['passed'] and all(x['passed'] for x in cleanup['cleanup']) and all(cleanup['restored'].values())
assert restored['passed'] and all(x=='0' for x in restored['units'].values()) and all(restored['absent_paths'].values())
assert not restored['processes'] and not restored['sessions'].strip() and restored['enforce']=='Permissive'
assert all(restored[x] for x in ['pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'])
assert not restored['complete_kernel_audit']
assert v['python_tests']==286 and v['python_suite_exit_code']==0 and v['poweroff_rc']==v['qemu_exit_code']==0
assert v['native_exit_code']==0
assert v['stderr_empty'] and v['native_terminal_result']=={'passed':True,'checks':20,'cleanup_rc':0}
assert not v['production_changed'] and v['availability_gaps_reproduced']==3
print('PASS: 20 controles; 3 falhas de disponibilidade reproduzidas, não qualificação do classificador')
