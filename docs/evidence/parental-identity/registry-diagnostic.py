"""VM-only proof for PAM validation of a root-owned identity registry."""
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import secrets
import subprocess

assert os.geteuid() == 0
assert 'lyra.parental-selinux-test=1' in Path('/proc/cmdline').read_text().split()
assert 'lyra.parental-identity-test=1' in Path('/proc/cmdline').read_text().split()
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'

USER = 'identitytest'
GROUP = 'identitytest'
MODULE = Path('/usr/lib64/security/pam_lyra_identity_registry_fixture.so')
PAM = Path('/etc/pam.d/lyra-identity-probe')
PAM_TMP = PAM.with_suffix('.new')
STATE_DIR = Path('/var/lib/lyra-parental-test')
STATE_FILE = STATE_DIR / 'identity-registry'
PROBE = '/opt/lyra-parental-probe/probe'
PAM_PROBE = '/root/identity-pam-probe.py'
SOURCE = '/root/identity-pam-registry-guard.c'
CONTEXT = 'lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
records = []
result = {'kind': 'pam-root-owned-generation-registry-proof',
          'full_account_protection': False, 'checks': records}


def run(args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check,
                          timeout=90)


def identity():
    p = pwd.getpwnam(USER)
    g = grp.getgrgid(p.pw_gid)
    return {'user': p.pw_name, 'uid': p.pw_uid, 'gid': p.pw_gid,
            'group': g.gr_name}


def registry(rows):
    content = 'LYRA-ID-REGISTRY-V1\n' + ''.join(
        f"{state}|{row['user']}|{row['uid']}|{row['gid']}|{row['group']}|{generation}\n"
        for state, row, generation in rows)
    tmp = STATE_DIR / 'identity-registry.new'
    tmp.write_text(content)
    tmp.chmod(0o600)
    run(['restorecon', str(tmp)])
    tmp.replace(STATE_FILE)
    run(['restorecon', str(STATE_FILE)])


def install_pam(row, generation):
    prefix = ('session required pam_selinux.so close\n'
              'session required pam_selinux.so open nottys\n')
    selector = (f"session [success=1 default=ignore] pam_succeed_if.so quiet "
                f"user != {row['user']} uid ne {row['uid']} gid ne {row['gid']}\n")
    binding = (f"session required pam_lyra_identity_registry_fixture.so "
               f"account=active|{row['user']}|{row['uid']}|{row['gid']}|{row['group']}|{generation}\n")
    PAM_TMP.write_text(prefix + selector + binding)
    PAM_TMP.chmod(0o644)
    run(['restorecon', str(PAM_TMP)])
    PAM_TMP.replace(PAM)
    run(['restorecon', str(PAM)])


def test(name, expected_open, expected_context=None, user=USER, program=None):
    p = run(['python3', PAM_PROBE, user, *(program or [PROBE])], check=False)
    first = json.loads(p.stdout.splitlines()[0])
    row = {'name': name, 'exit_code': p.returncode, 'pam_open_rc': first['pam_open_rc'],
           'selected_context': first['selected_context'], 'stderr': p.stderr}
    records.append(row)
    print(json.dumps(row), flush=True)
    if expected_open:
        assert p.returncode == 0 and first['pam_open_rc'] == 0, row
        if expected_context is not None:
            assert first['selected_context'] == expected_context == CONTEXT, row
        elif program:
            assert 'PAYLOAD_EXECUTED' in p.stdout, row
    else:
        assert p.returncode == 70 and first['pam_open_rc'] != 0, row
    row['passed'] = True


assert not MODULE.exists() and not PAM.exists() and not PAM_TMP.exists()
assert not STATE_DIR.exists()
assert USER not in {p.pw_name for p in pwd.getpwall()}
assert GROUP not in {g.gr_name for g in grp.getgrall()}
assert Path(PAM_PROBE).is_file() and Path(PROBE).is_file()
initial_enforce = run(['getenforce']).stdout.strip()
assert initial_enforce in ('Enforcing', 'Permissive')
uid = next(i for i in range(24000, 25000) if i not in {p.pw_uid for p in pwd.getpwall()})
gid = next(i for i in range(25000, 26000) if i not in {g.gr_gid for g in grp.getgrall()})
generation_a = secrets.token_hex(16)
generation_b = secrets.token_hex(16)
assert generation_a != generation_b
module_created = group_created = user_created = mapping_created = pam_created = False
state_created = False

