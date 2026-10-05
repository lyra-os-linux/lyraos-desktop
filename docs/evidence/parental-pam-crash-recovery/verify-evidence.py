"""Check sealed crash-boundary executions; never infer power-loss qualification."""
import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
load=lambda n:json.loads((P/n).read_text())
proof=load('provenance.json')
for name,digest in proof['artifacts'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest,name
for name,digest in proof['dependencies'].items():assert hashlib.sha256((P.parent/name).read_bytes()).hexdigest()==digest,name
phases={'origin-synced':None,'intent-synced':'intent','request-returned':'intent','acceptance-synced':'accepted'}
count=0;boot=None;operations=set();consumer_pids=set()
for point,phase in phases.items():
 r=load(point+'/result.json');expected=18 if phase is None else 19;assert r['passed'] is True and r['cleanup_rc']==0 and len(r['checks'])==expected;count+=expected
 assert r['profile_removed'] and r['close_hold_removed'] and r['admission_checks_unchanged']
 for key in ('full_account_protection','global_coverage_qualified','general_pam_runtime_qualified','production_adapters_qualified','power_loss_tested'):assert r[key] is False
 for f in ('native-crash.py','crash-worker.py'):assert r['metadata']['source_sha256'][f]==hashlib.sha256((P/f).read_bytes()).hexdigest()
 rows={c['name']:c for c in r['checks']};assert len(rows)==expected and all(c['passed'] is True for c in rows.values())
 initial=rows['consumer-exited-abruptly-without-finally-at-durable-boundary'];t=initial['trace'];effect=initial['effect'];requests=1 if point in ('request-returned','acceptance-synced') else 0
 assert initial['point']==point and initial['finally_skipped'] is True and initial['child']['rc']==91 and not initial['child']['stderr']
 assert t['point']==t['crash_stage']==point and t['request_entries']==t['request_returns']==requests
 assert t['authorization_calls']==(0 if phase is None else 1)
 if requests:assert t['reply']['type']=='o' and len(t['reply']['data'])==1 and re.fullmatch('/org/freedesktop/systemd1/job/[1-9][0-9]*',t['reply']['data'][0])
 if effect is None:assert phase is None
 else:
  assert effect['phase']==phase;operations.add(effect['owner']['operation'])
  if phase=='intent':assert effect['job'] is None
  else:assert effect['job']==t['reply']['data'][0]
 live=rows['fresh-consumer-keeps-incomplete-crash-operation-blocked-without-resubmission']['worker']
 assert live['code']==('RecoveryRequired' if phase is None else 'Busy') and not live['authorization_calls'] and live['before']==live['after']==effect and live['empty'] is False
 final=rows['post-crash-cold-observation-never-resubmits-or-fabricates-missing-effect'];cold=final['worker']
 assert final['trace']==t and final['expected_requests']==requests and final['peer_preserved'] and final['owned_masks_preserved'] and final['daemon_service_restart_qualified'] is False and final['power_loss_tested'] is False
 assert cold['empty'] is True
 if phase is None:assert cold['code']=='RecoveryRequired' and not cold['authorization_calls'] and cold['after'] is None
 else:
  denied=rows['denied-post-crash-cold-reconciliation-preserves-journal']['worker'];assert denied['code']=='Denied' and denied['before']==denied['after']==effect and len(denied['authorization_calls'])==1
  assert cold['code'] is None and cold['result']==cold['after'] and cold['after']['phase']=='observed-drained' and len(cold['authorization_calls'])==1
 for w in (live,cold):assert not w['inherited_pidfds'] and not w['ipc_requests'] and w['pid']!=t['pid'];consumer_pids.add(w['pid'])
 assert rows['closed-pam-profile-denies-new-admission-after-withdrawal']['unit']['ExecMainStatus']=='224'
 response=load(point+'/native-response.json');assert response['rc']==0 and not response['stderr'];assert json.loads(response['stdout'].splitlines()[-1])==dict(passed=True,checks=expected,cleanup_rc=0)
 readers=load(point+'/restoration-executions.json');assert {x['file'] for x in readers}=={'restore-check.py','restore-units.py','restore-ownership.py','restore-extra.py'}
 for x in readers:
  assert x['response']['rc']==0 and json.loads(x['response']['stdout'])['passed'] is True
  if x['file']=='restore-check.py':
   bid=json.loads(x['response']['stdout'])['boot_id']
   if boot is None:boot=bid
   assert bid==boot
assert count==75 and len(operations)==3 and len(consumer_pids)==8
assert load('matrix.json')['total_controls']==75 and load('matrix.json')['passed'] is True
assert load('poweroff-response.json')['rc']==0 and load('vm-off.json')['qemu_exit_code']==0
assert re.search(r'Ran 744 tests in ',(P/'python-suite.txt').read_text()) and '\nOK\n' in (P/'python-suite.txt').read_text()
print('PASS: 4 abrupt exit boundaries (rc91/no finally), 75 VM controls, 16 restoration readers, no resubmission; 744 tests. Production daemon/reboot/power loss remain unqualified.')
