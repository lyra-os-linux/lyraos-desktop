"""VM-only diagnostic: show that tuple-only bindings survive account reuse.

This intentionally characterizes a known design gap; it is not a security
test that should pass in a future lifecycle implementation. Run only on the
disposable, marked Lyra parental test disk as root.
"""
import grp
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import subprocess

assert os.geteuid() == 0
assert 'lyra.parental-selinux-test=1' in Path('/proc/cmdline').read_text().split()
assert 'lyra.parental-identity-test=1' in Path('/proc/cmdline').read_text().split()
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'

spec = importlib.util.spec_from_file_location('bindings', '/root/identity-bindings.py')
bindings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bindings)
MODULE = Path('/usr/lib64/security/pam_lyra_identity_fixture.so')
PAM = Path('/etc/pam.d/lyra-identity-probe')
USER = 'identitytest'
GROUP = 'identitytest'
CONTEXT = 'lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
PROBE = '/opt/lyra-parental-probe/probe'
PAM_PROBE = '/root/identity-pam-probe.py'
records = []
result = {'kind': 'tuple-binding-reuse-gap-diagnostic',
          'full_account_protection': False, 'observations': records}


def run(args):
    return subprocess.run(args, capture_output=True, text=True, check=True,
                          timeout=60).stdout


def ids():
    p = pwd.getpwnam(USER)
    g = grp.getgrgid(p.pw_gid)
    return {'user': p.pw_name, 'uid': p.pw_uid,
            'gid': p.pw_gid, 'group': g.gr_name}


def install_pam(account):
    fragment = bindings.render([account])
    content = ('session required pam_selinux.so close\n'
               'session required pam_selinux.so open nottys\n' + fragment)
    tmp = PAM.with_suffix('.new')
    tmp.write_text(content)
    tmp.chmod(0o644)
    run(['restorecon', str(tmp)])
    tmp.replace(PAM)
    run(['restorecon', str(PAM)])


def check_probe(label):
    p = subprocess.run(['python3', PAM_PROBE, USER, PROBE],
                       capture_output=True, text=True, timeout=30)
    first = json.loads(p.stdout.splitlines()[0])
    row = {'label': label, 'rc': p.returncode, 'pam': first,
           'stdout': p.stdout, 'stderr': p.stderr}
    records.append(row)
    print(json.dumps(row), flush=True)
    assert p.returncode == 0 and first['pam_open_rc'] == 0, row
    assert first['selected_context'] == CONTEXT, row
    assert f"uid={pwd.getpwnam(USER).pw_uid} context={CONTEXT}" in p.stdout, row
    return first


def remove_group_if_present():
    if GROUP in {g.gr_name for g in grp.getgrall()}:
        run(['groupdel', GROUP])


assert not MODULE.exists() and not PAM.exists() and not PAM.with_suffix('.new').exists()
assert USER not in {p.pw_name for p in pwd.getpwall()}
assert GROUP not in {g.gr_name for g in grp.getgrall()}
assert Path(PAM_PROBE).is_file() and Path(PROBE).is_file()
initial_enforce = run(['getenforce']).strip()
assert initial_enforce in ('Enforcing', 'Permissive')
used_uids = {p.pw_uid for p in pwd.getpwall()}
used_gids = {g.gr_gid for g in grp.getgrall()}
uid = next(i for i in range(24000, 25000) if i not in used_uids)
gid = next(i for i in range(25000, 26000) if i not in used_gids)
mapping_created = group_created = user_created = module_created = pam_created = False

try:
    run(['gcc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror', '-O2',
         '/root/identity-pam-guard.c', '-o', str(MODULE), '-lpam', '-lselinux'])
    MODULE.chmod(0o755)
    run(['restorecon', str(MODULE)])
    module_created = True
    run(['groupadd', '-g', str(gid), GROUP]); group_created = True
    run(['useradd', '-M', '-u', str(uid), '-g', str(gid), '-s', '/bin/bash', USER]); user_created = True
    run(['semanage', 'login', '-a', '-s', 'lyra_parental_u', '-r', 's0', USER]); mapping_created = True
    original = ids()
    install_pam(original); pam_created = True
    run(['setenforce', '1'])
    first_context = check_probe('original-provisioned-account')

    # Delete and recreate a distinct account record with the exact same
    # attributes. No supervised user process remains from check_probe().
    run(['semanage', 'login', '-d', USER]); mapping_created = False
    run(['userdel', USER]); user_created = False
    remove_group_if_present(); group_created = False
    run(['groupadd', '-g', str(gid), GROUP]); group_created = True
    run(['useradd', '-M', '-u', str(uid), '-g', str(gid), '-s', '/bin/bash', USER]); user_created = True
    run(['semanage', 'login', '-a', '-s', 'lyra_parental_u', '-r', 's0', USER]); mapping_created = True
    recreated = ids()
    assert recreated == original, {'original': original, 'recreated': recreated}
    second_context = check_probe('recreated-account-identical-name-uid-gid-group')

    result.update({'passed': True,
                   'finding': 'REPRODUCED: tuple-only PAM binding admits a newly created account when name/UID/GID/group are reused',
                   'original_identity': original,
                   'recreated_identity': recreated,
                   'same_context_after_recreation': second_context == first_context,
                   'stale_binding_reused': True,
                   'module_sha256': hashlib.sha256(MODULE.read_bytes()).hexdigest()})
    assert result['same_context_after_recreation'] and result['stale_binding_reused']
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
        clean('delete-fixture-group', remove_group_if_present)
    if pam_created:
        clean('remove-pam-stack', lambda: PAM.unlink(missing_ok=True))
    if module_created:
        clean('remove-pam-module', lambda: MODULE.unlink(missing_ok=True))
    result['cleanup'] = cleanup
    result['fixtures_removed'] = (not PAM.exists() and not MODULE.exists()
                                  and USER not in {p.pw_name for p in pwd.getpwall()}
                                  and GROUP not in {g.gr_name for g in grp.getgrall()})
    result['selinux_mode_restored'] = run(['getenforce']).strip() == initial_enforce
    result['passed'] = bool(result.get('passed') and all(c['passed'] for c in cleanup)
                            and result['fixtures_removed'] and result['selinux_mode_restored'])
    Path('/root/identity-reuse-result.json').write_text(json.dumps(result, indent=2) + '\n')

assert result['passed'], result
