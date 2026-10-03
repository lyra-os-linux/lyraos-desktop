import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
v=json.loads((P/'provenance.json').read_text())
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
r=json.loads((P/'result.json').read_text());assert r['passed'] and r['error'] is None and len(r['checks'])==12 and all(x['passed'] for x in r['checks']) and r['cleanup']['passed']
external={'namespace.py':'../parental-namespace-guard/namespace.py','coordinator.py':'../parental-coordinator/coordinator.py'}
for n,h in r['metadata']['source_sha256'].items():assert hashlib.sha256((P/external.get(n,n)).read_bytes()).hexdigest()==h,n
assert len(r['files'])==20 and len(r['edges'])==6 and len(r['includedirs']['/usr/share/dbus-1/system.d'])==17
assert any(x['path']=='/etc/dbus-1/system-local.conf' and x['optional'] for x in r['missing'])
assert [x['loaded'] for x in r['directory_probes']]==[True,True,False,False,True]
for flag in ('full_account_protection','global_source_coverage_qualified','configuration_semantics_qualified','loaded_configuration_identity_qualified'):assert r[flag] is False
assert r['cleanup']['names_preserved'] and r['cleanup']['broker_pid']==r['metadata']['broker_pid']
x=json.loads((P/'restored.json').read_text());assert x['passed'] and all(x['absent'].values()) and x['unknown_loaded_absent'] and x['broker_preserved']
execs=json.loads((P/'executions.json').read_text());assert len(execs)==3 and all(x['result']['rc']==0 and not x['result']['stderr'] for x in execs)
logs=[json.loads(x) for x in execs[0]['result']['stdout'].splitlines()];assert logs[:-1]==r['checks'] and logs[-1]==dict(passed=True,checks=12)
assert json.loads(execs[1]['result']['stdout'])==x
assert v['python_tests']==554 and v['new_python_tests']==16 and v['python_exit_code']==v['qemu_exit_code']==0
log=(P/'python-suite.txt').read_text();assert 'Ran 554 tests' in log and '\nOK\n' in log
print('PASS: 12 controles VM, 554 testes Python e fontes/restauração conferidos')
