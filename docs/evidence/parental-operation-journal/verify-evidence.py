"""Offline validation of scoped admission-withdrawal ownership evidence."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
r=read('result.json')
assert r['passed'] and r['error'] is None and r['cleanup_rc']==0 and not r['cleanup_stderr']
assert len(r['checks'])==31 and all(x['passed'] for x in r['checks'])
assert int((P/'exit-status').read_text())==0 and not(P/'stderr.log').read_bytes()
external={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','coordinator.py':'../parental-coordinator/coordinator.py','ordinary-coordinator.py':'../parental-ordinary-coordinator/ordinary-coordinator.py','barrier-writer.py':'../parental-registry-barrier/writer.py','manager_adapters.py':'../parental-manager-adapters/adapters.py','inventory.py':'../parental-inventory-gate/inventory.py'}
for n,h in r['metadata']['source_sha256'].items():assert hashlib.sha256((P/external.get(n,n)).read_bytes()).hexdigest()==h,n
for f in ('full_account_protection','all_producer_quiescence','production_journal_qualified','global_monotonic_revision_qualified','anti_rollback_qualified','power_loss_tested','kernel_reboot_tested','real_nss_mutations_tested','producer_revocation_tested'):assert r[f] is False,f
c={x['name']:x for x in r['checks']};assert len(c)==31
points=('intent-marker-synced','owned-intent-synced','legacy-marker-synced','legacy-journal-synced','owned-blocked-synced','proof-unlinked','retired-journal-synced','owned-retired-synced')
peer=c['baseline-ordinary-1000']['unit']['MainPID'];assert int(peer)>0
crashes=c['eight-subprocess-crashes-never-open-admission']['crashes']
assert tuple(x['point'] for x in crashes)==points and len({x['operation'] for x in crashes})==8
for event in crashes:
    point=event['point'];assert event['child_rc']==91
    fence=c['crash-fence-'+point];assert fence['child_rc']==91 and fence['point']==point and len(fence['marker_sha256'])==64
    assert fence['status']==('AdmissionWithdrawnNoQuiescence' if point=='owned-retired-synced' else 'BlockedRecoveryRequired')
    pam=c['pam-denies-after-crash-'+point]
    assert pam['unit']['MainPID']=='0' and pam['unit']['ExecMainStatus']=='224' and pam['peer_pid']==peer
    assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in pam['journal']
    done=c['fresh-authorized-resume-'+point]
    assert done['owner_operation']==event['operation'] and done['owner_revision']==3
    assert done['status']=='AdmissionWithdrawnNoQuiescence' and done['proof_absent'] and done['peer_preserved']
for n in ('corrupt-owner-refused-without-changing-barrier','recreated-proof-after-retirement-is-never-removed-by-resume','missing-marker-not-reconstructed-from-owner-record','inspection-read-only-and-peer-manager-preserved'):assert c[n]['passed']
a=read('cleanup.json');assert a['passed'] and all(x['passed'] for x in a['cleanup']) and all(a['restored'].values())
for n in ('inventory-restored.json','inventory-restored-independent.json'):
    a=read(n);assert a['passed'] and a.get('directory_absent',a.get('inventory_directory_absent')) is True
rest=read('restored.json')
assert rest['passed'] and all(x=='0' for x in rest['units'].values()) and all(rest['absent_paths'].values())
assert not rest['processes'] and not rest['sessions'].strip() and rest['enforce']=='Permissive' and not rest['complete_kernel_audit']
assert all(rest[f] for f in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
assert v['native_checks']==31 and v['python_tests']==455 and v['new_python_tests']==22 and v['failed_native_attempts']==0
assert v['native_exit_code']==v['python_suite_exit_code']==v['qemu_exit_code']==v['poweroff_rc']==0 and not v['production_changed']
assert 'Ran 455 tests' in (P/'python-suite.txt').read_text() and '\nOK\n' in (P/'python-suite.txt').read_text()
assert json.loads((P/'stdout.log').read_text().splitlines()[-1])=={'passed':True,'checks':31,'cleanup_rc':0}
print('PASS: 31 controles nativos, 455 testes; journal limitado à retirada de admissão')
