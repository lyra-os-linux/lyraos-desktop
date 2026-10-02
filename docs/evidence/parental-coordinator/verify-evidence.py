"""Read-only validation of the negative native coordinator evidence."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():
    assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
r=read('result.json');clean=read('cleanup.json');restored=read('restored.json')
assert r['passed'] and r['cleanup_rc']==0 and r['error'] is None
for flag in ['full_account_protection','production_authorization_tested','complete_classification_tested','real_producer_adapters_tested']:
    assert r[flag] is False,flag
for name,h in r['metadata']['source_sha256'].items():
    target={'barrier-pam-guard.c':'../parental-registry-barrier/pam-guard.c','barrier-writer.py':'../parental-registry-barrier/writer.py'}.get(name,name)
    assert hashlib.sha256((P/target).read_bytes()).hexdigest()==h,name
c={x['name']:x for x in r['checks']}
assert len(c)==len(r['checks'])==10 and all(x['passed'] for x in c.values())
a=c['real-managed-and-ordinary-managers-active'];ordinary=a['ordinary']['MainPID']
assert int(ordinary)>0 and int(a['managed']['MainPID'])>0
assert a['context']=='lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
healthy=c['clean-reconciliation-neither-blocks-nor-declares-enforcement-verified']
assert healthy['outcome']=='ExistingAssociationNeedsVerification' and healthy['files_unchanged']
assert c['denied-controller-authorization-has-no-durable-effect']['files_unchanged']
live=c['missing-adapters-persist-block-with-live-manager']
assert live['code']=='UnsupportedProducer' and live['holders']
assert all(h['comm']=='(sd-pam)' for h in live['holders'])
assert live['snapshot'][0][0]['state']=='transitioning'
assert c['native-lease-remains-busy-after-coordinator-refusal']['error'].startswith('busy: generation has admitted sessions;')
assert not c['exclusive-lease-alone-is-insufficient-for-coordinator']['holders']
empty=c['missing-adapters-deny-even-with-no-lease-holders']
assert empty['code']=='UnsupportedProducer' and empty['snapshot']==live['snapshot']
pam=c['native-pam-denies-manager-after-coordinator-block']
assert pam['unit']['MainPID']=='0' and pam['unit']['ExecMainStatus']=='224'
assert 'pam_lyra_identity_registry_fixture(systemd-user:session): Experimental registry-backed admission rejected session' in pam['journal']
recover=c['reconciliation-never-reenrolls-blocked-identity']
assert recover['outcome']=='BlockedUntilAuthorizedRecovery' and recover['barrier_present']
assert len(recover['snapshot'][0])==1 and recover['snapshot'][0][0]['state']=='recovering'
assert c['recovering-requires-separate-authorized-operation']['code']=='RecoveryRequired'
assert all(x['ordinary_pid']==ordinary for x in c.values() if 'ordinary_pid' in x)
assert clean['passed'] and all(x['passed'] for x in clean['cleanup']) and all(clean['restored'].values())
assert restored['passed'] and all(x=='0' for x in restored['units'].values()) and all(restored['absent_paths'].values())
assert not restored['processes'] and not restored['sessions'].strip() and restored['enforce']=='Permissive'
assert all(restored[k] for k in ['pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'])
assert not restored['complete_kernel_audit']
assert v['python_tests']==286 and v['new_unit_tests']==16 and v['python_suite_exit_code']==0
assert v['poweroff_rc']==v['qemu_exit_code']==0 and not v['production_changed']
print('PASS: 10 controles nativos, fontes, recusas por cobertura ausente, restauração e desligamento')
