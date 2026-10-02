"""Check recorded admission evidence offline; never load the PAM fixture."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for name,h in v['sha256'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==h,name
r=read('result.json');cleanup=read('cleanup.json');restored=read('restored.json')
assert r['passed'] and r['cleanup_rc']==0 and r['error'] is None and r['missing_parental_index_preserves_ordinary']
for flag in ('full_account_protection','whole_classification_qualified','missing_classifier_preserves_ordinary','real_nss_mutations_tested'):
    assert r[flag] is False,flag
for name,h in r['metadata']['source_sha256'].items():
    target={'attestation-pam-guard.c':'pam-guard.c','barrier-writer.py':'../parental-registry-barrier/writer.py'}.get(name,name)
    assert hashlib.sha256((P/target).read_bytes()).hexdigest()==h,name
rows=r['checks'];assert len(rows)==26 and len({x['name'] for x in rows})==26
assert all(x['passed'] for x in rows)
for x in rows:
    if x['allowed']:
        assert x['unit']['ActiveState']=='active' and int(x['unit']['MainPID'])>0
        assert x['context']=='lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0' if x['uid']==1003 else x['context'].startswith('unconfined_u:unconfined_r:unconfined_t:')
    else:
        assert x['unit']['MainPID']=='0' and x['unit']['ExecMainStatus']=='224'
        assert 'pam_lyra_attestation_fixture(systemd-user:session): Experimental attestation admission rejected session' in x['journal']
c={x['name']:x for x in rows}
for fault in ('missing-state','corrupt-state','missing-protected-role','missing-index','corrupt-index','unsafe-index-mode'):
    assert not c[fault+'-supervised-denied']['allowed'] and c[fault+'-supervised-denied']['uid']==1003
    assert c[fault+'-ordinary-preserved']['allowed'] and c[fault+'-ordinary-preserved']['uid']==1002
for fault in ('missing-proof','corrupt-proof','unsafe-proof-mode','partial-proof-identity'):
    assert not c[fault+'-ordinary-denied']['allowed'] and c[fault+'-ordinary-denied']['uid']==1002
    assert c[fault+'-supervised-preserved']['allowed'] and c[fault+'-supervised-preserved']['uid']==1003
assert not c['forged-ordinary-proof-supervised-mac-denied']['allowed'] and c['other-account-proof-ordinary-preserved']['allowed']
assert all(c[n]['allowed'] for n in ('supervised-baseline','ordinary-independent-baseline','final-supervised-restored','final-ordinary-restored'))
assert cleanup['passed'] and all(x['passed'] for x in cleanup['cleanup']) and all(cleanup['restored'].values())
assert restored['passed'] and all(x=='0' for x in restored['units'].values()) and all(restored['absent_paths'].values())
assert not restored['processes'] and not restored['sessions'].strip() and restored['enforce']=='Permissive'
assert all(restored[x] for x in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
assert not restored['complete_kernel_audit']
assert v['python_tests']==286 and v['python_suite_exit_code']==0 and v['poweroff_rc']==v['qemu_exit_code']==0
assert v['native_exit_code']==int((P/'exit-status').read_text())==0
assert v['stderr_empty'] and not (P/'stderr.log').read_bytes()
assert v['native_terminal_result']==json.loads((P/'stdout.log').read_text().splitlines()[-1])=={'passed':True,'checks':26,'cleanup_rc':0}
assert not v['production_changed'] and not v['whole_classification_qualified'] and not v['cutover_qualified']
print('PASS: 26 controles; acesso comum independente do índice parental, cutover ainda não qualificado')
