"""Destructive fixture tests: root, unique disposable disk and boot marker only.

Requires the pre-existing parental SELinux fixture and the three source files
copied to /root/identity-{pam-guard.c,bindings.py,pam-probe.py}. No real PAM
entry point is modified. This is session admission, not login authentication.
"""
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import grp
import signal
import subprocess

assert os.geteuid() == 0
assert 'lyra.parental-identity-test=1' in Path('/proc/cmdline').read_text().split()
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'
signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(143)))
spec = importlib.util.spec_from_file_location('bindings', '/root/identity-bindings.py')
bindings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bindings)
MODULE = Path('/usr/lib64/security/pam_lyra_identity_fixture.so')
PAM = Path('/etc/pam.d/lyra-identity-probe')
CONTEXT = 'lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
PROBE = '/opt/lyra-parental-probe/probe'
PREFIX = 'session required pam_selinux.so close\nsession required pam_selinux.so open nottys\n'
records, cleanup = [], []
result = {'kind': 'experimental-local-account-pam-session-bindings',
          'full_account_protection': False, 'checks': records, 'cleanup': cleanup}


def cmd(args):
    return subprocess.run(args, capture_output=True, text=True, check=True, timeout=120).stdout


def account(name):
    p = pwd.getpwnam(name)
    return dict(user=name, uid=p.pw_uid, gid=p.pw_gid, group=grp.getgrgid(p.pw_gid).gr_name)


def test(name, user='identitytest', expected=70, approved=False, pam_rc=None):
    program = [PROBE] if approved else ['/usr/bin/python3', '-c', 'print("PAYLOAD_EXECUTED")']
    p = subprocess.run(['python3', '/root/identity-pam-probe.py', user, *program],
                       capture_output=True, text=True, timeout=30)
    row = dict(name=name, user=user, expected=expected, rc=p.returncode,
               stdout=p.stdout, stderr=p.stderr)
    records.append(row)
    print(json.dumps(row), flush=True)
    assert p.returncode == expected, row
    session = json.loads(p.stdout.splitlines()[0])
    if expected == 70:
        assert session['pam_open_rc'] != 0, row
    else:
        assert session['pam_open_rc'] == 0, row
    if pam_rc is not None:
        assert session['pam_open_rc'] == pam_rc, row
    if expected:
        assert 'PAYLOAD_EXECUTED' not in p.stdout, row
    elif approved:
        assert session['selected_context'] == CONTEXT, row
        assert f'uid={pwd.getpwnam(user).pw_uid} context={CONTEXT}' in p.stdout, row
    else:
        assert 'PAYLOAD_EXECUTED' in p.stdout, row
    if expected == 126:
        assert '"exec_errno": 13' in p.stdout, row
    row['passed'] = True


def install(fragment):
    # Single replacement keeps the selector and guard roster coherent.
    temporary = PAM.with_suffix('.new')
    temporary.write_text(PREFIX + fragment)
    temporary.chmod(0o644)
    cmd(['restorecon', str(temporary)])
    temporary.replace(PAM)
    cmd(['restorecon', str(PAM)])


@contextlib.contextmanager
def change(command, restore):
    cmd(command)
    try:
        yield
    finally:
        cmd(restore)


