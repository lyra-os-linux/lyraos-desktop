import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
v=json.loads((P/'provenance.json').read_text())
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
external={'reference.py':'../parental-systemd-reference/reference.py','namespace.py':'../parental-namespace-guard/namespace.py','catalog.py':'../parental-service-catalog/catalog.py','coordinator.py':'../parental-coordinator/coordinator.py'}
execs=json.loads((P/'executions.json').read_text());assert len(execs)==4
for i,file in enumerate(('attempt-1-result.json','result.json')):
 r=json.loads((P/file).read_text());assert r['passed'] is bool(i) and r['cleanup']['passed']
 assert execs[i]['result']['rc']==(1 if i==0 else 0)
 assert bool(execs[i]['result']['stderr']) is (i==0)
 for n,h in r['metadata']['source_sha256'].items():
  path=external.get(n,n)
  if n=='native.py' and i==0:path='attempt-1-native.py'
  assert hashlib.sha256((P/path).read_bytes()).hexdigest()==h,(file,n)
 logs=[json.loads(s) for s in execs[i]['result']['stdout'].splitlines()]
 assert len(r['checks'])==(0 if i==0 else 9)
 assert logs[:-1]==r['checks'] and logs[-1]==dict(passed=bool(i),checks=len(r['checks']),cleanup=True)
 for flag in ('full_account_protection','global_coverage_qualified','real_activation_or_revocation_adapter_qualified','shared_privileged_services_qualified'):assert r[flag] is False
r=json.loads((P/'result.json').read_text());assert r['error'] is None and all(c['passed'] for c in r['checks'])
c={x['name']:x for x in r['checks']}
row=c['real-exec-with-same-pid-start-and-live-pidfd-refused'];before=row['before'];after=row['after']
assert before['pid']==after['pid'] and before['start_ticks']==after['start_ticks']
assert before['executable']!=after['executable'] and before['argv']!=after['argv'] and row['code']=='UnsupportedRuntime'
assert before['uids']==after['uids']==[1002]*4 and before['gids']==after['gids']==[1003]*4
assert c['real-unit-source-change-invalidates-running-reference']['code']=='UnverifiedLoadedUnit'
assert c['restored-unit-bytes-do-not-revive-old-source-reference']['code']=='Conflict'
x=json.loads((P/'restored.json').read_text());assert x['passed'] and all(x['absent'].values()) and not x['reserved_processes']
assert all(x[k] for k in ('accounts_and_pam_preserved','declarations_preserved','previous_accepted_unit_files_preserved','broker_preserved'))
assert x['unit_state']==dict(MainPID='0',ControlGroup='',LoadState='not-found',ActiveState='inactive')
assert x['source_sha256']==hashlib.sha256((P/'restore.py').read_bytes()).hexdigest()
assert json.loads(execs[2]['result']['stdout'])==x
assert all(e['result']['rc']==0 and not e['result']['stderr'] for e in execs[1:])
assert v['python_tests']==620 and v['new_python_tests']==18 and v['native_checks']==9 and v['failed_native_attempts']==1
assert v['python_exit_code']==v['qemu_exit_code']==0
log=(P/'python-suite.txt').read_text();assert 'Ran 620 tests' in log and '\nOK\n' in log
print('PASS: 620 testes Python, 9 controles VM, exec com mesmo PID recusado, preservação e primeira tentativa arquivada')
