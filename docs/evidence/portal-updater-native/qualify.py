"""Check integrity and consistency of the collected native RPM evidence."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
rpm = json.loads((root / 'updater-rpm.json').read_text())
assert rpm['passed'] and rpm['public_matches_build_api'] and rpm['units_match_git']
assert rpm['release_key_unchanged']
digest = rpm['packages'][0]['sha256']
for name in ('main', 'lang', 'rollback'):
    directory = root / name
    receipt = json.loads((directory / 'verified.json').read_text())
    assert receipt['passed'] and receipt['rpm_sha256'] == digest
    assert receipt['automatic_offline_reboot'] and receipt['offline_qemu_exit_code'] == 0
    for filename, expected in receipt['hashes'].items():
        assert Path(filename).name == filename
        assert hashlib.sha256((directory / filename).read_bytes()).hexdigest() == expected, (name, filename)
    bits = json.loads((directory / 'published-029.json').read_text())
    for binary, expected in rpm['binaries_sha256'].items():
        assert bits['sha256']['/usr/libexec/' + binary] == expected
    if name == 'rollback':
        result = json.loads((directory / 'rollback-completed.json').read_text())
        assert result['complete_inventory_restored'] and result['replay_not_consumed']
        assert result['state']['last_completed_step'] == 'rollback-verified'
    else:
        result = json.loads((directory / (name + '-success.json')).read_text())
        assert result['trust']['last_manifest_sequence'] == 1
        assert len(result['added']) == len(result['removed']) == (1 if name == 'main' else 2)
    assert result['state']['state'] == 'Completed'
    assert result['state']['boot_verification'] == 'Passed'
packagekit = json.loads((root / 'packagekit/verified.json').read_text())
assert packagekit['passed'] and packagekit['worker_sha256'] == rpm['offline_worker_sha256']
for filename, expected in packagekit['phases'].items():
    assert Path(filename).name == filename
    assert hashlib.sha256((root / 'packagekit' / filename).read_bytes()).hexdigest() == expected
print('Published Updater RPM: main, translations, native rollback and PackageKit evidence passed')
