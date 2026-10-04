"""Check archived source/transport/results without rerunning VM mutations."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
v=json.loads((P/'provenance.json').read_text())
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
ex=json.loads((P/'executions.json').read_text());assert len(ex)==5
pre=json.loads((P/'failed-preflight-1/response.json').read_text())
assert pre==ex[0]['result'] and pre['rc']==1 and not pre['stdout'] and 'dbus-adapter.py' in pre['stderr']
for i,prefix,good in ((1,'failed-native-1/',False),(2,'',True)):
 r=json.loads((P/(prefix+'result.json')).read_text());e=ex[i]['result']
 assert r['passed'] is good and r['cleanup_rc']==0 and not r['cleanup_stderr']
 assert e['rc']==(0 if good else 1) and bool(e['stderr']) is (not good)
 assert len(r['checks'])==(19 if good else 11) and all(c['passed'] for c in r['checks'])
 logs=[json.loads(l) for l in e['stdout'].splitlines()]
 assert logs[:-1]==r['checks'] and logs[-1]==dict(passed=good,checks=len(r['checks']),cleanup_rc=0)
 for n,h in r['metadata']['source_sha256'].items():
  source=P/v['external_sources'].get(n,n)
  if prefix and (P/prefix/n).is_file():source=P/prefix/n
  assert hashlib.sha256(source.read_bytes()).hexdigest()==h,(prefix,n)
 for flag in ('full_account_protection','global_coverage_qualified','shared_privileged_services_qualified','production_adapters_qualified','monotonic_revision_qualified','power_loss_tested'):assert r[flag] is False
 assert json.loads((P/(prefix+'cleanup.json')).read_text())['passed']
r=json.loads((P/'result.json').read_text());assert r['error'] is None
checks={c['name']:c for c in r['checks']}
c=checks['actual-unread-reply-disconnect-keeps-intent-uncertain-and-blocked']
assert len(c['members'])==2 and all(p['uids']==[1002]*4 for p in c['members'])
p=c['pending'];assert p['active']=={'type':'s','data':'deactivating'} and p['job']['type']=='(uo)' and p['job']['data'][0]>0 and p['populated']==1 and p['drained'] is False
assert p['sender']['rc']==0 and not p['sender']['stderr'] and p['sender']['stdout'].strip()=='request-flushed-reply-unread-connection-closed'
requests=c['requests'];assert len(requests)==2 and requests[0].endswith('.timer')
assert checks['denied-recovery-and-repeated-stop-do-not-resubmit']['requests']==requests
assert checks['reconstructed-controller-observes-parent-and-child-drained-without-resubmission']['requests']==requests
normal=checks['normal-job-replies-and-concurrent-masked-start-refusals'];assert len(normal['requests'])==3 and normal['requests'][:2]==requests and len(normal['starts'])==9
assert all(s['rc']!=0 and 'masked' in s['stderr'].lower() for s in normal['starts'])
rows=normal['rows'];assert len(rows)==3 and all(r['phase']=='observed-drained' and r['revision']==3 for r in rows.values())
assert rows[requests[1]]['job'] is None and all(r['job'].startswith('/org/freedesktop/systemd1/job/') for n,r in rows.items() if n!=requests[1])
effects=json.loads((P/'effect-state.json').read_text());decoded={json.loads(data)['unit']:json.loads(data) for n,data in effects.items() if n.startswith('.stop-')};assert decoded==rows
failed=json.loads((P/'failed-native-1/effect-state.json').read_text());assert len(failed)==2
assert next(json.loads(data) for n,data in failed.items() if n.startswith('.stop-'))['phase']=='accepted'
assert checks['target-manager-remains-denied-and-peer-admitted']['unit']['ExecMainStatus']=='224'
rest=json.loads((P/'restoration-executions.json').read_text());assert rest['passed']
assert rest['source_sha256']==hashlib.sha256((P/'restore-runner.py').read_bytes()).hexdigest()
outputs={'restore-check.py':'restored.json','restore-units.py':'units-restored-independent.json','restore-ownership.py':'ownership-restored-independent.json','restore-extra.py':'extra-restored.json'}
for n,file in outputs.items():
 e=rest['readers'][n];row=json.loads((P/file).read_text());assert row['passed'] and e['rc']==0 and not e['stderr'] and json.loads(e['stdout'])==row and e['source_sha256']==hashlib.sha256((P/n).read_bytes()).hexdigest()
assert json.loads(ex[3]['result']['stdout'])==dict(passed=True,readers=list(outputs))
assert all(e['result']['rc']==0 and not e['result']['stderr'] for e in ex[2:])
assert v['python_tests']==658 and v['new_python_tests']==20 and v['native_checks']==19 and v['python_exit_code']==v['qemu_exit_code']==0 and v['production_changed'] is False
suite=(P/'python-suite.txt').read_text();assert 'Ran 658 tests' in suite and '\nOK\n' in suite
print('PASS: 658 testes Python, 19 verificações VM, duas falhas preservadas, restauração independente e fontes conferidas')
