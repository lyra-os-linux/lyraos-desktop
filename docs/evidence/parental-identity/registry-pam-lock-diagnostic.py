"""Disposable PAM/session-lock integration proof for registry transitions."""
import grp
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import secrets
import subprocess
import sys

assert os.geteuid() == 0
assert 'lyra.parental-selinux-test=1' in Path('/proc/cmdline').read_text().split()
assert 'lyra.parental-identity-test=1' in Path('/proc/cmdline').read_text().split()
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'

USER = GROUP = 'identitytest'
STATE_DIR = Path('/var/lib/lyra-parental-test')
REGISTRY = STATE_DIR / 'identity-registry'
MODULE = Path('/usr/lib64/security/pam_lyra_identity_registry_fixture.so')
PAM = Path('/etc/pam.d/lyra-identity-probe')
PAM_TMP = PAM.with_suffix('.new')
STORE_SOURCE = '/root/identity-registry-transaction.py'
GUARD_SOURCE = '/root/identity-pam-registry-guard.c'
PROBE = '/root/identity-pam-probe.py'
HOLDER = '/root/identity-pam-lease-holder.py'
CONTEXT = 'lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
records = []
result = {'kind': 'pam-session-lock-transaction-integration',
          'full_account_protection': False, 'checks': records}

spec_path = Path(STORE_SOURCE)
assert spec_path.is_file() and Path(GUARD_SOURCE).is_file() and Path(PROBE).is_file() and Path(HOLDER).is_file()
spec = importlib.util.spec_from_file_location('registry_transaction', spec_path)
registry_transaction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry_transaction)
Store = registry_transaction.RegistryStore


def run(args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check, timeout=60)


def assert_session(name, expected, generation, record):
    p = run(['python3', PROBE, USER, '/opt/lyra-parental-probe/probe'], check=False)
    first = json.loads(p.stdout.splitlines()[0])
    passed = ((p.returncode == 0 and first['pam_open_rc'] == 0 and
               first['selected_context'] == CONTEXT) if expected else
              (p.returncode == 70 and first['pam_open_rc'] != 0))
    item = {'name': name, 'passed': bool(passed), 'exit_code': p.returncode,
            'pam_open_rc': first['pam_open_rc'], 'expected_admission': expected,
            'generation': generation}
    records.append(item)
    print(json.dumps(item), flush=True)
    assert passed, item


def account():
    p = pwd.getpwnam(USER)
    g = grp.getgrgid(p.pw_gid)
    return {'user': p.pw_name, 'uid': p.pw_uid, 'gid': p.pw_gid,
            'group': g.gr_name}


def install_pam(identity, generation):
    prefix = ('session required pam_selinux.so close\n'
              'session required pam_selinux.so open nottys\n')
    selector = (f"session [success=1 default=ignore] pam_succeed_if.so quiet "
                f"user != {identity['user']} uid ne {identity['uid']} gid ne {identity['gid']}\n")
    binding = (f"session required pam_lyra_identity_registry_fixture.so "
               f"account=active|{identity['user']}|{identity['uid']}|{identity['gid']}|"
               f"{identity['group']}|{generation}\n")
    PAM_TMP.write_text(prefix + selector + binding)
    PAM_TMP.chmod(0o644)
    run(['restorecon', str(PAM_TMP)])
    PAM_TMP.replace(PAM)
    run(['restorecon', str(PAM)])


def check(name, passed, **detail):
    item = {'name': name, 'passed': bool(passed), **detail}
    records.append(item)
    print(json.dumps(item), flush=True)
    assert item['passed'], item


assert not MODULE.exists() and not PAM.exists() and not PAM_TMP.exists() and not STATE_DIR.exists()
assert USER not in {p.pw_name for p in pwd.getpwall()}
assert GROUP not in {g.gr_name for g in grp.getgrall()}
assert Path(PROBE).is_file()
initial_enforce = run(['getenforce']).stdout.strip()
assert initial_enforce in ('Enforcing', 'Permissive')
uid = next(i for i in range(24000, 25000) if i not in {p.pw_uid for p in pwd.getpwall()})
gid = next(i for i in range(25000, 26000) if i not in {g.gr_gid for g in grp.getgrall()})
gen_a, gen_b = secrets.token_hex(16), secrets.token_hex(16)
module_created = group_created = user_created = mapping_created = pam_created = state_created = False
holder = None

