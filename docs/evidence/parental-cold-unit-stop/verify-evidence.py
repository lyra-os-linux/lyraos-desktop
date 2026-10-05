"""Verify the saved qualification without repeating VM operations."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
v=json.loads((P/'provenance.json').read_text())
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
sources=json.loads((P/'source-map.json').read_text());guest=json.loads((P/'guest-source-hashes.json').read_text())
assert set(sources)==set(guest)
for n,file in sources.items():assert hashlib.sha256((P/file).read_bytes()).hexdigest()==guest[n],n
ex=json.loads((P/'executions.json').read_text());assert len(ex)==7
for i,prefix,good in ((0,'failed-native-1/',False),(1,'',True)):
 r=json.loads((P/(prefix+'result.json')).read_text());e=json.loads((P/(prefix+'response.json')).read_text())
 assert e==ex[i]['result'] and e['rc']==(0 if good else 1) and bool(e['stderr']) is (not good)
 assert r['passed'] is good and r['cleanup_rc']==0 and not r['cleanup_stderr'] and len(r['checks'])==(20 if good else 14)
 logs=[json.loads(l) for l in e['stdout'].splitlines()]
 assert logs[:-1]==r['checks'] and logs[-1]==dict(passed=good,checks=len(r['checks']),cleanup_rc=0)
 assert all(c['passed'] for c in r['checks'])
 for n,h in r['metadata']['source_sha256'].items():
  f=P/sources[n]
  if prefix and (P/prefix/n).is_file():f=P/prefix/n
  assert hashlib.sha256(f.read_bytes()).hexdigest()==h,(prefix,n)
 for flag in ('full_account_protection','global_coverage_qualified','pam_runtime_qualified','production_adapters_qualified','power_loss_tested'):assert r[flag] is False
 assert json.loads((P/(prefix+'cleanup.json')).read_text())['passed']
c={c['name']:c for c in json.loads((P/'result.json').read_text())['checks']}
m=c['mixed-batch-stops-active-payload-without-cold-ipc-or-false-job-record'];assert len(m['commands'])==len(m['requests'])==2 and m['cold_effect'] is None and all(row['phase']=='observed-drained' for row in m['effects'].values())
assert m['requests'][0].endswith('.timer') and m['requests'][1].endswith('-plain.service')
effects=json.loads((P/'effect-state.json').read_text());assert {json.loads(data)['unit']:json.loads(data) for n,data in effects.items() if n.startswith('.stop-')}==m['effects']
cold=c['cold-service-is-inactive-masked-and-cgroup-empty']['properties'];assert cold['MainPID']=={'type':'u','data':0} and cold['ActiveState']['data']=='inactive' and cold['Job']['data']==[0,'/']
active=c['real-activation-during-cold-authorization-refused-while-active']['active'];assert active['MainPID']['data']>0
history=c['completed-root-maintenance-cycle-is-not-an-invocation-history-proof'];assert history['history_guaranteed'] is False and history['after']['MainPID']['data']==0
assert c['pam-service-admission-denied-after-withdrawal-reference-still-refused']['unit']['ExecMainStatus']=='224'
outputs={'restore-check.py':'restored.json','restore-units.py':'units-restored-independent.json','restore-ownership.py':'ownership-restored-independent.json','restore-extra.py':'extra-restored.json'}
for prefix,index in (('restoration-before-reopen/',2),('',4)):
 r=json.loads((P/(prefix+'restoration-executions.json')).read_text());assert r['passed'] and r['source_sha256']==guest['restore-runner.py']
 assert json.loads(ex[index]['result']['stdout'])==dict(passed=True,readers=list(outputs))
 for n,file in outputs.items():
  e=r['readers'][n];row=json.loads((P/(prefix+file)).read_text());assert e['rc']==0 and not e['stderr'] and json.loads(e['stdout'])==row and row['passed'] and e['source_sha256']==guest[n]
assert json.loads((P/'restore-response.json').read_text())==ex[4]['result']
assert json.loads((P/'sources-response.json').read_text())==ex[5]['result'] and json.loads(ex[5]['result']['stdout'])==guest
assert json.loads((P/'poweroff-response.json').read_text())==ex[6]['result']
assert all(e['result']['rc']==0 and not e['result']['stderr'] for e in ex[1:])
failed=json.loads((P/'failed-source-export-1/execution.json').read_text());assert failed['result']['rc']==1 and 'verify-evidence.py' in failed['result']['stderr']
assert 'verify-evidence.py' in json.loads((P/'failed-source-export-1/source-map.json').read_text()) and 'verify-evidence.py' not in sources
old=(P/'failed-python-1/python-suite.txt').read_text();assert 'Ran 676 tests' in old and 'FAILED (errors=3)' in old
suite=(P/'python-suite.txt').read_text();assert 'Ran 676 tests' in suite and '\nOK\n' in suite
assert v['python_tests']==676 and v['new_python_tests']==18 and v['native_checks']==20 and v['qemu_exit_codes']==[0,0] and v['production_changed'] is False
print('PASS: 676 testes Python, 20 verificações VM, fontes/retornos/falhas e duas restaurações conferidos')
