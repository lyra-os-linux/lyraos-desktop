"""Hold one experimental PAM session to exercise transaction exclusion."""
import ctypes
import json
import os
from pathlib import Path
import sys

assert os.geteuid() == 0
assert 'lyra.parental-selinux-test=1' in Path('/proc/cmdline').read_text().split()
assert 'lyra.parental-identity-test=1' in Path('/proc/cmdline').read_text().split()
assert Path('/sys/block/vda/serial').read_text().strip() == 'lyra-admission-test'
user = 'identitytest'
pam = ctypes.CDLL('libpam.so.0')
P = ctypes.c_void_p
I = ctypes.c_int
CALLBACK = ctypes.CFUNCTYPE(I, I, P, P, P)


@CALLBACK
def reject_conversation(n, msg, resp, data):
    return 19


class Conv(ctypes.Structure):
    _fields_ = [('conv', CALLBACK), ('data', P)]


conv = Conv(reject_conversation, None)
handle = P()
pam.pam_start.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(Conv), ctypes.POINTER(P)]
for name in ('pam_open_session', 'pam_close_session', 'pam_end'):
    getattr(pam, name).argtypes = [P, I]
    getattr(pam, name).restype = I
rc = pam.pam_start(b'lyra-identity-probe', user.encode(), ctypes.byref(conv), ctypes.byref(handle))
assert rc == 0, rc
opened = False
try:
    rc = pam.pam_open_session(handle, 0)
    print(json.dumps({'event': 'opened', 'pam_open_rc': rc}), flush=True)
    if rc:
        sys.exit(70)
    opened = True
    if sys.stdin.readline().strip() != 'release':
        sys.exit(71)
finally:
    if opened:
        print(json.dumps({'event': 'closed', 'pam_close_rc': pam.pam_close_session(handle, 0)}), flush=True)
    pam.pam_end(handle, rc)
