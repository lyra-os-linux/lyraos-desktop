"""Verify archived execution/source correspondence, not runtime qualification."""
import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
load=lambda name:json.loads((P/name).read_text())
proof=load('provenance.json')
for name,digest in proof['artifacts'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest,name
for name,digest in proof['dependencies'].items():assert hashlib.sha256((P.parent/name).read_bytes()).hexdigest()==digest,name
r=load('result.json');assert r['passed'] is True and r['cleanup_rc']==0 and len(r['checks'])==22
for field in ('full_account_protection','global_coverage_qualified','general_pam_runtime_qualified','production_adapters_qualified','power_loss_tested'):assert r[field] is False
assert r['profile_removed'] and r['close_hold_removed'] and r['admission_checks_unchanged']
for f in ('recovery.py','native-recovery.py'):assert r['metadata']['source_sha256'][f]==hashlib.sha256((P/f).read_bytes()).hexdigest()
rows={row['name']:row for row in r['checks']};assert len(rows)==22 and all(row['passed'] is True for row in rows.values())
a=rows['recovery-stop-accepted-helper-alive-completion-withheld'];b=rows['pending-recovery-reauthorized-without-resubmitting-stop'];c=rows['fixture-release-drain-reconciled-with-new-authorization-and-no-resubmission']
assert a['effect']['phase']=='accepted' and a['populated']==1 and a['drained'] is False
assert a['effect']==b['effect'] and a['requests']==b['requests']==c['requests'] and len(a['requests'])==1
assert c['effect']['phase']=='observed-drained' and c['effect']['revision']==3 and c['populated']==0 and c['drained'] is True
assert c['forced_helper_termination_qualified'] is False and c['peer_preserved'] and c['owned_masks_preserved']
origin=rows['historical-origin-retained-after-main-exit-without-new-orphan-capture'];assert origin['main_exited'] is True and origin['helper_exited'] is False
assert 'retained-origin-expired-after-closing-both-pins' in rows
assert rows['closed-pam-profile-denies-new-admission-after-withdrawal']['unit']['ExecMainStatus']=='224'
response=load('native-response.json');assert response['rc']==0 and not response['stderr'];summary=json.loads(response['stdout'].splitlines()[-1]);assert summary==dict(passed=True,checks=22,cleanup_rc=0)
assert re.search(r'Ran 716 tests in ',(P/'python-suite.txt').read_text()) and '\nOK\n' in (P/'python-suite.txt').read_text()
for path in ('restoration-executions.json','failed-native-1/restoration-executions.json'):
 readers=load(path);assert {row['file'] for row in readers}=={'restore-check.py','restore-units.py','restore-ownership.py','restore-extra.py'}
 for row in readers:assert row['response']['rc']==0 and json.loads(row['response']['stdout'])['passed'] is True
failed=load('failed-native-1/result.json');assert failed['passed'] is False and failed['cleanup_rc']==0 and len(failed['checks'])==17
assert load('failed-native-1/native-response.json')['rc']==1
assert load('poweroff-response.json')['rc']==0 and load('vm-off.json')['qemu_exit_code']==0
assert proof['specific_tests']==20 and proof['suite_tests']==716
print('PASS: retained origin, fresh authorization, one StopUnit, drain reconciliation; 716 tests/22 VM controls/4 restoration readers. Production and forced termination remain unqualified.')
