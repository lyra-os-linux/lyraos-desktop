import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
v=json.loads((P/'provenance.json').read_text())
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
r=json.loads((P/'result.json').read_text());assert r['passed'] and r['error'] is None and len(r['checks'])==8 and all(x['passed'] for x in r['checks'])
external={'sources.py':'../parental-source-set/sources.py','namespace.py':'../parental-namespace-guard/namespace.py','coordinator.py':'../parental-coordinator/coordinator.py'}
for n,h in r['metadata']['source_sha256'].items():assert hashlib.sha256((P/external.get(n,n)).read_bytes()).hexdigest()==h,n
for f in ('full_account_protection','global_coverage_qualified','systemd_execution_binding_qualified','precedence_resolution_qualified','real_activation_or_revocation_tested'):assert r[f] is False
assert len(r['original_declarations'])==13 and sum(bool(x['systemd_unit']) for x in r['original_declarations'])==12
c={x['name']:x for x in r['checks']};assert c['installed-13-declarations-typed-with-local-passwd-and-group']['declarations']==r['original_declarations']
obs=c['declared-users-and-actual-systemd-fields-kept-separate']['observations'];assert len(obs)==12 and all(x['observed']['LoadState']=='loaded' for x in obs)
assert {x['name'] for x in obs if x['user_differs']}=={'org.freedesktop.PolicyKit1','org.freedesktop.timesync1'}
assert c['target-local-uid-declared-without-granting-producer-coverage']['identity']==dict(user='ordinaryuser',uid=1002,gid=1003)
x=json.loads((P/'restored.json').read_text());assert x['passed'] and all(x['absent'].values()) and all(x[k] for k in ('definitions_preserved','accounts_preserved','pam_preserved','alias_preserved','broker_preserved'))
execs=json.loads((P/'executions.json').read_text());assert len(execs)==3 and all(x['result']['rc']==0 and not x['result']['stderr'] for x in execs)
logs=[json.loads(x) for x in execs[0]['result']['stdout'].splitlines()];assert logs[:-1]==r['checks'] and logs[-1]==dict(passed=True,checks=8)
assert json.loads(execs[1]['result']['stdout'])==x
assert v['python_tests']==586 and v['new_python_tests']==16 and v['python_exit_code']==v['qemu_exit_code']==0
log=(P/'python-suite.txt').read_text();assert 'Ran 586 tests' in log and '\nOK\n' in log
print('PASS: 8 controles VM, 586 testes Python, declarações e restauração conferidas')
