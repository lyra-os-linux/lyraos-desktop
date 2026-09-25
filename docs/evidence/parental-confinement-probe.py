import json, pathlib, subprocess

assert 'lyra.virtualization-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
# The restriction is applied only in a fictitious user's short-lived child.
child = r'''
import ctypes, errno, json, os, pathlib, platform, shutil, subprocess, sys, tempfile
assert platform.machine() == 'x86_64'
libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long
abi = libc.syscall(444, 0, 0, 1)
result = {'abi': abi, 'uid': os.getuid(), 'kernel': platform.release(), 'checks': []}
if abi < 1:
    result.update(supported=False, errno=ctypes.get_errno())
    print(json.dumps(result)); sys.exit(0)
class Ruleset(ctypes.Structure):
    _fields_ = [('handled_access_fs', ctypes.c_uint64)]
class PathRule(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('allowed_access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]
def require(value):
    if value < 0: raise OSError(ctypes.get_errno(), os.strerror(ctypes.get_errno()))
    return value
with tempfile.TemporaryDirectory(prefix='lyra-landlock-') as temporary:
    copied = temporary + '/copied-true'
    shutil.copy2('/usr/bin/true', copied)
    attr = Ruleset(1) # LANDLOCK_ACCESS_FS_EXECUTE only: deliberately incomplete.
    fd = require(libc.syscall(444, ctypes.byref(attr), ctypes.sizeof(attr), 0))
    approved = ['/usr/bin/true', os.path.realpath(sys.executable),
                os.path.realpath('/lib64/ld-linux-x86-64.so.2')]
    for path in approved:
        target = os.open(path, os.O_PATH | os.O_CLOEXEC)
        try:
            rule = PathRule(1, target)
            require(libc.syscall(445, fd, 1, ctypes.byref(rule), 0))
        finally: os.close(target)
    require(libc.prctl(38, 1, 0, 0, 0)) # PR_SET_NO_NEW_PRIVS
    require(libc.syscall(446, fd, 0)); os.close(fd)
    cases = [('approved', ['/usr/bin/true'], False),
             ('unapproved', ['/usr/bin/false'], True),
             ('copied-approved', [copied], True),
             ('approved-loader-copied-executable',
              [os.path.realpath('/lib64/ld-linux-x86-64.so.2'), copied], False),
             ('approved-interpreter-arbitrary-code',
              [sys.executable, '-c', 'print("ARBITRARY_CODE_EXECUTED")'], False)]
    for name, argv, denied in cases:
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=10)
            row = {'name': name, 'rc': p.returncode, 'stdout': p.stdout, 'denied': False}
        except PermissionError as e:
            row = {'name': name, 'errno': e.errno, 'denied': e.errno == errno.EACCES}
        assert row['denied'] == denied, row
        if not denied: assert row['rc'] == 0, row
        result['checks'].append(row)
    result.update(supported=True, approved_paths=approved, full_account_protection=False)
print(json.dumps(result))
'''
p = subprocess.run(['runuser', '-u', 'parentaltest', '--', 'python3', '-c', child],
                   capture_output=True, text=True, timeout=30)
assert p.returncode == 0, (p.stdout, p.stderr)
result = json.loads(p.stdout)
pathlib.Path('/tmp/parental-confinement.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
