"""Offline verification of root inventory refusals; no full coverage claim."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
r=read('result.json');assert r['passed'] and r['error'] is None and r['cleanup_rc']==0 and len(r['checks'])==23 and all(x['passed'] for x in r['checks'])
assert int((P/'exit-status').read_text())==0 and not(P/'stderr.log').read_bytes()
external={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','coordinator.py':'../parental-coordinator/coordinator.py','ordinary-coordinator.py':'../parental-ordinary-coordinator/ordinary-coordinator.py','barrier-writer.py':'../parental-registry-barrier/writer.py','manager_adapters.py':'../parental-manager-adapters/adapters.py'}
for n,h in r['metadata']['source_sha256'].items():assert hashlib.sha256((P/external.get(n,n)).read_bytes()).hexdigest()==h,n
for f in ('full_account_protection','whole_namespace_inventory_qualified','complete_coverage_issuer_implemented','production_adapters_qualified','global_monotonic_revision_qualified','anti_rollback_qualified','power_loss_tested','real_nss_mutations_tested','all_producer_quiescence'):assert r[f] is False,f
c={x['name']:x for x in r['checks']};assert len(c)==23
x=c['root-protected-inventory-records-unsupported-families'];assert x['revision']==1 and len(x['states'])==7 and list(x['states'].values()).count('unsupported')==5 and x['states']['classification']==x['states']['user-manager']=='registered'
x=c['all-preflight-refusals-preserve-ordinary-managers-and-proofs'];assert x['authorization_calls']==x['adapter_calls']==0
assert x['peer_pid']==c['baseline-ordinary-1000']['unit']['MainPID'] and x['target_pid']==c['baseline-ordinary-1002']['unit']['MainPID'] and int(x['peer_pid'])>0 and int(x['target_pid'])>0
for name in ('whole-account-preflight-refuses-partial-catalog-without-authority-effects','seven-registered-family-names-do-not-issue-whole-coverage','forced-candidate-cannot-bypass-whole-coverage-check','stale-revision-rejected-before-authorization-or-withdrawal','changed-route-digest-rejected-without-revision-bump','configuration-cannot-self-assert-complete-coverage','inventory-refusal-never-removes-existing-withdrawal-authority','busy-target-inventory-lock-does-not-block-peer-read','cooperating-writer-cannot-replace-live-target-snapshot'):assert c[name]['passed']
a=read('cleanup.json');assert a['passed'] and all(x['passed'] for x in a['cleanup']) and all(a['restored'].values())
for n in ('inventory-restored.json','inventory-restored-independent.json'):
    a=read(n);assert a['passed'];assert a.get('directory_absent',a.get('inventory_directory_absent')) is True
rest=read('restored.json');assert rest['passed'] and all(x=='0' for x in rest['units'].values()) and all(rest['absent_paths'].values()) and not rest['processes'] and not rest['sessions'].strip() and rest['enforce']=='Permissive' and not rest['complete_kernel_audit']
assert all(rest[f] for f in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
assert v['native_checks']==23 and v['python_tests']==433 and v['new_python_tests']==29 and v['failed_native_attempts']==0
assert v['native_exit_code']==v['python_suite_exit_code']==v['qemu_exit_code']==v['poweroff_rc']==0 and not v['production_changed']
assert 'Ran 433 tests' in (P/'python-suite.txt').read_text() and '\nOK\n' in (P/'python-suite.txt').read_text()
assert json.loads((P/'stdout.log').read_text().splitlines()[-1])=={'passed':True,'checks':23,'cleanup_rc':0}
print('PASS: 23 controles de inventário, 433 testes; cobertura completa permanece indisponível')
