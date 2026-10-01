"""Offline verification of real cron jobs and VM restoration."""
import hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parent
p=json.loads((BASE/'provenance.json').read_text())
for group in ('source_sha256','artifact_sha256'):
    for name,expected in p[group].items():
        assert hashlib.sha256((BASE/name).read_bytes()).hexdigest()==expected,name
r=json.loads((BASE/'result.json').read_text());restored=json.loads((BASE/'restored.json').read_text())
capture=json.loads((BASE/'capture.json').read_text());packages=json.loads((BASE/'packages-restored.json').read_text())
assert r['passed'] and len(r['checks'])==9 and all(x['passed'] for x in r['checks'])
c={x['name']:x for x in r['checks']};assert len(c)==9
for guest,local in {'cron-exercise.py':'exercise.py','cron-fixture.c':'payload.c',
    'producer-pam-account-guard.c':'../parental-producers/pam-account-guard.c',
    'lyra-cron-registry.cil':'registry.cil','barrier-writer.py':'../parental-registry-barrier/writer.py'}.items():
    assert r['source_sha256'][guest]==hashlib.sha256((BASE/local).read_bytes()).hexdigest(),guest
assert len(r['fixture_spool_labels'])==2
assert all('user_cron_spool_t' in x['after'] for x in r['fixture_spool_labels'])
for name in ('blocked-next-user-and-system-cron-denied','stale-generation-user-and-system-cron-denied'):
    x=c[name];assert len(x['guard_rejections'])==len(x['cron_account_errors'])==2
    assert x['journal_after_cursor'] and x['supervised_count']==1
    assert all(line=='pam_lyra_producer_registry_fixture(crond:account): Experimental producer registry admission rejected account' for line in x['guard_rejections'])
    assert all('(cronfixture) FAILED to authorize user with PAM (Permission denied)'==line for line in x['cron_account_errors'])
owners=c['root-cron-monitors-retain-generation-lease']['holders']
assert len(owners)==2 and all(x['uids']==[0]*4 and x['exe']=='/usr/sbin/cron' for x in owners)
revoked=c['trusted-fixture-payload-stop-releases-root-monitor-leases']
assert revoked['payload_pidfds_exited']==2 and revoked['signaled_uid']==31300 and not revoked['root_signals']
assert sum(x.get('qualification')=='known-producer-gap' for x in r['checks'])==1
assert c['ordinary-original-jobs-and-shared-daemon-preserved']['cron_pid']==c['baseline-real-user-and-system-crontabs-admitted']['cron_pid']
assert c['ordinary-original-jobs-and-shared-daemon-preserved']['ordinary']==c['baseline-real-user-and-system-crontabs-admitted']['ordinary']
assert capture['passed'] and not capture['stderr'] and capture['final_process_state'] in ('Z','absent')
assert capture['result_sha256']==hashlib.sha256((BASE/'result.json').read_bytes()).hexdigest()
assert [json.loads(line) for line in capture['stdout'].splitlines()]==r['checks']
assert all(x['passed'] for x in r['cleanup']) and all(r['restored'].values())
assert packages['packages_before_sha256']==hashlib.sha256((BASE/'packages-before.txt').read_bytes()).hexdigest()
assert json.loads((BASE/'installation.json').read_text())['stdout'].count('digests signatures OK')==3
assert packages['passed'] and packages['package_set_restored'] and packages['introduced']==['cron','cronie','debianutils']
assert restored['passed'] and not restored['processes'] and not restored['sessions'].strip()
assert all(restored['absent_paths'].values()) and all(v=='0' for v in restored['units'].values())
assert all(restored[k] for k in ('accounts_removed','groups_removed','policy_removed','package_set_restored','introduced_packages_removed','cron_binary_removed','cron_pam_removed','common_pam_preserved'))
assert not r['full_account_protection'] and not r['clock_modified']
assert p['vm']['final_state']=='powered-off' and p['vm']['qemu_exit_code']==0
assert p['python_suite_exit_code']==0 and not p['production_changed']
print('PASS: 9 native cron checks, 4 exact account denials, 2 exited payload pidfds, packages and restoration')
