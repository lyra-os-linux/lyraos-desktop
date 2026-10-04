import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
v=json.loads((P/'provenance.json').read_text())
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
r=json.loads((P/'result.json').read_text());assert r['passed'] and r['error'] is None and len(r['checks'])==8 and all(x['passed'] for x in r['checks'])
external={'namespace.py':'../parental-namespace-guard/namespace.py','binding.py':'../parental-namespace-dbus/binding.py','coordinator.py':'../parental-coordinator/coordinator.py'}
for n,h in r['metadata']['source_sha256'].items():assert hashlib.sha256((P/external.get(n,n)).read_bytes()).hexdigest()==h,n
for flag in ('full_account_protection','global_coverage_qualified','graph_semantics_qualified','real_revocation_tested'):assert r[flag] is False
c={x['name']:x for x in r['checks']};x=c['real-graph-files-roots-absences-and-alias-bound'];assert x['files']==21 and len(x['roots'])==5 and set(x['missing'])=={'/usr/lib/dbus-1/system-services','/usr/local/share/dbus-1/system-services','/etc/dbus-1/system-local.conf'}
for name in ('optional-override-creation-refuses-old-and-unclassified-new-plan','alternative-root-creation-refuses-before-marker-0','alternative-root-creation-refuses-before-marker-1'):assert not c[name]['effects']
assert c['vendor-policy-added-between-callbacks-prevents-second-marker']['effects']==['first-readonly-marker']
x=json.loads((P/'restored.json').read_text());assert x['passed'] and all(x['absent'].values()) and all(x[k] for k in ('configuration_preserved','accounts_and_pam_preserved','alias_preserved','broker_preserved'))
execs=json.loads((P/'executions.json').read_text());assert len(execs)==3 and all(x['result']['rc']==0 and not x['result']['stderr'] for x in execs)
logs=[json.loads(x) for x in execs[0]['result']['stdout'].splitlines()];assert logs[:-1]==r['checks'] and logs[-1]==dict(passed=True,checks=8)
assert json.loads(execs[1]['result']['stdout'])==x
assert v['python_tests']==570 and v['new_python_tests']==16 and v['python_exit_code']==v['qemu_exit_code']==0
log=(P/'python-suite.txt').read_text();assert 'Ran 570 tests' in log and '\nOK\n' in log
print('PASS: 8 controles VM, 570 testes Python, fontes e restauração conferidos')
