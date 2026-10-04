import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
v=json.loads((P/'provenance.json').read_text())
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
external={'namespace.py':'../parental-namespace-guard/namespace.py','catalog.py':'../parental-service-catalog/catalog.py','coordinator.py':'../parental-coordinator/coordinator.py'}
execs=json.loads((P/'executions.json').read_text());assert len(execs)==5
for index,f in enumerate(('attempt-1-result.json','attempt-2-result.json','result.json')):
 r=json.loads((P/f).read_text());assert r['passed'] is (index==2)
 assert execs[index]['result']['rc']==(0 if index==2 else 1)
 assert bool(execs[index]['result']['stderr']) is (index!=2)
 for n,h in r['metadata']['source_sha256'].items():
  path=external.get(n,n)
  if n=='native.py' and index<2:path=f'attempt-{index+1}-native.py'
  assert hashlib.sha256((P/path).read_bytes()).hexdigest()==h,(f,n)
 logs=[json.loads(s) for s in execs[index]['result']['stdout'].splitlines()]
 assert logs[:-1]==r['checks'] and logs[-1]==dict(passed=index==2,checks=len(r['checks']))
 assert len(r['checks'])==(0,10,15)[index]
 for flag in ('full_account_protection','global_coverage_qualified','running_credentials_qualified','real_activation_or_revocation_tested','storage_fault_injection_real'):assert r[flag] is False
r=json.loads((P/'result.json').read_text());assert r['error'] is None and len(r['references'])==9 and all(c['passed'] for c in r['checks'])
assert {u['name'] for u in r['unsupported']}=={'org.freedesktop.PolicyKit1','org.freedesktop.login1','org.freedesktop.timesync1'}
c={x['name']:x for x in r['checks']};d={x['name']:x['properties'] for x in c['unsupported-configurations-remain-refused']['diagnostics']}
assert d['org.freedesktop.PolicyKit1']['Type']['data']==d['org.freedesktop.login1']['Type']['data']=='notify-reload'
assert d['org.freedesktop.timesync1']['ExecStartEx']['data'][0][2]==['ambient']
x=json.loads((P/'restored.json').read_text());assert x['passed'] and x['manager_cache_rollback_claimed'] is False
assert all(x[k] for k in ('references_preserved','accounts_and_pam_preserved','declarations_preserved','broker_preserved','unused_lock_absent'))
assert x['source_sha256']==hashlib.sha256((P/'restore.py').read_bytes()).hexdigest()
assert x['broker_pid']==r['metadata']['broker_pid']
assert json.loads(execs[3]['result']['stdout'])==x
assert all(e['result']['rc']==0 and e['result']['stderr']=='' for e in execs[2:])
assert v['python_tests']==602 and v['new_python_tests']==16 and v['native_checks']==15 and v['failed_native_attempts']==2
assert v['python_exit_code']==v['qemu_exit_code']==0
log=(P/'python-suite.txt').read_text();assert 'Ran 602 tests' in log and '\nOK\n' in log
print('PASS: 15 controles VM, 602 testes Python, nove referências, três recusas e duas tentativas falhas preservadas')
