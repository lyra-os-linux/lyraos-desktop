"""Static audit of extracted official RPMs; does not install or load a policy.

Usage: python3 parental-mac-audit.py /path/to/parental-mac
Input directory contains packages.json and package-name extraction directories.
"""
import bz2
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
packages = json.loads((root / 'packages.json').read_text())
verified = []
for record in packages:
    if 'signature' not in record:
        continue
    rpm = root / Path(record['location']).name
    assert hashlib.sha512(rpm.read_bytes()).hexdigest() == record['checksum']
    signature = subprocess.check_output(['rpm', '-Kv', str(rpm)], text=True)
    assert 'Signature' in signature and 'NOKEY' not in signature and 'NOT OK' not in signature
    verified.append({'name': record['name'], 'version': record['version'],
                     'sha512': record['checksum'], 'signature': signature})
assert {'selinux-policy', 'selinux-policy-targeted', 'pam', 'gdm',
        'patterns-base-selinux'} <= {r['name'] for r in verified}

policy = root / 'selinux-policy-targeted/etc/selinux/targeted'
modules = {}
for name in ('unprivuser', 'xguest'):
    data = (policy / 'active/modules/100' / name / 'cil').read_bytes()
    source = bz2.decompress(data).decode() if data.startswith(b'BZh') else data.decode()
    prefix = 'user' if name == 'unprivuser' else 'xguest'
    expected = [f'(typeattributeset {prefix}_usertype ({prefix}_t',
                f'(allow {prefix}_usertype bin_t (file ',
                f'(allow {prefix}_usertype shell_exec_t (file ']
    excerpts = []
    for needle in expected:
        found = [line for line in source.splitlines() if line.startswith(needle)]
        if needle.startswith('(allow '):
            found = [line for line in found if 'execute_no_trans' in line]
        assert found, needle
        excerpts.extend(found)
    assert all('execute_no_trans' in line for line in excerpts if line.startswith('(allow '))
    modules[name] = {'cil_sha256': hashlib.sha256(source.encode()).hexdigest(),
                     'execution_rules': excerpts}

base = next(r for r in packages if r['name'] == 'selinux-policy')
scripts = subprocess.check_output(['rpm', '-qp', '--scripts',
                                  str(root / Path(base['location']).name)], text=True)
assert 'pam-config -a --selinux' in scripts
assert 'SELINUX=enforcing' in scripts
result = {
    'date': '2026-09-21',
    'kind': 'static-official-package-audit',
    'packages': verified,
    'default_login_mapping': (policy / 'seusers').read_text(),
    'profiles': modules,
    'package_script_enables_pam_selinux': True,
    'package_script_default_mode': 'enforcing',
    'package_scripts_executed': False,
    'runtime_enforcement_qualified': False,
    'gnome_session_qualified': False,
    'application_allowlist_qualified': False,
    'conclusion': 'Upstream user_t/xguest_t permit generic system binaries and shells; mapping alone is not the approved application allowlist.'
}
print(json.dumps(result, indent=2))
