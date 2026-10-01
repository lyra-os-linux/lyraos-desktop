"""Read-only verifier of recorded VM session-exit evidence."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():
    assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
r=read('result.json'); restored=read('restored.json')
for name,h in r['source_sha256'].items():
    assert hashlib.sha256((P/v['guest_source_mapping'][name]).read_bytes()).hexdigest()==h,name
assert r['passed'] and not r['full_account_protection'] and not r['full_gnome_session_tested']
assert r['password_authentication_tested']
c={x['name']:x for x in r['checks']}
assert len(c)==len(r['checks'])==8 and all(x['passed'] for x in c.values())
opening=c['supervised-password-active']
assert opening['user']=='parentaltest' and len(opening['processes'])==1
assert opening['processes'][0]['uids']==[1003]*4
assert opening['processes'][0]['context']=='lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
names=[e.get('name') for e in opening['client_events'] if e['event']=='signal']
assert 'VerificationComplete' in names and 'SessionOpened' in names
leases=c['gdm-worker-and-linger-manager-hold-distinct-leases']
assert any('gdm-session-worker [pam/gdm-password]' in h['cmdline'] for h in leases['holders'])
assert any(h['comm']=='(sd-pam)' for h in leases['holders'])
normal=c['normal-session-exit-releases-worker-but-not-linger-manager']
assert normal['pidfds_exited']==2 and normal['holders']
assert all(h['comm']=='(sd-pam)' for h in normal['holders'])
assert normal['supervised_classes'] and all(s['Class']=='manager' and s['User']=='1003' for s in normal['supervised_classes'])
assert 'Gdm: Process exit status: 0' in normal['journal']
assert 'pam_unix(gdm-password:session): session closed for user parentaltest' in normal['journal']
assert normal['manager_pid']==leases['manager_pid']
gap=c['session-exit-is-not-account-quiescence']
assert gap['gap_reproduced'] and gap['error'].startswith('busy:') and gap['holders']
assert gap['snapshot'][0][0]['state']=='transitioning'
assert gap['snapshot'][1][opening['generation']]['phase']=='blocked'
rev=c['explicit-logind-revocation-releases-manager-lease-preserving-other-user-and-gdm']
assert rev['command']['rc']==0
end=c['explicit-revocation-allows-tombstone-without-reenrollment']
assert end['barrier_present'] and end['snapshot'][0][0]['state']=='tombstone'
assert len(end['snapshot'][0])==1
retry=c['lingering-marker-does-not-authorize-readmission-after-revocation']
assert retry['status']=='224' and retry['linger_present']
assert retry['cause']=='pam_lyra_identity_registry_fixture(systemd-user:session): Experimental registry-backed admission rejected session'
assert normal['ordinary_pid']==rev['ordinary_pid']==retry['ordinary_pid']
assert normal['gdm_pid']==rev['gdm_pid']==retry['gdm_pid']
assert all(x['passed'] for x in r['cleanup'])
for k in ['vendor_preserved','official_worker_restored','helper_label_restored','files_restored','passwords_restored','fixture_removed','managers_stopped','permissive_restored','fixture_processes_gone','linger_removed']:
    assert r[k],k
assert restored['passed'] and all(x=='0' for x in restored['units'].values())
assert all(restored['absent_paths'].values()) and not restored['uid_processes'] and not restored['sessions'].strip()
assert restored['policy_removed'] and restored['enforce']=='Permissive'
assert restored['worker_sha256']==r['official_worker_sha256']
assert not restored['complete_kernel_audit']
assert v['poweroff_rc']==v['qemu_exit_code']==v['python_suite_exit_code']==0 and v['python_tests']==270
assert not v['production_changed']
print('PASS: 8 controles nativos, saída normal/PAM, lingering, revogação, restauração e hashes')