assert not MODULE.exists() and not PAM.exists() and not PAM.with_suffix('.new').exists()
assert 'identitytest' not in {p.pw_name for p in pwd.getpwall()}
assert 'identityrenamed' not in {p.pw_name for p in pwd.getpwall()}
assert not {'identitytest', 'identitygroupchanged'} & {g.gr_name for g in grp.getgrall()}
initial_enforce = cmd(['getenforce']).strip()
assert initial_enforce in ('Enforcing', 'Permissive')
assert 'lyra_parental_probe_t' not in cmd(['semanage', 'permissive', '-l']).split()
uid = next(i for i in range(21000, 22000) if i not in {p.pw_uid for p in pwd.getpwall()})
other_uid = next(i for i in range(uid + 1, 23000) if i not in {p.pw_uid for p in pwd.getpwall()})
gid = next(i for i in range(23000, 24000) if i not in {g.gr_gid for g in grp.getgrall()})
before_accounts = {name: account(name) for name in ('parentaltest', 'ordinaryuser')}
group_created = user_created = mapping_created = False
try:
    cmd(['gcc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror', '-O2',
         '/root/identity-pam-guard.c', '-o', str(MODULE), '-lpam', '-lselinux'])
    MODULE.chmod(0o755)
    cmd(['restorecon', str(MODULE)])
    result['module_sha256'] = hashlib.sha256(MODULE.read_bytes()).hexdigest()
    cmd(['groupadd', '-g', str(gid), 'identitytest']); group_created = True
    cmd(['useradd', '-M', '-u', str(uid), '-g', str(gid), '-s', '/bin/bash', 'identitytest']); user_created = True
    cmd(['semanage', 'login', '-a', '-s', 'lyra_parental_u', '-r', 's0', 'identitytest']); mapping_created = True
    roster = [account('parentaltest'), account('identitytest')]
    result['bindings'] = roster
    fragment = bindings.render(roster)
    result['pam_configuration'] = PREFIX + fragment
    install(fragment)
    cmd(['setenforce', '1'])
    for user in ('parentaltest', 'identitytest'):
        test('approved-' + user, user, 0, True)
        test('python-denied-' + user, user, 126)
    test('ordinary-healthy', 'ordinaryuser', 0)

    disabled = MODULE.with_suffix('.so.disabled')
    assert not disabled.exists()
    MODULE.rename(disabled)
    try:
        test('missing-module-first', 'parentaltest')
        test('missing-module-second')
        test('ordinary-missing-module', 'ordinaryuser', 0)
    finally:
        disabled.rename(MODULE)

    with change(['setenforce', '0'], ['setenforce', '1']):
        test('global-permissive')
        test('ordinary-global-permissive', 'ordinaryuser', 0)
    with change(['semanage', 'permissive', '-a', 'lyra_parental_probe_t'],
                ['semanage', 'permissive', '-d', 'lyra_parental_probe_t']):
        test('domain-permissive')
        test('ordinary-domain-permissive', 'ordinaryuser', 0)
    with change(['semanage', 'login', '-d', 'identitytest'],
                ['semanage', 'login', '-a', '-s', 'lyra_parental_u', '-r', 's0', 'identitytest']):
        test('missing-selinux-mapping')
        test('ordinary-missing-mapping', 'ordinaryuser', 0)

    with change(['groupmod', '-n', 'identitygroupchanged', 'identitytest'],
                ['groupmod', '-n', 'identitytest', 'identitygroupchanged']):
        test('private-group-renamed')
        test('ordinary-group-renamed', 'ordinaryuser', 0)
    with change(['usermod', '-l', 'identityrenamed', 'identitytest'],
                ['usermod', '-l', 'identitytest', 'identityrenamed']):
        test('account-renamed', 'identityrenamed')
        test('ordinary-account-renamed', 'ordinaryuser', 0)
    with change(['usermod', '-u', str(other_uid), 'identitytest'],
                ['usermod', '-u', str(uid), 'identitytest']):
        test('uid-drift')
        test('ordinary-uid-drift', 'ordinaryuser', 0)
    with change(['usermod', '-g', str(before_accounts['ordinaryuser']['gid']), 'identitytest'],
                ['usermod', '-g', str(gid), 'identitytest']):
        test('primary-gid-drift')
        test('ordinary-gid-drift', 'ordinaryuser', 0)
    with change(['usermod', '-g', str(roster[0]['gid']), 'identitytest'],
                ['usermod', '-g', str(gid), 'identitytest']):
        test('two-bindings-match-denied')
        test('other-bound-account-preserved', 'parentaltest', 0, True)
        test('ordinary-two-bindings-match', 'ordinaryuser', 0)

    selector = fragment.splitlines()[0] + '\n'
    valid = f'account=identitytest:{uid}:{gid}:identitytest'
    invalid = {
        'empty': '', 'unknown-option': 'debug', 'empty-field': f'account=identitytest::{gid}:identitytest',
        'extra-field': valid + ':extra', 'root-id': f'account=identitytest:0:{gid}:identitytest',
        'negative-id': f'account=identitytest:-1:{gid}:identitytest',
        'leading-zero': f'account=identitytest:0{uid}:{gid}:identitytest',
        'reserved-id': f'account=identitytest:4294967295:{gid}:identitytest',
        'overflow': f'account=identitytest:99999999999999999999999999999:{gid}:identitytest',
        'bad-name': f'account=identity.test:{uid}:{gid}:identitytest',
        'duplicate': valid + ' ' + valid,
        'duplicate-uid': valid + f' account=another:{uid}:{gid+1}:another',
        'duplicate-gid': valid + f' account=another:{other_uid}:{gid}:another',
        'duplicate-group': valid + f' account=another:{other_uid}:{gid+1}:identitytest',
        'too-long': 'account=' + 'x'*256,
        'too-many': ' '.join([valid]*33),
    }
    try:
        for name, args in invalid.items():
            install(selector + 'session required pam_lyra_identity_fixture.so ' + args + '\n')
            test('invalid-' + name, pam_rc=3)
        test('ordinary-invalid-arguments-skipped', 'ordinaryuser', 0)
    finally:
        install(fragment)
    for user in ('parentaltest', 'identitytest'):
        test('recovery-approved-' + user, user, 0, True)
        test('recovery-python-denied-' + user, user, 126)
    test('recovery-ordinary', 'ordinaryuser', 0)
    result['passed'] = True
finally:
    # Try every cleanup step even if a preceding one fails; preserve failures.
    def clean(name, action):
        try:
            action()
            cleanup.append({'name': name, 'passed': True})
        except Exception as error:
            cleanup.append({'name': name, 'passed': False, 'error': str(error)})
    clean('restore-enforcing', lambda: cmd(['setenforce', '1' if initial_enforce == 'Enforcing' else '0']))
    if mapping_created:
        clean('remove-fixture-mapping', lambda: cmd(['semanage', 'login', '-d', 'identitytest']))
    if user_created:
        clean('remove-fixture-user', lambda: cmd(['userdel', 'identitytest']))
    if group_created:
        # userdel may remove its private group automatically.
        if 'identitytest' in {g.gr_name for g in grp.getgrall()}:
            clean('remove-fixture-group', lambda: cmd(['groupdel', 'identitytest']))
    clean('remove-fixture-pam', lambda: PAM.unlink(missing_ok=True))
    clean('remove-fixture-module', lambda: MODULE.unlink(missing_ok=True))
    result['original_accounts_preserved'] = before_accounts == {name: account(name) for name in before_accounts}
    result['fixture_removed'] = not (PAM.exists() or MODULE.exists() or
        'identitytest' in {p.pw_name for p in pwd.getpwall()} or
        'identityrenamed' in {p.pw_name for p in pwd.getpwall()} or
        {'identitytest', 'identitygroupchanged'} & {g.gr_name for g in grp.getgrall()})
    result['enforcing_restored'] = cmd(['getenforce']).strip() == initial_enforce
    result['passed'] = bool(result.get('passed') and all(c['passed'] for c in cleanup)
        and result['original_accounts_preserved'] and result['fixture_removed'] and result['enforcing_restored'])
    Path('/root/identity-results.json').write_text(json.dumps(result, indent=2) + '\n')
assert result['passed'], result
