#!/usr/bin/python3
"""Verify archived signed RPM transaction evidence; does not replay the VM."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent
result=json.loads((root/'signed-result.json').read_text())
response=json.loads((root/'signed-native-response.json').read_text())
publication=json.loads((root/'publication.json').read_text())
assert response['rc']==0 and result['passed'] is True
assert json.loads(response['stdout'].splitlines()[-1])==result
assert len(result['checks'])==7 and all(c['passed'] is True for c in result['checks'])
assert result['disk_is_disposable_overlay'] is True and result['host_changed'] is False
assert result['fixture_rpms']['lyra-release.rpm']==publication['staging_rpm_sha256']
assert (root/'staging-rpm-sha256.txt').read_text().split()[0]==publication['staging_rpm_sha256']
assert publication['signing_fingerprint']=='399218A6E088C4053F4533BE58097F767EDCA82E'
for name,digest in publication['evidence_sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
print('PASS: seven signed RPM checks and artifact identity match')

if publication.get('host_installed'):
    host=json.loads((root/'host-install.json').read_text())
    assert host['passed'] is True and host['install']['rc']==0 and host['rpm_verify']['rc']==0
    assert host['after']['nevra']==publication['host_nevra']
    assert host['release_rpm_sha256']==publication['release_api_rpm_sha256']
    assert host['delivery']=='obs_api' and host['public_release_verified'] is False
    for key in ('vendor_sha256','product_sha256'):assert host['before'][key]==host['after'][key]
    assert host['after']['identity']['PRETTY_NAME']=='Lyra OS 1.1'
    assert host['after']['identity']['LOGO']=='distributor-logo-lyra'
    print('PASS: host installed accepted release RPM; vendor and Updater marker preserved')

if publication.get('release_publication')=='verified':
    public=json.loads((root/'release-public-verification.json').read_text())
    assert public['signing_fingerprint']==publication['signing_fingerprint']
    assert public['metadata_signature']=='verified'
    assert public['url']=='https://download.opensuse.org/repositories/home:/rodrigosbrito:/lyra/openSUSE_Leap_16.1'
    assert len(public['packages'])==1 and public['packages'][0]['signature']=='verified'
    assert public['packages'][0]['sha256']==publication['release_api_rpm_sha256']
    assert public['packages'][0]['filename']==publication['staging_rpm']
    gate=(root/'release-check-published.txt').read_text()
    assert gate.count('enabled targets published')==3 and 'ERROR' not in gate
    print('PASS: public release signatures and whole-channel gate; RPM matches installed artifact')
