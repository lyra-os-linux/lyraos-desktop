"""Verify archived sources, functional results and complete GDM denial evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent

def load(name):
    return json.loads((BASE / name).read_text())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

provenance = load('provenance.json')
for kind in ('source_sha256', 'artifact_sha256'):
    for relative, expected in provenance[kind].items():
        assert digest(BASE / relative) == expected, (kind, relative)

results = {name: load(name + '-result.json') for name in ('writer', 'native-manager', 'two-account-pam', 'gdm')}
for name, count in {'writer': 52, 'native-manager': 30, 'two-account-pam': 18, 'gdm': 22}.items():
    result = results[name]
    assert result['passed'] and len(result['checks']) == count, name
    assert len({r['name'] for r in result['checks']}) == count, name
    assert all(row['passed'] for row in result['checks']), name

guard, writer = digest(BASE / 'pam-guard.c'), digest(BASE / 'writer.py')
assert results['writer']['source_sha256'] == writer
for name in ('native-manager', 'gdm'):
    sources = results[name]['source_sha256']
    assert sources['barrier-writer.py'] == writer
    assert sources['barrier-pam-guard.c'] == guard
    assert sources['barrier-' + ('native-manager.py' if name == 'native-manager' else 'gdm.py')] == digest(BASE / (name + '.py'))
pam = results['two-account-pam']
assert pam['store_source_sha256'] == writer and pam['guard_source_sha256'] == guard
assert pam['harness_source_sha256'] == digest(BASE / 'two-account-pam.py')
assert pam['probe_sha256'] == digest(BASE / '../parental-identity/pam-probe.py')
assert pam['holder_sha256'] == digest(BASE / '../parental-identity/pam-lease-holder.py')
assert all(results['native-manager']['restored'].values())
assert pam['fixtures_removed'] and pam['selinux_mode_restored']
assert all(row['passed'] for name in ('native-manager', 'two-account-pam', 'gdm') for row in results[name]['cleanup'])

by_name = {r['name']: r for r in pam['checks']}
for name in ('durable-barrier-denies-even-active-registry', 'new-a-admission-denied-while-a-lease-still-live'):
    assert by_name[name]['pam_open_rc'] != 0 and by_name[name]['exit_code'] == 70
for name in ('barrier-only-a-preserves-b-admission', 'b-new-enrollment-admitted-while-a-live-and-blocked'):
    assert by_name[name]['pam_open_rc'] == 0 and by_name[name]['exit_code'] == 0
assert by_name['a-session-survives-unrelated-b-transition']['passed']

spec = importlib.util.spec_from_file_location('evidence', BASE / '../parental-registry-gdm/evidence.py')
evidence = importlib.util.module_from_spec(spec); spec.loader.exec_module(evidence)
denials = [r for r in results['gdm']['checks'] if (r.get('rejection') or {}).get('worker_pid')]
assert len(denials) == 8
for row in denials:
    denial = row['rejection']
    verified = evidence.rejection(row['journal'], denial['manager_pid'], row['user'],
                                  missing_module=row['name'].startswith('missing-module'), service='gdm-password')
    assert verified == denial and row['processes'] == [] and row['post_rejection_observation_seconds'] == 2
assert all(results['gdm'][key] for key in ('vendor_preserved', 'official_worker_restored',
    'helper_label_restored', 'files_restored', 'passwords_restored', 'fixture_removed',
    'managers_stopped', 'permissive_restored', 'fixture_processes_gone'))
restored = load('restored.json')
assert restored['passed'] and all(v == '0' for v in restored['units'].values())
assert not restored['sessions'].strip() and not restored['uid_processes']
assert all(restored['absent_paths'].values()) and restored['policy_removed']
assert provenance['vm']['final_state'] == 'powered-off' and provenance['vm']['qemu_exit_code'] == 0
assert not restored['complete_kernel_audit'] and not provenance['production_changed']
print('PASS: 52 writer + 30 native manager + 18 two-account PAM + 22 GDM; sources and restoration verified')
