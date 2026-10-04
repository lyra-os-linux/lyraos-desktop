import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
v=json.loads((P/'provenance.json').read_text())
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
execs=json.loads((P/'executions.json').read_text());assert len(execs)==10
cases=[(i,f'failed-attempt-{i+1}/result.json') for i in range(4)]+[(4,'artifact-attempt-5/result.json'),(7,'result.json')]
for i,file in cases:
 r=json.loads((P/file).read_text());good=i in (4,7)
 assert r['passed'] is good and r['cleanup_rc']==0 and not r['cleanup_stderr']
 assert execs[i]['result']['rc']==(0 if good else 1) and bool(execs[i]['result']['stderr']) is (not good)
 assert len(r['checks'])=={0:8,1:10,2:11,3:16,4:17,7:17}[i] and all(c['passed'] for c in r['checks'])
 for n,h in r['metadata']['source_sha256'].items():
  path=v['external_sources'].get(n,n)
  archive=f'failed-attempt-{i+1}' if not good else 'artifact-attempt-5' if i==4 else None
  if archive and (P/archive/n).is_file():path=archive+'/'+n
  assert hashlib.sha256((P/path).read_bytes()).hexdigest()==h,(file,n,path)
 logs=[json.loads(s) for s in execs[i]['result']['stdout'].splitlines()]
 checks=json.loads(json.dumps(r['checks']))
 if i in (3,4):
  c={x['name']:x for x in checks};bad=c['exec-during-authorization-refused-before-any-timer-or-service-stop']
  assert bad['commands']==c['guarded-existing-adapter-stops-timer-before-verified-services-peer-preserved']['commands']
  bad['commands']=[] # Explicit known mutable-list defect, archived source/result intact.
 assert logs[:-1]==checks and logs[-1]==dict(passed=good,checks=len(r['checks']),cleanup_rc=0)
 for flag in ('full_account_protection','global_coverage_qualified','shared_privileged_services_qualified','production_adapters_qualified','monotonic_revision_qualified','power_loss_tested'):assert r[flag] is False
r=json.loads((P/'result.json').read_text());assert r['error'] is None
c={x['name']:x for x in r['checks']}
assert c['exec-during-authorization-refused-before-any-timer-or-service-stop']['commands']==[]
restart=c['restart-during-authorization-refuses-pinned-epoch-and-preserves-new-payload'];assert restart['old_pid']!=restart['new_pid']
s=c['guarded-existing-adapter-stops-timer-before-verified-services-peer-preserved'];assert len(s['commands'])==3 and s['commands'][0][2].endswith('.timer')
assert all(u['MainPID']=='0' and u['ActiveState']=='inactive' for u in s['units'].values())
assert c['target-manager-remains-denied-and-peer-admitted']['unit']['ExecMainStatus']=='224'
outputs={'restore-check.py':'restored.json','restore-units.py':'units-restored-independent.json','restore-ownership.py':'ownership-restored-independent.json','restore-extra.py':'extra-restored.json'}
for prefix,index in (('artifact-attempt-5/',5),('',8)):
 rest=json.loads((P/(prefix+'restoration-executions.json')).read_text());assert rest['passed']
 assert rest['source_sha256']==hashlib.sha256((P/'restore-runner.py').read_bytes()).hexdigest()
 for name,e in rest['readers'].items():
  assert e['rc']==0 and not e['stderr'] and e['source_sha256']==hashlib.sha256((P/name).read_bytes()).hexdigest()
  row=json.loads((P/(prefix+outputs[name])).read_text());assert row['passed'] and json.loads(e['stdout'])==row
 assert json.loads(execs[index]['result']['stdout'])==dict(passed=True,readers=list(outputs))
assert all(e['result']['rc']==0 and not e['result']['stderr'] for e in execs[4:])
assert json.loads((P/'cleanup.json').read_text())['passed']
assert v['python_tests']==638 and v['new_python_tests']==18 and v['native_checks']==17 and v['failed_native_attempts']==4 and v['artifact_mismatch_attempts']==2
assert v['python_exit_code']==v['qemu_exit_code']==0
log=(P/'python-suite.txt').read_text();assert 'Ran 638 tests' in log and '\nOK\n' in log
print('PASS: 638 testes Python, 17 controles VM, 4 falhas e 2 divergências de registro arquivadas, restauração independente')