try:
    run(['gcc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror', '-O2', GUARD_SOURCE,
         '-o', str(MODULE), '-lpam', '-lselinux'])
    MODULE.chmod(0o755)
    run(['restorecon', str(MODULE)])
    module_created = True
    run(['groupadd', '-g', str(gid), GROUP]); group_created = True
    run(['useradd', '-M', '-u', str(uid), '-g', str(gid), '-s', '/bin/bash', USER]); user_created = True
    run(['semanage', 'login', '-a', '-s', 'lyra_parental_u', '-r', 's0', USER]); mapping_created = True
    identity_a = account()
    STATE_DIR.mkdir(mode=0o700)
    run(['restorecon', str(STATE_DIR)])
    state_created = True
    store = Store(STATE_DIR)
    store.seed([{'state': 'active', **identity_a, 'generation': gen_a}])
    install_pam(identity_a, gen_a); pam_created = True
    run(['setenforce', '1'])
    result['module_sha256'] = hashlib.sha256(MODULE.read_bytes()).hexdigest()
    result['guard_source_sha256'] = hashlib.sha256(Path(GUARD_SOURCE).read_bytes()).hexdigest()
    result['store_source_sha256'] = hashlib.sha256(spec_path.read_bytes()).hexdigest()

    assert_session('active-session-admitted', True, gen_a, identity_a)
    holder = subprocess.Popen(['python3', HOLDER], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    opened_line = holder.stdout.readline()
    opened = json.loads(opened_line)
    check('lease-holder-opened-session', opened.get('event') == 'opened' and opened.get('pam_open_rc') == 0,
          event=opened)

    busy = False
    try:
        store.begin(gen_a)
    except registry_transaction.StoreError as error:
        busy = 'busy:' in str(error)
        busy_message = str(error)
    rows, journal = store.snapshot()
    check('transition-refused-while-session-live', busy and journal is None and
          next(r for r in rows if r['generation'] == gen_a)['state'] == 'active',
          error=busy_message if busy else 'exclusive lock unexpectedly acquired')

    holder.stdin.write('release\n'); holder.stdin.flush()
    closed_line = holder.stdout.readline()
    closed = json.loads(closed_line)
    holder.wait(timeout=20)
    holder = None
    check('pam-close-releases-session-lease', closed.get('event') == 'closed' and
          closed.get('pam_close_rc') == 0, event=closed)

    store.begin(gen_a)
    rows, journal = store.snapshot()
    check('transition-starts-after-session-close', journal is not None and
          journal['phase'] == 'blocked' and
          next(r for r in rows if r['generation'] == gen_a)['state'] == 'transitioning')
    assert_session('new-session-denied-during-transition', False, gen_a, identity_a)

    store.tombstone(gen_a)
    run(['semanage', 'login', '-d', USER]); mapping_created = False
    run(['userdel', USER]); user_created = False
    if GROUP in {g.gr_name for g in grp.getgrall()}:
        run(['groupdel', GROUP])
    group_created = False
    run(['groupadd', '-g', str(gid), GROUP]); group_created = True
    run(['useradd', '-M', '-u', str(uid), '-g', str(gid), '-s', '/bin/bash', USER]); user_created = True
    run(['semanage', 'login', '-a', '-s', 'lyra_parental_u', '-r', 's0', USER]); mapping_created = True
    identity_b = account()
    check('same-unix-tuple-recreated', identity_b == identity_a,
          uid=identity_b['uid'], gid=identity_b['gid'])
    assert_session('tombstoned-old-generation-denied', False, gen_a, identity_b)

    store.publish(gen_a, {'state': 'active', **identity_b, 'generation': gen_b})
    install_pam(identity_b, gen_b)
    assert_session('new-generation-admitted-after-explicit-enrollment', True, gen_b, identity_b)
    result['passed'] = True
finally:
    if holder is not None:
        try:
            holder.stdin.write('release\n'); holder.stdin.flush()
            holder.wait(timeout=10)
        except Exception:
            holder.kill(); holder.wait(timeout=5)
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
        clean('remove-state-directory', lambda: [p.unlink(missing_ok=True) for p in STATE_DIR.iterdir()] and STATE_DIR.rmdir())
    result['cleanup'] = cleanup
    result['fixtures_removed'] = (not MODULE.exists() and not PAM.exists() and not STATE_DIR.exists() and
                                  USER not in {p.pw_name for p in pwd.getpwall()} and
                                  GROUP not in {g.gr_name for g in grp.getgrall()})
    result['selinux_mode_restored'] = run(['getenforce']).stdout.strip() == initial_enforce
    result['passed'] = bool(result.get('passed') and all(x['passed'] for x in cleanup) and
                            result['fixtures_removed'] and result['selinux_mode_restored'])
    Path('/root/identity-registry-pam-lock-result.json').write_text(json.dumps(result, indent=2) + '\n')

assert result['passed'], result
