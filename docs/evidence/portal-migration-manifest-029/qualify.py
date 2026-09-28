"""Verify the signed testing document and retained sequence-2 VM evidence."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parent
def read(name):
    return json.loads((root / name).read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest = root / 'releases-v1.json'
signature = root / 'releases-v1.json.asc'
document = read('releases-v1.json')
previous = json.loads((root.parent / 'portal-migration-manifest/releases-v1.json').read_text())
assert manifest.read_bytes() == (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode()
assert {key for key in document if document[key] != previous[key]} == {'sequence', 'minimum_updater_version'}
assert document['sequence'] == 2 and document['minimum_updater_version'] == '0.2.9'
assert document['status'] == 'testing' and document['source'] == document['target']
assert all('16.1' in repo['base_url'] for repo in document['repositories'])
receipt = read('signature-verified.json')
assert sha(manifest) == receipt['manifest_sha256'] == 'da0e5194f24d78fdbcfd9174f9dc79dce8d1c832d54053c2917ce5f4e1196218'
assert sha(signature) == receipt['signature_sha256']
key = root / 'release-signing-key.gpg'
assert sha(key) == 'f8bd374b5c218881cb731a706144d10ac5cb5b4e65f1d711f153b836788307fc'
with tempfile.TemporaryDirectory(prefix='lyra-evidence-gpg-') as directory:
    result = subprocess.run(['gpgv', '--homedir', directory, '--status-fd', '1', '--keyring', str(key), str(signature), str(manifest)], capture_output=True, text=True, check=True)
    assert '[GNUPG:] VALIDSIG 01B63EEDBE6B079126A0116EFA7353A131ECEFEB ' in result.stdout
audit = read('policy-audit.json')
assert audit['passed'] and audit['manifest_sha256'] == sha(manifest)
assert audit['rejected_versions'] == ['0.2.5', '0.2.6', '0.2.7', '0.2.8']
assert audit['audit_source_sha256'] == sha(root / 'audit.rs')
native = read('native/verified.json')
assert native['passed'] and native['sequence'] == 2 and native['minimum_updater'] == '0.2.9'
assert native['endpoint']['manifest_sha256'] == sha(manifest)
assert native['endpoint']['signature_sha256'] == sha(signature)
assert native['native_polkit'] and native['native_uefi_grub'] and native['automatic_offline_reboot']
assert native['offline_qemu_exit_code'] == 0
for name, expected in native['hashes'].items():
    assert Path(name).name == name
    assert sha(root / 'native' / name) == expected, name
success = read('native/lang-success.json')
assert success['state']['state'] == 'Completed' and success['state']['boot_verification'] == 'Passed'
assert success['trust']['last_manifest_sequence'] == 2
assert len(success['added']) == len(success['removed']) == 2
replay = read('native/replay-sequence2.json')
assert replay['passed'] and replay['response']['error_code'] == 'MIGRATION_ALREADY_APPLIED'
print('Official sequence-2 signature, minimum 0.2.9, native lifecycle and replay evidence passed')
