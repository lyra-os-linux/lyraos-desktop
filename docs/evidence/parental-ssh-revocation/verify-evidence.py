"""Offline checks of the exact archived SSH experiment and its restoration."""
import hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parent
provenance=json.loads((BASE/'provenance.json').read_text())
for group in ('source_sha256','artifact_sha256'):
    for name,expected in provenance[group].items():
        assert hashlib.sha256((BASE/name).read_bytes()).hexdigest()==expected,name
result=json.loads((BASE/'result.json').read_text())
restored=json.loads((BASE/'restored.json').read_text())
assert result['passed'] and len(result['checks'])==24 and all(row['passed'] for row in result['checks'])
checks={row['name']:row for row in result['checks']};assert len(checks)==24
sources={'ssh-revocation-exercise.py':'exercise.py','ssh-pam-account-guard.c':'pam-account-guard.c',
         'barrier-writer.py':'../parental-registry-barrier/writer.py','lyra-ssh-registry.cil':'registry.cil',
         'ssh_revoke.py':'revoke.py'}
for guest,local in sources.items():
    assert result['source_sha256'][guest]==hashlib.sha256((BASE/local).read_bytes()).hexdigest(),guest
assert checks['durable-barrier-alone-does-not-revoke-old-tunnel']['busy']
assert checks['durable-barrier-alone-does-not-revoke-old-tunnel']['forwarded']
assert checks['old-multiplex-can-open-channel-until-transport-revoked']['rc']==0
revoked=checks['target-transports-and-command-revoked']
assert revoked['pidfds'] and revoked['pidfds_exited']==len(revoked['holders_before'])==6
assert revoked['logind_rc']==0 and not revoked['custom_signals'] and not revoked['forwarded']
assert all(revoked[k]==255 for k in ('tunnel_rc','command_rc','mux_rc'))
assert sum(row['uids']==[0,0,0,0] for row in revoked['holders_before'])==3
assert all('/user.slice/user-31000.slice/session-' in row['cgroup'] for row in revoked['holders_before'])
assert checks['ordinary-connections-and-shared-listener-preserved']['forwarded']
assert checks['pending-authentication-survives-logind-until-account-recheck']['passed']
assert checks['ordinary-existing-tunnel-survives-entire-transition']['passed']
negatives=[row for row in result['checks'] if row.get('account_rejection')]
assert len(negatives)==6
for row in negatives:
    rejection=row['account_rejection']
    assert row['rc']==255 and rejection['sequential_attempt'] and rejection['user']=='clirestricted'
    assert rejection['lines']==[
        'pam_lyra_ssh_registry_fixture(sshd:account): Experimental SSH registry admission rejected account',
        'Access denied for user clirestricted by PAM account configuration [preauth]']
assert all(row['passed'] for row in result['cleanup'])
assert all(result[k] for k in ('original_accounts_preserved','vendor_restored','fixtures_removed','enforce_restored'))
assert restored['passed'] and all(v=='0' for v in restored['units'].values())
assert all(restored['absent_paths'].values()) and not restored['sessions'].strip() and not restored['processes']
assert restored['accounts_removed'] and restored['groups_removed'] and restored['policy_removed']
assert restored['enforce']=='Permissive' and restored['sshd_enabled']=='disabled'
assert provenance['vm']['final_state']=='powered-off' and provenance['vm']['qemu_exit_code']==0
assert not provenance['production_changed'] and not provenance['full_account_protection']
print('PASS: 24 native SSH checks, 6 exact account denials, 6 exited pidfds, sources and restoration')
