from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];P=Path(__file__).resolve().parent
v=json.loads((P/'provenance.json').read_text())
for n,h in v['sha256'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
r=json.loads((P/'result.json').read_text());e=json.loads((P/'native-response.json').read_text())
assert r['passed'] and len(r['checks'])==7 and e['rc']==0 and not e['stderr']
rows=[json.loads(line) for line in e['stdout'].splitlines()];assert rows[:-1]==r['checks'] and rows[-1]==r
assert all(c['passed'] for c in r['checks'])
c={c['name']:c for c in r['checks']};identity=c['base-update-reapplies-branding-and-preserves-image-metadata']['identity']
assert identity['PRETTY_NAME']=='Lyra OS 1.1' and identity['BUILD_ID']=='lyra-trigger-rehearsal' and identity['IMAGE_VERSION']=='alpha8-test'
assert c['removal-restores-original-link']['identity']['ID']=='opensuse-leap'
for i in (1,2,3):assert json.loads((P/f'failed-attempt-{i}/native-response.json').read_text())['rc']==1
assert v['python_tests']==10 and v['vm_checks']==7 and v['qemu_exit_code']==0 and not v['obs_published'] and not v['host_rpm_installed']
assert 'Ran 10 tests' in (P/'python-tests.txt').read_text() and '\nOK\n' in (P/'python-tests.txt').read_text()
print('PASS: 10 testes, 7 verificações RPM reais, fontes e três falhas preservadas')
