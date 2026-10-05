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
print('PASS: seven signed RPM checks and artifact identity match')
