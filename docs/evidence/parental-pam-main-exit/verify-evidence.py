#!/usr/bin/python3
"""Verify archived main-exit fixture, not a VM replay or global qualification."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
load=lambda name:json.loads((root/name).read_text())
p=load('provenance.json')
for name,digest in p['sha256'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
r=load('result.json');response=load('native-response.json');assert response['rc']==0 and not response['stderr']
assert r['passed'] is True and r['error'] is None and r['cleanup_rc']==0 and not r['cleanup_stderr']
assert r['profile_removed'] is True and r['close_hold_removed'] is True and r['admission_checks_unchanged'] is True
assert len(r['checks'])==19 and all(c['passed'] is True for c in r['checks'])
lines=[json.loads(line) for line in response['stdout'].splitlines()]
assert lines[:-1]==r['checks'] and lines[-1]==dict(passed=True,checks=19,cleanup_rc=0)
for name in ('native-pam-exit.py','pam-close-hold.c'):assert r['metadata']['source_sha256'][name]==hashlib.sha256((root/name).read_bytes()).hexdigest()
original=root.parent/'parental-ordinary-withdrawal/pam-guard.c'
assert r['metadata']['source_sha256'][original.name.replace('pam-guard.c','withdrawal-pam-guard.c')]==hashlib.sha256(original.read_bytes()).hexdigest()
assert (root/'pam-close-hold.c').read_text().replace('#include <time.h>\n','').split('PAM_EXTERN int pam_sm_close_session')[0]==original.read_text().split('PAM_EXTERN int pam_sm_close_session')[0]
checks={c['name']:c for c in r['checks']}
row=checks['main-exited-during-authorization-helper-still-alive']
assert row['unit']['MainPID']=='0' and row['job']==dict(type='(uo)',data=[0,'/']) and row['populated']==1 and row['drained'] is False
assert row['main_pidfd_exited'] is True and row['helper_pidfd_exited'] is False
assert checks['main-exit-conflict-refused-before-stop-no-completion-created']['commands']==[]
assert checks['main-exit-conflict-refused-before-stop-no-completion-created']['requests']==[]
assert checks['fresh-capture-refuses-missing-main-with-live-helper-before-authorization']['authorization_count_unchanged'] is True
assert checks['automatic-manager-drain-observed-without-claiming-stop-effect']['effect'] is None
assert checks['automatic-manager-drain-observed-without-claiming-stop-effect']['drained'] is True
journal=load('helper-journal-response.json');assert journal['rc']==0 and 'Experimental VM-only PAM close hold entered' in journal['stdout']
for k in ('full_account_protection','global_coverage_qualified','general_pam_runtime_qualified','production_adapters_qualified','power_loss_tested'):assert r[k] is False
readers=load('restoration-executions.json');assert readers['passed'] is True and readers['close_hold_absent'] is True and len(readers['independent_readers'])==4
for row in readers['independent_readers'].values():assert row['rc']==0 and not row['stderr'] and json.loads(row['stdout'])['passed'] is True
assert load('poweroff-response.json')['rc']==0 and p['qemu_exit_code']==0
assert load('failed-native-1/result.json')['passed'] is False and load('failed-native-1/result.json')['cleanup_rc']==0
assert 'SyntaxError' in load('failed-preflight-2/native-response.json')['stderr']
assert 'Ran 696 tests' in (root/'python-suite.txt').read_text() and '\nOK\n' in (root/'python-suite.txt').read_text()
print('PASS: 19 VM checks, 696 tests, four restoration readers; zero MainPID/job does not prove empty session')
