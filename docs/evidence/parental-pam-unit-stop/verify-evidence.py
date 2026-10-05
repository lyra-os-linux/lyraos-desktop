#!/usr/bin/python3
"""Check the archived closed-PAM fixture; not a native replay."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
load=lambda name:json.loads((root/name).read_text())
provenance=load('provenance.json')
for name,digest in provenance['sha256'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
r=load('result.json');response=load('native-response.json')
assert response['rc']==0 and not response['stderr'] and r['passed'] is True and r['error'] is None
assert r['cleanup_rc']==0 and not r['cleanup_stderr'] and r['profile_removed'] is True
assert len(r['checks'])==16 and all(c['passed'] is True for c in r['checks'])
lines=[json.loads(line) for line in response['stdout'].splitlines()]
assert lines[:-1]==r['checks'] and lines[-1]==dict(passed=True,checks=16,cleanup_rc=0)
for n in ('pam.py','native-pam.py'):assert r['metadata']['source_sha256'][n]==hashlib.sha256((root/n).read_bytes()).hexdigest()
for k in ('full_account_protection','global_coverage_qualified','general_pam_runtime_qualified','production_adapters_qualified','power_loss_tested'):assert r[k] is False
readers=load('restoration-executions.json');assert readers['passed'] is True and len(readers['independent_readers'])==4
for row in readers['independent_readers'].values():assert row['rc']==0 and not row['stderr'] and json.loads(row['stdout'])['passed'] is True
assert load('poweroff-response.json')['rc']==0 and provenance['qemu_exit_code']==0
assert load('failed-native-1/result.json')['passed'] is False
assert 'Ran 18 tests' in (root/'python-tests.txt').read_text() and '\nOK\n' in (root/'python-tests.txt').read_text()
assert 'Ran 694 tests' in (root/'python-suite.txt').read_text() and '\nOK\n' in (root/'python-suite.txt').read_text()
print('PASS: 18 tests, 694 suite tests, 16 VM checks and four restoration readers; global qualification remains false')
