"""Offline verification of the experimental producer matrix."""
import hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parent
p=json.loads((BASE/'provenance.json').read_text())
for group in ('source_sha256','artifact_sha256'):
    for name,expected in p[group].items():
        assert hashlib.sha256((BASE/name).read_bytes()).hexdigest()==expected,name
r=json.loads((BASE/'result.json').read_text()); restored=json.loads((BASE/'restored.json').read_text())
assert r['passed'] and len(r['checks'])==14 and all(x['passed'] for x in r['checks'])
assert len({x['name'] for x in r['checks']})==14
for guest,local in {'producer-exercise.py':'exercise.py','producer-pam-account-guard.c':'pam-account-guard.c',
    'barrier-writer.py':'../parental-registry-barrier/writer.py','lyra-producer-registry.cil':'registry.cil'}.items():
    assert r['source_sha256'][guest]==hashlib.sha256((BASE/local).read_bytes()).hexdigest(),guest
c={x['name']:x for x in r['checks']}
for name in ('blocked-system-user-with-pam-denied','blocked-system-timer-with-pam-denied','old-pam-generation-denied-after-enrollment'):
    assert c[name]['unit']['MainPID']=='0' and c[name]['unit']['ExecMainStatus']=='224'
assert sum(x.get('qualification')=='known-producer-gap' for x in r['checks'])==3
assert all(x['passed'] for x in r['cleanup']) and all(r['restored'].values())
assert restored['passed'] and not restored['processes'] and not restored['sessions'].strip()
assert all(restored['absent_paths'].values()) and all(v=='0' for v in restored['units'].values())
assert restored['accounts_removed'] and restored['groups_removed'] and restored['policy_removed']
assert not r['full_account_protection'] and not r['cron_tested'] and not r['dbus_activation_tested']
assert p['vm']['final_state']=='powered-off' and p['vm']['qemu_exit_code']==0
assert p['python_suite_exit_code']==0 and not p['production_changed']
print('PASS: 14 native producer checks, 3 documented gaps, sources and restoration')
