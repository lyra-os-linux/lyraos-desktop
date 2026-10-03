"""Offline verification of filesystem ownership, not live producer coverage."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
external={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','coordinator.py':'../parental-coordinator/coordinator.py','ordinary-coordinator.py':'../parental-ordinary-coordinator/ordinary-coordinator.py','barrier-writer.py':'../parental-registry-barrier/writer.py','manager_adapters.py':'../parental-manager-adapters/adapters.py','inventory.py':'../parental-inventory-gate/inventory.py','operations.py':'../parental-operation-journal/operations.py','unit-adapter.py':'../parental-unit-adapter/unit-adapter.py','dbus-adapter.py':'../parental-dbus-adapter/dbus-adapter.py'}
def sources(result,directory=P):
    for n,h in result['metadata']['source_sha256'].items():
        p=P/external[n] if n in external else directory/n
        assert hashlib.sha256(p.read_bytes()).hexdigest()==h,n
r=read('result.json');sources(r)
assert r['passed'] and r['error'] is None and r['cleanup_rc']==0 and not r['cleanup_stderr']
assert len(r['checks'])==36 and all(x['passed'] for x in r['checks'])
assert int((P/'exit-status').read_text())==0 and not(P/'stderr.log').read_bytes()
assert json.loads((P/'stdout.log').read_text().splitlines()[-1])=={'passed':True,'checks':36,'cleanup_rc':0}
for f in ('full_account_protection','all_producer_quiescence','live_producer_inhibition_tested','production_journal_qualified','global_monotonic_revision_qualified','anti_rollback_qualified','power_loss_tested','kernel_reboot_tested','real_nss_mutations_tested','producer_revocation_tested'):assert r[f] is False,f
c={x['name']:x for x in r['checks']};assert len(c)==36
owner=c['owned-negative-admission-ready-before-producer-effects']['owner'];assert owner['phase']=='retired' and owner['revision']==3
peer=c['baseline-ordinary-1000']['unit']['MainPID'];assert int(peer)>0
for family in ('system-units','dbus-activation'):
    for point in ('intent-synced','effect-synced','fenced-journal-synced'):
        crash=c['durable-resource-crash-'+family+'-'+point]
        assert crash['child_rc']==91 and crash['owner']['owner']==owner
        assert crash['owner']['family']==family and crash['owner']['protocol_digest']==r['metadata']['source_sha256']['ownership.py']
        assert crash['owner']['phase']==('fenced' if point=='fenced-journal-synced' else 'intent')
        assert crash['resource_state']['state']==('available' if point=='intent-synced' else 'fenced')
        pam=c['pam-barrier-after-'+family+'-'+point]
        assert pam['unit']['MainPID']=='0' and pam['unit']['ExecMainStatus']=='224' and pam['peer_pid']==peer
        assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in pam['journal']
        done=c['authorized-resource-resume-'+family+'-'+point]
        assert done['owner']['phase']=='fenced' and done['owner']['revision']==2 and done['owner']['owner']==owner
        assert done['peer_pid']==peer and done['peer_preserved'] and done['authorization_calls']==1 and done['idempotent_retry_readonly']
        if family=='dbus-activation':assert done['owner']['original']==done['owner']['effect']
assert c['owned-hardlink-intermediate-resumes-original-inode']['fixture_intermediate_created_explicitly']
assert c['second-uid-operation-cannot-claim-first-owner']['first_uid']==1002 and c['second-uid-operation-cannot-claim-first-owner']['second_uid']==1000
assert c['second-uid-operation-cannot-claim-first-owner']['peer_existing_manager_preserved']
assert c['one-stable-global-ledger-lock-serializes-both-uids']['uids']==[1002,1000]
assert c['one-stable-global-ledger-lock-serializes-both-uids']['lock_inode']==c['missing-global-ledger-lock-never-created']['lock_inode']
def restored(prefix):
    a=read(prefix+'cleanup.json');assert a['passed'] and all(x['passed'] for x in a['cleanup']) and all(a['restored'].values())
    for n,key in (('inventory-restored.json','directory_absent'),('inventory-restored-independent.json','inventory_directory_absent'),('filesystem-restored.json','scratch_absent'),('filesystem-restored-independent.json','scratch_absent')):
        a=read(prefix+n);assert a['passed'] and a[key]
    a=read(prefix+'restored.json');assert a['passed'] and all(x=='0' for x in a['units'].values()) and all(a['absent_paths'].values())
    assert not a['processes'] and not a['sessions'].strip() and a['enforce']=='Permissive' and not a['complete_kernel_audit']
    assert all(a[f] for f in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
restored('')
f=P/'failed-attempt-1';assert int((f/'exit-status').read_text())==1 and not(f/'stdout.log').read_bytes()
assert "ModuleNotFoundError: No module named 'owned_common'" in (f/'stderr.log').read_text()
assert all(read('failed-attempt-1/failure-check.json').values())
f=P/'failed-attempt-2';failed=read('failed-attempt-2/result.json');sources(failed,f)
assert not failed['passed'] and len(failed['checks'])==30 and all(x['passed'] for x in failed['checks'])
assert failed['cleanup_rc']==0 and int((f/'exit-status').read_text())==1 and 'UnknownInventory' in (f/'stderr.log').read_text()
restored('failed-attempt-2/')
assert v['native_checks']==36 and v['python_tests']==482 and v['new_python_tests']==27 and v['failed_native_attempts']==2
assert v['native_exit_code']==v['python_suite_exit_code']==v['qemu_exit_code']==v['poweroff_rc']==0 and not v['production_changed']
assert 'Ran 482 tests' in (P/'python-suite.txt').read_text() and '\nOK\n' in (P/'python-suite.txt').read_text()
print('PASS: 36 controles nativos, 482 testes; ownership limitado ao sistema de arquivos')