try:
    run(['gcc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror', '-O2', SOURCE,
         '-o', str(MODULE), '-lpam', '-lselinux'])
    MODULE.chmod(0o755)
    run(['restorecon', str(MODULE)])
    module_created = True
    run(['groupadd', '-g', str(gid), GROUP]); group_created = True
    run(['useradd', '-M', '-u', str(uid), '-g', str(gid), '-s', '/bin/bash', USER]); user_created = True
    run(['semanage', 'login', '-a', '-s', 'lyra_parental_u', '-r', 's0', USER]); mapping_created = True
    row_a = identity()
    STATE_DIR.mkdir(mode=0o700)
    run(['restorecon', str(STATE_DIR)])
    state_created = True
    registry([('active', row_a, generation_a)])
    install_pam(row_a, generation_a); pam_created = True
    run(['setenforce', '1'])
    result['module_sha256'] = hashlib.sha256(MODULE.read_bytes()).hexdigest()
    result['source_sha256'] = hashlib.sha256(Path(SOURCE).read_bytes()).hexdigest()
    result['runner_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['generation_a'] = generation_a
    result['generation_b'] = generation_b
    test('active-generation-admitted', True, CONTEXT)
    test('ordinary-account-preserved', True, user='ordinaryuser',
         program=['/usr/bin/python3', '-c', 'print("PAYLOAD_EXECUTED")'])

    # The trusted lifecycle transition persists A's tombstone before account removal.
    registry([('tombstone', row_a, generation_a)])
    run(['semanage', 'login', '-d', USER]); mapping_created = False
    run(['userdel', USER]); user_created = False
    if GROUP in {g.gr_name for g in grp.getgrall()}:
        run(['groupdel', GROUP])
    group_created = False
    run(['groupadd', '-g', str(gid), GROUP]); group_created = True
    run(['useradd', '-M', '-u', str(uid), '-g', str(gid), '-s', '/bin/bash', USER]); user_created = True
    run(['semanage', 'login', '-a', '-s', 'lyra_parental_u', '-r', 's0', USER]); mapping_created = True
    row_b = identity()
    assert row_b == row_a
    test('same-tuple-recreated-with-tombstone-denied', False)

    # An explicit new enrollment creates B; the stale A configuration remains rejected.
    registry([('tombstone', row_a, generation_a), ('active', row_b, generation_b)])
    install_pam(row_b, generation_b)
    test('explicit-new-generation-admitted', True, CONTEXT)
    registry([('tombstone', row_a, generation_a), ('blocked', row_b, generation_b)])
    test('blocked-generation-denied', False)
    registry([('tombstone', row_a, generation_a), ('active', row_b, generation_b)])
    test('active-generation-restored', True, CONTEXT)
    install_pam(row_a, generation_a)
    test('stale-generation-config-denied', False)

    # Matching accounts fail closed for absent, malformed, or writable state.
    install_pam(row_b, generation_b)
    saved = STATE_FILE.read_bytes()
    STATE_FILE.unlink()
    test('missing-registry-denied', False)
    STATE_FILE.write_bytes(b'not a valid registry\n')
    STATE_FILE.chmod(0o600)
    run(['restorecon', str(STATE_FILE)])
    test('malformed-registry-denied', False)
    STATE_FILE.write_bytes(saved)
    STATE_FILE.chmod(0o666)
    run(['restorecon', str(STATE_FILE)])
    test('group-world-writable-registry-denied', False)
    STATE_FILE.write_bytes(saved)
    STATE_FILE.chmod(0o644)
    run(['restorecon', str(STATE_FILE)])
    test('group-world-readable-registry-denied', False)
    STATE_FILE.write_bytes(saved)
    STATE_FILE.chmod(0o600)
    run(['restorecon', str(STATE_FILE)])
    test('recovery-valid-registry-admitted', True, CONTEXT)
    result['passed'] = True
finally:
    cleanup = []

    def clean(name, action):
        try:
            action()
            cleanup.append({'name': name, 'passed': True})
        except Exception as error:
            cleanup.append({'name': name, 'passed': False, 'error': str(error)})

    clean('restore-selinux-mode', lambda: run(['setenforce', '1' if initial_enforce == 'Enforcing' else '0']))
    if mapping_created:
        clean('delete-login-mapping', lambda: run(['semanage', 'login', '-d', USER]))
    if user_created:
        clean('delete-fixture-user', lambda: run(['userdel', USER]))
    if group_created and GROUP in {g.gr_name for g in grp.getgrall()}:
        clean('delete-fixture-group', lambda: run(['groupdel', GROUP]))
    if pam_created:
        clean('remove-pam-stack', lambda: PAM.unlink(missing_ok=True))
    if module_created:
        clean('remove-pam-module', lambda: MODULE.unlink(missing_ok=True))
    if state_created:
        clean('remove-test-registry', lambda: [p.unlink(missing_ok=True) for p in STATE_DIR.iterdir()] and STATE_DIR.rmdir())
    result['cleanup'] = cleanup
    result['fixtures_removed'] = (not MODULE.exists() and not PAM.exists() and not STATE_DIR.exists() and
                                  USER not in {p.pw_name for p in pwd.getpwall()} and
                                  GROUP not in {g.gr_name for g in grp.getgrall()})
    result['selinux_mode_restored'] = run(['getenforce']).stdout.strip() == initial_enforce
    result['passed'] = bool(result.get('passed') and all(item['passed'] for item in cleanup) and
                            result['fixtures_removed'] and result['selinux_mode_restored'])
    Path('/root/identity-registry-result.json').write_text(json.dumps(result, indent=2) + '\n')

assert result['passed'], result
