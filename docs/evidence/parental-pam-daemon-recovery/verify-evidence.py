"""Archived source/execution verification; not a production qualification."""
import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
load=lambda n:json.loads((P/n).read_text())
proof=load('provenance.json')
for name,digest in proof['artifacts'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest,name
for name,digest in proof['dependencies'].items():assert hashlib.sha256((P.parent/name).read_bytes()).hexdigest()==digest,name
r=load('result.json');assert r['passed'] is True and r['cleanup_rc']==0 and len(r['checks'])==29
for key in ('full_account_protection','global_coverage_qualified','general_pam_runtime_qualified','production_adapters_qualified','power_loss_tested'):assert r[key] is False
assert r['profile_removed'] and r['close_hold_removed'] and r['admission_checks_unchanged']
for f in ('restart.py','native-restart.py','restarted-reader.py'):assert r['metadata']['source_sha256'][f]==hashlib.sha256((P/f).read_bytes()).hexdigest()
rows={c['name']:c for c in r['checks']};assert len(rows)==29 and all(c['passed'] is True for c in rows.values())
a=rows['recovery-stop-accepted-helper-alive-completion-withheld'];b=rows['pending-recovery-reauthorized-without-resubmitting-stop'];assert a['effect']==b['effect'] and a['effect']['phase']=='accepted' and a['populated']==1 and a['drained'] is False
origin=rows['origin-sealed-before-main-exit-and-first-stop'];assert len(origin['invocation'])==16 and any(origin['invocation'])
workers=[]
for name,row in rows.items():
 if 'worker' not in row:continue
 w=row['worker'];workers.append(w);assert w['inherited_pidfds']==[] and w['ipc_requests']==[] and w['before']==a['effect']
 if name=='fresh-process-refuses-live-orphan-without-authorization-or-new-ipc':assert w['code']=='Busy' and not w['empty'] and not w['authorization_calls'] and w['after']==w['before']
 elif name.startswith('fresh-process-refuses-unsafe-origin-'):assert w['code']=='StorageFailure' and not w['authorization_calls'] and w['after']==w['before'] and row['original_inode_restored'] is True
 elif name=='fresh-process-denied-cold-reconciliation-keeps-existing-acceptance':assert w['code']=='Denied' and len(w['authorization_calls'])==1 and w['after']==w['before']
 else:
  assert name=='fresh-process-reconstructs-root-origin-and-reconciles-cold-existing-stop'
  assert w['outcome']=='reconciled' and w['code'] is None and w['empty'] is True and len(w['authorization_calls'])==1
  assert w['after']==w['result'] and w['after']['phase']=='observed-drained' and w['after']['revision']==3
  assert row['requests']==a['requests']==b['requests'] and len(row['requests'])==1
  assert row['peer_preserved'] and row['owned_masks_preserved'] and row['forced_helper_termination_qualified'] is False and row['daemon_service_restart_qualified'] is False
  assert w['properties']['InvocationID']=={'type':'ay','data':[]}
assert len(workers)==7 and len({w['pid'] for w in workers})==7
for kind in ('permissions','owner','hardlink','symlink'):assert 'fresh-process-refuses-unsafe-origin-'+kind in rows
assert 'original-consumer-context-closed-before-fresh-process-recovery' in rows
assert rows['closed-pam-profile-denies-new-admission-after-withdrawal']['unit']['ExecMainStatus']=='224'
response=load('native-response.json');assert response['rc']==0 and not response['stderr'];assert json.loads(response['stdout'].splitlines()[-1])==dict(passed=True,checks=29,cleanup_rc=0)
assert re.search(r'Ran 744 tests in ',(P/'python-suite.txt').read_text()) and '\nOK\n' in (P/'python-suite.txt').read_text()
readers=load('restoration-executions.json');assert {x['file'] for x in readers}=={'restore-check.py','restore-units.py','restore-ownership.py','restore-extra.py'}
for x in readers:assert x['response']['rc']==0 and json.loads(x['response']['stdout'])['passed'] is True
assert load('poweroff-response.json')['rc']==0 and load('vm-off.json')['qemu_exit_code']==0
assert proof['specific_tests']==28 and proof['suite_tests']==744
assert (P/'tests-source.txt').read_bytes()==(P.parents[2]/'tests/test_parental_pam_daemon_recovery.py').read_bytes()
print('PASS: root origin, cold reconciliation in 7 fresh consumers without inherited pidfds or new StopUnit; 744 tests/29 VM controls/4 restoration readers. Production daemon/reboot/hung PAM remain unqualified.')
