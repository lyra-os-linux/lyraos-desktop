"""Offline source/artifact integrity; does not rerun or qualify native producers."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
v=json.loads((P/'provenance.json').read_text())
for path,digest in v['sha256'].items():
    assert hashlib.sha256((P/path).read_bytes()).hexdigest()==digest,path
log=(P/'python-suite.txt').read_text()
assert 'Ran 530 tests' in log and '\nOK\n' in log
assert v['new_tests']==26 and v['python_tests']==530 and v['python_exit_code']==0
assert v['native_tests_run']==0 and not v['production_changed'] and not v['global_coverage_qualified']
print('PASS: fontes/artefatos conferidos; 530 testes Python registrados; cobertura global não qualificada')
