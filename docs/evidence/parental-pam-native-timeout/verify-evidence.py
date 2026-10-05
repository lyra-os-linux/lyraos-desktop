"""Verify scoped kernel signal evidence and archived execution correspondence."""
import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
load=lambda n:json.loads((P/n).read_text())
proof=load('provenance.json')
for name,digest in proof['artifacts'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest,name
for name,digest in proof['dependencies'].items():assert hashlib.sha256((P.parent/name).read_bytes()).hexdigest()==digest,name
assert (P/'pam-close-hold.c').read_text().replace('began.tv_sec >= 300','began.tv_sec >= 30')==(P.parent/'parental-pam-main-exit/pam-close-hold.c').read_text()
r=load('result.json');assert r['passed'] is True and r['cleanup_rc']==0 and len(r['checks'])==24
assert r['manager_logging_restored'] is True and r['tracing_restored'] is True
assert r['profile_removed'] and r['close_hold_removed'] and r['admission_checks_unchanged']
for key in ('full_account_protection','global_coverage_qualified','general_pam_runtime_qualified','production_adapters_qualified','power_loss_tested'):assert r[key] is False
for name in ('native-timeout.py','pam-close-hold.c'):assert r['metadata']['source_sha256'][name]==hashlib.sha256((P/name).read_bytes()).hexdigest()
rows={c['name']:c for c in r['checks']};assert len(rows)==24 and all(c['passed'] is True for c in rows.values())
policy=rows['native-stop-policy-measured-after-mask-reload-without-modification'];p=policy['properties'];timeout=p['TimeoutStopUSec']['data']/1000000
assert 0<timeout<=95 and policy['fixture_hold_seconds']==300
assert p['SendSIGKILL']=={'type':'b','data':True} and p['FinalKillSignal']=={'type':'i','data':9} and p['KillMode']=={'type':'s','data':'control-group'} and p['TimeoutStopFailureMode']=={'type':'s','data':'terminate'}
a=rows['recovery-stop-accepted-helper-alive-completion-withheld'];b=rows['pending-recovery-reauthorized-without-resubmitting-stop'];assert a['effect']==b['effect'] and a['effect']['phase']=='accepted' and a['populated']==1 and a['drained'] is False
arm=rows['isolated-kernel-signal-trace-armed-for-pinned-helper-and-systemd-sender'];assert arm['sender_pid']==1 and arm['sender_comm']=='systemd' and arm['global_trace_unchanged'] is True
final=rows['native-timeout-kills-held-helper-before-fixture-release-and-reconciles'];assert final['helper_pid']==arm['helper_pid']
assert final['marker_still_present'] is True and timeout-3<=final['elapsed']<2*timeout+15<300
assert final['result']=={'type':'s','data':'timeout'} and 'timed out' in final['journal'].lower()
signals=[line for line in final['signal_trace'].splitlines() if 'signal_generate:' in line];assert signals and all('systemd-1 ' in line and 'sig=9 ' in line and 'pid='+str(final['helper_pid'])+' ' in line and 'res=0' in line for line in signals)
assert final['requests']==a['requests']==b['requests'] and len(final['requests'])==1 and final['effect']['phase']=='observed-drained' and final['populated']==0 and final['drained'] is True
assert final['peer_preserved'] and final['owned_masks_preserved'] and final['closed_helper_timeout_qualified'] is True and final['general_hung_process_termination_qualified'] is False
assert final['heartbeats'] and all(h['marker_still_present'] is True and h['helper_pidfd_exited'] is False and h['populated']==1 for h in final['heartbeats'])
assert rows['closed-pam-profile-denies-new-admission-after-withdrawal']['unit']['ExecMainStatus']=='224'
for prefix in ('','failed-native-1/','failed-native-2/'):
 readers=load(prefix+'restoration-executions.json');assert {x['file'] for x in readers}=={'restore-check.py','restore-units.py','restore-ownership.py','restore-extra.py'}
 for x in readers:assert x['response']['rc']==0 and json.loads(x['response']['stdout'])['passed'] is True
 if prefix:
  failed=load(prefix+'result.json');assert failed['passed'] is False and failed['cleanup_rc']==0
  assert load(prefix+'native-response.json')['rc']==1
  if prefix=='failed-native-2/':assert failed['manager_logging_restored'] is True
reader=load('diagnostics-restoration.json');assert reader['rc']==0;d=json.loads(reader['stdout']);assert d['passed'] is True and d['instance_removed'] is True and d['tracing']==r['trace_global_before'] and d['manager_log_level']==r['metadata']['original_manager_log_level']
response=load('native-response.json');assert response['rc']==0 and not response['stderr'];assert json.loads(response['stdout'].splitlines()[-1])==dict(passed=True,checks=24,cleanup_rc=0)
assert re.search(r'Ran 744 tests in ',(P/'python-suite.txt').read_text()) and '\nOK\n' in (P/'python-suite.txt').read_text()
assert load('poweroff-response.json')['rc']==0 and load('vm-off.json')['qemu_exit_code']==0
print('PASS: native systemd SIGKILL from PID1 to pinned held PAM helper before 300s marker release; 744 tests/24 VM controls/4 restoration readers plus diagnostics restoration. D-state/general PAM/production remain unqualified.')
