"""Offline verification of native system-bus activation and restoration."""
import hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parent
p=json.loads((BASE/'provenance.json').read_text())
for group in ('source_sha256','artifact_sha256'):
    for name,expected in p[group].items():
        assert hashlib.sha256((BASE/name).read_bytes()).hexdigest()==expected,name
r=json.loads((BASE/'result.json').read_text());restored=json.loads((BASE/'restored.json').read_text())
assert r['passed'] and len(r['checks'])==17 and all(x['passed'] for x in r['checks'])
c={x['name']:x for x in r['checks']};assert len(c)==17
for guest,local in {'dbus-activation-exercise.py':'exercise.py','dbus-fixture-service.c':'service.c',
    'producer-pam-account-guard.c':'../parental-producers/pam-account-guard.c',
    'lyra-producer-registry.cil':'../parental-producers/registry.cil',
    'barrier-writer.py':'../parental-registry-barrier/writer.py'}.items():
    assert r['source_sha256'][guest]==hashlib.sha256((BASE/local).read_bytes()).hexdigest(),guest
assert sum(x.get('qualification')=='known-producer-gap' for x in r['checks'])==4
for name in ('new-systemd-dbus-with-pam-denied','stale-generation-dbus-pam-denied'):
    x=c[name];assert x['command']['rc']==1 and x['unit']['MainPID']=='0' and x['unit']['ExecMainStatus']=='224'
    assert x['guard_rejection']==['pam_lyra_producer_registry_fixture(lyra-producer-fixture:account): Experimental producer registry admission rejected account']
for name in ('baseline-exec-user-broker-transient-without-pam','new-exec-user-dbus-bypasses-barrier'):
    x=c[name];assert x['unit']['User']=='31200' and x['unit']['PAMName']==''
    assert x['unit_name'].startswith('dbus-') and x['cgroup'].startswith('0::/system.slice/')
    assert x['uids']==[31200]*4 and x['unit']['MainPID']==str(x['pid'])
assert c['fixture-dbus-producers-revoked-without-shared-broker-restart']['pidfds_exited']==4
assert c['disarmed-route-cannot-reactivate']['command']['rc']==1
assert 'not activatable' in c['disarmed-route-cannot-reactivate']['command']['stderr']
assert c['ordinary-owner-and-shared-broker-survive-entire-transition']['ordinary_pid']==c['baseline-ordinary-dbus-with-pam']['pid']
assert restored['bus_service_pid']==c['ordinary-owner-and-shared-broker-survive-entire-transition']['broker_pid']
assert all(x['passed'] for x in r['cleanup']) and all(r['restored'].values())
assert restored['passed'] and restored['activation_removed'] and restored['bus_service_preserved']
assert not restored['processes'] and not restored['sessions'].strip() and not restored['remaining_service_paths']
assert all(restored['absent_paths'].values()) and all(v=='0' for v in restored['units'].values())
assert restored['accounts_removed'] and restored['groups_removed'] and restored['policy_removed']
assert not r['full_account_protection'] and not r['cron_tested'] and r['dbus_activation_tested']
assert p['vm']['final_state']=='powered-off' and p['vm']['qemu_exit_code']==0
assert p['python_suite_exit_code']==0 and not p['production_changed']
print('PASS: 17 native D-Bus checks, 4 documented gaps, 4 exited pidfds, sources and restoration')
